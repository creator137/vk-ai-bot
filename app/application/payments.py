from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.payments.robokassa import RobokassaSignatureBuilder
from app.payments.service import (
    PaymentCheckoutPage,
    PaymentConfirmationResult,
    PaymentInitResult,
    SubscriptionPaymentService,
)
from app.subscriptions.catalog import get_subscription_plan
from app.users.service import UserService
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.vk_transport.vk_api import VkMessagesApi


@dataclass(frozen=True, slots=True)
class RobokassaPaymentInitResult:
    payment_id: int
    vk_user_id: int
    user_id: int
    plan_code: str
    amount_rub: int
    payment_url: str
    is_test: bool


class RobokassaPaymentInitHandler:
    def __init__(self, service: SubscriptionPaymentService) -> None:
        self._service = service

    def create_for_vk_user_id(
        self,
        *,
        vk_user_id: int,
        plan_code: str,
    ) -> RobokassaPaymentInitResult:
        result = self._service.create_for_vk_user_id(
            vk_user_id=vk_user_id,
            plan_code=plan_code,
        )
        return _build_init_result(result)

    def build_checkout_page(self, *, payment_id: int) -> PaymentCheckoutPage:
        return self._service.build_checkout_page(payment_id=payment_id)


class RobokassaCallbackHandler:
    def __init__(self, service: SubscriptionPaymentService) -> None:
        self._service = service

    def confirm_result(
        self,
        *,
        invoice_id: int,
        out_sum: str,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> PaymentConfirmationResult:
        return self._service.confirm_result(
            invoice_id=invoice_id,
            out_sum=out_sum,
            signature_value=signature_value,
            shp_params=shp_params,
        )

    def validate_success_redirect(
        self,
        *,
        invoice_id: int,
        out_sum: str,
        signature_value: str,
        shp_params: dict[str, str],
    ) -> PaymentConfirmationResult:
        return self._service.validate_success_redirect(
            invoice_id=invoice_id,
            out_sum=out_sum,
            signature_value=signature_value,
            shp_params=shp_params,
        )

    def get_payment_status(
        self,
        *,
        payment_id: int,
    ) -> str | None:
        payment = self._service.get_by_id(payment_id)
        if payment is None:
            return None
        return payment.status


def build_robokassa_payment_init_handler(
    session: Session,
    settings: Settings,
) -> RobokassaPaymentInitHandler:
    return RobokassaPaymentInitHandler(
        _build_subscription_payment_service(session=session, settings=settings)
    )


def build_robokassa_callback_handler(
    session: Session,
    settings: Settings,
) -> RobokassaCallbackHandler:
    return RobokassaCallbackHandler(
        _build_subscription_payment_service(session=session, settings=settings)
    )


def _build_subscription_payment_service(
    *,
    session: Session,
    settings: Settings,
) -> SubscriptionPaymentService:
    robokassa = None
    robokassa_fallbacks: list[RobokassaSignatureBuilder] = []
    password1 = settings.robokassa_password1
    password2 = settings.robokassa_password2
    if settings.robokassa_test_mode:
        password1 = settings.robokassa_password1_test or password1
        password2 = settings.robokassa_password2_test or password2

    if (
        settings.robokassa_merchant_login
        and password1
        and password2
    ):
        robokassa = RobokassaSignatureBuilder(
            merchant_login=settings.robokassa_merchant_login,
            password1=password1,
            password2=password2,
            hash_algorithm=settings.robokassa_hash_algorithm,
            test_mode=settings.robokassa_test_mode,
        )
        if settings.robokassa_test_mode:
            fallback_password1 = settings.robokassa_password1
            fallback_password2 = settings.robokassa_password2
            if (
                fallback_password1
                and fallback_password2
                and (fallback_password1 != password1 or fallback_password2 != password2)
            ):
                robokassa_fallbacks.append(
                    RobokassaSignatureBuilder(
                        merchant_login=settings.robokassa_merchant_login,
                        password1=fallback_password1,
                        password2=fallback_password2,
                        hash_algorithm=settings.robokassa_hash_algorithm,
                        test_mode=settings.robokassa_test_mode,
                    )
                )

    return SubscriptionPaymentService(
        session=session,
        notify_payment_activated=_build_payment_activation_notifier(session=session, settings=settings),
        robokassa=robokassa,
        robokassa_fallbacks=robokassa_fallbacks,
        app_base_url=settings.app_base_url,
    )


def _build_init_result(result: PaymentInitResult) -> RobokassaPaymentInitResult:
    return RobokassaPaymentInitResult(
        payment_id=result.payment_id,
        vk_user_id=result.vk_user_id,
        user_id=result.user_id,
        plan_code=result.plan_code,
        amount_rub=result.amount_rub,
        payment_url=result.payment_url,
        is_test=result.is_test,
    )


def _build_payment_activation_notifier(
    *,
    session: Session,
    settings: Settings,
):
    if not settings.vk_outbound_token:
        return None

    messages_api = VkMessagesApi(
        token=settings.vk_outbound_token,
        api_version=settings.vk_api_version,
    )
    user_service = UserService(session=session)

    def notify(*, user_id: int, plan_code: str) -> None:
        user = user_service.get_by_id(user_id)
        if user is None:
            return
        plan = get_subscription_plan(plan_code)
        messages_api.send_text_message(
            peer_id=user.vk_user_id,
            text=(
                "Оплата прошла успешно.\n"
                f"Тариф {plan.title} активирован.\n"
                f"Начислено: {plan.included_tokens:,} токенов.".replace(",", " ")
            ),
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    return notify
