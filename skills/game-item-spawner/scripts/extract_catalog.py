#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从二进制 DLL（或任意文件）内嵌资源里提取 JSON 目录 (物品目录等).
原理: 很多游戏把 item-catalog.json 之类内嵌为字节串, 含 UTF-8 中文.
用 "records" 等标志字符串定位, 平衡括号法提取完整 JSON.
也可以直接让用户提供导出好的 JSON — 本脚本是兜底.

用法:
  python extract_catalog.py <dll_or_file> [marker] [out.json]
  - marker: 定位标志 (默认 "records"), 建议用 JSON 里唯一的键名
  - out:   输出 JSON 路径 (默认 <input>.catalog.json)
然后可转 items_data.js: 见 SKILL.md 步骤2
"""
import json
import re
import sys


def extract_json(data: bytes, marker: bytes) -> bytes:
    """找到含 marker 的 JSON 对象, 平衡括号提取."""
    m = re.search(re.escape(marker), data)
    if not m:
        raise ValueError(f"marker {marker!r} not found")
    # 尝试向后找到真实起点 (允许 marker 前有引号/BOM)
    start = data.rfind(b"{", 0, m.start())
    # 如果 rfind 太靠前导致是别的 {, 回退: 从 marker 往回找最近的 { 或带引号键的起点
    if start < 0:
        # 从 marker 字符串往回找 (可能前面有 quote)
        q = data.rfind(b'"', 0, m.start())
        start = data.rfind(b"{", 0, q) if q > 0 else -1
    if start < 0:
        raise ValueError("no '{' before marker")
    depth = 0
    for i in range(start, len(data)):
        c = data[i]
        if c == 0x7B:  # {
            depth += 1
        elif c == 0x7D:  # }
            depth -= 1
            if depth == 0:
                return data[start:i + 1]
    raise ValueError("unbalanced braces")


def decode_json(js: bytes):
    """尝试多种编码解析 JSON."""
    errors = []
    for enc in ("utf-8", "utf-16", "gbk"):
        try:
            return json.loads(js.decode(enc)), enc
        except (UnicodeDecodeError, ValueError) as e:
            errors.append(f"{enc}: {e}")
    raise ValueError("cannot decode JSON: " + "; ".join(errors))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    marker = (sys.argv[2] if len(sys.argv) > 2 else '"records"').encode()
    out = sys.argv[3] if len(sys.argv) > 3 else src + ".catalog.json"

    data = open(src, "rb").read()
    js = extract_json(data, marker)
    obj, enc = decode_json(js)
    # 猜测记录数单位
    if isinstance(obj, dict) and "records" in obj:
        n = len(obj["records"])
    elif isinstance(obj, dict):
        n = None
    else:
        n = len(obj)
    open(out, "wb").write(js)
    print(f"extracted {len(js)} bytes -> {out}  (records: {n})")
    # 打印首个记录预览
    recs = obj.get("records", obj) if isinstance(obj, dict) else obj
    if isinstance(recs, list) and recs:
        print("sample:", json.dumps(recs[0], ensure_ascii=False)[:200])


if __name__ == "__main__":
    main()
