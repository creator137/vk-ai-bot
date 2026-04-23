from __future__ import annotations

import asyncio
from html import escape
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.application.payments import (
    build_robokassa_callback_handler,
    build_robokassa_payment_init_handler,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.payments.robokassa import RobokassaError

router = APIRouter(prefix="/payments/robokassa", tags=["robokassa"])


@router.get("/start/{payment_id}", response_class=HTMLResponse)
async def robokassa_start(
    payment_id: int,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    handler = build_robokassa_payment_init_handler(session, settings)
    try:
        page = handler.build_checkout_page(payment_id=payment_id)
    except RobokassaError as error:
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "not configured" in str(error).casefold()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return HTMLResponse(_render_payment_start_page(gateway_url=page.gateway_url, form_fields=page.form_fields))


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
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    return PlainTextResponse(f"OK{invoice_id}")


@router.api_route("/success", methods=["GET", "POST"], response_class=HTMLResponse)
async def robokassa_success(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
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
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    payment_status = result.status
    if payment_status != "paid":
        payment_status = await _wait_for_paid_status(
            invoice_id=invoice_id,
            session=session,
            settings=settings,
        )

    if payment_status == "paid":
        return HTMLResponse(
            _render_payment_page(
                title="Оплата подтверждена",
                heading="Подписка активирована",
                body=(
                    "Платёж подтверждён. Подписка уже применена, "
                    "можно возвращаться в VK и продолжать работу."
                ),
                tone="success",
                auto_redirect_seconds=2,
                auto_redirect_href=settings.vk_return_url,
                **_build_vk_button_args(settings),
            )
        )

    return HTMLResponse(
        _render_payment_page(
            title="Оплата обрабатывается",
            heading="Платёж принят",
            body=(
                "Мы получили платёж, но финальное серверное подтверждение "
                "ещё в пути. Обычно это занимает несколько секунд."
            ),
            tone="pending",
            auto_refresh_seconds=3,
            **_build_vk_button_args(settings),
        )
    )


@router.api_route("/fail", methods=["GET", "POST"], response_class=HTMLResponse)
async def robokassa_fail(
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    return HTMLResponse(
        _render_payment_page(
            title="Оплата не завершена",
            heading="Платёж не завершён",
            body="Оплату можно попробовать ещё раз, когда будете готовы.",
            tone="fail",
            **_build_vk_button_args(settings),
        )
    )


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


def _build_vk_button_args(settings: Settings) -> dict[str, str]:
    args: dict[str, str] = {}
    if settings.vk_return_url:
        args["primary_button_label"] = "Вернуться в VK"
        args["primary_button_href"] = settings.vk_return_url
    if settings.vk_community_url:
        args["secondary_button_label"] = "Открыть сообщество"
        args["secondary_button_href"] = settings.vk_community_url
    return args


async def _wait_for_paid_status(
    *,
    invoice_id: int,
    session: Session,
    settings: Settings,
    attempts: int = 6,
    delay_seconds: float = 0.5,
) -> str | None:
    status_value = None
    for attempt in range(attempts):
        handler = build_robokassa_callback_handler(session, settings)
        status_value = handler.get_payment_status(payment_id=invoice_id)
        if status_value == "paid":
            return status_value
        if attempt < attempts - 1:
            await asyncio.sleep(delay_seconds)
            session.expire_all()
    return status_value


def _render_payment_page(
    *,
    title: str,
    heading: str,
    body: str,
    tone: str,
    auto_refresh_seconds: int | None = None,
    auto_redirect_seconds: int | None = None,
    auto_redirect_href: str | None = None,
    primary_button_label: str | None = None,
    primary_button_href: str | None = None,
    secondary_button_label: str | None = None,
    secondary_button_href: str | None = None,
) -> str:
    palette = {
        "success": ("#0f5132", "#d1e7dd", "#f3fbf6", "#2787f5"),
        "pending": ("#7a4b00", "#ffe7b8", "#fff7e8", "#2787f5"),
        "fail": ("#842029", "#f5c2c7", "#fff1f2", "#2787f5"),
    }
    text_color, border_color, panel_color, accent_color = palette[tone]
    refresh_tag = ""
    refresh_note = ""
    if auto_refresh_seconds is not None:
        refresh_tag = f'<meta http-equiv="refresh" content="{auto_refresh_seconds}">'
        refresh_note = (
            "<p class=\"hint\">"
            "Если статус уже обновился, страница сама перезагрузится."
            "</p>"
        )
    redirect_script = ""
    redirect_note = ""
    if auto_redirect_seconds is not None and auto_redirect_href:
        refresh_tag += (
            f'<meta http-equiv="refresh" content="{auto_redirect_seconds};url={escape(auto_redirect_href, quote=True)}">'
        )
        redirect_script = (
            "<script>"
            f"window.setTimeout(function () {{ window.location.href = {auto_redirect_href!r}; }}, {auto_redirect_seconds * 1000});"
            "</script>"
        )
        redirect_note = (
            "<p class=\"hint\">"
            f"Через {auto_redirect_seconds} сек. вернём вас обратно в VK. "
            "Если этого не произошло, используйте кнопку ниже."
            "</p>"
        )
    actions = ""
    if primary_button_label and primary_button_href:
        actions += (
            "<div class=\"actions\">"
            f"<a class=\"button button-primary\" href=\"{primary_button_href}\">{primary_button_label}</a>"
        )
        if secondary_button_label and secondary_button_href:
            actions += (
                f"<a class=\"button button-secondary\" href=\"{secondary_button_href}\">{secondary_button_label}</a>"
            )
        actions += "</div>"

    return (
        "<!doctype html>"
        "<html lang=\"ru\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"{refresh_tag}"
        f"<title>{title}</title>"
        "<style>"
        "body{margin:0;font-family:Arial,sans-serif;background:linear-gradient(180deg,#f4f7fb 0%,#eef3f8 100%);color:#1f1f1f;}"
        ".wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}"
        ".card{max-width:560px;width:100%;background:"
        f"{panel_color};border:1px solid {border_color};border-radius:28px;padding:32px;"
        "box-shadow:0 24px 60px rgba(34,47,62,.12);overflow:hidden;position:relative;}"
        ".card:before{content:'';position:absolute;inset:0 auto auto 0;width:100%;height:6px;background:linear-gradient(90deg,#2787f5 0%,#59a7ff 55%,#ffb347 100%);}"
        ".brand{display:flex;align-items:center;gap:12px;margin-bottom:18px;padding-top:10px;}"
        ".brand-badge{width:48px;height:48px;border-radius:16px;background:linear-gradient(135deg,#2787f5 0%,#5aa9ff 100%);display:flex;align-items:center;justify-content:center;color:#fff;font-size:22px;font-weight:700;box-shadow:0 10px 24px rgba(39,135,245,.28);}"
        ".brand-copy{display:flex;flex-direction:column;gap:2px;}"
        ".brand-title{font-size:15px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#4a5568;}"
        ".brand-subtitle{font-size:14px;color:#6b7280;}"
        f".eyebrow{{color:{text_color};font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;}}"
        "h1{margin:12px 0 16px;font-size:34px;line-height:1.05;}"
        "p{margin:0;font-size:18px;line-height:1.6;max-width:44ch;}"
        ".actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px;}"
        ".button{display:inline-flex;align-items:center;justify-content:center;padding:14px 18px;border-radius:14px;text-decoration:none;font-weight:700;font-size:16px;transition:transform .12s ease,box-shadow .12s ease;}"
        f".button-primary{{background:{accent_color};color:#fff;box-shadow:0 12px 26px rgba(39,135,245,.26);}}"
        ".button-secondary{background:#fff;color:#1f2937;border:1px solid #d7e0ea;}"
        ".button:hover{transform:translateY(-1px);}"
        ".hint{margin-top:16px;font-size:14px;opacity:.72;}"
        ".footer{margin-top:18px;font-size:13px;color:#6b7280;}"
        "@media (max-width:640px){.card{padding:24px;border-radius:22px;}h1{font-size:28px;}p{font-size:16px;}.button{width:100%;}}"
        "</style>"
        f"{redirect_script}"
        "</head>"
        "<body>"
        "<div class=\"wrap\">"
        "<section class=\"card\">"
        "<div class=\"brand\">"
        "<div class=\"brand-badge\">VK</div>"
        "<div class=\"brand-copy\">"
        "<div class=\"brand-title\">AI BOT</div>"
        "<div class=\"brand-subtitle\">Оплата через Robokassa</div>"
        "</div>"
        "</div>"
        f"<div class=\"eyebrow\">{title}</div>"
        f"<h1>{heading}</h1>"
        f"<p>{body}</p>"
        f"{actions}"
        f"{refresh_note}"
        f"{redirect_note}"
        "<div class=\"footer\">Если VK не открылся автоматически, можно закрыть эту вкладку и вернуться в диалог вручную.</div>"
        "</section>"
        "</div>"
        "</body>"
        "</html>"
    )


def _render_payment_start_page(
    *,
    gateway_url: str,
    form_fields: dict[str, str],
) -> str:
    hidden_inputs = "".join(
        (
            f'<input type="hidden" name="{escape(key)}" value="{escape(value, quote=True)}">'
            for key, value in form_fields.items()
        )
    )
    return (
        "<!doctype html>"
        "<html lang=\"ru\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Переход к оплате</title>"
        "<style>"
        "body{margin:0;font-family:Arial,sans-serif;background:#f5f7fb;color:#1f2937;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px;}"
        ".card{max-width:520px;width:100%;background:#fff;border:1px solid #dbe4ee;border-radius:24px;padding:28px;box-shadow:0 24px 60px rgba(34,47,62,.12);}"
        "h1{margin:0 0 12px;font-size:28px;line-height:1.1;}"
        "p{margin:0;color:#4b5563;font-size:16px;line-height:1.6;}"
        ".button{margin-top:20px;display:inline-flex;align-items:center;justify-content:center;padding:14px 18px;border-radius:14px;background:#2787f5;color:#fff;text-decoration:none;border:none;font-weight:700;font-size:16px;cursor:pointer;}"
        "</style>"
        "<script>"
        "window.addEventListener('load', function () {"
        "  var form = document.getElementById('robokassa-start-form');"
        "  if (form) { form.submit(); }"
        "});"
        "</script>"
        "</head>"
        "<body>"
        "<section class=\"card\">"
        "<h1>Переход к оплате</h1>"
        "<p>Открываем защищённую форму Robokassa. Если переадресация не сработала автоматически, нажмите кнопку ниже.</p>"
        f"<form id=\"robokassa-start-form\" action=\"{escape(gateway_url, quote=True)}\" method=\"post\" accept-charset=\"utf-8\">"
        f"{hidden_inputs}"
        "<noscript><button class=\"button\" type=\"submit\">Продолжить оплату</button></noscript>"
        "</form>"
        "</section>"
        "</body>"
        "</html>"
    )
