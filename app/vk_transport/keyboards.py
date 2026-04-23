from __future__ import annotations

import json

from app.ai.provider_catalog import PROVIDER_OPTIONS
from app.subscriptions.catalog import LITE_PLAN, MAX_PLAN, PRO_PLAN


def build_cabinet_inline_keyboard() -> dict[str, object]:
    return {
        "one_time": False,
        "inline": True,
        "buttons": [
            [
                _text_button(
                    label=PROVIDER_OPTIONS[0].button_text,
                    payload={"type": "provider_select", "provider": PROVIDER_OPTIONS[0].code},
                    color="secondary",
                ),
                _text_button(
                    label=PROVIDER_OPTIONS[1].button_text,
                    payload={"type": "provider_select", "provider": PROVIDER_OPTIONS[1].code},
                    color="secondary",
                ),
            ],
            [
                _text_button(
                    label=PROVIDER_OPTIONS[2].button_text,
                    payload={"type": "provider_select", "provider": PROVIDER_OPTIONS[2].code},
                    color="secondary",
                ),
                _text_button(
                    label="💎 Премиум",
                    payload={"type": "plans_open"},
                    color="primary",
                ),
            ],
            [
                _text_button(
                    label="📘 Инструкция",
                    payload={"type": "instruction_open"},
                    color="secondary",
                ),
                _text_button(
                    label="🆘 Поддержка",
                    payload={"type": "support_open"},
                    color="secondary",
                ),
            ],
        ],
    }


def build_plans_inline_keyboard() -> dict[str, object]:
    return {
        "one_time": False,
        "inline": True,
        "buttons": [
            [
                _text_button(
                    label=LITE_PLAN.button_text,
                    payload={"type": "plan_open", "plan": LITE_PLAN.code},
                    color="primary",
                ),
                _text_button(
                    label=PRO_PLAN.button_text,
                    payload={"type": "plan_open", "plan": PRO_PLAN.code},
                    color="positive",
                ),
            ],
            [
                _text_button(
                    label=MAX_PLAN.button_text,
                    payload={"type": "plan_open", "plan": MAX_PLAN.code},
                    color="secondary",
                ),
                _text_button(
                    label="Меню",
                    payload={"type": "cabinet_open"},
                    color="negative",
                ),
            ],
        ],
    }


def build_plan_detail_inline_keyboard(payment_url: str | None = None) -> dict[str, object]:
    buttons: list[list[dict[str, object]]] = []
    if payment_url:
        buttons.append([_open_link_button(label="Оплата", link=payment_url)])

    buttons.append(
        [
            _text_button(
                label="🌿 Lite",
                payload={"type": "plan_open", "plan": LITE_PLAN.code},
                color="primary",
            ),
            _text_button(
                label="🚀 Pro",
                payload={"type": "plan_open", "plan": PRO_PLAN.code},
                color="positive",
            ),
        ]
    )
    buttons.append(
        [
            _text_button(
                label="👑 Max",
                payload={"type": "plan_open", "plan": MAX_PLAN.code},
                color="secondary",
            ),
            _text_button(
                label="Меню",
                payload={"type": "cabinet_open"},
                color="negative",
            ),
        ]
    )

    return {
        "one_time": False,
        "inline": True,
        "buttons": buttons,
    }


def build_dialog_menu_keyboard() -> dict[str, object]:
    return {
        "one_time": False,
        "inline": True,
        "buttons": [
            [
                _text_button(
                    label="Меню",
                    payload={"type": "cabinet_open"},
                    color="negative",
                )
            ]
        ],
    }


def _text_button(
    *,
    label: str,
    payload: dict[str, object],
    color: str,
) -> dict[str, object]:
    return {
        "action": {
            "type": "text",
            "label": label,
            "payload": json.dumps(payload, ensure_ascii=False),
        },
        "color": color,
    }


def _open_link_button(
    *,
    label: str,
    link: str,
) -> dict[str, object]:
    return {
        "action": {
            "type": "open_link",
            "label": label,
            "link": link,
        }
    }
