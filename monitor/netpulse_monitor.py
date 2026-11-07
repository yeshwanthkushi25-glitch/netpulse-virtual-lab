#!/usr/bin/env python3
"""Check VM reachability and report the result to NetPulse.

Uses only the Python standard library so it can run directly on lab VMs.
"""

import argparse
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

LATENCY_PATTERN = re.compile(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE)


@dataclass
class CheckResult:
    source: str
    target: str
    status: str
    checked_at: str
    latency_ms: Optional[float]
    message: str


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ping_command(target, timeout, system=None):
    system = (system or platform.system()).lower()
    timeout_ms = max(1, int(timeout * 1000))
    if system == "windows":
        return ["ping", "-n", "1", "-w", str(timeout_ms), target]
    if system == "darwin":
        return ["ping", "-c", "1", "-W", str(timeout_ms), target]
    timeout_seconds = max(1, int(round(timeout)))
    return ["ping", "-c", "1", "-W", str(timeout_seconds), target]


def run_ping(target, timeout=2.0, system=None):
    """Return (is_up, latency_ms, diagnostic_message)."""
    command = ping_command(target, timeout, system)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 2,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("The ping command is not installed. Install iputils-ping on Ubuntu/Debian.") from exc
    except subprocess.TimeoutExpired:
        return False, None, "Ping command timed out"

    output = f"{completed.stdout}\n{completed.stderr}".strip()
    match = LATENCY_PATTERN.search(output)
    latency = round(float(match.group(1)), 3) if match else None
    if completed.returncode == 0:
        return True, latency, "Target reachable"
    diagnostic = output.splitlines()[-1][:240] if output else "No reply from target"
    return False, None, diagnostic


def build_result(source, target, timeout=2.0, simulate=None):
    if simulate:
        return CheckResult(
            source=source,
            target=target,
            status=simulate,
            checked_at=utc_now(),
            latency_ms=1.25 if simulate == "up" else None,
            message="Simulated reachable link" if simulate == "up" else "Simulated failed link",
        )
    is_up, latency, message = run_ping(target, timeout)
    return CheckResult(source, target, "up" if is_up else "down", utc_now(), latency, message)


def send_status(api_url, result, timeout=10):
    endpoint = f"{api_url.rstrip('/')}/status"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(asdict(result)).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "NetPulse-Monitor/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            if not 200 <= response.status < 300:
                raise RuntimeError(f"API returned HTTP {response.status}: {response_body}")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach the NetPulse API: {exc.reason}") from exc


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="NetPulse virtual lab reachability monitor")
    parser.add_argument("--target", default=os.environ.get("NETPULSE_TARGET"), help="VM B hostname or IP address")
    parser.add_argument("--source", default=os.environ.get("NETPULSE_SOURCE", socket.gethostname()), help="VM A display name")
    parser.add_argument("--api-url", default=os.environ.get("NETPULSE_API_URL"), help="API base URL, without /status")
    parser.add_argument("--interval", type=float, default=float(os.environ.get("NETPULSE_INTERVAL", "10")), help="Seconds between checks")
    parser.add_argument("--timeout", type=float, default=2.0, help="Ping timeout in seconds")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without sending it")
    parser.add_argument("--simulate", choices=("up", "down"), help="Simulate a result instead of running ping")
    args = parser.parse_args(argv)
    if not args.target:
        parser.error("--target or NETPULSE_TARGET is required")
    if not args.dry_run and not args.api_url:
        parser.error("--api-url or NETPULSE_API_URL is required unless --dry-run is used")
    if args.interval <= 0 or args.timeout <= 0:
        parser.error("--interval and --timeout must be positive")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        while True:
            try:
                result = build_result(args.source, args.target, args.timeout, args.simulate)
                payload = asdict(result)
                if args.dry_run:
                    print(json.dumps(payload, indent=2))
                else:
                    send_status(args.api_url, result)
                    print(json.dumps(payload), flush=True)
            except (RuntimeError, ValueError) as exc:
                print(f"NetPulse error: {exc}", file=sys.stderr, flush=True)
                if args.once:
                    return 1
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nNetPulse monitor stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
