"""Integration tests for NetPulse local server (scripts/local_demo.py)."""

import json
import os
import sys
import unittest
from datetime import datetime, timezone

# Add scripts directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import local_demo  # noqa: E402


class LocalDemoValidationTests(unittest.TestCase):
    """Test local server's internal validation and store generation."""

    def test_make_item(self):
        item = local_demo.make_item("vm-a", "vm-b", "up", 1.25, "Connected")
        self.assertEqual(item["connection_id"], "vm-a#vm-b")
        self.assertEqual(item["status"], "up")
        self.assertEqual(item["latency_ms"], 1.25)
        self.assertEqual(item["message"], "Connected")

    def test_validate_payload_valid(self):
        payload = {
            "source": "vm-a",
            "target": "vm-b",
            "status": "down",
            "message": "Link severed",
        }
        item = local_demo.validate_payload(payload)
        self.assertEqual(item["status"], "down")
        self.assertIsNone(item["latency_ms"])
        self.assertEqual(item["connection_id"], "vm-a#vm-b")

    def test_validate_payload_invalid_status(self):
        with self.assertRaises(ValueError):
            local_demo.validate_payload({"source": "vm-a", "target": "vm-b", "status": "maybe"})

    def test_validate_payload_invalid_identifier(self):
        with self.assertRaises(ValueError):
            local_demo.validate_payload({"source": "bad id $$", "target": "vm-b", "status": "up"})


if __name__ == "__main__":
    unittest.main()
