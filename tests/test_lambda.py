"""Unit tests for NetPulse AWS Lambda handler (lambda/app.py)."""

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

# Add lambda directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lambda")))

import app  # noqa: E402


class LambdaValidationTests(unittest.TestCase):
    """Test validation and formatting of input payloads."""

    def test_valid_payload_up(self):
        payload = {
            "source": "vm-a",
            "target": "vm-b",
            "status": "up",
            "checked_at": "2026-11-07T10:00:00.000Z",
            "latency_ms": 1.45,
            "message": "VM A connected to VM B",
        }
        item = app.validate_status_payload(payload)
        self.assertEqual(item["connection_id"], "vm-a#vm-b")
        self.assertEqual(item["source"], "vm-a")
        self.assertEqual(item["target"], "vm-b")
        self.assertEqual(item["status"], "up")
        self.assertEqual(item["latency_ms"], 1.45)
        self.assertEqual(item["message"], "VM A connected to VM B")
        self.assertTrue(item["checked_at"].endswith("Z"))
        self.assertTrue("received_at" in item)

    def test_valid_payload_degraded(self):
        payload = {
            "source": "vm-a",
            "target": "vm-b",
            "status": "degraded",
            "checked_at": "2026-11-07T10:00:00.000Z",
            "latency_ms": 52.4,
            "message": "Intermittent jitter spike",
        }
        item = app.validate_status_payload(payload)
        self.assertEqual(item["status"], "degraded")
        self.assertEqual(item["latency_ms"], 52.4)

    def test_valid_payload_down(self):
        payload = {
            "source": "vm-a",
            "target": "vm-b",
            "status": "down",
            "checked_at": "2026-11-07T10:00:00.000Z",
            "latency_ms": None,
            "message": "Host unreachable",
        }
        item = app.validate_status_payload(payload)
        self.assertEqual(item["status"], "down")
        self.assertIsNone(item["latency_ms"])

    def test_invalid_status_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.validate_status_payload({"source": "vm-a", "target": "vm-b", "status": "unknown"})

    def test_invalid_identifier_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.validate_status_payload({"source": "vm a invalid!", "target": "vm-b", "status": "up"})

    def test_negative_latency_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.validate_status_payload({
                "source": "vm-a",
                "target": "vm-b",
                "status": "up",
                "latency_ms": -5.0,
                "checked_at": "2026-11-07T10:00:00Z",
            })

    def test_boolean_latency_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.validate_status_payload({
                "source": "vm-a",
                "target": "vm-b",
                "status": "up",
                "latency_ms": True,
                "checked_at": "2026-11-07T10:00:00Z",
            })

    def test_timestamp_without_timezone_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.validate_status_payload({
                "source": "vm-a",
                "target": "vm-b",
                "status": "up",
                "checked_at": "2026-11-07 10:00:00",
            })

    def test_non_dict_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.validate_status_payload("not-a-dict")


class LambdaHandlerContractTests(unittest.TestCase):
    """Test the full Lambda handler routing, DynamoDB interaction, and HTTP responses."""

    def setUp(self):
        self.mock_table = MagicMock()
        self.mock_table.scan.return_value = {"Items": []}
        self.patcher = patch.object(app, "_TABLE", self.mock_table)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_options_cors_preflight(self):
        event = {"httpMethod": "OPTIONS", "path": "/status"}
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 204)
        self.assertEqual(res["headers"]["Access-Control-Allow-Origin"], "*")

    def test_post_validates_and_stores_item(self):
        event = {
            "httpMethod": "POST",
            "path": "/status",
            "body": json.dumps({
                "source": "vm-a",
                "target": "vm-b",
                "status": "up",
                "checked_at": "2026-11-07T12:00:00Z",
                "latency_ms": 2.45,
                "message": "VM connected",
            }),
        }
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertTrue(body["ok"])
        self.assertEqual(body["item"]["connection_id"], "vm-a#vm-b")
        self.mock_table.put_item.assert_called_once()

    def test_post_bad_payload_returns_400(self):
        event = {
            "httpMethod": "POST",
            "path": "/status",
            "body": json.dumps({"source": "vm-a", "status": "bad-status"}),
        }
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 400)
        body = json.loads(res["body"])
        self.assertFalse(body["ok"])
        self.assertIn("error", body)

    def test_get_existing_status_returns_200(self):
        self.mock_table.get_item.return_value = {
            "Item": {
                "connection_id": "vm-a#vm-b",
                "source": "vm-a",
                "target": "vm-b",
                "status": "up",
                "checked_at": "2026-11-07T12:00:00.000Z",
                "latency_ms": Decimal("1.45"),
                "message": "Operational",
            }
        }
        event = {
            "httpMethod": "GET",
            "path": "/status",
            "queryStringParameters": {"source": "vm-a", "target": "vm-b"},
        }
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertTrue(body["ok"])
        self.assertEqual(body["item"]["status"], "up")
        self.assertEqual(body["item"]["latency_ms"], 1.45)
        self.mock_table.get_item.assert_called_once_with(
            Key={"connection_id": "vm-a#vm-b"}, ConsistentRead=True
        )

    def test_get_not_found_returns_404(self):
        self.mock_table.get_item.return_value = {}
        event = {
            "httpMethod": "GET",
            "path": "/status",
            "queryStringParameters": {"source": "vm-a", "target": "vm-b"},
        }
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 404)
        body = json.loads(res["body"])
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "unknown")

    def test_get_all_connections(self):
        self.mock_table.scan.return_value = {
            "Items": [
                {"connection_id": "vm-a#vm-b", "status": "up"},
                {"connection_id": "vm-a#vm-c", "status": "down"}
            ]
        }
        event = {"httpMethod": "GET", "path": "/connections"}
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertEqual(len(body["connections"]), 2)

    def test_api_key_auth_rejected_when_configured(self):
        with patch.object(app, "API_KEY", "secret-token-123"):
            event = {
                "httpMethod": "POST",
                "path": "/status",
                "headers": {"x-api-key": "wrong-token"},
                "body": json.dumps({"source": "vm-a", "target": "vm-b", "status": "up", "checked_at": "2026-11-07T12:00:00Z"}),
            }
            res = app.handler(event, None)
            self.assertEqual(res["statusCode"], 401)

    def test_unsupported_path_returns_404(self):
        event = {"httpMethod": "GET", "path": "/invalid-route"}
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 404)

    def test_unsupported_method_returns_405(self):
        event = {"httpMethod": "DELETE", "path": "/status"}
        res = app.handler(event, None)
        self.assertEqual(res["statusCode"], 405)


if __name__ == "__main__":
    unittest.main()
