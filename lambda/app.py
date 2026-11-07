"""NetPulse API Gateway Lambda handler.

Accepts reachability telemetry, enforces security & validation contracts,
and persists real-time connectivity status in Amazon DynamoDB.
"""

import base64
import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "netpulse-status")
API_KEY = os.environ.get("API_KEY")  # Optional authorization key
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
VALID_STATUSES = {"up", "down", "degraded"}
_TABLE = None


class ValidationError(ValueError):
    """Client supplied an invalid status report."""


class AuthenticationError(Exception):
    """Client failed API key authentication."""


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, x-api-key, Authorization",
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
        "body": json.dumps(payload, default=_json_default),
    }


def _json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _table():
    global _TABLE
    if _TABLE is None:
        import boto3
        _TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _TABLE


def _check_auth(event):
    if not API_KEY:
        return  # Open access mode for local or classroom evaluations
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    token = headers.get("x-api-key") or headers.get("authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]
    if token != API_KEY:
        raise AuthenticationError("Unauthorized: Invalid or missing API key.")


def _identifier(value, field):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError(
            f"{field} must be 1-64 characters using letters, numbers, dots, underscores, or hyphens."
        )
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise ValidationError("checked_at must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("checked_at must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValidationError("checked_at must include a timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def validate_status_payload(data):
    """Validate a telemetry report and return formatted item."""
    if not isinstance(data, dict):
        raise ValidationError("The JSON body must be an object.")

    source = _identifier(data.get("source"), "source")
    target = _identifier(data.get("target"), "target")
    status = data.get("status")
    if status not in VALID_STATUSES:
        raise ValidationError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}.")

    latency = data.get("latency_ms")
    if latency is not None:
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise ValidationError("latency_ms must be a number or null.")
        if not math.isfinite(latency) or not 0 <= latency <= 3_600_000:
            raise ValidationError("latency_ms must be between 0 and 3600000.")
        latency = round(float(latency), 3)

    default_msg = "Target reachable" if status == "up" else ("Link degraded" if status == "degraded" else "Target unreachable")
    message = data.get("message", default_msg)
    if not isinstance(message, str) or len(message) > 300:
        raise ValidationError("message must be a string of at most 300 characters.")

    item = {
        "connection_id": f"{source}#{target}",
        "source": source,
        "target": target,
        "status": status,
        "checked_at": _timestamp(data.get("checked_at")),
        "latency_ms": latency,
        "message": message,
        "received_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }

    # Optional history tracking for latency trend visualization
    if "history" in data and isinstance(data["history"], list):
        item["history"] = data["history"][:20]

    return item


def _dynamodb_item(item):
    return json.loads(json.dumps(item), parse_float=Decimal)


def _parse_body(event):
    body = event.get("body") or "{}"
    try:
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        return json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValidationError("Request body must be valid JSON.") from exc


def _method_and_path(event):
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    method = http.get("method") or event.get("httpMethod") or ""
    path = event.get("rawPath") or event.get("path") or ""
    return method.upper(), path


def handler(event, context):
    """Handle HTTP API routes GET /status, POST /status, and GET /connections."""
    method, path = _method_and_path(event)
    try:
        if method == "OPTIONS":
            return _response(204, {})

        if path.endswith("/connections"):
            # Multi-connection overview route
            scan_res = _table().scan(Limit=50)
            items = scan_res.get("Items", [])
            return _response(200, {"ok": True, "connections": items, "count": len(items)})

        if not path.endswith("/status"):
            return _response(404, {"ok": False, "error": "Route not found."})

        if method == "POST":
            _check_auth(event)
            item = validate_status_payload(_parse_body(event))
            _table().put_item(Item=_dynamodb_item(item))
            LOGGER.info("Stored %s status for %s", item["status"], item["connection_id"])
            return _response(200, {"ok": True, "item": item})

        if method == "GET":
            params = event.get("queryStringParameters") or {}
            source = params.get("source")
            target = params.get("target")

            # If no parameters specified, return all monitored connections
            if not source and not target:
                scan_res = _table().scan(Limit=50)
                items = scan_res.get("Items", [])
                return _response(200, {"ok": True, "connections": items, "count": len(items)})

            source = _identifier(source, "source")
            target = _identifier(target, "target")
            connection_id = f"{source}#{target}"
            result = _table().get_item(Key={"connection_id": connection_id}, ConsistentRead=True)
            item = result.get("Item")
            if not item:
                return _response(
                    404,
                    {
                        "ok": False,
                        "status": "unknown",
                        "error": "No checks have been recorded for this connection.",
                    },
                )
            return _response(200, {"ok": True, "item": item})

        return _response(405, {"ok": False, "error": "Method not allowed."})
    except AuthenticationError as exc:
        return _response(401, {"ok": False, "error": str(exc)})
    except ValidationError as exc:
        return _response(400, {"ok": False, "error": str(exc)})
    except Exception:
        LOGGER.exception("NetPulse request failed")
        return _response(500, {"ok": False, "error": "Internal server error."})
