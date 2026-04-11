from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.access_grants import (
    AccessGrantIssue,
    build_access_grant_issuance_handler,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db_session

router = APIRouter(prefix="/internal/access-grants", tags=["internal-access"])


class AccessGrantIssueRequest(BaseModel):
    vk_user_id: int = Field(gt=0)


class AccessGrantIssueResponse(BaseModel):
    vk_user_id: int
    user_id: int
    grant_created: bool


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
    response_model=AccessGrantIssueResponse,
    dependencies=[Depends(require_internal_access_token)],
)
def issue_access_grant(
    payload: AccessGrantIssueRequest,
    session: Session = Depends(get_db_session),
) -> AccessGrantIssueResponse:
    handler = build_access_grant_issuance_handler(session)
    issued = handler.issue_for_vk_user_id(payload.vk_user_id)
    return _build_response(issued)


def _build_response(issued: AccessGrantIssue) -> AccessGrantIssueResponse:
    return AccessGrantIssueResponse(
        vk_user_id=issued.vk_user_id,
        user_id=issued.user_id,
        grant_created=issued.grant_created,
    )
