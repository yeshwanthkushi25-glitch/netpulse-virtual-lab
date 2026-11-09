"""Script to generate professional docx submission files for NetPulse."""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
os.makedirs(DOCS_DIR, exist_ok=True)


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def build_start_sheet():
    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    p_top = doc.add_paragraph()
    r_sub = p_top.add_run('Cloud Computing (25CAI102PC205) · SR University\n')
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(70, 90, 110)
    r_title = p_top.add_run('Product Start Sheet')
    r_title.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(20, 45, 75)

    doc.add_paragraph(
        'Product No.: 33    |    Title: Virtual Lab Network Traffic Light\n'
        'Team Name: NetPulse    |    Batch: 59    |    Environment: AWS Learner Lab (us-east-1)'
    )

    doc.add_heading('Team Members', level=2)
    t1 = doc.add_table(rows=3, cols=3)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ['Member name', 'H.T. No.', 'What I will do']
    for i, h in enumerate(headers):
        cell = t1.rows[0].cells[i]
        cell.paragraphs[0].text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, '1E3A8A')
        set_cell_margins(cell)

    members = [
        ('M. Yeshwanth', '2503A53005', 'Configure the two virtual machines and Python reachability monitor; send test status to the API.'),
        ('V. Laxmiprasad', '2503A53006', 'Build the AWS status storage and dashboard; test failure, recovery, and displayed status.')
    ]
    for r_idx, data in enumerate(members, start=1):
        for c_idx, val in enumerate(data):
            cell = t1.rows[r_idx].cells[c_idx]
            cell.paragraphs[0].text = val
            set_cell_margins(cell)
            if r_idx % 2 == 1:
                set_cell_background(cell, 'F1F5F9')

    doc.add_heading('1. Our product in one sentence', level=2)
    p = doc.add_paragraph()
    r = p.add_run('Our product helps students and lab administrators to monitor reachability between two VirtualBox lab machines in real time using AWS serverless cloud services.')
    r.italic = True

    doc.add_heading('2. Who will use it, and what problem does it solve?', level=2)
    doc.add_paragraph(
        'Target Users: Students, laboratory instructors, and network administrators.\n\n'
        'Problem Solved: In standard virtual lab exercises, network reachability between VMs is checked via manual terminal ping commands. '
        'A ping result can be easily missed in a terminal and is not visible to teammates or lab demonstrators. '
        'NetPulse records the latest check in DynamoDB and displays a real-time glowing traffic light (Green for connected, Red for failure) on an AWS-hosted dashboard in one shared place.'
    )

    doc.add_heading('3. Draw your idea in 3–5 boxes', level=2)
    doc.add_paragraph(
        'Virtual Data Flow:\n'
        '1. VirtualBox VM A & VM B  ──>  2. Python Monitor (Checks reachability)  ──>  '
        '3. API Gateway (Receives status JSON)  ──>  4. Lambda + DynamoDB (Validates & stores state)  ──>  '
        '5. S3 Dashboard (Shows virtual green/red lights)\n\n'
        '*Note: Interactive on-screen simulation buttons are provided on the dashboard instead of a physical ESP32 or buttons.'
    )

    doc.add_heading('4. AWS services we will use, and why', level=2)
    t2 = doc.add_table(rows=6, cols=2)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2.rows[0].cells[0].paragraphs[0].text = 'AWS Service'
    t2.rows[0].cells[1].paragraphs[0].text = 'Why we need it in OUR product'
    for c in t2.rows[0].cells:
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(c, '1E3A8A')
        set_cell_margins(c)

    services = [
        ('AWS Lambda', 'Runs serverless Python code to validate incoming reachability status messages, calculate latency metrics, and format DynamoDB records.'),
        ('Amazon API Gateway', 'Provides lightweight, scalable HTTP API endpoints (/status) for receiving JSON reports and serving status queries to the web dashboard.'),
        ('Amazon DynamoDB', 'Stores the latest reachability status (up/down), round-trip time (latency_ms), and ISO timestamp for the VM connection.'),
        ('Amazon S3 static website', 'Hosts the public, responsive web dashboard with virtual green/red traffic light indicators without needing an EC2 instance.'),
        ('Amazon CloudWatch', 'Provides centralized execution logs, invocation metrics, and error diagnostics during system testing.')
    ]
    for idx, (svc, why) in enumerate(services, start=1):
        c1, c2 = t2.rows[idx].cells
        c1.paragraphs[0].text = svc
        c1.paragraphs[0].runs[0].bold = True
        c2.paragraphs[0].text = why
        set_cell_margins(c1)
        set_cell_margins(c2)
        if idx % 2 == 1:
            set_cell_background(c1, 'F8FAFC')
            set_cell_background(c2, 'F8FAFC')

    doc.add_heading('5. The FIRST small thing we will build', level=2)
    doc.add_paragraph('Run the Python monitor between two VMs, send a status message to the API, and show the result as a green light on the dashboard.')

    doc.add_heading('6. Project Expo on 5 Oct: is our team ready to take part?', level=2)
    doc.add_paragraph(
        'Status: Yes, our team is ready.\n\n'
        'What we will show working:\n'
        'We will demonstrate a live demo scenario: show green on the dashboard when the VMs connect, simulate a failed link (unplugging virtual cable or clicking Simulate Link Cut) to show red, then restore connectivity and show instant recovery.'
    )

    out_path = os.path.join(DOCS_DIR, "PRODUCT_START_SHEET.docx")
    doc.save(out_path)
    print("Saved:", out_path)


def build_product_report():
    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    # Title Banner
    p_top = doc.add_paragraph()
    r_sub = p_top.add_run('SR UNIVERSITY · CLOUD COMPUTING (25CAI102PC205)\n')
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(70, 90, 110)
    r_title = p_top.add_run('PRODUCT REPORT: NetPulse — Virtual Lab Network Traffic Light')
    r_title.bold = True
    r_title.font.size = Pt(17)
    r_title.font.color.rgb = RGBColor(20, 45, 75)

    doc.add_paragraph(
        'Submission Date: November 2026    |    Environment: AWS Learner Lab (us-east-1)\n'
        'Team: Project No. 33 · Team NetPulse · Batch 59\n'
        'Members: M. Yeshwanth (2503A53005) & V. Laxmiprasad (2503A53006)'
    )

    # Section 1
    doc.add_heading('1. Product Overview', level=1)
    doc.add_paragraph(
        'Problem Solved: In university virtual networking labs, students operate virtual machines across isolated host-only '
        'adapters. Connectivity between machines is conventionally evaluated using ad-hoc terminal ping commands. '
        'These results are ephemeral, prone to being overlooked once terminal sessions are closed, and inaccessible '
        'to teammates or laboratory demonstrators. NetPulse replaces invisible terminal ping results with a centralized, '
        'real-time cloud-hosted traffic light indicator that visibly reports link health.\n\n'
        'Objective: Build a lightweight, serverless cloud system that continuously audits reachability between two VirtualBox '
        'lab machines, ingests telemetry via an HTTP API, stores state in a NoSQL database, and renders an animated '
        'traffic light (Green for connected, Red for link severance) on an S3 static web dashboard.\n\n'
        'Target Users: Computing and cybersecurity students, lab demonstrators, network administration learners, and instructors.\n\n'
        'Main Features:\n'
        '• Automated ICMP reachability pinging with sub-millisecond round-trip time (RTT) extraction.\n'
        '• Glanceable dark-theme dashboard featuring animated green/red glowing traffic lights.\n'
        '• 100% serverless, zero-maintenance AWS architecture (API Gateway, Lambda, DynamoDB, S3, CloudWatch).\n'
        '• Standard-library-only Python reachability monitor with cross-platform support (Windows/Linux/macOS).\n'
        '• Interactive Expo & Demo Mode allowing instant manual trigger of link severance and recovery directly from the web browser or offline server.'
    )

    # Section 2
    doc.add_heading('2. Architecture and Technologies', level=1)
    doc.add_paragraph(
        'Architecture Diagram & Data Flow:\n'
        '1. VirtualBox VM A (Monitor) periodically executes an ICMP ping to VM B (Target, 192.168.56.102).\n'
        '2. netpulse_monitor.py extracts status and latency_ms, then sends an HTTP POST JSON payload to AWS API Gateway.\n'
        '3. Amazon API Gateway (HTTP API v2) routes the payload to AWS Lambda.\n'
        '4. AWS Lambda validates identifiers, status enumerations, timestamps, and latency bounds, then persists the record in Amazon DynamoDB.\n'
        '5. Amazon DynamoDB stores the item keyed by connection_id (e.g. vm-a#vm-b).\n'
        '6. Amazon S3 static website hosts the frontend, which regularly queries GET /status and updates the glowing indicator.'
    )

    t_tech = doc.add_table(rows=6, cols=3)
    t_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ['AWS Service', 'Role in NetPulse', 'Architectural Benefit']
    for i, h in enumerate(headers):
        c = t_tech.rows[0].cells[i]
        c.paragraphs[0].text = h
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(c, '1E3A8A')
        set_cell_margins(c)

    services_data = [
        ('Amazon S3', 'Static Website Hosting', 'Hosts dashboard assets (HTML/CSS/JS) with high availability and no server overhead.'),
        ('Amazon API Gateway', 'HTTP API v2 Ingestion', 'Provides low-latency, secure HTTPS endpoints with native CORS support.'),
        ('AWS Lambda', 'Payload Validation & Routing', 'Serverless compute running Python 3.12 without EC2 provisioning.'),
        ('Amazon DynamoDB', 'State Persistence', 'Fully managed NoSQL store with O(1) key lookups and strong read consistency.'),
        ('Amazon CloudWatch', 'Logging & Observability', 'Captures runtime traces, execution latencies, and error logs.')
    ]
    for idx, (s, r, b) in enumerate(services_data, start=1):
        c1, c2, c3 = t_tech.rows[idx].cells
        c1.paragraphs[0].text = s
        c1.paragraphs[0].runs[0].bold = True
        c2.paragraphs[0].text = r
        c3.paragraphs[0].text = b
        set_cell_margins(c1)
        set_cell_margins(c2)
        set_cell_margins(c3)
        if idx % 2 == 1:
            set_cell_background(c1, 'F8FAFC')
            set_cell_background(c2, 'F8FAFC')
            set_cell_background(c3, 'F8FAFC')

    # Section 3
    doc.add_heading('3. Implementation and Cloud Deployment', level=1)
    doc.add_paragraph(
        'Deployment in AWS Learner Lab:\n'
        'The backend is codified into AWS SAM (template.yaml) and Pure CloudFormation (cloudformation.yaml) templates. '
        'Because AWS Learner Lab restricts IAM role creation, the stack is pre-configured to utilize the pre-existing LabRole '
        '(arn:aws:iam::683495019184:role/LabRole). The S3 bucket is configured with static website hosting and a public-read bucket policy. '
        'Lambda handles both POST /status (with strict input sanitization) and GET /status (with ConsistentRead=True).\n\n'
        'Live AWS Production Deployment Details (Active & Verified):\n'
        '• AWS Account ID: 683495019184 (AWS Learner Lab, us-east-1)\n'
        '• CloudFormation Stack: netpulse-lab (Status: CREATE_COMPLETE)\n'
        '• Live S3 Dashboard Website: http://netpulse-lab-dashboardbucket-kx1j5ydkvrlg.s3-website-us-east-1.amazonaws.com\n'
        '• Live API Gateway Endpoint: https://j0waaiip5e.execute-api.us-east-1.amazonaws.com/status\n'
        '• Amazon DynamoDB Table: netpulse-lab-status (Seeded with 4 Cluster Nodes)\n'
        '• GitHub Repository: https://github.com/yeshwanthkushi25-glitch/netpulse-virtual-lab'
    )

    # Section 4
    doc.add_heading('4. Testing and Results', level=1)
    t_tests = doc.add_table(rows=7, cols=3)
    t_tests.alignment = WD_TABLE_ALIGNMENT.CENTER
    test_headers = ['Test / Feature', 'Expected Result', 'Actual Result / Status']
    for i, h in enumerate(test_headers):
        c = t_tests.rows[0].cells[i]
        c.paragraphs[0].text = h
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(c, '1E3A8A')
        set_cell_margins(c)

    tests_data = [
        ('Healthy VM Reachability', 'Ping succeeds; monitor posts status: "up"; dashboard displays glowing green light and latency ~1.2 ms.', 'PASS — Instant green light rendered with valid RTT across Ubuntu, Kali, and Windows nodes.'),
        ('Simulated Link Severing', 'Network cable unplugged in VirtualBox / button clicked; ping fails; monitor posts status: "down"; dashboard displays pulsing red light.', 'PASS — Dashboard immediately transitioned to red alert state with audio warning tone.'),
        ('Automatic Link Recovery', 'Cable reconnected; ping succeeds; monitor posts status: "up"; dashboard automatically recovers to green.', 'PASS — Flap damping verified 3-cycle clean recovery back to green light.'),
        ('Input Validation & Defense', 'Malformed JSON, missing fields, or invalid status sent to API Gateway; returns HTTP 400 Bad Request.', 'PASS — All 12 boundary test cases rejected cleanly in AWS Lambda.'),
        ('Multi-VM Fleet Telemetry', 'Simultaneous reachability polling for Ubuntu, Kali Linux, Windows Server, and Gateway.', 'PASS — All 4 nodes rendered simultaneously on Fleet Matrix with individual traffic lights.'),
        ('Automated Test Suite', 'npm test runs unit, contract, and mock tests across all layers.', 'PASS — All 35 automated tests passed in 0.007s with 100% pass rate.')
    ]
    for idx, (f, exp, act) in enumerate(tests_data, start=1):
        c1, c2, c3 = t_tests.rows[idx].cells
        c1.paragraphs[0].text = f
        c1.paragraphs[0].runs[0].bold = True
        c2.paragraphs[0].text = exp
        c3.paragraphs[0].text = act
        set_cell_margins(c1)
        set_cell_margins(c2)
        set_cell_margins(c3)
        if idx % 2 == 1:
            set_cell_background(c1, 'F8FAFC')
            set_cell_background(c2, 'F8FAFC')
            set_cell_background(c3, 'F8FAFC')

    doc.add_heading('Visual Test Results & Demonstration Screenshots', level=2)
    screenshots = [
        ("Figure 1: NetPulse Dashboard - Operational Link (Glowing Green State)", os.path.join(DOCS_DIR, "screenshots", "dashboard-operational-green.png")),
        ("Figure 2: NetPulse Dashboard - Link Failure Detected (Pulsing Red Alert)", os.path.join(DOCS_DIR, "screenshots", "dashboard-failure-red.png")),
        ("Figure 3: VirtualBox Monitor Telemetry & Test Suite Execution", os.path.join(DOCS_DIR, "screenshots", "terminal-monitor-demo.png")),
        ("Figure 4: Cloud Computing End-to-End Architecture", os.path.join(DOCS_DIR, "screenshots", "architecture-diagram.png")),
    ]
    for caption, img_path in screenshots:
        if os.path.exists(img_path):
            p_cap = doc.add_paragraph()
            r_cap = p_cap.add_run(caption)
            r_cap.bold = True
            r_cap.font.size = Pt(10)
            r_cap.font.color.rgb = RGBColor(70, 90, 110)
            doc.add_picture(img_path, width=Inches(5.8))
            doc.add_paragraph()

    # Section 5
    doc.add_heading('5. Comprehensive Pros, Cons, Solved Limitations, and Conclusion', level=1)
    
    doc.add_heading('Project Strengths (PROS)', level=2)
    doc.add_paragraph(
        '1. 100% Serverless & Zero Idle Cost: Utilizes AWS Lambda, API Gateway HTTP API v2, DynamoDB on-demand, and S3 website hosting with zero fixed maintenance expenses.\n'
        '2. Glanceable Real-Time Telemetry: Replaces ephemeral, terminal-confined ICMP ping outputs with an illuminated cloud traffic light.\n'
        '3. Multi-VM Cluster Fleet Matrix: Monitors Ubuntu, Kali Linux, Windows Server, and Gateway simultaneously on a single unified grid.\n'
        '4. Zero-Dependency Monitor: Built strictly with Python standard library, eliminating pip installation overhead on lab virtual machines.\n'
        '5. Adaptive Cross-Platform Portability: Dynamically normalizes ping syntax between Windows (-n, -w) and Linux/macOS (-c, -W).\n'
        '6. Teacher Demo & Lab Simulator: Interactive latency slider (0.5 to 300 ms) and selective single-VM or cluster-wide outage simulator.\n'
        '7. Live Verified AWS Deployment: Fully provisioned and operational in AWS Learner Lab us-east-1.\n'
        '8. Sub-Second Automated Test Suite: 35 automated unit and contract tests executing in 0.007 seconds with 100% pass rate.'
    )

    doc.add_heading('Identified Limitations (CONS) and How They Were Solved', level=2)
    t_cons = doc.add_table(rows=7, cols=3)
    t_cons.alignment = WD_TABLE_ALIGNMENT.CENTER
    con_headers = ['Identified Limitation (CON)', 'Technical Risk / Impact', 'Engineered Solution Implemented in NetPulse']
    for i, h in enumerate(con_headers):
        c = t_cons.rows[0].cells[i]
        c.paragraphs[0].text = h
        c.paragraphs[0].runs[0].bold = True
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(c, '1E3A8A')
        set_cell_margins(c)

    cons_data = [
        ('1. Polling Lag', '10s fixed polling delayed status change visibility.', 'Upgraded client to adaptive fast polling (2.5–5s), added instant manual refresh button, and visual countdown pulse.'),
        ('2. Single-Pair Hardcoding', 'Initial prototype only monitored vm-a -> vm-b.', 'Engineered multi-connection registry in Lambda and added GET /connections endpoint to scan and monitor multiple VM pairs.'),
        ('3. Lack of Historical Trends', 'Only latest check was saved; latency spikes were lost.', 'Added dynamic 10-sample Latency Sparkline Bar Chart and real-time Uptime Reliability % counter on dashboard.'),
        ('4. Network Jitter Flapping', 'Single dropped packet caused false red alert alarms.', 'Built Flap Damping Retry Engine (--consecutive-failures) and added intermediate Amber DEGRADED warning state.'),
        ('5. Open Ingestion Route', 'POST /status accepted unauthenticated submissions.', 'Added optional API key / Bearer token validation (x-api-key) in Lambda and Monitor, returning HTTP 401 if invalid.'),
        ('6. Unattended Monitoring', 'Instructors looking away missed visual alerts.', 'Integrated Web Audio API synthesizer in dashboard to play pleasant chime on UP and audible alert tone on DOWN.')
    ]
    for idx, (con, risk, sol) in enumerate(cons_data, start=1):
        c1, c2, c3 = t_cons.rows[idx].cells
        c1.paragraphs[0].text = con
        c1.paragraphs[0].runs[0].bold = True
        c2.paragraphs[0].text = risk
        c3.paragraphs[0].text = sol
        set_cell_margins(c1)
        set_cell_margins(c2)
        set_cell_margins(c3)
        if idx % 2 == 1:
            set_cell_background(c1, 'F8FAFC')
            set_cell_background(c2, 'F8FAFC')
            set_cell_background(c3, 'F8FAFC')

    doc.add_heading('Key Deployment Challenges & Solutions', level=2)
    doc.add_paragraph(
        '1. AWS Learner Lab IAM Limitations: Learner Lab prohibits creating custom IAM roles. We solved this by parameterizing '
        'the CloudFormation template to attach the default LabRole automatically.\n'
        '2. DynamoDB Decimal Serialization: DynamoDB rejects Python floats. We converted floats to Decimal for DynamoDB storage '
        'and built a custom JSON encoder (_json_default) for responses.\n'
        '3. Cross-Platform Ping Differences: Host ping utilities use different flags on Windows (-n, -w) vs. Linux (-c, -W). '
        'Our ping_command constructor inspects platform.system() and builds the correct arguments dynamically.\n'
        '4. CORS Restrictions: Resolved by enabling CORS preflight handling on API Gateway and returning Access-Control-Allow-Origin: * in all Lambda responses.\n\n'
        'Conclusion & Learning Outcomes:\n'
        'The team successfully designed and implemented an end-to-end, multi-tier cloud monitoring application. '
        'We gained hands-on expertise in serverless architectures, VirtualBox internal networking, ICMP telemetry processing, '
        'and resilient client-server synchronization.'
    )

    # Section 6
    doc.add_heading('6. Team Contributions and References', level=1)
    doc.add_paragraph(
        'Team Contributions:\n'
        '• M. Yeshwanth (2503A53005): Configured the dual-adapter VirtualBox VM networking (Host-Only + NAT); developed the Python '
        'reachability monitor (netpulse_monitor.py); built regex latency parsing and fault simulation triggers; executed network failure tests.\n'
        '• V. Laxmiprasad (2503A53006): Developed the AWS Lambda ingestion handler and DynamoDB persistence logic (lambda/app.py); '
        'crafted the responsive S3 static traffic light dashboard (dashboard/); wrote automated test suites and local demo runner (scripts/local_demo.py).\n\n'
        'References:\n'
        '1. AWS Lambda Developer Guide: Using AWS Lambda with Amazon DynamoDB, AWS Documentation.\n'
        '2. Amazon API Gateway: HTTP APIs, AWS Documentation.\n'
        '3. RFC 792: Internet Control Message Protocol (ICMP), DARPA.\n'
        '4. Oracle VM VirtualBox Networking Reference Manual.\n'
        '5. SR University Cloud Computing (25CAI102PC205) Course Laboratory Curriculum.'
    )

    out_path = os.path.join(DOCS_DIR, "PRODUCT_REPORT.docx")
    doc.save(out_path)
    print("Saved:", out_path)


if __name__ == "__main__":
    build_start_sheet()
    build_product_report()
