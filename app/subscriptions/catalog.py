from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SubscriptionPlan:
    code: str
    title: str
    price_rub: int
    included_tokens: int
    button_text: str
    short_description: str
    image_filename: str


FREE_PLAN = SubscriptionPlan(
    "free",
    "Free",
    0,
    5_000,
    "Free",
    "Стартовый бонус для новых пользователей",
    "lite.jpeg",
)
LITE_PLAN = SubscriptionPlan(
    "lite",
    "Lite",
    300,
    35_000,
    "🌿 Lite",
    "Для старта и спокойного ритма",
    "lite.jpeg",
)
PRO_PLAN = SubscriptionPlan(
    "pro",
    "Pro",
    500,
    100_000,
    "🚀 Pro",
    "Оптимальный выбор на каждый день",
    "pro.jpeg",
)
MAX_PLAN = SubscriptionPlan(
    "max",
    "Max",
    1_000,
    200_000,
    "👑 Max",
    "Для плотного общения и больших задач",
    "max.jpeg",
)

PLANS_BY_CODE = {
    FREE_PLAN.code: FREE_PLAN,
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


def get_subscription_plan_image_path(plan_code: str) -> str:
    plan = get_subscription_plan(plan_code)
    assets_dir = Path(__file__).resolve().parent.parent / "assets" / "tariffs"
    return str(assets_dir / plan.image_filename)


def render_subscription_plans_text() -> str:
    lines = [
        "AI BOT",
        "",
        "Будущее уже здесь.",
        "",
        "💎 Премиум — это:",
        "ИИ без ограничений, без ожидания и с максимальными возможностями.",
        "",
        "Выбери свой уровень по лучшим ценам👇",
    ]
    return "\n".join(lines)


def render_subscription_plan_detail_text(
    plan_code: str,
    *,
    payment_url: str | None = None,
    is_test: bool = False,
) -> str:
    plan = get_subscription_plan(plan_code)
    if plan.code == "lite":
        lines = [
            "💎 Lite — 300₽ (̶1̶5̶0̶0̶)̶",
            "",
            "🔥35.000 токенов🔥",
            "",
            "Для учёбы и повседневных задач",
            "",
            "✔️ Быстрые ответы без очереди",
            "✔️ Работа с текстом и фото",
            "✔️ Генерация изображений",
            "",
            "📦 Хватит для:",
            "— учебы",
            "— домашних заданий",
            "— повседневных вопросов",
        ]
    elif plan.code == "pro":
        lines = [
            "⭐️ PRO — 500₽ (̶4̶0̶0̶0̶)̶",
            "🔥 Выбор большинства",
            "",
            "🔥100.000 токенов🔥",
            "",
            "Для тех, кто пользуется ИИ каждый день",
            "",
            "✔️ Всё из Lite + больше возможностей",
            "✔️ Приоритетные ответы",
            "✔️ Генерация музыки и изображений",
            "",
            "📦 Подходит для:",
            "— работы",
            "— контента",
            "— постоянного использования",
        ]
    else:
        lines = [
            "👑 Max — 1000₽ (̶9̶0̶0̶0̶)̶",
            "",
            "🔥200.000 токенов🔥",
            "",
            "Максимум возможностей без компромиссов",
            "",
            "✔️ Всё включено",
            "✔️ Самый быстрый доступ (без очередей)",
            "✔️ Новые функции раньше всех",
            "✔️ VIP поддержка",
            "",
            "🚀 Для тех, кто хочет максимум",
        ]

    lines.extend([""])

    if payment_url:
        lines.append("Нажмите кнопку оплаты ниже, чтобы перейти к оформлению.")
    else:
        lines.append("Оплата появится сразу после настройки платёжного кабинета.")

    lines.extend(["", "После подтверждения оплаты тариф активируется автоматически."])
    return "\n".join(lines)
