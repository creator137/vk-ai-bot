from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.subscriptions import (
    SubscriptionIssueResult,
    build_subscription_issuance_handler,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db_session

router = APIRouter(prefix="/internal/subscriptions", tags=["internal-subscriptions"])


class SubscriptionIssueRequest(BaseModel):
    vk_user_id: int = Field(gt=0)
    plan_code: Literal["lite", "pro", "max"]


class SubscriptionIssueResponse(BaseModel):
    vk_user_id: int
    user_id: int
    plan_code: str
    included_tokens: int
    used_tokens: int


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
    response_model=SubscriptionIssueResponse,
    dependencies=[Depends(require_internal_access_token)],
)
def issue_subscription(
    payload: SubscriptionIssueRequest,
    session: Session = Depends(get_db_session),
) -> SubscriptionIssueResponse:
    handler = build_subscription_issuance_handler(session)
    issued = handler.issue_for_vk_user_id(
        vk_user_id=payload.vk_user_id,
        plan_code=payload.plan_code,
    )
    return _build_response(issued)


def _build_response(issued: SubscriptionIssueResult) -> SubscriptionIssueResponse:
    return SubscriptionIssueResponse(
        vk_user_id=issued.vk_user_id,
        user_id=issued.user_id,
        plan_code=issued.plan_code,
        included_tokens=issued.included_tokens,
        used_tokens=issued.used_tokens,
    )
