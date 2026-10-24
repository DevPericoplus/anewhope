"""Contrato del colector: clasificación, stub_status y tablas por app."""

import os
import tempfile
import unittest

from nginx_monitor.parse import classify, parse_line, parse_stub
from nginx_monitor.store import connect, insert_requests, stats


class ParseTest(unittest.TestCase):
    def test_apps(self):
        self.assertEqual(classify("www.laim.app", 443), "laimweb")
        self.assertEqual(classify("www.getmylllm.com", 443), "frontend")
        self.assertEqual(classify("www.getmylllm.com", 8443), "backoffice")
        self.assertEqual(classify("artifactory.anewhope.silicon.loc", 443), "")

    def test_line_drops_query_and_ip(self):
        row = parse_line(
            '{"ts":"2026-10-24T16:00:00+00:00","host":"www.laim.app","port":443,'
            '"ip":"203.0.113.8","method":"GET","path":"/foro/hilo?token=secret",'
            '"status":200,"bytes":1200,"rt":0.042,"urt":"0.031"}'
        )
        self.assertEqual(row["app"], "laimweb")
        self.assertEqual(row["feature"], "/foro")
        self.assertNotIn("203.0.113.8", row["visitor"])
        self.assertEqual(row["request_ms"], 42)
        self.assertNotIn("token", row["path"])

    def test_stub(self):
        text = "Active connections: 3\nserver accepts handled requests\n 10 10 25\nReading: 1 Writing: 1 Waiting: 1\n"
        got = parse_stub(text)
        self.assertEqual(got["active"], 3)
        self.assertEqual(got["requests"], 25)
        self.assertEqual(got["handled"], 10)


class StoreTest(unittest.TestCase):
    def test_tables_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(os.path.join(tmp, "nginx.db"))
            insert_requests(conn, [
                {"app": "laimweb", "ts": "2026-10-24T16:01:00", "visitor": "a",
                 "method": "GET", "path": "/", "feature": "inicio", "status": 200,
                 "bytes": 10, "request_ms": 5, "upstream_ms": 4},
                {"app": "frontend", "ts": "2026-10-24T16:01:00", "visitor": "b",
                 "method": "GET", "path": "/", "feature": "inicio", "status": 500,
                 "bytes": 3, "request_ms": 80, "upstream_ms": 70},
            ])
            laim = stats(conn, "laimweb")
            front = stats(conn, "frontend")
            self.assertEqual(laim["requests"], 1)
            self.assertEqual(laim["s2xx"], 1)
            self.assertEqual(front["s5xx"], 1)
            self.assertEqual(laim["s5xx"], 0)


if __name__ == "__main__":
    unittest.main()
