"""``DataNormalizer`` 단위 테스트 (T-008)."""

from __future__ import annotations

import unittest

from semi_senti.collector.normalizer import DataNormalizer


class TestDataNormalizer(unittest.TestCase):
    # ----- to_float -----
    def test_to_float_handles_various_inputs(self) -> None:
        self.assertEqual(DataNormalizer.to_float("1,234"), 1234.0)
        self.assertEqual(DataNormalizer.to_float("(1,500)"), -1500.0)
        self.assertEqual(DataNormalizer.to_float("12.5"), 12.5)
        self.assertEqual(DataNormalizer.to_float(7), 7.0)
        self.assertIsNone(DataNormalizer.to_float(None))
        self.assertIsNone(DataNormalizer.to_float(""))
        self.assertIsNone(DataNormalizer.to_float("-"))
        self.assertIsNone(DataNormalizer.to_float("N/A"))
        self.assertIsNone(DataNormalizer.to_float("abc"))

    def test_to_float_default_when_nan(self) -> None:
        self.assertIsNone(DataNormalizer.to_float(float("nan")))
        self.assertEqual(DataNormalizer.to_float(float("nan"), default=0.0), 0.0)

    def test_to_int_truncates(self) -> None:
        self.assertEqual(DataNormalizer.to_int("12.9"), 12)
        self.assertEqual(DataNormalizer.to_int("1,000"), 1000)
        self.assertIsNone(DataNormalizer.to_int(None))
        self.assertEqual(DataNormalizer.to_int("--", default=-1), -1)

    # ----- normalize_date -----
    def test_normalize_date_various(self) -> None:
        self.assertEqual(DataNormalizer.normalize_date("2026-05-16"), "2026-05-16")
        self.assertEqual(DataNormalizer.normalize_date("20260516"), "2026-05-16")
        self.assertEqual(
            DataNormalizer.normalize_date("2026-05-16T09:30:00"), "2026-05-16"
        )
        self.assertEqual(
            DataNormalizer.normalize_date("2026-05-16 09:30:00.123"), "2026-05-16"
        )
        self.assertIsNone(DataNormalizer.normalize_date(""))
        self.assertIsNone(DataNormalizer.normalize_date("not-a-date"))

    # ----- to_krw -----
    def test_to_krw_passthrough_for_krw(self) -> None:
        self.assertEqual(DataNormalizer.to_krw(1000, "KRW"), 1000)
        self.assertIsNone(DataNormalizer.to_krw(None))

    def test_to_krw_usd_conversion(self) -> None:
        krw = DataNormalizer.to_krw(1.0, "USD")
        self.assertIsNotNone(krw)
        assert krw is not None
        self.assertGreater(krw, 100)  # USD 환산은 KRW 대비 큰 값

    # ----- normalize_financial_record -----
    def test_normalize_financial_record_full(self) -> None:
        record = DataNormalizer.normalize_financial_record(
            stock_code="005930",
            record_date="20260516",
            raw={
                "open": "70,000",
                "high": "71,500",
                "low": "69,000",
                "close": "70,500",
                "volume": "12,345,678",
                "revenue": "300,000,000",
                "operating_profit": "(50,000,000)",
                "per": "12.3",
                "pbr": "1.4",
                "eps": "8,500",
            },
        )
        self.assertEqual(record["stock_code"], "005930")
        self.assertEqual(record["record_date"], "2026-05-16")
        self.assertEqual(record["open_price"], 70000.0)
        self.assertEqual(record["volume"], 12345678)
        self.assertEqual(record["operating_profit"], -50000000.0)
        self.assertEqual(record["currency"], "KRW")

    def test_normalize_financial_record_missing_fields(self) -> None:
        record = DataNormalizer.normalize_financial_record(
            stock_code="005930",
            record_date="2026-05-16",
            raw={},
        )
        for k in ("open_price", "high_price", "close_price", "volume", "per", "pbr", "eps"):
            self.assertIsNone(record[k])

    def test_normalize_financial_record_invalid_date(self) -> None:
        with self.assertRaises(ValueError):
            DataNormalizer.normalize_financial_record(
                stock_code="005930",
                record_date="not-a-date",
                raw={},
            )

    def test_normalize_financial_record_requires_stock_code(self) -> None:
        with self.assertRaises(ValueError):
            DataNormalizer.normalize_financial_record(
                stock_code="",
                record_date="2026-05-16",
                raw={},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
