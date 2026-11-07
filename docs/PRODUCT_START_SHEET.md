# Cloud Computing (25CAI102PC205) · SR University
## Product Start Sheet

---

### OUR PRODUCT
- **Product No.**: 33
- **Title**: Virtual Lab Network Traffic Light (NetPulse)
- **Team Name**: Team NetPulse
- **Batch**: Batch 59
- **Environment**: AWS Learner Lab (`us-east-1`)

| Member Name | H.T. No. | What I Will Do |
| :--- | :--- | :--- |
| **M. Yeshwanth** | 2503A53005 | Configure the two virtual machines and Python reachability monitor; send test status to the API. |
| **V. Laxmiprasad** | 2503A53006 | Build the AWS status storage and dashboard; test failure, recovery, and displayed status. |

---

### 1. Our Product in One Sentence
> **Our product helps** students and lab administrators **to** monitor network reachability between two VirtualBox lab machines in real time **using AWS** serverless cloud services.

---

### 2. Who Will Use It, and What Problem Does It Solve?
- **Target Users**: Students, faculty instructors, teaching assistants, and network administration learners in virtualized computing laboratories.
- **Problem Solved**: In standard virtual lab exercises, network reachability between virtual machines is verified through manual ping commands executed in isolated command-line terminals. If a link fails or degrades, the failure is easily missed by peers and instructors. NetPulse solves this by providing a unified, centralized, real-time "traffic light" dashboard hosted in the cloud. It transforms invisible command-line ping output into an instant, high-visibility green/red indicator visible to the whole laboratory group.

---

### 3. Draw Your Idea in 3–5 Boxes
```
+-----------------------------------+
|  1. VirtualBox VM A & VM B        |
|     (Lab Environment)             |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|  2. Python Reachability Monitor   |
|     (Runs ping & formats JSON)    |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|  3. Amazon API Gateway (HTTP API) |
|     (Receives status reports)     |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|  4. AWS Lambda + DynamoDB         |
|     (Validates & persists state)  |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|  5. Amazon S3 Static Dashboard    |
|     (Virtual Green/Red Light UI)  |
+-----------------------------------+
```
*(Interactive simulation buttons are also provided on the web dashboard to trigger state transitions without requiring physical hardware).*

---

### 4. AWS Services We Will Use, and Why

| AWS Service | Why We Need It in OUR Product |
| :--- | :--- |
| **AWS Lambda** | Validates incoming status JSON payloads, formats timestamps and latency figures, and handles read/write logic without server management. |
| **Amazon API Gateway** | Provides a lightweight, high-performance HTTP API endpoint (`/status`) with integrated CORS to receive monitor data and serve dashboard requests. |
| **Amazon DynamoDB** | Fast NoSQL key-value store maintaining the latest reachability state (`up`/`down`), timestamp, and round-trip time for each monitored connection. |
| **Amazon S3** | Hosts the static, responsive single-page dashboard (`index.html`, `styles.css`, `app.js`) with high availability at low cost. |
| **Amazon CloudWatch** | Aggregates runtime execution logs, traces API invocation latency, and captures diagnostic errors during testing and evaluation. |

---

### 5. The FIRST Small Thing We Will Build
Run the Python monitor on VM A targeting VM B, send an initial JSON status payload (`status: "up"`) through API Gateway to Lambda and DynamoDB, and display the glowing **green traffic light** on the S3 web dashboard.

---

### 6. Project Expo on 5 Oct: Is Our Team Ready to Take Part?
- **Status**: **Yes**
- **What We Will Show Working**:
  1. **Operational Green State**: Show VM A actively pinging VM B across VirtualBox internal network, transmitting telemetry to AWS, and lighting up the dashboard green with latency metrics (~1.2 ms).
  2. **Simulated Link Failure (Red Light)**: Sever the virtual link (by unplugging the VirtualBox virtual adapter cable or clicking the "Simulate Link Cut" button) to demonstrate the dashboard immediately transitioning to a glowing, pulsing red alert light.
  3. **Automatic Link Recovery**: Reconnect the virtual adapter, showing automatic detection and recovery of the connection back to operational green.
