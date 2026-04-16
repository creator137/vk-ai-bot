from __future__ import annotations

import json
import unittest

from app.vk_transport.keyboards import (
    build_cabinet_inline_keyboard,
    build_dialog_menu_keyboard,
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
        self.assertEqual(button["action"]["label"], "🏠 Кабинет")
        self.assertEqual(
            json.loads(button["action"]["payload"]),
            {"type": "cabinet_open"},
        )

    def test_cabinet_inline_keyboard_contains_only_provider_buttons(self) -> None:
        keyboard = build_cabinet_inline_keyboard()

        self.assertTrue(keyboard["inline"])
        self.assertEqual(len(keyboard["buttons"]), 2)
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][0]],
            ["🤖 Claude", "⚡ Gemini"],
        )
        self.assertEqual(
            [button["action"]["label"] for button in keyboard["buttons"][1]],
            ["💬 ChatGPT", "💎 Тарифы"],
        )
        self.assertEqual(keyboard["buttons"][0][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][0][1]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][1][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][1][1]["color"], "primary")

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
            ["👑 Max", "🏠 Кабинет"],
        )
        self.assertEqual(keyboard["buttons"][0][0]["color"], "secondary")
        self.assertEqual(keyboard["buttons"][0][1]["color"], "primary")
        self.assertEqual(keyboard["buttons"][1][0]["color"], "positive")
        self.assertEqual(keyboard["buttons"][1][1]["color"], "secondary")
