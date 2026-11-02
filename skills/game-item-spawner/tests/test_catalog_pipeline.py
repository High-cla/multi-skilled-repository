#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for extraction, JSON-to-JS conversion, and safe page rendering."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from extract_catalog import decode_json, extract_json  # noqa: E402
from json_to_js import normalize_catalog, write_js  # noqa: E402


class ExtractCatalogTests(unittest.TestCase):
    def test_extract_ignores_braces_inside_json_strings(self):
        source = (
            b"binary-prefix\xff noise "
            b'{"records":[{"stableId":"alpha","name":"literal } { braces"}]}'
            b" binary-suffix"
        )
        extracted = extract_json(source, b'"records"')
        document, _ = decode_json(extracted)
        self.assertEqual(document["records"][0]["name"], "literal } { braces")

    def test_extract_supports_utf16_resource_text(self):
        source_text = 'prefix {"records":[{"stableId":"utf16"}]} suffix'
        source = source_text.encode("utf-16-le")
        extracted = extract_json(source, b'"records"')
        document, encoding = decode_json(extracted)
        self.assertIn("utf-16", encoding)
        self.assertEqual(document["records"][0]["stableId"], "utf16")

    def test_missing_marker_fails_loudly(self):
        with self.assertRaises(ValueError):
            extract_json(b'{"items":[]}', b'"records"')


class JsonToJsTests(unittest.TestCase):
    def test_normalizes_records_and_id_alias(self):
        items = normalize_catalog({
            "records": [
                {"id": 42, "name": "tool", "categories": "TOOLS", "itemTypes": ["A", "B"]}
            ]
        })
        self.assertEqual(items[0]["stableId"], "42")
        self.assertEqual(items[0]["nameZh"], "tool")
        self.assertEqual(items[0]["categories"], ["TOOLS"])
        self.assertEqual(items[0]["itemTypes"], ["A", "B"])

    def test_duplicate_or_missing_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate stableId"):
            normalize_catalog({"records": [{"stableId": "x"}, {"stableId": "x"}]})
        with self.assertRaisesRegex(ValueError, "stableId"):
            normalize_catalog({"records": [{"nameZh": "no id"}]})

    def test_js_output_is_global_and_escapes_script_markup(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "assets" / "items_data.js"
            items = normalize_catalog({"records": [
                {"stableId": "x", "nameZh": "</script><img src=x onerror=alert(1)>"}
            ]})
            write_js(items, output)
            generated = output.read_text(encoding="utf-8")
            self.assertIn("window.ITEMS =", generated)
            self.assertIn("\\u003c/script\\u003e", generated)
            self.assertNotIn("</script>", generated)


class BrowserSafetyTests(unittest.TestCase):
    def test_catalog_fields_are_not_interpolated_into_html(self):
        html = (ROOT / "assets" / "items_browser.html").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", html)
        self.assertIn("textContent", html)
        self.assertIn("document.createElement", html)
        self.assertIn("/api/spawn/status", html)
        self.assertIn("Mock 模拟完成", html)


if __name__ == "__main__":
    unittest.main()
