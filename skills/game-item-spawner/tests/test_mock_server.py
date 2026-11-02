#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTP-level tests for the mock spawn queue and origin policy."""
import http.client
import json
import queue
from collections import OrderedDict
import sys
import threading
import time
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mock_spawn_server import Handler, MockRuntime  # noqa: E402


class MockServerHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = MockRuntime()
        handler = type("TestHandler", (Handler,), {"runtime": cls.runtime})
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server.allowed_origins = {
            "http://localhost:8090",
            "http://127.0.0.1:8090",
        }
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, origin=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {}
        if origin:
            headers["Origin"] = origin
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        headers = dict(response.getheaders())
        connection.close()
        return status, headers, json.loads(payload) if payload else None

    def test_health_identifies_mock_mode(self):
        status, _, body = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "mock")
        self.assertIn("queueCapacity", body)

    def test_spawn_is_queued_then_completes_as_mock(self):
        status, _, accepted = self.request("/api/spawn?itemId=fixture.item&count=2")
        self.assertEqual(status, 202)
        self.assertIn(accepted["state"], ("queued", "processing", "succeeded"))
        self.assertTrue(accepted["requestId"])

        deadline = time.time() + 3
        result = None
        while time.time() < deadline:
            status, _, result = self.request(
                "/api/spawn/status?id=" + accepted["requestId"]
            )
            if result and result["state"] == "succeeded":
                break
            time.sleep(0.02)

        self.assertEqual(status, 200)
        self.assertEqual(result["mode"], "mock")
        self.assertTrue(result["simulated"])
        self.assertEqual(result["spawned"], 2)
        self.assertEqual(result["state"], "succeeded")

    def test_untrusted_origin_is_rejected_before_enqueue(self):
        status, _, body = self.request(
            "/api/spawn?itemId=must.not.enqueue",
            origin="https://attacker.example",
        )
        self.assertEqual(status, 403)
        self.assertEqual(body["state"], "rejected")
        self.assertEqual(body["err"], "origin not allowed")

    def test_allowed_origin_gets_exact_cors_header(self):
        status, headers, _ = self.request(
            "/api/health", origin="http://localhost:8090"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://localhost:8090")
        self.assertEqual(headers.get("Vary"), "Origin")

    def test_invalid_count_is_rejected(self):
        status, _, body = self.request("/api/spawn?itemId=x&count=999")
        self.assertEqual(status, 400)
        self.assertEqual(body["state"], "rejected")

    def test_full_queue_is_rejected_with_429(self):
        runtime = MockRuntime.__new__(MockRuntime)
        runtime.pending = queue.Queue(maxsize=1)
        runtime.statuses = OrderedDict()
        runtime.lock = threading.Lock()
        runtime.pending.put_nowait(object())
        request, status = runtime.enqueue("overflow.item", 1)
        self.assertEqual(status, 429)
        self.assertEqual(request["state"], "rejected")
        self.assertEqual(request["err"], "mock queue is full")


if __name__ == "__main__":
    unittest.main()
