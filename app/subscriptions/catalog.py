from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubscriptionPlan:
    code: str
    title: str
    price_rub: int
    included_tokens: int
    button_text: str
    short_description: str


LITE_PLAN = SubscriptionPlan(
    "lite",
    "Lite",
    379,
    35_000,
    "🌿 Lite",
    "Для старта и спокойного ритма",
)
PRO_PLAN = SubscriptionPlan(
    "pro",
    "Pro",
    599,
    100_000,
    "🚀 Pro",
    "Оптимальный выбор на каждый день",
)
MAX_PLAN = SubscriptionPlan(
    "max",
    "Max",
    1_190,
    200_000,
    "👑 Max",
    "Для плотного общения и больших задач",
)

PLANS_BY_CODE = {
    LITE_PLAN.code: LITE_PLAN,
    PRO_PLAN.code: PRO_PLAN,
    MAX_PLAN.code: MAX_PLAN,
}

PLANS_BY_BUTTON_TEXT = {}
for plan in (LITE_PLAN, PRO_PLAN, MAX_PLAN):
    PLANS_BY_BUTTON_TEXT[plan.button_text.casefold()] = plan
    PLANS_BY_BUTTON_TEXT[plan.title.casefold()] = plan
    PLANS_BY_BUTTON_TEXT[plan.code.casefold()] = plan


def get_subscription_plan(plan_code: str) -> SubscriptionPlan:
    try:
        return PLANS_BY_CODE[plan_code]
    except KeyError as error:
        raise ValueError(f"Unsupported subscription plan: {plan_code}") from error


def find_subscription_plan_by_button_text(text: str) -> SubscriptionPlan | None:
    return PLANS_BY_BUTTON_TEXT.get(text.strip().casefold())


def render_subscription_plans_text() -> str:
    lines = [
        "AI BOT",
        "",
        "💎 Тарифы",
        "Подберите формат под свой ритм общения и объём задач.",
        "",
        f"{LITE_PLAN.button_text}",
        f"• {LITE_PLAN.price_rub}₽ в месяц",
        f"• {LITE_PLAN.included_tokens} в запасе для общения",
        f"• {LITE_PLAN.short_description}",
        "",
        f"{PRO_PLAN.button_text}",
        f"• {PRO_PLAN.price_rub}₽ в месяц",
        f"• {PRO_PLAN.included_tokens} для активного общения",
        f"• {PRO_PLAN.short_description}",
        "",
        f"{MAX_PLAN.button_text}",
        f"• {MAX_PLAN.price_rub}₽ в месяц",
        f"• {MAX_PLAN.included_tokens} для максимального темпа",
        f"• {MAX_PLAN.short_description}",
        "",
        "Чем короче переписка, тем медленнее расходуется баланс.",
        "Нажмите на тариф ниже, чтобы посмотреть его подробнее.",
    ]
    return "\n".join(lines)


def render_subscription_plan_detail_text(
    plan_code: str,
    *,
    payment_url: str | None = None,
    is_test: bool = False,
) -> str:
    plan = get_subscription_plan(plan_code)
    lines = [
        "AI BOT",
        "",
        plan.button_text,
        f"{plan.price_rub}₽ в месяц",
        "",
        "Что входит:",
        f"• {plan.included_tokens} в запасе для общения",
        f"• {plan.short_description}",
    ]

    if plan.code == "lite":
        lines.append("• Подойдёт, если бот нужен для коротких ежедневных задач")
    elif plan.code == "pro":
        lines.append("• Самый универсальный вариант для работы и общения")
    else:
        lines.append("• Лучший вариант, если бот нужен вам каждый день и помногу")

    lines.extend(
        [
            "",
        ]
    )

    if payment_url:
        lines.extend(
            [
                "Ссылка на оплату:",
                payment_url,
            ]
        )
        if is_test:
            lines.append("Тестовый режим оплаты включён.")
    else:
        lines.append("Оплата будет доступна после настройки платёжного кабинета.")

    lines.extend(
        [
            "",
            "После подтверждения оплаты тариф активируется автоматически.",
        ]
    )
    return "\n".join(lines)
