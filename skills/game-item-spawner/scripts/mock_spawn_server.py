#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mock 生成服务器 — 用于无游戏时验证网页全链路.
模拟 /api/health + /api/spawn?itemId=X&count=N 响应.
用法: python mock_spawn_server.py [--port 26880]
然后在浏览器打开网页 → 状态点应变绿 → 点"生成" → toast "已生成: xxx ×1".
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def get_port():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=26880)
    args, _ = p.parse_known_args()
    return args.port


PORT = get_port()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            body = json.dumps({"ok": True}).encode()
        elif path == "/api/spawn":
            body = json.dumps({"ok": True, "queued": "mock x1"}).encode()
        else:
            body = json.dumps({"ok": False, "err": "bad path"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"[mock] spawn server on http://localhost:{PORT}/")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
