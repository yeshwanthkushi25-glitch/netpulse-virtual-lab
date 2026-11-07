"""Unit tests for NetPulse reachability monitor (monitor/netpulse_monitor.py)."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add monitor directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "monitor")))

import netpulse_monitor as monitor  # noqa: E402


class MonitorPingTests(unittest.TestCase):
    """Test ping command construction and output parsing across OS platforms."""

    def test_ping_command_windows(self):
        cmd = monitor.ping_command("192.168.56.102", timeout=2.5, system="windows")
        self.assertEqual(cmd, ["ping", "-n", "1", "-w", "2500", "192.168.56.102"])

    def test_ping_command_linux(self):
        cmd = monitor.ping_command("192.168.56.102", timeout=3.0, system="linux")
        self.assertEqual(cmd, ["ping", "-c", "1", "-W", "3", "192.168.56.102"])

    def test_ping_command_darwin(self):
        cmd = monitor.ping_command("192.168.56.102", timeout=2.0, system="darwin")
        self.assertEqual(cmd, ["ping", "-c", "1", "-W", "2000", "192.168.56.102"])

    def test_latency_regex_windows_style(self):
        output = "Reply from 192.168.56.102: bytes=32 time=4ms TTL=64"
        match = monitor.LATENCY_PATTERN.search(output)
        self.assertIsNotNone(match)
        self.assertEqual(float(match.group(1)), 4.0)

    def test_latency_regex_windows_sub_millisecond(self):
        output = "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128"
        match = monitor.LATENCY_PATTERN.search(output)
        self.assertIsNotNone(match)
        self.assertEqual(float(match.group(1)), 1.0)

    def test_latency_regex_linux_style(self):
        output = "64 bytes from 192.168.56.102: icmp_seq=1 ttl=64 time=0.835 ms"
        match = monitor.LATENCY_PATTERN.search(output)
        self.assertIsNotNone(match)
        self.assertEqual(float(match.group(1)), 0.835)

    def test_build_result_simulation_up(self):
        res = monitor.build_result("vm-a", "vm-b", simulate="up")
        self.assertEqual(res.status, "up")
        self.assertEqual(res.source, "vm-a")
        self.assertEqual(res.target, "vm-b")
        self.assertEqual(res.latency_ms, 1.25)
        self.assertIn("Simulated", res.message)

    def test_build_result_simulation_degraded(self):
        res = monitor.build_result("vm-a", "vm-b", simulate="degraded")
        self.assertEqual(res.status, "degraded")
        self.assertIsNotNone(res.latency_ms)

    def test_build_result_simulation_down(self):
        res = monitor.build_result("vm-a", "vm-b", simulate="down")
        self.assertEqual(res.status, "down")
        self.assertIsNone(res.latency_ms)
        self.assertIn("failed", res.message.lower())

    @patch("netpulse_monitor.run_ping")
    def test_flap_damping_threshold(self, mock_ping):
        # When 1 failure occurs with threshold=2, it reports degraded instead of immediately down
        mock_ping.return_value = (False, None, "No reply")
        res = monitor.build_result("vm-a", "vm-b", consecutive_failures=1, threshold=2)
        self.assertEqual(res.status, "degraded")

        # When 2 failures occur, it reaches threshold and reports down
        res2 = monitor.build_result("vm-a", "vm-b", consecutive_failures=2, threshold=2)
        self.assertEqual(res2.status, "down")


class MonitorNetworkTests(unittest.TestCase):
    """Test HTTP sending and error reporting."""

    @patch("urllib.request.urlopen")
    def test_send_status_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = monitor.CheckResult(
            source="vm-a",
            target="vm-b",
            status="up",
            checked_at="2026-11-07T12:00:00Z",
            latency_ms=1.5,
            message="Reachable",
        )
        api_res = monitor.send_status("http://example.com/api", res, api_key="test-key")
        self.assertTrue(api_res.get("ok"))
        mock_urlopen.assert_called_once()

    def test_cli_argument_parsing(self):
        args = monitor.parse_args(["--target", "192.168.56.102", "--dry-run", "--once", "--consecutive-failures", "2"])
        self.assertEqual(args.target, "192.168.56.102")
        self.assertTrue(args.dry_run)
        self.assertTrue(args.once)
        self.assertEqual(args.consecutive_failures, 2)


if __name__ == "__main__":
    unittest.main()
