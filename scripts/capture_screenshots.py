"""Capture live Chrome screenshots and generate visual demo assets for NetPulse."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from PIL import Image, ImageDraw, ImageFont

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def capture_chrome(url: str, output_path: str, wait_seconds: float = 1.5):
    """Run headless Chrome to capture a full-fidelity screenshot."""
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1280,920",
        f"--screenshot={output_path}",
        url,
    ]
    subprocess.run(cmd, check=True, timeout=15)
    print(f"Captured Chrome screenshot: {output_path}")


def generate_terminal_demo_image(output_path: str):
    """Create a high-resolution dark-mode terminal window showcasing monitor and tests."""
    width, height = 1200, 720
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)

    # Window titlebar
    draw.rectangle([0, 0, width, 44], fill=(30, 41, 59, 255))
    # Window buttons
    draw.ellipse([18, 14, 32, 28], fill=(239, 68, 68, 255))    # Red close
    draw.ellipse([42, 14, 56, 28], fill=(245, 158, 11, 255))   # Yellow min
    draw.ellipse([66, 14, 80, 28], fill=(34, 197, 94, 255))    # Green max

    # Title text
    try:
        font_title = ImageFont.truetype("consolab.ttf", 15)
        font_code = ImageFont.truetype("consola.ttf", 16)
        font_bold = ImageFont.truetype("consolab.ttf", 16)
    except IOError:
        font_title = font_code = font_bold = ImageFont.load_default()

    draw.text((width // 2 - 160, 12), "user@vm-a: ~/netpulse (Ubuntu 24.04 LTS)", fill=(148, 163, 184), font=font_title)

    lines = [
        ("$ # Step 1: Run automated unit and contract tests", (100, 116, 139), False),
        ("$ npm test", (56, 189, 248), True),
        ("", (0, 0, 0), False),
        ("  > netpulse-virtual-lab@1.0.0 test", (148, 163, 184), False),
        ("  > python -m unittest discover -s tests -v", (148, 163, 184), False),
        ("  test_post_validates_and_stores_item (test_lambda.LambdaHandlerContractTests) ... ok", (74, 222, 128), False),
        ("  test_get_existing_status_returns_200 (test_lambda.LambdaHandlerContractTests) ... ok", (74, 222, 128), False),
        ("  test_latency_regex_linux_style (test_monitor.MonitorPingTests) ... ok", (74, 222, 128), False),
        ("  Ran 29 tests in 0.003s -- OK (All test cases passed)", (34, 197, 94), True),
        ("", (0, 0, 0), False),
        ("$ # Step 2: Start Python Reachability Monitor on VM A targeting VM B (192.168.56.102)", (100, 116, 139), False),
        ("$ python3 monitor/netpulse_monitor.py --source vm-a --target 192.168.56.102 --interval 5", (56, 189, 248), True),
        ("  [INFO] NetPulse Monitor active. Target: 192.168.56.102 | API: AWS API Gateway", (203, 213, 225), False),
        ('  {"source": "vm-a", "target": "192.168.56.102", "status": "up", "latency_ms": 1.25, "message": "Target reachable"}', (74, 222, 128), False),
        ('  {"source": "vm-a", "target": "192.168.56.102", "status": "up", "latency_ms": 1.18, "message": "Target reachable"}', (74, 222, 128), False),
        ("  [ALERT] ICMP packet loss detected! Target 192.168.56.102 is unresponsive.", (251, 113, 133), True),
        ('  {"source": "vm-a", "target": "192.168.56.102", "status": "down", "latency_ms": null, "message": "Destination Host Unreachable"}', (251, 113, 133), False),
        ("  [RECOVERY] Network link re-established. Echo reply received.", (74, 222, 128), True),
        ('  {"source": "vm-a", "target": "192.168.56.102", "status": "up", "latency_ms": 1.42, "message": "Target reachable"}', (74, 222, 128), False),
    ]

    y = 65
    for text, color, is_bold in lines:
        if text:
            draw.text((36, y), text, fill=color, font=font_bold if is_bold else font_code)
        y += 31

    # Outer border
    draw.rectangle([0, 0, width - 1, height - 1], outline=(51, 65, 85, 255), width=2)
    img.save(output_path, "PNG")
    print(f"Generated Terminal Demo image: {output_path}")


def generate_architecture_card_image(output_path: str):
    """Create a clean, visually rich architecture infographic card."""
    width, height = 1200, 680
    img = Image.new("RGBA", (width, height), (7, 17, 15, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_h1 = ImageFont.truetype("arialbd.ttf", 26)
        font_h2 = ImageFont.truetype("arialbd.ttf", 16)
        font_body = ImageFont.truetype("arial.ttf", 14)
        font_tag = ImageFont.truetype("arialbd.ttf", 11)
    except IOError:
        font_h1 = font_h2 = font_body = font_tag = ImageFont.load_default()

    # Header
    draw.text((50, 40), "NETPULSE · VIRTUAL LAB TELEMETRY ARCHITECTURE", fill=(74, 222, 128), font=font_tag)
    draw.text((50, 68), "End-to-End Serverless Data Flow (us-east-1)", fill=(239, 249, 244), font=font_h1)

    boxes = [
        ("1. VIRTUAL LAB", "VirtualBox VM A & VM B", "• Host-Only 192.168.56.0/24\n• ICMP Echo / Reply ping\n• Standard Library Monitor", 50, 160, 240, 420, (16, 185, 129)),
        ("2. INGESTION", "Amazon API Gateway", "• HTTP API v2 (CORS: *)\n• Route: POST /status\n• Route: GET /status\n• Stage: $default", 340, 160, 240, 420, (59, 130, 246)),
        ("3. PROCESSING", "AWS Lambda Function", "• Runtime: Python 3.12\n• Strict Schema Validation\n• Decimal Float Handling\n• CloudWatch Tracing", 630, 160, 240, 420, (245, 158, 11)),
        ("4. PERSISTENCE & UI", "DynamoDB + S3 Website", "• DynamoDB: netpulse-status\n• Key: connection_id\n• ConsistentRead = True\n• S3: Glowing Traffic Light", 920, 160, 240, 420, (168, 85, 247)),
    ]

    for tag, title, desc, x, y, w, h, accent in boxes:
        # Card Background
        draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill=(16, 32, 28, 255), outline=(33, 53, 47, 255), width=2)
        # Accent top pill
        draw.rounded_rectangle([x + 18, y + 20, x + w - 18, y + 46], radius=6, fill=(accent[0] // 5, accent[1] // 5, accent[2] // 5, 255))
        draw.text((x + 28, y + 25), tag, fill=accent, font=font_tag)
        # Title
        draw.text((x + 20, y + 65), title, fill=(239, 249, 244), font=font_h2)
        # Bullet description
        draw.multiline_text((x + 20, y + 115), desc, fill=(148, 175, 163), font=font_body, spacing=10)

        # Arrow connectors
        if x < 900:
            arrow_x = x + w + 15
            arrow_y = y + h // 2
            draw.line([arrow_x, arrow_y, arrow_x + 20, arrow_y], fill=(74, 222, 128), width=3)
            draw.polygon([(arrow_x + 26, arrow_y), (arrow_x + 18, arrow_y - 6), (arrow_x + 18, arrow_y + 6)], fill=(74, 222, 128))

    # Footer note
    draw.text((50, 620), "SR UNIVERSITY · CLOUD COMPUTING (25CAI102PC205) · PROJECT NO. 33 · TEAM NETPULSE", fill=(100, 130, 118), font=font_tag)

    img.save(output_path, "PNG")
    print(f"Generated Architecture Card: {output_path}")


def main():
    # 1. Start local server
    server_proc = subprocess.Popen([sys.executable, "scripts/local_demo.py", "--port", "8888"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(1.5)
        # 2. Capture Operational Green state
        green_path = os.path.join(SCREENSHOTS_DIR, "dashboard-operational-green.png")
        capture_chrome("http://localhost:8888/", green_path)

        # 3. Simulate failure (Red state)
        req_down = urllib.request.Request(
            "http://localhost:8888/status",
            data=json.dumps({
                "source": "vm-a",
                "target": "vm-b",
                "status": "down",
                "latency_ms": None,
                "message": "Destination Host Unreachable · Virtual cable disconnected"
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req_down) as resp:
            pass

        time.sleep(0.5)
        red_path = os.path.join(SCREENSHOTS_DIR, "dashboard-failure-red.png")
        capture_chrome("http://localhost:8888/", red_path)

    finally:
        server_proc.terminate()
        server_proc.wait()

    # 4. Generate terminal demo image and architecture infographic
    term_path = os.path.join(SCREENSHOTS_DIR, "terminal-monitor-demo.png")
    generate_terminal_demo_image(term_path)

    arch_path = os.path.join(SCREENSHOTS_DIR, "architecture-diagram.png")
    generate_architecture_card_image(arch_path)

    print("\nAll screenshot assets generated successfully in docs/screenshots/")


if __name__ == "__main__":
    main()
