from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.payments import build_robokassa_payment_init_handler
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.payments.robokassa import RobokassaError

router = APIRouter(prefix="/internal/payments/robokassa", tags=["internal-payments"])


class RobokassaPaymentInitRequest(BaseModel):
    vk_user_id: int = Field(gt=0)
    plan_code: Literal["lite", "pro", "max"]


class RobokassaPaymentInitResponse(BaseModel):
    payment_id: int
    vk_user_id: int
    user_id: int
    plan_code: str
    amount_rub: int
    payment_url: str
    is_test: bool


def require_internal_access_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.internal_access_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal access token is not configured",
        )

    if x_internal_token != settings.internal_access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal access token",
        )


@router.post(
    "",
    response_model=RobokassaPaymentInitResponse,
    dependencies=[Depends(require_internal_access_token)],
)
def create_robokassa_payment(
    payload: RobokassaPaymentInitRequest,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RobokassaPaymentInitResponse:
    handler = build_robokassa_payment_init_handler(session, settings)
    try:
        created = handler.create_for_vk_user_id(
            vk_user_id=payload.vk_user_id,
            plan_code=payload.plan_code,
        )
    except RobokassaError as error:
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "not configured" in str(error).casefold()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return RobokassaPaymentInitResponse(
        payment_id=created.payment_id,
        vk_user_id=created.vk_user_id,
        user_id=created.user_id,
        plan_code=created.plan_code,
        amount_rub=created.amount_rub,
        payment_url=created.payment_url,
        is_test=created.is_test,
    )
