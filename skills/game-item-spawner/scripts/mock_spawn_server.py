#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded mock server for browser-to-queue status testing.

Mock completion means only that the mock worker simulated the request. It does
not prove that a real game API created or inserted an item into an inventory.
"""
import argparse
import json
import queue
import threading
import time
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

QUEUE_CAPACITY = 128
MAX_COUNT = 25
STATUS_LIMIT = 256


class MockRuntime:
    def __init__(self):
        self.pending = queue.Queue(maxsize=QUEUE_CAPACITY)
        self.statuses = OrderedDict()
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self._work, name="mock-spawn-worker", daemon=True)
        self.worker.start()

    def enqueue(self, item_id, count):
        request = {
            "ok": True,
            "mode": "mock",
            "requestId": uuid.uuid4().hex,
            "itemId": item_id,
            "state": "received",
            "requested": count,
            "spawned": 0,
            "err": "",
            "simulated": True,
        }
        with self.lock:
            self.statuses[request["requestId"]] = request
            self._prune_locked()
        try:
            self.pending.put_nowait(request)
        except queue.Full:
            with self.lock:
                request.update(ok=False, state="rejected", err="mock queue is full")
                self._prune_locked()
            return request, 429

        with self.lock:
            request["state"] = "queued"
        return request, 202

    def get_status(self, request_id):
        with self.lock:
            current = self.statuses.get(request_id)
            return dict(current) if current else None

    def health(self):
        return {
            "ok": True,
            "mode": "mock",
            "pending": self.pending.qsize(),
            "queueCapacity": QUEUE_CAPACITY,
            "note": "mock completion is simulated; no game inventory is modified",
        }

    def _prune_locked(self):
        while len(self.statuses) > STATUS_LIMIT:
            request_id, oldest = next(iter(self.statuses.items()))
            if oldest["state"] in ("queued", "processing"):
                self.statuses.move_to_end(request_id)
                if all(item["state"] in ("queued", "processing") for item in self.statuses.values()):
                    break
            else:
                self.statuses.popitem(last=False)

    def _work(self):
        while True:
            request = self.pending.get()
            if request is None:
                self.pending.task_done()
                return
            with self.lock:
                request["state"] = "processing"
            for _ in range(request["requested"]):
                time.sleep(0.025)
                with self.lock:
                    request["spawned"] += 1
            with self.lock:
                request["state"] = "succeeded"
                request["err"] = ""
                self._prune_locked()
            self.pending.task_done()


class Handler(BaseHTTPRequestHandler):
    runtime = None

    def _origin_allowed(self):
        origin = self.headers.get("Origin")
        return not origin or origin in self.server.allowed_origins

    def do_OPTIONS(self):
        if not self._origin_allowed():
            self._send(403, {"ok": False, "state": "rejected", "err": "origin not allowed"})
            return
        self._send(204, None)

    def do_GET(self):
        if not self._origin_allowed():
            self._send(403, {"ok": False, "state": "rejected", "err": "origin not allowed"})
            return
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)

        if parsed.path == "/api/health":
            self._send(200, self.runtime.health())
            return

        if parsed.path == "/api/spawn":
            item_id = query.get("itemId", [""])[0]
            count_text = query.get("count", ["1"])[0]
            if not item_id or len(item_id) > 128 or any(ord(char) < 32 for char in item_id):
                self._send(400, {"ok": False, "state": "rejected", "err": "invalid itemId"})
                return
            try:
                count = int(count_text)
            except ValueError:
                count = 0
            if count < 1 or count > MAX_COUNT:
                self._send(400, {"ok": False, "state": "rejected",
                                 "err": f"count must be 1-{MAX_COUNT}"})
                return
            result, status = self.runtime.enqueue(item_id, count)
            self._send(status, result)
            return

        if parsed.path == "/api/spawn/status":
            request_id = query.get("id", [""])[0]
            result = self.runtime.get_status(request_id)
            if result is None:
                self._send(404, {"ok": False, "err": "unknown requestId"})
            else:
                self._send(200, result)
            return

        self._send(404, {"ok": False, "err": "not found"})

    def _send(self, status, payload):
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        origin = self.headers.get("Origin")
        if origin and origin in self.server.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=26880)
    parser.add_argument(
        "--allow-origin", action="append", default=[],
        help="exact browser origin to allow; repeat for multiple origins "
             "(default: http://localhost:8090 and http://127.0.0.1:8090)",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    runtime = MockRuntime()
    handler = type("BoundHandler", (Handler,), {"runtime": runtime})
    server = ThreadingHTTPServer(("localhost", args.port), handler)
    server.allowed_origins = set(args.allow_origin or [
        "http://localhost:8090", "http://127.0.0.1:8090"
    ])
    server.daemon_threads = True
    print(f"[mock] listening on http://127.0.0.1:{args.port}/ (queue capacity: {QUEUE_CAPACITY})")
    print("[mock] status: /api/spawn returns queued; /api/spawn/status reports mock completion")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock] stopping")
    finally:
        server.shutdown()
        server.server_close()
        try:
            runtime.pending.put_nowait(None)
        except queue.Full:
            pass


if __name__ == "__main__":
    main()
