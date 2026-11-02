#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 DLL/资源文件中提取内嵌 JSON 目录。

用法:
  python extract_catalog.py <dll_or_file> [marker] [out.json]

默认查找 JSON 键 "records"，输出 <input>.catalog.json。
提取后使用 json_to_js.py 将 JSON 转为网页加载的 items_data.js。
"""
import json
import sys
from pathlib import Path


def _balanced_end(text: str, start: int) -> int:
    """返回 start 处 JSON 对象/数组的结束位置；字符串中的括号不参与计数。"""
    if start >= len(text) or text[start] not in "{[":
        raise ValueError("JSON value must start with '{' or '['")
    pairs = {"{": "}", "[": "]"}
    stack = []
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in pairs:
            stack.append(pairs[char])
        elif char in "}]":
            if not stack or stack[-1] != char:
                raise ValueError("mismatched JSON brackets")
            stack.pop()
            if not stack:
                return index + 1
    raise ValueError("unbalanced JSON brackets")


def _decode_candidates(data: bytes):
    # errors=ignore discards arbitrary non-text bytes around a resource; the
    # extracted candidate is still required to pass json.loads before use.
    for encoding in ("utf-8-sig", "utf-16-le", "utf-16-be", "gbk"):
        try:
            text = data.decode(encoding, errors="ignore")
        except (LookupError, UnicodeError):
            continue
        yield encoding, text


def extract_json(data: bytes, marker: bytes) -> bytes:
    """定位包含 marker 的完整 JSON 值，并验证其可解析性。"""
    marker_text = marker.decode("utf-8", errors="strict")
    failures = []
    for encoding, text in _decode_candidates(data):
        cursor = 0
        while True:
            position = text.find(marker_text, cursor)
            if position < 0:
                break
            start = text.rfind("{", 0, position)
            while start >= 0:
                try:
                    end = _balanced_end(text, start)
                    candidate = text[start:end]
                    if marker_text in candidate:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, (dict, list)):
                            return candidate.encode(encoding.replace("-sig", ""))
                except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                    failures.append(str(exc))
                start = text.rfind("{", 0, start)
            cursor = position + len(marker_text)
    detail = failures[-1] if failures else "marker not found in a decodable text region"
    raise ValueError("could not locate a valid JSON object containing marker: " + detail)


def decode_json(raw: bytes):
    errors = []
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gbk"):
        try:
            return json.loads(raw.decode(encoding)), encoding
        except (UnicodeDecodeError, ValueError) as exc:
            errors.append(f"{encoding}: {exc}")
    raise ValueError("cannot decode extracted JSON: " + "; ".join(errors))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        return 2
    source = Path(args[0])
    marker = (args[1] if len(args) > 1 else '"records"').encode("utf-8")
    output = Path(args[2]) if len(args) > 2 else Path(str(source) + ".catalog.json")

    raw = source.read_bytes()
    extracted = extract_json(raw, marker)
    obj, encoding = decode_json(extracted)
    output.write_bytes(extracted)

    records = obj.get("records", obj) if isinstance(obj, dict) else obj
    count = len(records) if isinstance(records, (list, dict)) else 0
    print(f"extracted {len(extracted)} bytes -> {output} (encoding: {encoding}, records: {count})")
    if isinstance(records, list) and records:
        print("sample:", json.dumps(records[0], ensure_ascii=False)[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
