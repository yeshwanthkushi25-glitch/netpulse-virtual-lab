#!/usr/bin/env python3
"""NetPulse Local Development Server & Offline Demo Runner.

Serves the NetPulse dashboard on http://localhost:8000 and mocks the AWS
API Gateway + Lambda + DynamoDB backend in memory.

Usage:
    python scripts/local_demo.py          # Run local server and API
    python scripts/local_demo.py --demo   # Run server with automated multi-phase demo
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
VALID_STATUSES = {"up", "down", "degraded"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_item(source: str, target: str, status: str, latency_ms: float | None = None, message: str = ""):
    if not message:
        if status == "up":
            message = "VMs are connected and reachable."
        elif status == "degraded":
            message = "Transient packet latency spike detected."
        else:
            message = "Target host is unreachable."
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
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}.")
    latency = data.get("latency_ms")
    if latency is not None:
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            raise ValueError("latency_ms must be numeric or null.")
        if latency < 0 or latency > 3600000:
            raise ValueError("latency_ms out of range.")
        latency = round(float(latency), 3)
    default_msg = "Target reachable" if status == "up" else ("Link degraded" if status == "degraded" else "Target unreachable")
    message = data.get("message", default_msg)
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-api-key, Authorization")
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

        if path == "/connections":
            self._send_json(200, {"ok": True, "connections": list(STORE.values()), "count": len(STORE)})
            return

        if path == "/status":
            params = urllib.parse.parse_qs(parsed.query)
            if not params:
                self._send_json(200, {"ok": True, "connections": list(STORE.values()), "count": len(STORE)})
                return
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

                if item["status"] == "up":
                    status_color = "\033[92m● UP\033[0m"
                elif item["status"] == "degraded":
                    status_color = "\033[93m● DEGRADED\033[0m"
                else:
                    status_color = "\033[91m● DOWN\033[0m"

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
    """Demonstrates: Green connected -> Degraded Jitter -> Link Failure -> Recovery."""
    key = f"{source}#{target}"
    time.sleep(1.0)
    print("\n" + "=" * 65)
    print("  🚀 NETPULSE AUTOMATED DEMO SEQUENCE INITIATED")
    print("=" * 65)

    # Phase 1: Operational Green
    print("\n[Phase 1/4] Normal Reachability (Green Light)")
    STORE[key] = make_item(source, target, "up", 1.34, "VM A and VM B connected via VirtualBox host-only adapter.")
    print("  Status stored: UP (1.34 ms). Dashboard showing operational light.")
    time.sleep(6.0)

    # Phase 2: Transient Jitter / Degraded State (Amber Light)
    print("\n[Phase 2/4] Transient Jitter Spike / Packet Loss Warning (Amber Light)")
    STORE[key] = make_item(source, target, "degraded", 48.6, "Flap damping: Single packet loss or latency spike detected.")
    print("  Status stored: DEGRADED (48.6 ms). Dashboard showing warning amber light.")
    time.sleep(6.0)

    # Phase 3: Link Cut (Red Light)
    print("\n[Phase 3/4] Link Severed / Virtual Cable Unplugged (Red Alert Light)")
    STORE[key] = make_item(source, target, "down", None, "Destination Host Unreachable. Connection lost between lab VMs.")
    print("  Status stored: DOWN (None). Dashboard showing critical red light.")
    time.sleep(7.0)

    # Phase 4: Recovery (Back to Green)
    print("\n[Phase 4/4] Connection Restored (Recovery to Green Light)")
    STORE[key] = make_item(source, target, "up", 1.55, "Target reachable. Network link re-established.")
    print("  Status stored: UP (1.55 ms). Dashboard recovered to green light.")
    print("\n" + "=" * 65)
    print("  ✅ FULL DEMONSTRATION CYCLE COMPLETE")
    print("  The local server remains active for interactive grading.")
    print("=" * 65 + "\n")


class ThreadedTCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="NetPulse Local Dashboard & Mock API Server")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--demo", action="store_true", help="Run automated green -> degraded -> down -> recovery demo")
    parser.add_argument("--open", action="store_true", help="Open default web browser automatically")
    parser.add_argument("--source", default="vm-a", help="Default source VM name (default: vm-a)")
    parser.add_argument("--target", default="vm-b", help="Default target VM name (default: vm-b)")
    args = parser.parse_args()

    # Pre-populate store
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
