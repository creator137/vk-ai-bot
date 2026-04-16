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
                    label="💎 Тарифы",
                    payload={"type": "plans_open"},
                    color="primary",
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
                    color="secondary",
                ),
                _text_button(
                    label=PRO_PLAN.button_text,
                    payload={"type": "plan_open", "plan": PRO_PLAN.code},
                    color="primary",
                ),
            ],
            [
                _text_button(
                    label=MAX_PLAN.button_text,
                    payload={"type": "plan_open", "plan": MAX_PLAN.code},
                    color="positive",
                ),
                _text_button(
                    label="🏠 Кабинет",
                    payload={"type": "cabinet_open"},
                    color="secondary",
                ),
            ],
        ],
    }


def build_dialog_menu_keyboard() -> dict[str, object]:
    return {
        "one_time": True,
        "buttons": [
            [
                _text_button(
                    label="🏠 Кабинет",
                    payload={"type": "cabinet_open"},
                    color="secondary",
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
