from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.application.payments import build_robokassa_callback_handler
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.payments.robokassa import RobokassaError

router = APIRouter(prefix="/payments/robokassa", tags=["robokassa"])


@router.api_route("/result", methods=["GET", "POST"], response_class=PlainTextResponse)
async def robokassa_result(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    payload = await _extract_request_payload(request)
    invoice_id = _require_int(payload, "InvId")
    out_sum = _require_string(payload, "OutSum")
    signature_value = _require_string(payload, "SignatureValue")
    shp_params = _extract_shp_params(payload)

    handler = build_robokassa_callback_handler(session, settings)
    try:
        handler.confirm_result(
            invoice_id=invoice_id,
            out_sum=out_sum,
            signature_value=signature_value,
            shp_params=shp_params,
        )
    except RobokassaError as error:
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "not configured" in str(error).casefold()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(error),
        ) from error

    return PlainTextResponse(f"OK{invoice_id}")


@router.api_route("/success", methods=["GET", "POST"], response_class=PlainTextResponse)
async def robokassa_success(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    payload = await _extract_request_payload(request)
    invoice_id = _require_int(payload, "InvId")
    out_sum = _require_string(payload, "OutSum")
    signature_value = _require_string(payload, "SignatureValue")
    shp_params = _extract_shp_params(payload)

    handler = build_robokassa_callback_handler(session, settings)
    try:
        result = handler.validate_success_redirect(
            invoice_id=invoice_id,
            out_sum=out_sum,
            signature_value=signature_value,
            shp_params=shp_params,
        )
    except RobokassaError as error:
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "not configured" in str(error).casefold()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(error),
        ) from error

    if result.status == "paid":
        return PlainTextResponse("Платёж подтверждён. Подписка активирована.")

    return PlainTextResponse("Платёж принят. Ждём серверное подтверждение оплаты.")


@router.api_route("/fail", methods=["GET", "POST"], response_class=PlainTextResponse)
async def robokassa_fail() -> PlainTextResponse:
    return PlainTextResponse("Оплата не завершена. Можно попробовать ещё раз.")


async def _extract_request_payload(request: Request) -> dict[str, str]:
    if request.method == "POST":
        raw_body = (await request.body()).decode("utf-8")
        return {key: value for key, value in parse_qsl(raw_body, keep_blank_values=True)}

    return {key: value for key, value in request.query_params.items()}


def _require_string(payload: dict[str, str], key: str) -> str:
    value = payload.get(key)
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing parameter: {key}",
        )
    return value


def _require_int(payload: dict[str, str], key: str) -> int:
    raw_value = _require_string(payload, key)
    try:
        return int(raw_value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid integer parameter: {key}",
        ) from error


def _extract_shp_params(payload: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in payload.items()
        if key.startswith("Shp_")
    }
