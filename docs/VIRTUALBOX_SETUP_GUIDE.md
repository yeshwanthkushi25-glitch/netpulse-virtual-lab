# NetPulse — VirtualBox Virtual Lab Setup & Simulation Guide

This guide walks you through configuring two VirtualBox virtual machines (VM A and VM B) to demonstrate network reachability monitoring with NetPulse.

---

## 1. Overview of the Virtual Lab

```
+-----------------------------------+          +-----------------------------------+
|      VirtualBox VM A              |          |      VirtualBox VM B              |
|      (Monitor Machine)            |          |      (Target Machine)             |
|                                   |          |                                   |
|  - Hostname: vm-a                 |          |  - Hostname: vm-b                 |
|  - IP: 192.168.56.101             |  Ping    |  - IP: 192.168.56.102             |
|  - Runs: netpulse_monitor.py      | -------->|  - Responds to ICMP echo          |
+-----------------------------------+          +-----------------------------------+
                  |
                  | HTTP POST JSON
                  v
       [ AWS API Gateway / Local ]
                  |
                  v
          [ AWS Lambda ]
                  |
                  v
         [ Amazon DynamoDB ]
                  |
                  v
      [ NetPulse Web Dashboard ]
      (Green Light / Red Light)
```

---

## 2. VirtualBox Network Configuration

For VM A to communicate with VM B while maintaining outbound internet access to AWS, configure **two network adapters** on each VM:

### Adapter 1: NAT (For Outbound AWS Internet Access)
- **Attached to**: `NAT`
- Provides internet access so VM A can call the AWS API Gateway URL.

### Adapter 2: Host-Only or Internal Network (For Inter-VM Reachability Testing)
- **Attached to**: `Host-only Adapter` (e.g., `VirtualBox Host-Only Ethernet Adapter` / `vboxnet0`)
  - Alternatively: `Internal Network` with name `netpulse-lan`
- **Promiscuous Mode**: `Allow All`
- **Cable Connected**: Checked (enabled)

---

## 3. Network Addressing

### On VM A (Monitor VM):
Set a static IP or DHCP on the second adapter (e.g. `enp0s8` or `eth1`):
```bash
sudo ip addr add 192.168.56.101/24 dev enp0s8
sudo ip link set dev enp0s8 up
```

### On VM B (Target VM):
Set the target IP:
```bash
sudo ip addr add 192.168.56.102/24 dev enp0s8
sudo ip link set dev enp0s8 up
```

Verify that VM A can ping VM B from the terminal:
```bash
ping -c 3 192.168.56.102
```

---

## 4. Running the NetPulse Monitor on VM A

Copy `monitor/netpulse_monitor.py` to VM A.

### Command Syntax:
```bash
python3 netpulse_monitor.py \
  --source vm-a \
  --target 192.168.56.102 \
  --api-url https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com \
  --interval 5
```

*(If testing locally with `scripts/local_demo.py` on your host machine, set `--api-url http://192.168.56.1:8000`)*.

### Terminal Output:
```json
{"source": "vm-a", "target": "192.168.56.102", "status": "up", "checked_at": "2026-11-07T12:00:00.000Z", "latency_ms": 1.45, "message": "Target reachable"}
```

---

## 5. Demonstration Scenarios

### Scenario A: Normal Healthy Connection (Green Light)
1. Both VMs are running and connected.
2. Monitor sends periodic pings (`status: up`, latency ~1.2 ms).
3. The NetPulse Dashboard displays the **glowing green traffic light** with message:
   `"LINK OPERATIONAL: VMs are connected"`.

### Scenario B: Link Failure Simulation (Red Light)
To simulate network failure between the VMs, choose one of these three methods:

1. **VirtualBox GUI Virtual Cable Unplug**:
   - In the VirtualBox window for VM B (or VM A), go to:
     **Devices** → **Network** → **Network Settings...** → **Adapter 2**
   - Uncheck **Cable Connected** and click OK.
2. **Linux Interface Shutdown (CLI)**:
   - On VM B, run:
     ```bash
     sudo ip link set dev enp0s8 down
     ```
3. **Monitor Simulation Flag**:
   - Run the monitor with:
     ```bash
     python3 netpulse_monitor.py --target 192.168.56.102 --simulate down --api-url ...
     ```
4. **Interactive Web Dashboard Button**:
   - Click the **"Simulate Link Cut (Red)"** button right on the NetPulse dashboard.

**Outcome**:
Within seconds, the monitor detects packet loss, sends `status: "down"`, and the NetPulse dashboard transitions to a **pulsing red alert light** with message:
`"CONNECTION LOST: Target unreachable"`.

### Scenario C: Link Recovery (Green Light Restored)
1. Restore the virtual link:
   - Check **Cable Connected** in VirtualBox, or
   - Run `sudo ip link set dev enp0s8 up` on VM B, or
   - Click **"Link Operational (Green)"** on the dashboard.
2. The next ping succeeds.
3. The dashboard automatically returns to the **green operational state** with recorded round-trip latency.
