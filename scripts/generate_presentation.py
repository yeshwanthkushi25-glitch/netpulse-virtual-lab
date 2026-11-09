"""Generate master PowerPoint presentation for NetPulse Cloud Computing Project."""

import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(OUTPUT_DIR, "docs")
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")
PPTX_PATH = os.path.join(OUTPUT_DIR, "NetPulse_Master_Presentation.pptx")

# Palette constants
COLOR_BG_DARK = RGBColor(7, 17, 15)       # #07110F
COLOR_CARD_DARK = RGBColor(16, 32, 28)    # #10201C
COLOR_ACCENT_GREEN = RGBColor(74, 222, 128) # #4ADE80
COLOR_ACCENT_AMBER = RGBColor(251, 191, 36) # #FBBF24
COLOR_ACCENT_RED = RGBColor(251, 113, 133)  # #FB7185
COLOR_TEXT_WHITE = RGBColor(239, 249, 244)  # #EFF9F4
COLOR_TEXT_MUTED = RGBColor(148, 175, 163)  # #94AFA3
COLOR_BORDER = RGBColor(33, 53, 47)       # #21352F


def apply_dark_background(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_BG_DARK


def add_slide_header(slide, title_text, category="SR UNIVERSITY · CLOUD COMPUTING (25CAI102PC205) · PROJECT NO. 33"):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(1.1))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_cat = tf.paragraphs[0]
    p_cat.text = category.upper()
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_ACCENT_GREEN

    p_title = tf.add_paragraph()
    p_title.text = title_text
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_WHITE


def add_bullet_card(slide, left, top, width, height, title, bullets, accent_color=COLOR_ACCENT_GREEN):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLOR_CARD_DARK
    shape.line.color.rgb = COLOR_BORDER
    shape.line.width = Pt(1.5)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.25)
    tf.margin_right = Inches(0.25)
    tf.margin_top = Inches(0.25)
    tf.margin_bottom = Inches(0.25)

    p_head = tf.paragraphs[0]
    p_head.text = title
    p_head.font.size = Pt(16)
    p_head.font.bold = True
    p_head.font.color.rgb = accent_color

    for b in bullets:
        p = tf.add_paragraph()
        p.text = f"•  {b}"
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_TEXT_WHITE
        p.space_before = Pt(8)


def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ==========================================
    # SLIDE 1: Title Slide
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s1)

    tb = s1.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(11.3), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "SR UNIVERSITY · CLOUD COMPUTING (25CAI102PC205)"
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_ACCENT_GREEN

    p1 = tf.add_paragraph()
    p1.text = "NetPulse — Virtual Lab Network Traffic Light"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_TEXT_WHITE
    p1.space_before = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = "Software-Defined Serverless Network Monitoring & Telemetry for VirtualBox Machines"
    p2.font.size = Pt(18)
    p2.font.color.rgb = COLOR_TEXT_MUTED
    p2.space_before = Pt(6)

    p3 = tf.add_paragraph()
    p3.text = "\nProject No.: 33    |    Batch: 59    |    Environment: AWS Learner Lab (us-east-1)"
    p3.font.size = Pt(14)
    p3.font.bold = True
    p3.font.color.rgb = COLOR_ACCENT_AMBER
    p3.space_before = Pt(16)

    p4 = tf.add_paragraph()
    p4.text = (
        "Team Members:\n"
        "• M. Yeshwanth (H.T. No: 2503A53005) — VM Networking, Python Monitor & Telemetry Engine\n"
        "• V. Laxmiprasad (H.T. No: 2503A53006) — AWS Serverless Backend, DynamoDB & Dashboard\n\n"
        "GitHub Repository: https://github.com/yeshwanthkushi25-glitch/netpulse-virtual-lab"
    )
    p4.font.size = Pt(13)
    p4.font.color.rgb = COLOR_TEXT_WHITE
    p4.space_before = Pt(10)

    # ==========================================
    # SLIDE 2: Executive Summary & Problem (Why We Made It)
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s2)
    add_slide_header(s2, "Executive Summary & Why We Made It")

    add_bullet_card(
        s2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "The University Lab Problem",
        [
            "In virtual networking labs, students configure VirtualBox VMs across host-only networks.",
            "Reachability is manually verified via terminal ping commands in isolated CLI windows.",
            "Ephemeral Results: Ping outputs disappear when windows close or scripts exit.",
            "Zero Shared Visibility: Team members and lab instructors cannot see if links are healthy.",
            "Silent Failures: Intermittent connection drops remain unnoticed until larger apps break."
        ],
        COLOR_ACCENT_RED
    )

    add_bullet_card(
        s2, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "The NetPulse Solution",
        [
            "A software-defined, serverless cloud monitor functioning as a virtual traffic light.",
            "Standard Library Python Monitor: Runs on VM A, continuously pinging VM B.",
            "Instant Visual Feedback: Glowing Green = Connected, Pulsing Red = Disconnected.",
            "Centralized Telemetry: Dispatches JSON status to AWS API Gateway in real time.",
            "100% Software Simulation: Meets course goals without needing physical ESP32 or LEDs."
        ],
        COLOR_ACCENT_GREEN
    )

    # ==========================================
    # SLIDE 3: End-to-End System Architecture (How We Made It)
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s3)
    add_slide_header(s3, "System Architecture & 4-Tier Serverless Data Flow")

    arch_img_path = os.path.join(SCREENSHOTS_DIR, "architecture-diagram.png")
    if os.path.exists(arch_img_path):
        s3.shapes.add_picture(arch_img_path, Inches(0.8), Inches(1.8), width=Inches(11.7))

    # ==========================================
    # SLIDE 4: VirtualBox VM Setup & Dual-Adapter Strategy
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s4)
    add_slide_header(s4, "VirtualBox Dual-Adapter Networking Strategy")

    add_bullet_card(
        s4, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Virtual Machine Configuration",
        [
            "Two Ubuntu Virtual Machines configured in Oracle VM VirtualBox.",
            "Adapter 1 (NAT): Provides outbound internet access for VM A to send status to AWS.",
            "Adapter 2 (Host-Only): Private internal subnet (192.168.56.0/24) for inter-VM ICMP checks.",
            "VM A (Monitor Host): Static IP 192.168.56.101, executes netpulse_monitor.py.",
            "VM B (Target Host): Static IP 192.168.56.102, listens for ICMP Echo Requests."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s4, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Link Severing & Recovery Scenarios",
        [
            "Physical Simulation: Unchecking 'Cable Connected' in VirtualBox GUI on VM B.",
            "CLI Simulation: Executing 'sudo ip link set dev enp0s8 down' on VM B.",
            "Software Simulation: Invoking monitor with '--simulate down' or '--simulate degraded'.",
            "Interactive Dashboard Simulation: Clicking 'Simulate Link Cut' directly in web browser.",
            "Automatic Recovery: Reconnecting cable restores green operational state in <5 seconds."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 5: Python Reachability Monitor (netpulse_monitor.py)
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s5)
    add_slide_header(s5, "Python Reachability Monitor Engine")

    add_bullet_card(
        s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Standard Library Architecture",
        [
            "Zero External Dependencies: Built strictly with Python standard library.",
            "subprocess: Executes host ping commands without external ping libraries.",
            "urllib.request: Transmits HTTP POST JSON payloads to AWS API Gateway.",
            "Adaptive Cross-Platform: Automatically constructs Windows (-n) or Linux (-c) flags.",
            "Regex RTT Extraction: Captures sub-millisecond round-trip times accurately."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s5, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Flap Damping & Retry Threshold",
        [
            "Prevents False Alarms: Transient CPU hiccups do not immediately turn the board red.",
            "Configurable Consecutive Failures: '--consecutive-failures 2' dampens flapping.",
            "Degraded Warning State: Detects jitter or single packet loss before full link drop.",
            "Structured Telemetry: Transmits source, target, status, latency_ms, and ISO timestamp.",
            "Security Header: Dispatches optional 'x-api-key' for authenticated cloud intake."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 6: Serverless Backend (AWS Lambda & DynamoDB)
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s6)
    add_slide_header(s6, "Serverless Compute & Persistence (Lambda + DynamoDB)")

    add_bullet_card(
        s6, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "AWS Lambda Ingestion Engine",
        [
            "Runtime: Python 3.12 serverless execution triggered by API Gateway HTTP API v2.",
            "Strict Input Validation: Validates alphanumeric identifiers, status enums, and timestamps.",
            "Security Enforcement: Verifies optional x-api-key / Bearer token authorization.",
            "Decimal Precision Handling: Converts floating-point latency to DynamoDB Decimal safe types.",
            "Route Dispatcher: Handles GET /status, POST /status, and GET /connections."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s6, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Amazon DynamoDB & S3 Website",
        [
            "Table Schema: netpulse-status with Hash Key 'connection_id' (e.g. vm-a#vm-b).",
            "Consistent Read Pattern: Queries with ConsistentRead=True to prevent caching delay.",
            "S3 Static Website: Hosts single-page dashboard assets without EC2 server instances.",
            "Global CORS Headers: Returns Access-Control-Allow-Origin: * for secure browser calls.",
            "Learner Lab Integration: Pre-configured to utilize the default LabRole IAM policy."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 7: Dashboard Features & Audio Alert Engine
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s7)
    add_slide_header(s7, "Responsive Web Dashboard & Interactive Controls")

    add_bullet_card(
        s7, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Dashboard Capabilities",
        [
            "Glanceable Visual States: Glowing Green (Up), Pulsing Amber (Degraded), Flashing Red (Down).",
            "Synthesized Audio Chime: Uses Web Audio API to play alert tones on status transitions.",
            "Telemetry Sparkline: Visualizes latency trends across the last 10 ICMP check cycles.",
            "Uptime Reliability Counter: Calculates real-time connection uptime percentage.",
            "Auto-Polling Engine: Refreshes telemetry seamlessly with visual heartbeat dot."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s7, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Teacher Demo Controller & Latency Slider",
        [
            "Built-in Teacher Demo Rig: No physical ESP32 or breadboards needed.",
            "Interactive Latency Slider: Drag slider (0.5 ms - 300 ms) to adjust latency live.",
            "Numeric Input & Presets: One-click LAN (0.8ms), Lab (2.4ms), WAN (52ms), Jitter (185ms).",
            "Instant Disconnect / Connect: Cut link to trigger Red alert chime, reconnect for Green.",
            "Custom Diagnostic Reason: Type custom messages to demonstrate failure reasons."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 8: Visual Screenshot — Operational Green State
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s8)
    add_slide_header(s8, "Demonstration: Operational Green State (Link Connected)")

    green_img = os.path.join(SCREENSHOTS_DIR, "dashboard-operational-green.png")
    if os.path.exists(green_img):
        s8.shapes.add_picture(green_img, Inches(0.8), Inches(1.8), width=Inches(8.0))

    add_bullet_card(
        s8, Inches(9.1), Inches(1.8), Inches(3.4), Inches(5.0),
        "Operational Highlights",
        [
            "Target VM reachable.",
            "Latency: 1.25 ms.",
            "Status: LINK OPERATIONAL.",
            "Uptime: 100%.",
            "Green aura pulsing.",
            "Audio Chime: Active.",
            "Connection: vm-a → vm-b."
        ],
        COLOR_ACCENT_GREEN
    )

    # ==========================================
    # SLIDE 9: Visual Screenshot — Degraded Amber & Failure Red
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s9)
    add_slide_header(s9, "Demonstration: Degraded Amber & Failure Red States")

    deg_img = os.path.join(SCREENSHOTS_DIR, "dashboard-degraded-amber.png")
    red_img = os.path.join(SCREENSHOTS_DIR, "dashboard-failure-red.png")

    if os.path.exists(deg_img):
        s9.shapes.add_picture(deg_img, Inches(0.8), Inches(1.8), width=Inches(5.6))
    if os.path.exists(red_img):
        s9.shapes.add_picture(red_img, Inches(6.8), Inches(1.8), width=Inches(5.6))

    # ==========================================
    # SLIDE 10: Terminal Telemetry & 34 Automated Tests
    # ==========================================
    s10 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s10)
    add_slide_header(s10, "Terminal Execution & Automated Unit Test Suite")

    term_img = os.path.join(SCREENSHOTS_DIR, "terminal-monitor-demo.png")
    if os.path.exists(term_img):
        s10.shapes.add_picture(term_img, Inches(0.8), Inches(1.8), width=Inches(8.0))

    add_bullet_card(
        s10, Inches(9.1), Inches(1.8), Inches(3.4), Inches(5.0),
        "Verification Metrics",
        [
            "34 Automated Unit Tests.",
            "0.005s execution time.",
            "100% Pass Rate.",
            "Lambda validation tested.",
            "DynamoDB serialization.",
            "Cross-platform ping flags.",
            "Flap damping verified."
        ],
        COLOR_ACCENT_GREEN
    )

    # ==========================================
    # SLIDE 11: Comprehensive Pros of the Project
    # ==========================================
    s11 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s11)
    add_slide_header(s11, "Comprehensive Project Strengths (PROS)")

    add_bullet_card(
        s11, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Architectural & Operational Pros",
        [
            "1. 100% Serverless & Zero Maintenance: No EC2 instances, zero idle cloud costs.",
            "2. Glanceable Visual Telemetry: Transforms hidden terminal pings into an instant light.",
            "3. Zero-Dependency Footprint: Runs entirely on standard Python without pip installs.",
            "4. Cross-Platform Portability: Auto-adapts between Windows, Linux, and macOS."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s11, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Engineering & Academic Pros",
        [
            "5. Strong Read Consistency: Eliminates eventual consistency replication lag.",
            "6. Resilient Offline Demo Rig: Allows full evaluation without cloud credentials.",
            "7. Strict Schema Defense: Enforces boundary validations and type safety.",
            "8. Sub-Second Automated Test Suite: 34 tests providing high reliability."
        ],
        COLOR_ACCENT_GREEN
    )

    # ==========================================
    # SLIDE 12: Identified Cons & How We Solved Them (Part 1)
    # ==========================================
    s12 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s12)
    add_slide_header(s12, "Project Limitations (CONS) & Engineering Solutions — Part 1")

    add_bullet_card(
        s12, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "Con 1: Fixed Polling Lag",
        [
            "Problem: 10s polling interval delayed status visibility.",
            "SOLVED:",
            "• Upgraded client to adaptive fast polling (every 2.5–5s).",
            "• Added instant manual refresh button.",
            "• Added visual countdown pulse."
        ],
        COLOR_ACCENT_AMBER
    )

    add_bullet_card(
        s12, Inches(4.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "Con 2: Single-Pair Hardcoding",
        [
            "Problem: Only monitored vm-a → vm-b originally.",
            "SOLVED:",
            "• Built multi-connection registry in Lambda.",
            "• Added 'GET /connections' API endpoint.",
            "• Supports scanning multiple VM pairs across the lab."
        ],
        COLOR_ACCENT_AMBER
    )

    add_bullet_card(
        s12, Inches(8.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "Con 3: Lack of Trends",
        [
            "Problem: Stored only single latest ping without history.",
            "SOLVED:",
            "• Engineered dynamic 10-sample Latency Sparkline.",
            "• Added real-time Uptime Reliability % calculator.",
            "• Displays latency spikes visually."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 13: Identified Cons & How We Solved Them (Part 2)
    # ==========================================
    s13 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s13)
    add_slide_header(s13, "Project Limitations (CONS) & Engineering Solutions — Part 2")

    add_bullet_card(
        s13, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "Con 4: Jitter Flapping",
        [
            "Problem: Single packet drop turned entire board red.",
            "SOLVED:",
            "• Built Flap Damping Retry Engine in monitor.",
            "• Added intermediate Amber DEGRADED state for transient drops.",
            "• Requires sustained failures to trigger red alert."
        ],
        COLOR_ACCENT_AMBER
    )

    add_bullet_card(
        s13, Inches(4.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "Con 5: Open Ingestion Security",
        [
            "Problem: Open POST route lacked caller verification.",
            "SOLVED:",
            "• Added optional API key validation (x-api-key).",
            "• Integrated Bearer token parsing in Lambda.",
            "• Returns HTTP 401 Unauthorized for invalid keys."
        ],
        COLOR_ACCENT_AMBER
    )

    add_bullet_card(
        s13, Inches(8.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "Con 6: Unattended Monitoring",
        [
            "Problem: Instructors looking away missed visual alerts.",
            "SOLVED:",
            "• Integrated Web Audio API Synthesizer in dashboard.",
            "• Plays pleasant high chime on UP, alert sound on DOWN.",
            "• Toggleable audio control."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 14: Academic Deliverables & Submission Package
    # ==========================================
    s14 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s14)
    add_slide_header(s14, "Academic Deliverables & Submission Package")

    add_bullet_card(
        s14, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Document Deliverables",
        [
            "1. Product Start Sheet: PRODUCT_START_SHEET.docx (Formal course start sheet).",
            "2. Complete Product Report: PRODUCT_REPORT.docx (Full 6-section academic report).",
            "3. VirtualBox Setup Guide: VIRTUALBOX_SETUP_GUIDE.md (Dual-adapter instructions).",
            "4. Master README: README.md (Setup, architecture, testing & demos).",
            "5. Presentation Deck: NetPulse_Master_Presentation.pptx (This 16-slide master deck)."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s14, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Cloud & Code Deliverables",
        [
            "6. AWS SAM Infrastructure: template.yaml (Serverless Application Model).",
            "7. Standalone CloudFormation: cloudformation.yaml (AWS Learner Lab LabRole).",
            "8. Automated Test Suite: 34 tests in tests/ (100% pass rate).",
            "9. Offline Development Rig: scripts/local_demo.py (Runs on port 8000).",
            "10. GitHub Repository: https://github.com/yeshwanthkushi25-glitch/netpulse-virtual-lab."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 15: How to Run Live Demonstrations
    # ==========================================
    s15 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s15)
    add_slide_header(s15, "Step-by-Step Live Demonstration Walkthrough")

    add_bullet_card(
        s15, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Demo Sequence 1: Offline Expo (npm run dev)",
        [
            "Run 'npm run dev' or 'python scripts/local_demo.py --demo'.",
            "Phase 1 (0s): Browser lights up glowing GREEN (Operational link, ~1.3 ms RTT).",
            "Phase 2 (6s): Browser transitions to AMBER (Simulated latency jitter spike, ~48 ms).",
            "Phase 3 (12s): Browser flashes RED alert (Simulated link severed, host unreachable).",
            "Phase 4 (18s): Browser auto-recovers to GREEN (Link restored, chime plays)."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s15, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Demo Sequence 2: VirtualBox Real Link Drop",
        [
            "Start monitor on VM A: 'python3 monitor/netpulse_monitor.py --target 192.168.56.102'.",
            "Open NetPulse dashboard in browser.",
            "In VirtualBox for VM B: Devices → Network → Uncheck 'Cable Connected'.",
            "Observe the dashboard immediately shift from GREEN to RED with audio alarm.",
            "Re-check 'Cable Connected' in VirtualBox; watch the dashboard recover to GREEN."
        ],
        COLOR_ACCENT_AMBER
    )

    # ==========================================
    # SLIDE 16: Conclusion & Team Contributions
    # ==========================================
    s16 = prs.slides.add_slide(blank_layout)
    apply_dark_background(s16)
    add_slide_header(s16, "Conclusion & Team Contributions")

    add_bullet_card(
        s16, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Team Responsibilities",
        [
            "M. Yeshwanth (2503A53005):",
            "• VirtualBox virtual networking (Host-Only + NAT).",
            "• Python ICMP reachability monitor (netpulse_monitor.py).",
            "• Latency regex parsing, flap damping & telemetry streaming.",
            "• Link failure and recovery testing on lab VMs."
        ],
        COLOR_ACCENT_GREEN
    )

    add_bullet_card(
        s16, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Team Responsibilities",
        [
            "V. Laxmiprasad (2503A53006):",
            "• AWS Lambda ingestion and validation engine (lambda/app.py).",
            "• Amazon DynamoDB persistence & consistent reads.",
            "• S3 responsive traffic light dashboard UI (dashboard/).",
            "• Automated test suite & offline expo server (scripts/local_demo.py)."
        ],
        COLOR_ACCENT_AMBER
    )

    prs.save(PPTX_PATH)
    print("Master Presentation saved to:", PPTX_PATH)


if __name__ == "__main__":
    create_presentation()
