#!/usr/bin/env python3
"""NetPulse Local Development Server & Offline Demo Runner.

Serves the NetPulse dashboard on http://localhost:8000 and mocks the AWS
API Gateway + Lambda + DynamoDB backend in memory.

Usage:
    python scripts/local_demo.py          # Run local server and API
    python scripts/local_demo.py --demo   # Run server with automated failure/recovery demo
"""

import argparse
import http.server
import json
import mimetypes
import os
import re
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone

STORE: dict[str, dict] = {}
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_item(source: str, target: str, status: str, latency_ms: float | None = None, message: str = ""):
    if not message:
        message = "VMs are connected and reachable." if status == "up" else "Target host is unreachable."
    now = utc_now()
    return {
        "connection_id": f"{source}#{target}",
        "source": source,
        "target": target,
        "status": status,
        "checked_at": now,
        "latency_ms": round(float(latency_ms), 3) if latency_ms is not None else None,
        "message": message[:300],
        "received_at": now,
    }


def validate_payload(data: dict):
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object.")
    source = data.get("source")
    target = data.get("target")
    if not isinstance(source, str) or not IDENTIFIER_RE.fullmatch(source):
        raise ValueError("Invalid 'source' identifier.")
    if not isinstance(target, str) or not IDENTIFIER_RE.fullmatch(target):
        raise ValueError("Invalid 'target' identifier.")
    status = data.get("status")
    if status not in ("up", "down"):
        raise ValueError("status must be 'up' or 'down'.")
    latency = data.get("latency_ms")
    if latency is not None:
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise ValueError("latency_ms must be numeric or null.")
        if latency < 0 or latency > 3600000:
            raise ValueError("latency_ms out of range.")
        latency = round(float(latency), 3)
    message = data.get("message", "Target reachable" if status == "up" else "Target unreachable")
    checked_at = data.get("checked_at") or utc_now()

    return {
        "connection_id": f"{source}#{target}",
        "source": source,
        "target": target,
        "status": status,
        "checked_at": checked_at,
        "latency_ms": latency,
        "message": str(message)[:300],
        "received_at": utc_now(),
    }


class NetPulseHandler(http.server.BaseHTTPRequestHandler):
    dashboard_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard"))

    def log_message(self, format_str, *args):
        # Override to keep server console logs clean
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} - {args[1]}\n")

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-api-key")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/status":
            params = urllib.parse.parse_qs(parsed.query)
            source = params.get("source", ["vm-a"])[0]
            target = params.get("target", ["vm-b"])[0]
            key = f"{source}#{target}"
            item = STORE.get(key)
            if item:
                self._send_json(200, {"ok": True, "item": item})
            else:
                self._send_json(
                    404,
                    {
                        "ok": False,
                        "status": "unknown",
                        "error": "No checks have been recorded for this connection.",
                    },
                )
            return

        # Serve static dashboard files
        relative_path = path.lstrip("/")
        if not relative_path or relative_path == "":
            relative_path = "index.html"

        file_path = os.path.abspath(os.path.join(self.dashboard_dir, relative_path))
        # Prevent directory traversal
        if not file_path.startswith(self.dashboard_dir) or not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_error(404, f"File not found: {relative_path}")
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except OSError as exc:
            self.send_error(500, f"Error reading file: {exc}")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path in ("/status", "/simulate"):
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(raw_body)
                item = validate_payload(data)
                STORE[item["connection_id"]] = item
                status_color = "\033[92m● UP\033[0m" if item["status"] == "up" else "\033[91m● DOWN\033[0m"
                latency_str = f"{item['latency_ms']} ms" if item["latency_ms"] is not None else "No response"
                print(f"  [UPDATE] {item['source']} -> {item['target']}: {status_color} ({latency_str}) - {item['message']}")
                self._send_json(200, {"ok": True, "item": item})
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": f"Server error: {exc}"})
            return

        self.send_error(404, "Route not found")


def run_automated_demo(source="vm-a", target="vm-b"):
    """Demonstrates: Green connected -> Simulated Link Failure -> Recovery."""
    key = f"{source}#{target}"
    time.sleep(1.0)
    print("\n" + "=" * 65)
    print("  🚀 NETPULSE AUTOMATED DEMO SEQUENCE INITIATED")
    print("=" * 65)

    # Initial Healthy State
    print("\n[Step 1/3] Normal Connectivity (Green Light)")
    STORE[key] = make_item(source, target, "up", 1.34, "VM A and VM B are connected via VirtualBox network adapter.")
    print(f"  Status stored: UP (1.34 ms). Dashboard showing operational light.")
    time.sleep(7.0)

    # Simulated Failure
    print("\n[Step 2/3] Simulating Link Cut / Cable Unplugged (Red Light)")
    STORE[key] = make_item(source, target, "down", None, "Destination Host Unreachable. Connection lost between VM A and VM B.")
    print(f"  Status stored: DOWN (None). Dashboard showing critical red light.")
    time.sleep(8.0)

    # Recovery
    print("\n[Step 3/3] Restoring Connectivity / Cable Plugged Back (Recovery to Green)")
    STORE[key] = make_item(source, target, "up", 1.82, "Target reachable. Network link restored between lab VMs.")
    print(f"  Status stored: UP (1.82 ms). Dashboard recovered to green light.")
    print("\n" + "=" * 65)
    print("  ✅ DEMO COMPLETED: Link recovery verified.")
    print("  The local server remains active. You can test live pings or refresh the dashboard.")
    print("=" * 65 + "\n")


class ThreadedTCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="NetPulse Local Dashboard & Mock API Server")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--demo", action="store_true", help="Run automated green -> failure -> recovery demo")
    parser.add_argument("--open", action="store_true", help="Open default web browser automatically")
    parser.add_argument("--source", default="vm-a", help="Default source VM name (default: vm-a)")
    parser.add_argument("--target", default="vm-b", help="Default target VM name (default: vm-b)")
    args = parser.parse_args()

    # Pre-populate initial store state so the dashboard has immediate data
    key = f"{args.source}#{args.target}"
    STORE[key] = make_item(args.source, args.target, "up", 1.25, "VirtualBox lab link operational.")

    server = ThreadedTCPServer((args.host, args.port), NetPulseHandler)
    local_url = f"http://localhost:{args.port}"

    print("-" * 65)
    print("   🌐 NetPulse Virtual Lab Network Monitor — Local Server")
    print(f"   Dashboard URL:  {local_url}")
    print(f"   API Endpoint:   {local_url}/status")
    print(f"   Monitoring:     {args.source} -> {args.target}")
    print("-" * 65)

    if args.demo:
        demo_thread = threading.Thread(target=run_automated_demo, args=(args.source, args.target), daemon=True)
        demo_thread.start()

    if args.open:
        webbrowser.open(local_url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NetPulse local server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
