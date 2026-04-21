from __future__ import annotations

import json
import unittest

from app.vk_transport.keyboards import (
    build_cabinet_inline_keyboard,
    build_dialog_menu_keyboard,
    build_plan_detail_inline_keyboard,
    build_plans_inline_keyboard,
)


class VkKeyboardsTests(unittest.TestCase):
    def test_dialog_menu_keyboard_has_single_cabinet_button(self) -> None:
        keyboard = build_dialog_menu_keyboard()

        self.assertNotIn("inline", keyboard)
        self.assertTrue(keyboard["one_time"])
        self.assertEqual(len(keyboard["buttons"]), 1)
        self.assertEqual(len(keyboard["buttons"][0]), 1)

        button = keyboard["buttons"][0][0]
        self.assertEqual(button["action"]["label"], "Меню")
        self.assertEqual(
            json.loads(button["action"]["payload"]),
            {"type": "cabinet_open"},
        )
        self.assertEqual(button["color"], "negative")

    def test_cabinet_inline_keyboard_contains_provider_premium_help_and_support(self) -> None:
        keyboard = build_cabinet_inline_keyboard()

        self.assertTrue(keyboard["inline"])
        self.assertEqual(len(keyboard["buttons"]), 3)
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][0]],
            ["🤖 Claude", "⚡ Gemini"],
        )
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][1]],
            ["💬 ChatGPT", "💎 Премиум"],
        )
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][2]],
            ["📘 Инструкция", "🆘 Поддержка"],
        )
        self.assertEqual(keyboard["buttons"][0][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][0][1]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][1][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][1][1]["color"], "primary")
        self.assertEqual(keyboard["buttons"][2][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][2][1]["color"], "secondary")

    def test_plans_inline_keyboard_contains_plan_cards_and_cabinet(self) -> None:
        keyboard = build_plans_inline_keyboard()

        self.assertTrue(keyboard["inline"])
        self.assertEqual(len(keyboard["buttons"]), 2)
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][0]],
            ["🌿 Lite", "🚀 Pro"],
        )
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][1]],
            ["👑 Max", "Меню"],
        )
        self.assertEqual(keyboard["buttons"][0][0]["color"], "primary")
        self.assertEqual(keyboard["buttons"][0][1]["color"], "positive")
        self.assertEqual(keyboard["buttons"][1][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][1][1]["color"], "negative")

    def test_plan_detail_keyboard_contains_payment_link_and_menu(self) -> None:
        keyboard = build_plan_detail_inline_keyboard("https://example.com/pay")

        self.assertTrue(keyboard["inline"])
        self.assertEqual(keyboard["buttons"][0][0]["action"]["type"], "open_link")
        self.assertEqual(keyboard["buttons"][0][0]["action"]["label"], "Оплата")
        self.assertEqual(keyboard["buttons"][0][0]["action"]["link"], "https://example.com/pay")
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][1]],
            ["🌿 Lite", "🚀 Pro"],
        )
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][2]],
            ["👑 Max", "Меню"],
        )
