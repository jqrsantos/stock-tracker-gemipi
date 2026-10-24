import os
import sys
import unittest
import importlib.util
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Explicitly load listener/main.py to avoid collisions with api/main.py
listener_dir = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("listener_main", listener_dir / "main.py")
listener_main = importlib.util.module_from_spec(spec)
sys.modules["listener_main"] = listener_main
spec.loader.exec_module(listener_main)


class TestTelegramListener(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        listener_main.AUTHORIZED_CHAT_ID = "12345678"
        listener_main.current_job = None

    def test_is_authorized(self):
        # Matching chat
        mock_update = MagicMock()
        mock_update.effective_chat.id = 12345678
        self.assertTrue(listener_main.is_authorized(mock_update))

        # Non-matching chat
        mock_update.effective_chat.id = 99999999
        self.assertFalse(listener_main.is_authorized(mock_update))

        # None chat
        mock_update.effective_chat = None
        self.assertFalse(listener_main.is_authorized(mock_update))

    def test_main_keyboard_layout(self):
        kb = listener_main.MAIN_KEYBOARD
        self.assertTrue(kb.is_persistent)
        self.assertTrue(kb.resize_keyboard)
        keyboard_buttons = [[b.text for b in row] for row in kb.keyboard]
        self.assertEqual(
            keyboard_buttons,
            [
                ["🌅 Run Daily Briefing", "🦅 Run Weekly Deep Scour"],
                ["📊 Watchlist & Status", "❓ Help"],
            ],
        )

    async def test_job_concurrency_lock(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 12345678
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        # Simulate job already active
        listener_main.current_job = {
            "name": "Daily Market Briefing",
            "started_at": datetime.now(),
        }

        # Attempt to run weekly while daily is active
        await listener_main.handle_weekly(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        self.assertIn("already in progress", args[0])
        self.assertIn("Daily Market Briefing", args[0])

    async def test_handle_daily_starts_background_task(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 12345678
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.bot = MagicMock()

        with patch.object(listener_main, "execute_job_in_background", new_callable=AsyncMock) as mock_exec, \
             patch("asyncio.create_task") as mock_create_task:
            await listener_main.handle_daily(mock_update, mock_context)
            self.assertIsNotNone(listener_main.current_job)
            self.assertEqual(listener_main.current_job["name"], "Daily Market Briefing")
            mock_create_task.assert_called_once()

    async def test_handle_status_formatting(self):
        with patch.object(listener_main.requests, "get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "summary": {
                    "total_scouted": 4,
                    "win_rate_pct": 75.0,
                    "avg_return_pct": 12.5,
                    "active_count": 3,
                    "dismissed_count": 1,
                    "best_pick": {"ticker": "NOW", "return_pct": 28.4},
                },
                "picks": [
                    {"ticker": "NOW", "status": "ACTIVE"},
                    {"ticker": "ASML", "status": "ACTIVE"},
                    {"ticker": "ADBE", "status": "ACTIVE"},
                    {"ticker": "LMT", "status": "DISMISSED"},
                ],
            }

            mock_update = MagicMock()
            mock_update.effective_chat.id = 12345678
            mock_update.message.reply_text = AsyncMock()
            mock_context = MagicMock()

            await listener_main.handle_status(mock_update, mock_context)
            args, _ = mock_update.message.reply_text.call_args
            msg = args[0]
            self.assertIn("Total Tracked: `4`", msg)
            self.assertIn("Active Conviction: `3` (NOW, ASML, ADBE)", msg)
            self.assertIn("Dismissed Archive: `1`", msg)
            self.assertIn("Best Pick: `NOW (+28.4%)`", msg)
            self.assertIn("🟢 **Idle**", msg)

    async def test_text_router(self):
        mock_update = MagicMock()
        mock_update.effective_chat.id = 12345678
        mock_context = MagicMock()

        with patch.object(listener_main, "handle_daily", new_callable=AsyncMock) as mock_daily, \
             patch.object(listener_main, "handle_weekly", new_callable=AsyncMock) as mock_weekly, \
             patch.object(listener_main, "handle_status", new_callable=AsyncMock) as mock_status, \
             patch.object(listener_main, "handle_start_help", new_callable=AsyncMock) as mock_help, \
             patch.object(listener_main, "evaluate_single_stock", new_callable=AsyncMock) as mock_eval:

            # 1. Daily button
            mock_update.message.text = "🌅 Run Daily Briefing"
            await listener_main.handle_text_message(mock_update, mock_context)
            mock_daily.assert_called_once()

            # 2. Weekly button
            mock_update.message.text = "🦅 Run Weekly Deep Scour"
            await listener_main.handle_text_message(mock_update, mock_context)
            mock_weekly.assert_called_once()

            # 3. Status button
            mock_update.message.text = "📊 Watchlist & Status"
            await listener_main.handle_text_message(mock_update, mock_context)
            mock_status.assert_called_once()

            # 4. Help button
            mock_update.message.text = "❓ Help"
            await listener_main.handle_text_message(mock_update, mock_context)
            mock_help.assert_called_once()

            # 5. Ticker input
            mock_update.message.text = "NOW"
            await listener_main.handle_text_message(mock_update, mock_context)
            mock_eval.assert_called_once()


if __name__ == "__main__":
    unittest.main()
