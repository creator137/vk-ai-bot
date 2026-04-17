from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.payments.robokassa import RobokassaSignatureBuilder
from app.payments.service import (
    PaymentConfirmationResult,
    PaymentInitResult,
    SubscriptionPaymentService,
)


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
    if (
        settings.robokassa_merchant_login
        and settings.robokassa_password1
        and settings.robokassa_password2
    ):
        robokassa = RobokassaSignatureBuilder(
            merchant_login=settings.robokassa_merchant_login,
            password1=settings.robokassa_password1,
            password2=settings.robokassa_password2,
            hash_algorithm=settings.robokassa_hash_algorithm,
            test_mode=settings.robokassa_test_mode,
        )

    return SubscriptionPaymentService(
        session=session,
        robokassa=robokassa,
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
