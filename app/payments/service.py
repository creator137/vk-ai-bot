from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from app.payments.models import SubscriptionPayment
from app.payments.repository import SubscriptionPaymentRepository
from app.payments.robokassa import (
    RobokassaError,
    RobokassaPaymentLink,
    RobokassaSignatureBuilder,
    normalize_out_sum,
)
from app.subscriptions.catalog import get_subscription_plan
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PaymentInitResult:
    payment_id: int
    vk_user_id: int
    user_id: int
    plan_code: str
    amount_rub: int
    payment_url: str
    is_test: bool


@dataclass(frozen=True, slots=True)
class PaymentConfirmationResult:
    payment_id: int
    user_id: int
    plan_code: str
    status: str


@dataclass(frozen=True, slots=True)
class PaymentCheckoutPage:
    payment_id: int
    payment_url: str
    gateway_url: str
    form_fields: dict[str, str]


class SubscriptionPaymentService:
    def __init__(
        self,
        *,
        session: Session,
        payment_repository: SubscriptionPaymentRepository | None = None,
        user_service: UserService | None = None,
        subscription_service: SubscriptionService | None = None,
        notify_payment_activated: Callable[..., None] | None = None,
        robokassa: RobokassaSignatureBuilder | None = None,
        robokassa_fallbacks: list[RobokassaSignatureBuilder] | None = None,
        app_base_url: str | None = None,
        receipt_sno: str | None = None,
        receipt_tax: str = "none",
        receipt_payment_method: str = "full_prepayment",
        receipt_payment_object: str = "service",
    ) -> None:
        self._session = session
        self._payment_repository = payment_repository or SubscriptionPaymentRepository(session)
        self._user_service = user_service or UserService(session=session)
        self._subscription_service = subscription_service or SubscriptionService(session=session)
        self._notify_payment_activated = notify_payment_activated
        self._robokassa = robokassa
        self._robokassa_fallbacks = robokassa_fallbacks or []
        self._app_base_url = app_base_url.rstrip("/") if app_base_url else None
        self._receipt_sno = receipt_sno
        self._receipt_tax = receipt_tax
        self._receipt_payment_method = receipt_payment_method
        self._receipt_payment_object = receipt_payment_object

    def create_for_vk_user_id(
        self,
        *,
        vk_user_id: int,
        plan_code: str,
    ) -> PaymentInitResult:
        if self._robokassa is None:
            raise RobokassaError("Robokassa is not configured")

        user = self._user_service.find_or_create_by_vk_user_id(vk_user_id)
        plan = get_subscription_plan(plan_code)
        payment = self._payment_repository.create(
            user_id=user.id,
            plan_code=plan.code,
            amount_rub=plan.price_rub,
        )
        link = self._build_payment_link_for_payment(payment)
        self._session.commit()
        self._session.refresh(payment)
        logger.info(
            (
                "Robokassa payment initialized: payment_id=%s user_id=%s "
                "vk_user_id=%s plan_code=%s amount_rub=%s test_mode=%s"
            ),
            payment.id,
            payment.user_id,
            user.vk_user_id,
            payment.plan_code,
            payment.amount_rub,
            self._robokassa.test_mode,
        )
        return _build_init_result(
            payment=payment,
            vk_user_id=user.vk_user_id,
            payment_link=link,
            hosted_payment_url=self._build_hosted_payment_url(payment.id) or link.payment_url,
            is_test=self._robokassa.test_mode,
        )

    def build_checkout_page(self, *, payment_id: int) -> PaymentCheckoutPage:
        if self._robokassa is None:
            raise RobokassaError("Robokassa is not configured")

        payment = self._require_payment(payment_id)
        if payment.status == "paid":
            raise RobokassaError(f"Payment is already paid: {payment_id}")

        link = self._build_payment_link_for_payment(payment)
        return PaymentCheckoutPage(
            payment_id=payment.id,
            payment_url=link.payment_url,
            gateway_url="https://auth.robokassa.ru/Merchant/Index.aspx",
            form_fields=link.payload,
        )

    def confirm_result(
        self,
        *,
        invoice_id: int,
        out_sum: str,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> PaymentConfirmationResult:
        if self._robokassa is None:
            raise RobokassaError("Robokassa is not configured")

        payment = self._require_payment(invoice_id)
        self._validate_payment_details(
            payment=payment,
            out_sum=out_sum,
            shp_params=shp_params,
        )
        matched_result_builder = self._find_matching_result_builder(
            out_sum=normalize_out_sum(out_sum),
            invoice_id=invoice_id,
            signature_value=signature_value,
            shp_params=shp_params,
        )
        if matched_result_builder is None:
            raise RobokassaError("Invalid Robokassa result signature")
        if matched_result_builder is not self._robokassa:
            logger.warning(
                "Robokassa result signature accepted by fallback verifier: payment_id=%s user_id=%s",
                payment.id,
                payment.user_id,
            )

        if payment.status != "paid":
            self._activate_paid_payment(payment)
            logger.info(
                "Robokassa payment confirmed and subscription activated: payment_id=%s user_id=%s plan_code=%s",
                payment.id,
                payment.user_id,
                payment.plan_code,
            )
        else:
            logger.info(
                "Robokassa payment confirmation accepted for already paid invoice: payment_id=%s user_id=%s",
                payment.id,
                payment.user_id,
            )

        return _build_confirmation_result(payment)

    def validate_success_redirect(
        self,
        *,
        invoice_id: int,
        out_sum: str,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> PaymentConfirmationResult:
        if self._robokassa is None:
            raise RobokassaError("Robokassa is not configured")

        payment = self._require_payment(invoice_id)
        self._validate_payment_details(
            payment=payment,
            out_sum=out_sum,
            shp_params=shp_params,
        )
        matched_success_builder = self._find_matching_success_builder(
            out_sum=normalize_out_sum(out_sum),
            invoice_id=invoice_id,
            signature_value=signature_value,
            shp_params=shp_params,
        )
        if matched_success_builder is None:
            raise RobokassaError("Invalid Robokassa success signature")
        if matched_success_builder is not self._robokassa:
            logger.warning(
                "Robokassa success signature accepted by fallback verifier: payment_id=%s user_id=%s",
                payment.id,
                payment.user_id,
            )
        if payment.status != "paid":
            self._activate_paid_payment(payment)
            logger.warning(
                "Robokassa payment activated via success redirect fallback: payment_id=%s user_id=%s plan_code=%s",
                payment.id,
                payment.user_id,
                payment.plan_code,
            )

        logger.info(
            "Robokassa success redirect validated: payment_id=%s user_id=%s status=%s",
            payment.id,
            payment.user_id,
            payment.status,
        )
        return _build_confirmation_result(payment)

    def get_by_id(self, payment_id: int) -> SubscriptionPayment | None:
        return self._payment_repository.get_by_id(payment_id)

    def _require_payment(self, invoice_id: int) -> SubscriptionPayment:
        payment = self._payment_repository.get_by_id(invoice_id)
        if payment is None:
            raise RobokassaError(f"Payment not found: {invoice_id}")
        return payment

    def _validate_payment_details(
        self,
        *,
        payment: SubscriptionPayment,
        out_sum: str,
        shp_params: dict[str, str],
    ) -> None:
        normalized_sum = normalize_out_sum(out_sum)
        expected_sum = normalize_out_sum(str(payment.amount_rub))
        if normalized_sum != expected_sum:
            raise RobokassaError("Robokassa OutSum does not match payment amount")

        shp_user = shp_params.get("Shp_user")
        shp_plan = shp_params.get("Shp_plan")
        if shp_user != str(payment.user_id):
            raise RobokassaError("Robokassa user parameter does not match payment")
        if shp_plan != payment.plan_code:
            raise RobokassaError("Robokassa plan parameter does not match payment")

    def _build_callback_url(self, path: str) -> str | None:
        if not self._app_base_url:
            return None
        return f"{self._app_base_url}{path}"

    def _build_hosted_payment_url(self, payment_id: int) -> str | None:
        return self._build_callback_url(f"/payments/robokassa/start/{payment_id}")

    def _build_payment_link_for_payment(
        self,
        payment: SubscriptionPayment,
    ) -> RobokassaPaymentLink:
        if self._robokassa is None:
            raise RobokassaError("Robokassa is not configured")

        plan = get_subscription_plan(payment.plan_code)
        return self._robokassa.build_payment_link(
            amount_rub=payment.amount_rub,
            invoice_id=payment.id,
            description=f"Подписка {plan.title} для VK",
            shp_params={
                "Shp_user": str(payment.user_id),
                "Shp_plan": plan.code,
            },
            receipt=self._build_receipt_for_payment(payment),
            result_url=self._build_callback_url("/payments/robokassa/result"),
            success_url=self._build_callback_url("/payments/robokassa/success"),
            fail_url=self._build_callback_url("/payments/robokassa/fail"),
        )

    def _build_receipt_for_payment(self, payment: SubscriptionPayment) -> dict[str, object]:
        plan = get_subscription_plan(payment.plan_code)
        receipt: dict[str, object] = {
            "items": [
                {
                    "name": f"Подписка {plan.title}",
                    "quantity": 1,
                    "sum": payment.amount_rub,
                    "payment_method": self._receipt_payment_method,
                    "payment_object": self._receipt_payment_object,
                    "tax": self._receipt_tax,
                }
            ]
        }
        if self._receipt_sno:
            receipt["sno"] = self._receipt_sno
        return receipt

    def _activate_paid_payment(self, payment: SubscriptionPayment) -> None:
        self._subscription_service.issue_for_user_id(
            user_id=payment.user_id,
            plan_code=payment.plan_code,
        )
        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(payment)
        if self._notify_payment_activated is None:
            return
        try:
            self._notify_payment_activated(
                user_id=payment.user_id,
                plan_code=payment.plan_code,
            )
        except Exception as error:
            logger.warning(
                "Payment activation notification failed: payment_id=%s user_id=%s error=%s",
                payment.id,
                payment.user_id,
                str(error),
            )

    def _find_matching_result_builder(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> RobokassaSignatureBuilder | None:
        for builder in self._iter_signature_builders():
            if builder.verify_result_signature(
                out_sum=out_sum,
                invoice_id=invoice_id,
                signature_value=signature_value,
                shp_params=shp_params,
            ):
                return builder
        return None

    def _find_matching_success_builder(
        self,
        *,
        out_sum: str,
        invoice_id: int,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> RobokassaSignatureBuilder | None:
        for builder in self._iter_signature_builders():
            if builder.verify_success_signature(
                out_sum=out_sum,
                invoice_id=invoice_id,
                signature_value=signature_value,
                shp_params=shp_params,
            ):
                return builder
        return None

    def _iter_signature_builders(self) -> list[RobokassaSignatureBuilder]:
        builders: list[RobokassaSignatureBuilder] = []
        if self._robokassa is not None:
            builders.append(self._robokassa)
        builders.extend(self._robokassa_fallbacks)
        return builders


def _build_init_result(
    *,
    payment: SubscriptionPayment,
    vk_user_id: int,
    payment_link: RobokassaPaymentLink,
    hosted_payment_url: str,
    is_test: bool,
) -> PaymentInitResult:
    return PaymentInitResult(
        payment_id=payment.id,
        vk_user_id=vk_user_id,
        user_id=payment.user_id,
        plan_code=payment.plan_code,
        amount_rub=payment.amount_rub,
        payment_url=hosted_payment_url,
        is_test=is_test,
    )


def _build_confirmation_result(payment: SubscriptionPayment) -> PaymentConfirmationResult:
    return PaymentConfirmationResult(
        payment_id=payment.id,
        user_id=payment.user_id,
        plan_code=payment.plan_code,
        status=payment.status,
    )
