# -*- coding: utf-8 -*-
"""DART corp_code 조회 유닛 테스트."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from semi_senti.collector.base import CollectorError
from semi_senti.collector.dart_corp import DartCorpCodeResolver, _parse_corp_xml


# Open DART corpCode.xml 실제 구조: <list> 가 회사 1건, 필드는 list 직속 자식
_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126380</corp_code>
    <corp_name>Samsung</corp_name>
    <stock_code>005930</stock_code>
  </list>
  <list>
    <corp_code>00164779</corp_code>
    <corp_name>SK hynix</corp_name>
    <stock_code>000660</stock_code>
  </list>
  <list>
    <corp_code>00434003</corp_code>
    <corp_name>Unlisted</corp_name>
    <stock_code> </stock_code>
  </list>
</result>
""".encode("utf-8")


class TestDartCorpParsing(unittest.TestCase):
    def test_parse_corp_xml(self) -> None:
        mapping = _parse_corp_xml(_SAMPLE_XML)
        self.assertEqual(len(mapping), 2)
        self.assertEqual(mapping["005930"], "00126380")
        self.assertEqual(mapping["000660"], "00164779")

    def test_resolve_from_cache_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Path(tmpdir) / "dart_corp_codes.json"
            cache.write_text(
                json.dumps({"mapping": {"005930": "00999999"}}),
                encoding="utf-8",
            )
            resolver = DartCorpCodeResolver()
            resolver._cache_path = cache  # noqa: SLF001 — 테스트 전용
            self.assertEqual(resolver.resolve("005930"), "00999999")

    def test_resolve_builtin_when_lookup_fails(self) -> None:
        resolver = DartCorpCodeResolver()
        with mock.patch.object(
            resolver,
            "load_mapping",
            side_effect=CollectorError("no api"),
        ):
            self.assertEqual(resolver.resolve("005930"), "00126380")


if __name__ == "__main__":
    unittest.main(verbosity=2)
