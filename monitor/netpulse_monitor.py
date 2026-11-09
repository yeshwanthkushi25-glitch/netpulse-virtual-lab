#!/usr/bin/env python3
"""Check VM reachability and report the result to NetPulse.

Uses only the Python standard library so it can run directly on lab VMs.
Includes flap damping / retry thresholds to avoid false alarms from transient jitter.
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


def build_result(source, target, timeout=2.0, simulate=None, consecutive_failures=0, threshold=1):
    if simulate:
        latency = 1.25 if simulate == "up" else (45.8 if simulate == "degraded" else None)
        msg_map = {
            "up": "Simulated reachable link",
            "degraded": "Simulated link degradation (Packet latency spike)",
            "down": "Simulated failed link",
        }
        return CheckResult(
            source=source,
            target=target,
            status=simulate,
            checked_at=utc_now(),
            latency_ms=latency,
            message=msg_map.get(simulate, "Simulated status"),
        )

    is_up, latency, message = run_ping(target, timeout)
    if is_up:
        return CheckResult(source, target, "up", utc_now(), latency, message)

    # Flap damping: if consecutive failures haven't reached threshold, report degraded
    if consecutive_failures < threshold:
        return CheckResult(
            source=source,
            target=target,
            status="degraded",
            checked_at=utc_now(),
            latency_ms=None,
            message=f"Transient drop detected ({consecutive_failures}/{threshold}): {message}",
        )

    return CheckResult(source, target, "down", utc_now(), latency, message)


def send_status(api_url, result, api_key=None, timeout=10):
    endpoint = f"{api_url.rstrip('/')}/status"
    headers = {"Content-Type": "application/json", "User-Agent": "NetPulse-Monitor/1.0"}
    if api_key:
        headers["x-api-key"] = api_key

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(asdict(result)).encode("utf-8"),
        headers=headers,
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


def get_target_list(args):
    """Extract list of unique targets from --target or --targets."""
    targets = []
    if getattr(args, "targets", None):
        for t in args.targets:
            clean = t.strip()
            if clean and clean not in targets:
                targets.append(clean)
    if getattr(args, "target", None):
        for t in args.target.split(","):
            clean = t.strip()
            if clean and clean not in targets:
                targets.append(clean)
    return targets


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="NetPulse virtual lab reachability monitor")
    parser.add_argument("--target", default=os.environ.get("NETPULSE_TARGET"), help="VM target hostname/IP (or comma-separated for multiple VMs)")
    parser.add_argument("--targets", nargs="+", default=None, help="List of target hostnames or IP addresses")
    parser.add_argument("--source", default=os.environ.get("NETPULSE_SOURCE", socket.gethostname()), help="VM A display name")
    parser.add_argument("--api-url", default=os.environ.get("NETPULSE_API_URL"), help="API base URL, without /status")
    parser.add_argument("--api-key", default=os.environ.get("NETPULSE_API_KEY"), help="Optional API key for authorization")
    parser.add_argument("--interval", type=float, default=float(os.environ.get("NETPULSE_INTERVAL", "10")), help="Seconds between checks")
    parser.add_argument("--timeout", type=float, default=2.0, help="Ping timeout in seconds")
    parser.add_argument("--consecutive-failures", type=int, default=1, help="Failures required before marking DOWN (flap damping)")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without sending it")
    parser.add_argument("--simulate", choices=("up", "down", "degraded"), help="Simulate a result instead of running ping")
    args = parser.parse_args(argv)
    if not args.target and not args.targets:
        parser.error("--target or --targets or NETPULSE_TARGET is required")
    if not args.target and args.targets:
        args.target = args.targets[0]
    if not args.dry_run and not args.api_url:
        parser.error("--api-url or NETPULSE_API_URL is required unless --dry-run is used")
    if args.interval <= 0 or args.timeout <= 0:
        parser.error("--interval and --timeout must be positive")
    return args


def main(argv=None):
    args = parse_args(argv)
    targets = get_target_list(args)
    fail_counts = {t: 0 for t in targets}
    try:
        while True:
            for target in targets:
                try:
                    # Test ping to track fail_count
                    if not args.simulate:
                        is_up, _, _ = run_ping(target, args.timeout)
                        fail_counts[target] = 0 if is_up else (fail_counts[target] + 1)

                    result = build_result(
                        source=args.source,
                        target=target,
                        timeout=args.timeout,
                        simulate=args.simulate,
                        consecutive_failures=fail_counts[target],
                        threshold=args.consecutive_failures,
                    )
                    payload = asdict(result)
                    if args.dry_run:
                        print(json.dumps(payload, indent=2))
                    else:
                        send_status(args.api_url, result, api_key=args.api_key)
                        print(json.dumps(payload), flush=True)
                except (RuntimeError, ValueError) as exc:
                    print(f"NetPulse error for {target}: {exc}", file=sys.stderr, flush=True)
                    if args.once and len(targets) == 1:
                        return 1
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nNetPulse monitor stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
