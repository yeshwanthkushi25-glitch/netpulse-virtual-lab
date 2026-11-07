# Cloud Computing (25CAI102PC205) · SR University
# PRODUCT REPORT: NetPulse — Virtual Lab Network Traffic Light

**Course**: Cloud Computing (25CAI102PC205)  
**Submission Date**: November 2026  
**Environment**: AWS Learner Lab (`us-east-1`)  

---

## Team Details

- **Product Title**: Virtual Lab Network Traffic Light (NetPulse)
- **Team Number / Name**: Project No. 33 / Team NetPulse
- **Batch**: Batch 59
- **Team Members**:
  - **M. Yeshwanth** (Roll Number: `2503A53005`)
  - **V. Laxmiprasad** (Roll Number: `2503A53006`)

---

## 1. Product Overview

### Problem Statement
In undergraduate and graduate networking and cloud computing laboratory sessions, students work with virtualized machines (such as VirtualBox VMs) configured across internal host-only networks. Verifying whether two machines can successfully communicate typically relies on running command-line utilities like `ping` in an isolated terminal. 

This approach suffers from significant drawbacks:
- Terminal outputs are ephemeral and easily lost when an engineer switches windows or when the command finishes.
- Team members, laboratory partners, and instructors have no shared real-time visibility into whether the link between VMs is healthy, degraded, or completely down.
- Intermittent connectivity drops often go unnoticed until a larger application setup fails, creating complex debugging overhead.

### Objective
NetPulse delivers a software-defined, serverless network monitoring system that functions as a virtual "traffic light". A lightweight, zero-dependency Python monitor runs on the source VM, executes regular reachability checks against a destination VM, and streams connectivity telemetry to an AWS cloud backend. An intuitive, cloud-hosted static dashboard displays instantaneous visual feedback: a glowing **green light** for operational reachability and a pulsing **red light** for link loss.

### Target Users
- **Computing Students**: Provides visual confirmation that virtual network adapters, bridges, and routes are properly configured.
- **Laboratory Instructors and TAs**: Enables rapid, glanceable assessment of student network setups without inspecting individual terminal windows.
- **System & Network Administrators**: Demonstrates practical integration of serverless IoT telemetry architectures without physical hardware overhead.

### Main Features
- **Real-Time Reachability Auditing**: Automated background ping polling with millisecond round-trip time (RTT) extraction.
- **Glanceable Traffic Light UI**: Dark-themed, glassmorphic dashboard featuring animated visual feedback (green pulse for healthy link, red strobe alert for downtime).
- **Serverless Cloud Architecture**: Fully automated intake, schema validation, and persistence utilizing AWS HTTP API Gateway, AWS Lambda, and Amazon DynamoDB.
- **Zero-Dependency Monitor**: Built entirely with the Python standard library (`subprocess`, `urllib`, `re`), requiring no external packages on lab VMs.
- **Interactive Expo / Demo Mode**: Built-in interactive controls enabling instructors to test link severance and automatic recovery directly in browser or offline.

---

## 2. Architecture and Technologies

### Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            VIRTUAL LAB INFRASTRUCTURE                             |
|                                                                                   |
|   +-----------------------+                    +-----------------------+          |
|   |   VirtualBox VM A     |     ICMP Echo      |   VirtualBox VM B     |          |
|   |   (Monitor Host)      | -----------------> |   (Target Host)       |          |
|   |   IP: 192.168.56.101  | <----------------- |   IP: 192.168.56.102  |          |
|   |                       |    ICMP Reply      |                       |          |
|   |  netpulse_monitor.py  |                    +-----------------------+          |
|   +-----------+-----------+                                                       |
+---------------|-------------------------------------------------------------------+
                | HTTPS POST /status (JSON Payload)
                v
+-----------------------------------------------------------------------------------+
|                         AMAZON WEB SERVICES (us-east-1)                           |
|                                                                                   |
|  +----------------------------+                                                   |
|  |   Amazon API Gateway       | <── HTTP API (v2) with CORS Enabled               |
|  +--------------+-------------+                                                   |
|                 | Event Payload                                                   |
|                 v                                                                 |
|  +----------------------------+            +----------------------------+         |
|  |   AWS Lambda Function      | ─────────> |   Amazon CloudWatch Logs   |         |
|  |   (Validation & Routing)   |            |   (Traces & Error Audit)   |         |
|  +--------------+-------------+            +----------------------------+         |
|                 | PutItem / GetItem                                               |
|                 v                                                                 |
|  +----------------------------+                                                   |
|  |   Amazon DynamoDB          | <── Table: netpulse-status                        |
|  |   (Key: connection_id)     |     ConsistentRead = True                         |
|  +--------------+-------------+                                                   |
+-----------------|-----------------------------------------------------------------+
                  ^
                  | Periodic Polling (GET /status?source=vm-a&target=vm-b)
+-----------------|-----------------------------------------------------------------+
|                 |                                                                 |
|  +--------------+-------------+                                                   |
|  |   Amazon S3 Static Bucket  | ─── Hosts index.html, styles.css, app.js          |
|  +----------------------------+                                                   |
|                 │ Web Traffic                                                     |
|                 ▼                                                                 |
|  +----------------------------+                                                   |
|  |    End-User Web Browser    | <── Glowing Virtual Traffic Light (Green / Red)   |
|  +----------------------------+                                                   |
+-----------------------------------------------------------------------------------+
```

### AWS Cloud Services and Roles

| AWS Service | Role in NetPulse | Justification & Architectural Benefit |
| :--- | :--- | :--- |
| **Amazon S3** | Static Website Hosting | Serves dashboard frontend assets (`index.html`, `styles.css`, `app.js`). Eliminates the need for web server instances (EC2/Nginx), maximizing reliability with near-zero cost. |
| **Amazon API Gateway** | Status Ingestion Endpoint | HTTP API v2 routes `POST /status` from the Python monitor and `GET /status` from the dashboard with low latency and native CORS handling. |
| **AWS Lambda** | Business Logic & Ingestion Validation | Serverless Python 3.12 function validating input schema (identifiers, status flags, timestamps, latency boundaries) and executing DynamoDB operations. |
| **Amazon DynamoDB** | Persistent State Store | Serverless NoSQL table storing the single source of truth for connection reachability. Partition key `connection_id` allows $O(1)$ fast lookups with strong consistency. |
| **Amazon CloudWatch** | Observability & Logging | Automatically captures Lambda standard output, validation rejections, execution duration, and potential exceptions for system debugging. |

---

## 3. Implementation and Cloud Deployment

### 1. Virtual Machine & Monitor Implementation
- Two Ubuntu virtual machines were instantiated in Oracle VM VirtualBox.
- A **Host-Only Network Adapter** was assigned to both VMs (`192.168.56.101` for VM A and `192.168.56.102` for VM B).
- A second **NAT Adapter** was enabled on VM A to supply outbound internet connectivity for reaching the AWS API Gateway.
- The Python script (`monitor/netpulse_monitor.py`) executes an ICMP echo check using host ping commands. Regular expression parsing extracts round-trip latency (`LATENCY_PATTERN = re.compile(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms")`).
- The check result is wrapped in an ISO-8601 timestamped JSON payload and dispatched via `urllib.request.urlopen`.

### 2. Lambda Serverless Backend (`lambda/app.py`)
- **Route Dispatcher**: Inspects HTTP method and raw path. Handles preflight `OPTIONS` requests with appropriate CORS headers (`Access-Control-Allow-Origin: *`).
- **Strict Data Validation**: Enforces alphanumeric identifiers (`^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`), validates status enum (`up` or `down`), bounds latency between 0 and 3,600,000 ms, and validates RFC-3339 / ISO-8601 timestamps with explicit timezone information.
- **DynamoDB Operations**:
  - `POST`: Stores/overwrites connection record keyed by composite `connection_id = f"{source}#{target}"`.
  - `GET`: Queries DynamoDB with `ConsistentRead=True` to eliminate read replication delay on the dashboard.

### 3. S3 Static Web Dashboard (`dashboard/`)
- Pure HTML5, CSS3, and modern Vanilla ES6 JavaScript without heavy framework overhead.
- Configured with auto-refresh interval (default 10 seconds) and immediate manual refresh capability.
- Features **Interactive Simulation Controls** (`Link Operational (Green)` and `Simulate Link Cut (Red)`) enabling instant demonstration of state transitions during university project reviews.

### 4. CloudFormation / SAM Infrastructure as Code
- Complete infrastructure is codified in both `template.yaml` (AWS SAM) and `cloudformation.yaml` (Standalone CloudFormation for AWS Learner Lab).
- Supports AWS Learner Lab execution via default parameter mapping to existing `LabRole`.

### Deployment URLs & Project Links
- **GitHub Repository**: [https://github.com/yeshwanthkushi25-glitch/netpulse-virtual-lab](https://github.com/yeshwanthkushi25-glitch/netpulse-virtual-lab)
- **Deployment Endpoint**: AWS API Gateway `https://<api-id>.execute-api.us-east-1.amazonaws.com/status`
- **Dashboard URL**: S3 Static Website Endpoint `http://<bucket-name>.s3-website-us-east-1.amazonaws.com`

---

## 4. Testing and Results

The project was evaluated through offline unit test suites, integration tests, and live VirtualBox lab executions.

### Key Test Cases

| Test Case / Feature | Test Procedure | Expected Result | Actual Outcome & Status |
| :--- | :--- | :--- | :--- |
| **TC-01: Healthy VM Link Verification** | VM A pings VM B across host-only network (`192.168.56.102`). Monitor posts status to API. | Status marked as `up`; latency captured (~1.2 ms); Dashboard displays glowing green traffic light. | **PASS** — Dashboard rendered green state with accurate millisecond RTT. |
| **TC-02: Link Severing / Failure Detection** | Virtual network cable unplugged in VirtualBox settings on VM B; monitor executes next cycle. | Ping command fails; monitor detects packet loss and posts `status: "down"`; Dashboard displays pulsing red light. | **PASS** — Dashboard switched to red alert state with message "Target unreachable". |
| **TC-03: Automatic Link Recovery** | Reconnect virtual network cable on VM B; monitor executes next scheduled check. | ICMP echo succeeds; monitor transmits `status: "up"`; Dashboard recovers to green indicator. | **PASS** — Traffic light recovered to green automatically within one polling cycle. |
| **TC-04: API Input Validation & Defense** | Injected invalid payloads (e.g. invalid status string, negative latency, missing timezone, bad characters). | API Gateway Lambda returns `HTTP 400 Bad Request` with descriptive validation message; DynamoDB item unchanged. | **PASS** — Rejected all malformed requests cleanly. |
| **TC-05: Local Demo & Offline Expo Mode** | Executed `npm run dev` (`python scripts/local_demo.py --demo`) without cloud credentials. | Local HTTP server spins up on port 8000; automated sequence cycles through Green -> Red -> Green. | **PASS** — 100% functional offline simulation for presentation expo. |

### Unit Test Verification
An automated test suite (`tests/test_lambda.py`, `tests/test_monitor.py`, `tests/test_local_server.py`) with 29 test cases was executed:
```text
Ran 29 tests in 0.006s
OK
```

---

## 5. Challenges and Conclusion

### Challenges Encountered and Solutions
1. **AWS Learner Lab Permission Restrictions**:
   - *Challenge*: Learner Lab environments restrict the creation of arbitrary IAM roles and polices (`iam:CreateRole` denied).
   - *Solution*: Designed the CloudFormation templates with conditional logic to attach the pre-existing `LabRole` (`arn:aws:iam::<AccountId>:role/LabRole`), ensuring frictionless deployment in educational sandbox accounts.
2. **DynamoDB Number vs. Python Float Serialization**:
   - *Challenge*: DynamoDB SDK rejects native Python floating-point types to prevent binary floating-point precision loss.
   - *Solution*: Implemented a clean round-trip conversion utilizing Python's `decimal.Decimal` and custom JSON serializer `_json_default` in `lambda/app.py`.
3. **Cross-Platform Host Ping Syntax**:
   - *Challenge*: The standard ping syntax differs between Windows hosts (`ping -n 1 -w <ms>`) and Linux/macOS environments (`ping -c 1 -W <sec>`).
   - *Solution*: Developed an adaptive command constructor (`ping_command`) in `monitor/netpulse_monitor.py` that inspects `platform.system()` and normalizes timeout parameters across OS variants.
4. **Cross-Origin Resource Sharing (CORS)**:
   - *Challenge*: Web browsers blocked dashboard API requests from S3 website origin to API Gateway domain due to CORS restrictions.
   - *Solution*: Configured global CORS policies on API Gateway and embedded explicit CORS headers (`Access-Control-Allow-Origin: *`, `OPTIONS 204`) in all Lambda response methods.

### Key Achievements and Learning Outcomes
- Successfully architected and deployed a multi-tier, event-driven serverless IoT monitoring pipeline on AWS.
- Bridged low-level operating system network virtualization (VirtualBox ICMP) with modern cloud primitives.
- Achieved high reliability, zero runtime cost, and zero server management overhead.

---

## 6. Team Contributions and References

### Member Contributions

- **M. Yeshwanth (H.T. No. 2503A53005)**:
  - Engineered the VirtualBox virtual machine dual-adapter networking (NAT + Host-Only).
  - Authored the cross-platform reachability monitor (`monitor/netpulse_monitor.py`).
  - Implemented latency regex parsers and fault simulation triggers.
  - Performed link severance and network recovery testing.

- **V. Laxmiprasad (H.T. No. 2503A53006)**:
  - Developed the AWS Lambda ingestion and validation engine (`lambda/app.py`).
  - Configured Amazon DynamoDB data schema and strong consistency query patterns.
  - Designed and styled the responsive S3 static traffic light dashboard (`dashboard/`).
  - Created automated test suites and the offline demonstration server (`scripts/local_demo.py`).

### References
1. Amazon Web Services. *AWS Lambda Developer Guide: Working with AWS Lambda and Amazon DynamoDB*. AWS Documentation, 2026.
2. Amazon Web Services. *Amazon API Gateway: Building HTTP APIs with Lambda integrations*. AWS Documentation, 2026.
3. Postel, J. *Internet Control Message Protocol (ICMP)*. RFC 792, DARPA Internet Program Protocol Specification.
4. Oracle Corporation. *Oracle VM VirtualBox User Manual: Virtual Networking Modes*.
5. SR University. *Cloud Computing (25CAI102PC205) Course Laboratory Manual & Project Guidelines*.
