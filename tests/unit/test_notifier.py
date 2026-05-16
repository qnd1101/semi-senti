"""``notifier`` 패키지 단위 테스트 (Phase 4-1, T-041 ~ T-043)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from semi_senti.db import DBControl, init_database
from semi_senti.notifier import (
    NotificationManager,
    SentimentAlertWatcher,
    TelegramClient,
    TelegramSendError,
)
from semi_senti.notifier.manager import (
    build_sentiment_shift_message,
    build_signal_message,
)


# -----------------------------------------------------------------------------
# Pure builders
# -----------------------------------------------------------------------------


class TestSignalMessageBuilder(unittest.TestCase):
    def test_buy_message_format(self) -> None:
        msg = build_signal_message(
            stock_code="000660",
            stock_name="SK하이닉스",
            signal_type="BUY",
            price=128000,
            band_low=131500,
            band_high=170000,
            sentiment_score=-82,
            signaled_at="2026-05-02 14:32",
        )
        self.assertIn("🔔 [Semi Senti] 매매 시그널 발생", msg)
        self.assertIn("SK하이닉스 (000660)", msg)
        self.assertIn("🟢 BUY", msg)
        self.assertIn("128,000원", msg)
        self.assertIn("하단 131,500원 대비", msg)
        self.assertIn("-82 (공포 구간)", msg)
        self.assertIn("2026-05-02 14:32", msg)

    def test_sell_message_format(self) -> None:
        msg = build_signal_message(
            stock_code="005930",
            stock_name="삼성전자",
            signal_type="SELL",
            price=88000,
            band_low=70000,
            band_high=81000,
            sentiment_score=82,
        )
        self.assertIn("🔴 SELL", msg)
        self.assertIn("상단 81,000원 대비", msg)
        self.assertIn("+82 (탐욕 구간)", msg)


class TestSentimentShiftMessageBuilder(unittest.TestCase):
    def test_drop_message(self) -> None:
        msg = build_sentiment_shift_message(
            stock_code="000660",
            stock_name="SK하이닉스",
            previous_score=12,
            current_score=-45,
            delta=-57,
            period_label="1시간 내",
        )
        self.assertIn("📉", msg)
        self.assertIn("급락", msg)
        self.assertIn("Δ -57.0pt", msg)


# -----------------------------------------------------------------------------
# TelegramClient
# -----------------------------------------------------------------------------


class TestTelegramClientRetry(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["TELEGRAM_BOT_TOKEN"] = "TEST"
        os.environ["TELEGRAM_CHAT_ID"] = "12345"
        os.environ["NOTIFY_BACKOFF_SECONDS"] = "0"  # 테스트 속도 향상
        self.client = TelegramClient(max_retries=3, backoff_seconds=0.0)

    def tearDown(self) -> None:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        os.environ.pop("NOTIFY_BACKOFF_SECONDS", None)

    def test_send_with_retry_success_on_first(self) -> None:
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"ok": True, "result": {}}
        with patch("requests.post", return_value=mock_resp) as post:
            self.client.send_with_retry("hello")
        self.assertEqual(post.call_count, 1)

    def test_send_with_retry_recovers(self) -> None:
        # 첫 번째 호출 fail (4xx), 두 번째 성공.
        bad_resp = MagicMock(status_code=400)
        bad_resp.json.return_value = {"ok": False, "description": "bad"}
        good_resp = MagicMock(status_code=200)
        good_resp.json.return_value = {"ok": True}
        with patch("requests.post", side_effect=[bad_resp, good_resp]) as post:
            self.client.send_with_retry("hello")
        self.assertEqual(post.call_count, 2)

    def test_send_with_retry_exhausts(self) -> None:
        bad_resp = MagicMock(status_code=500)
        bad_resp.json.return_value = {"ok": False, "description": "boom"}
        with patch("requests.post", return_value=bad_resp) as post:
            with self.assertRaises(TelegramSendError):
                self.client.send_with_retry("hello")
        self.assertEqual(post.call_count, 3)

    def test_unconfigured_client_raises(self) -> None:
        client = TelegramClient(bot_token="", chat_id="")
        self.assertFalse(client.is_configured)
        with self.assertRaises(TelegramSendError):
            client.send("hello")


# -----------------------------------------------------------------------------
# NotificationManager + DB
# -----------------------------------------------------------------------------


class _DBBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "notifier_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        os.environ["TELEGRAM_BOT_TOKEN"] = "TEST"
        os.environ["TELEGRAM_CHAT_ID"] = "12345"
        os.environ["NOTIFY_BACKOFF_SECONDS"] = "0"
        init_database(db_path=self.db_path)
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks",
                {"stock_code": "000660", "name": "SK하이닉스", "market": "KOSPI"},
                conflict_columns=["stock_code"],
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        for k in (
            "SEMI_SENTI_SQLITE_PATH", "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID", "NOTIFY_BACKOFF_SECONDS",
        ):
            os.environ.pop(k, None)


class TestNotificationManager(_DBBase):
    def _ok_resp(self) -> MagicMock:
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"ok": True}
        return resp

    def test_notify_signal_persists_sent_record(self) -> None:
        with patch("requests.post", return_value=self._ok_resp()):
            with NotificationManager() as nm:
                result = nm.notify_signal(
                    stock_code="000660",
                    signal_type="BUY",
                    price=128000,
                    band_low=131500,
                    band_high=170000,
                    sentiment_score=-82,
                    signaled_at="2026-05-02T14:32:00",
                )
        self.assertTrue(result.success)
        self.assertIsNotNone(result.record_id)

        with DBControl(db_path=self.db_path) as db:
            row = db.fetch_one(
                "SELECT status, retry_count FROM notifications WHERE id = ?",
                (result.record_id,),
            )
        self.assertEqual(row["status"], "SENT")
        self.assertEqual(row["retry_count"], 0)

    def test_notify_signal_skips_hold(self) -> None:
        with NotificationManager() as nm:
            result = nm.notify_signal(
                stock_code="000660",
                signal_type="HOLD",
                price=128000, band_low=130000, band_high=170000,
                sentiment_score=-10,
            )
        self.assertTrue(result.skipped)
        self.assertIsNone(result.record_id)

    def test_notify_signal_dedupe(self) -> None:
        # 두 번째 호출은 같은 signaled_at 으로 dedupe 되어야 한다.
        with patch("requests.post", return_value=self._ok_resp()):
            with NotificationManager() as nm:
                first = nm.notify_signal(
                    stock_code="000660", signal_type="BUY", price=1, band_low=2, band_high=3,
                    sentiment_score=-80, signaled_at="2026-05-15T10:00:00",
                )
                second = nm.notify_signal(
                    stock_code="000660", signal_type="BUY", price=1, band_low=2, band_high=3,
                    sentiment_score=-80, signaled_at="2026-05-15T10:00:00",
                )
        self.assertTrue(first.success)
        self.assertTrue(second.skipped)
        self.assertEqual(second.skip_reason, "이미 발송된 시그널")

    def test_notify_signal_failure_records_failed(self) -> None:
        bad = MagicMock(status_code=400)
        bad.json.return_value = {"ok": False, "description": "boom"}
        with patch("requests.post", return_value=bad):
            with NotificationManager() as nm:
                result = nm.notify_signal(
                    stock_code="000660", signal_type="SELL",
                    price=200, band_low=100, band_high=180, sentiment_score=80,
                    signaled_at="2026-05-15T11:00:00",
                )
        self.assertFalse(result.success)

        with DBControl(db_path=self.db_path) as db:
            row = db.fetch_one(
                "SELECT status, retry_count, last_error FROM notifications "
                "WHERE id = ?",
                (result.record_id,),
            )
        self.assertEqual(row["status"], "FAILED")
        self.assertEqual(row["retry_count"], 3)
        self.assertIn("boom", row["last_error"])

    def test_count_failed(self) -> None:
        bad = MagicMock(status_code=400)
        bad.json.return_value = {"ok": False, "description": "x"}
        with patch("requests.post", return_value=bad):
            with NotificationManager() as nm:
                nm.notify_signal(
                    stock_code="000660", signal_type="BUY",
                    price=1, band_low=2, band_high=3, sentiment_score=-80,
                    signaled_at="2026-05-15T12:00:00",
                )
                self.assertEqual(nm.count_failed(), 1)


# -----------------------------------------------------------------------------
# SentimentAlertWatcher
# -----------------------------------------------------------------------------


class TestSentimentAlertWatcher(_DBBase):
    def setUp(self) -> None:
        super().setUp()
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "sentiment_scores",
                {"stock_code": "000660", "score_date": "2026-05-14",
                 "score": 12.0, "raw_score": 0.8, "news_count": 3},
                conflict_columns=["stock_code", "score_date"],
            )
            db.upsert(
                "sentiment_scores",
                {"stock_code": "000660", "score_date": "2026-05-15",
                 "score": -45.0, "raw_score": -3.0, "news_count": 7},
                conflict_columns=["stock_code", "score_date"],
            )

    def test_evaluate_triggers_alert_when_threshold_exceeded(self) -> None:
        ok = MagicMock(status_code=200)
        ok.json.return_value = {"ok": True}
        with patch("requests.post", return_value=ok):
            with SentimentAlertWatcher(threshold_pt=30.0) as watcher:
                result = watcher.evaluate("000660")
        self.assertIsNotNone(result)
        self.assertTrue(result.success)

    def test_evaluate_skips_when_below_threshold(self) -> None:
        # 임계값을 100pt 로 올려 변동(57pt) < threshold 가 되도록 한다.
        with SentimentAlertWatcher(threshold_pt=100.0) as watcher:
            result = watcher.evaluate("000660")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
