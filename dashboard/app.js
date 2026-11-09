(() => {
  "use strict";
  const config = Object.assign({ apiUrl: "", source: "vm-a", target: "vm-b", refreshIntervalMs: 3000 }, window.NETPULSE_CONFIG);
  const $ = (id) => document.getElementById(id);

  const elements = {
    panel: $("status-panel"), kicker: $("status-kicker"), title: $("status-title"),
    message: $("status-message"), checked: $("checked-at"), latency: $("latency"),
    button: $("refresh-button"), refreshLabel: $("refresh-label"), refreshDot: $("refresh-dot"),
    ctrlStatus: $("controller-status"),
    slider: $("latency-slider"), numInput: $("latency-num-input"), msgInput: $("demo-msg-input"),
    btnConnect: $("btn-demo-connect"), btnDegrade: $("btn-demo-degrade"), btnDisconnect: $("btn-demo-disconnect"),
    btnApply: $("btn-apply-demo"),
    btnAudio: $("btn-audio"), audioState: $("audio-state"), audioIcon: $("audio-icon"),
    sparkline: $("latency-sparkline"), uptime: $("uptime-val"),
    fleetGrid: $("fleet-grid"),
    fleetOnline: $("fleet-online-count"),
    fleetDegraded: $("fleet-degraded-count"),
    fleetDown: $("fleet-down-count"),
    targetSelect: $("target-select"),
    targetSubtitle: $("target-subtitle"),
    simTargetSelect: $("sim-target-select")
  };

  const VM_METADATA = {
    "vm-b": { name: "Ubuntu Target VM", ip: "192.168.56.102", os: "🐧 Ubuntu Linux" },
    "kali-linux": { name: "Kali Linux PenTest VM", ip: "192.168.56.103", os: "🐉 Kali Linux" },
    "win-server": { name: "Windows Server 2022", ip: "192.168.56.104", os: "🪟 Windows Server" },
    "lab-gateway": { name: "Host Default Gateway", ip: "192.168.56.1", os: "🌐 Lab Gateway" }
  };

  let timer;
  let currentFocusedTarget = config.target || "vm-b";
  let fleetConnections = {
    "vm-b": { source: config.source, target: "vm-b", status: "up", latency_ms: 1.25, message: "Target reachable", checked_at: new Date().toISOString() },
    "kali-linux": { source: config.source, target: "kali-linux", status: "up", latency_ms: 0.85, message: "Kali node reachable", checked_at: new Date().toISOString() },
    "win-server": { source: config.source, target: "win-server", status: "up", latency_ms: 2.10, message: "Windows node reachable", checked_at: new Date().toISOString() },
    "lab-gateway": { source: config.source, target: "lab-gateway", status: "up", latency_ms: 0.45, message: "Host gateway reachable", checked_at: new Date().toISOString() }
  };
  let previousFocusedStatus = null;
  let currentSimStatus = "up";
  const historyByTarget = {};
  let audioEnabled = localStorage.getItem("netpulse_audio") !== "false";

  $("source").textContent = config.source;
  if ($("target")) $("target").textContent = currentFocusedTarget;
  $("connection-id").textContent = `${config.source} → ${currentFocusedTarget}`;

  // Web Audio API Synthesizer (Zero external audio files needed)
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const audioCtx = AudioContextClass ? new AudioContextClass() : null;

  function playChime(type) {
    if (!audioEnabled || !audioCtx) return;
    try {
      if (audioCtx.state === "suspended") audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      const now = audioCtx.currentTime;

      if (type === "up") {
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (type === "degraded") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(440, now); // A4
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      } else if (type === "down") {
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(220, now); // A3
        osc.frequency.linearRampToValueAtTime(146.83, now + 0.25); // D3
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
      }
    } catch (_) {}
  }

  function syncAudioUI() {
    if (elements.audioState) elements.audioState.textContent = audioEnabled ? "ON" : "OFF";
    if (elements.audioIcon) elements.audioIcon.textContent = audioEnabled ? "🔔" : "🔕";
    if (elements.btnAudio) elements.btnAudio.style.opacity = audioEnabled ? "1" : "0.6";
  }
  if (elements.btnAudio) {
    syncAudioUI();
    elements.btnAudio.addEventListener("click", () => {
      audioEnabled = !audioEnabled;
      localStorage.setItem("netpulse_audio", audioEnabled ? "true" : "false");
      syncAudioUI();
      if (audioEnabled) playChime("up");
    });
  }

  function setState(state, kicker, title, message) {
    elements.panel.className = `status-panel ${state}`;
    elements.kicker.textContent = kicker;
    elements.title.textContent = title;
    elements.message.textContent = message;
  }

  function formatChecked(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || "—";
    const ageSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    const relative = ageSeconds < 5 ? "just now" : ageSeconds < 60 ? `${ageSeconds}s ago` : `${Math.floor(ageSeconds / 60)}m ago`;
    return `${relative} · ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
  }

  function updateTelemetry(target, item) {
    if (!historyByTarget[target]) historyByTarget[target] = [];
    const hist = historyByTarget[target];
    hist.push({ status: item.status, latency: item.latency_ms });
    if (hist.length > 10) hist.shift();

    const upCount = hist.filter(c => c.status === "up" || c.status === "degraded").length;
    const uptimePct = Math.round((upCount / hist.length) * 100);
    if (elements.uptime) {
      elements.uptime.textContent = `${uptimePct}%`;
      elements.uptime.style.color = uptimePct >= 90 ? "var(--green)" : (uptimePct >= 50 ? "var(--amber)" : "var(--red)");
    }

    if (elements.sparkline) {
      elements.sparkline.innerHTML = "";
      hist.forEach(h => {
        const bar = document.createElement("div");
        bar.className = `spark-bar ${h.status}`;
        let heightPct = 50;
        if (h.status === "up" && h.latency != null) {
          heightPct = Math.min(100, Math.max(16, Math.round(h.latency * 26)));
        } else if (h.status === "degraded") {
          heightPct = 85;
        } else {
          heightPct = 100;
        }
        bar.style.height = `${heightPct}%`;
        bar.title = `${h.status.toUpperCase()} · ${h.latency != null ? h.latency + ' ms' : 'Packet Drop'}`;
        elements.sparkline.appendChild(bar);
      });
    }
  }

  function renderFleetGrid() {
    if (!elements.fleetGrid) return;
    elements.fleetGrid.innerHTML = "";

    const targets = ["vm-b", "kali-linux", "win-server", "lab-gateway"];
    Object.keys(fleetConnections).forEach(t => {
      if (!targets.includes(t)) targets.push(t);
    });

    let online = 0, degraded = 0, down = 0;

    targets.forEach(tgt => {
      const item = fleetConnections[tgt] || { status: "up", latency_ms: 1.0, message: "OK" };
      const meta = VM_METADATA[tgt] || { name: tgt, ip: "192.168.56.x", os: "💻 Virtual Machine" };

      if (item.status === "up") online++;
      else if (item.status === "degraded") degraded++;
      else down++;

      const card = document.createElement("div");
      card.className = `fleet-card ${tgt === currentFocusedTarget ? "active" : ""}`;
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.title = `Click to inspect ${meta.name} (${tgt})`;

      const rttText = item.latency_ms != null ? `${Number(item.latency_ms).toFixed(item.latency_ms < 10 ? 2 : 1)} ms` : "No reply";

      card.innerHTML = `
        <div class="fleet-card-top">
          <span class="fleet-os-badge">${meta.os}</span>
          <span class="mini-beacon ${item.status}"></span>
        </div>
        <div class="fleet-card-name">${meta.name}</div>
        <div class="fleet-card-ip">${meta.ip}</div>
        <div class="fleet-card-metrics">
          <span class="fleet-rtt">${rttText}</span>
          <span class="fleet-state-tag ${item.status}">${item.status.toUpperCase()}</span>
        </div>
      `;

      card.addEventListener("click", () => {
        focusTarget(tgt);
      });

      elements.fleetGrid.appendChild(card);
    });

    if (elements.fleetOnline) elements.fleetOnline.textContent = online;
    if (elements.fleetDegraded) elements.fleetDegraded.textContent = degraded;
    if (elements.fleetDown) elements.fleetDown.textContent = down;
  }

  function focusTarget(tgt) {
    currentFocusedTarget = tgt;
    if ($("target")) $("target").textContent = tgt;
    if (elements.targetSelect) elements.targetSelect.value = tgt;
    $("connection-id").textContent = `${config.source} → ${tgt}`;

    const meta = VM_METADATA[tgt] || { name: tgt, ip: "192.168.56.x", os: "💻 Virtual Machine" };
    if (elements.targetSubtitle) elements.targetSubtitle.textContent = `${meta.name} (${meta.ip})`;

    const item = fleetConnections[tgt] || {
      source: config.source,
      target: tgt,
      status: "up",
      latency_ms: 1.2,
      checked_at: new Date().toISOString(),
      message: `${meta.name} reachable`
    };

    render(item, false);
    renderFleetGrid();
  }

  function render(item, triggerChime = true) {
    if (triggerChime && item.status !== previousFocusedStatus) {
      if (previousFocusedStatus !== null) playChime(item.status);
      previousFocusedStatus = item.status;
    }

    const meta = VM_METADATA[item.target] || { name: item.target, ip: "192.168.56.x" };

    if (item.status === "up") {
      setState("up", `LINK OPERATIONAL · ${item.target.toUpperCase()}`, `${meta.name} is connected`, item.message || "Target VM is responding normally to ICMP reachability checks.");
      currentSimStatus = "up";
    } else if (item.status === "degraded") {
      setState("degraded", `LINK DEGRADED · ${item.target.toUpperCase()}`, "High latency / packet jitter", item.message || "Intermittent network response detected between lab machines.");
      currentSimStatus = "degraded";
    } else {
      setState("down", `CONNECTION LOST · ${item.target.toUpperCase()}`, `${meta.name} unreachable`, item.message || "The latest reachability check could not reach the target VM.");
      currentSimStatus = "down";
    }

    elements.checked.textContent = formatChecked(item.checked_at);
    elements.latency.textContent = item.latency_ms == null ? "No response" : `${Number(item.latency_ms).toFixed(item.latency_ms < 10 ? 2 : 1)} ms`;
    updateTelemetry(item.target, item);
  }

  async function postTelemetry(status, latency, message) {
    const base = (config.apiUrl || "").replace(/\/$/, "");
    let targetToSim = elements.simTargetSelect ? elements.simTargetSelect.value : "current";
    if (targetToSim === "current") targetToSim = currentFocusedTarget;

    const payload = {
      source: config.source,
      target: targetToSim,
      status: status,
      checked_at: new Date().toISOString(),
      latency_ms: latency,
      message: message
    };

    if (elements.ctrlStatus) elements.ctrlStatus.textContent = "UPDATING...";
    try {
      const response = await fetch(`${base}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (elements.ctrlStatus) elements.ctrlStatus.textContent = "APPLIED ⚡";
      await refresh();
    } catch (err) {
      console.warn("Direct API call unavailable; rendering locally", err);
      if (elements.ctrlStatus) elements.ctrlStatus.textContent = "LOCAL STATE";

      if (targetToSim === "all") {
        Object.keys(fleetConnections).forEach(t => {
          fleetConnections[t] = Object.assign({}, payload, { target: t });
        });
      } else {
        fleetConnections[targetToSim] = payload;
      }
      render(fleetConnections[currentFocusedTarget]);
      renderFleetGrid();
    }
    setTimeout(() => {
      if (elements.ctrlStatus) elements.ctrlStatus.textContent = "READY";
    }, 2000);
  }

  async function refresh() {
    elements.button.disabled = true;
    elements.refreshLabel.textContent = "Checking for updates…";
    elements.refreshDot.classList.remove("error");
    const base = (config.apiUrl || "").replace(/\/$/, "");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    try {
      // Query multi-connection status
      const response = await fetch(`${base}/status?target=all`, { cache: "no-store", signal: controller.signal });
      const data = await response.json().catch(() => ({}));

      if (response.ok && Array.isArray(data.connections) && data.connections.length > 0) {
        data.connections.forEach(conn => {
          fleetConnections[conn.target] = conn;
        });
        const currentItem = fleetConnections[currentFocusedTarget] || data.connections[0];
        render(currentItem);
        renderFleetGrid();
      } else if (response.ok && data.item) {
        fleetConnections[data.item.target] = data.item;
        render(data.item);
        renderFleetGrid();
      } else if (response.status === 404) {
        setState("unknown", "WAITING FOR DATA", "No status yet", "Start the Python monitor on VM A to publish the first check.");
        elements.checked.textContent = "—";
        elements.latency.textContent = "—";
      } else {
        throw new Error(data.error || `HTTP ${response.status}`);
      }
      elements.refreshLabel.textContent = `Auto-refresh active (every ${Math.round(config.refreshIntervalMs / 1000)}s)`;
    } catch (error) {
      // Offline fallback: keep local fleet state visible
      render(fleetConnections[currentFocusedTarget] || { status: "unknown", latency_ms: null, message: "Offline" });
      renderFleetGrid();
      elements.refreshLabel.textContent = error.name === "AbortError" ? "Request timed out — retrying automatically" : "Update failed — retrying automatically";
      elements.refreshDot.classList.add("error");
    } finally {
      clearTimeout(timeout);
      elements.button.disabled = false;
    }
  }

  // Two-way synchronization between Latency Slider & Number Input
  if (elements.slider && elements.numInput) {
    elements.slider.addEventListener("input", (e) => {
      elements.numInput.value = e.target.value;
    });
    elements.numInput.addEventListener("input", (e) => {
      elements.slider.value = e.target.value;
    });
  }

  // Target VM Dropdown Switcher
  if (elements.targetSelect) {
    elements.targetSelect.addEventListener("change", (e) => {
      focusTarget(e.target.value);
    });
  }

  // Teacher Demo Action Buttons
  if (elements.btnConnect) {
    elements.btnConnect.addEventListener("click", () => {
      currentSimStatus = "up";
      const lat = parseFloat(elements.numInput.value) || 1.25;
      const msg = "VM connected via VirtualBox host-only adapter";
      postTelemetry("up", lat, msg);
    });
  }

  if (elements.btnDegrade) {
    elements.btnDegrade.addEventListener("click", () => {
      currentSimStatus = "degraded";
      let lat = parseFloat(elements.numInput.value) || 52.0;
      if (lat < 20) {
        lat = 52.0;
        elements.numInput.value = lat;
        elements.slider.value = lat;
      }
      const msg = "High network latency / packet jitter detected on VM bridge";
      elements.msgInput.value = msg;
      postTelemetry("degraded", lat, msg);
    });
  }

  if (elements.btnDisconnect) {
    elements.btnDisconnect.addEventListener("click", () => {
      currentSimStatus = "down";
      const msg = "Destination Host Unreachable · Virtual network cable unplugged";
      elements.msgInput.value = msg;
      postTelemetry("down", null, msg);
    });
  }

  if (elements.btnApply) {
    elements.btnApply.addEventListener("click", () => {
      const lat = currentSimStatus === "down" ? null : (parseFloat(elements.numInput.value) || 1.25);
      const msg = elements.msgInput.value || (currentSimStatus === "up" ? "Target reachable" : "Target unreachable");
      postTelemetry(currentSimStatus, lat, msg);
    });
  }

  // Quick Preset Buttons
  document.querySelectorAll(".btn-preset").forEach(btn => {
    btn.addEventListener("click", () => {
      const lat = parseFloat(btn.dataset.latency);
      const status = btn.dataset.status;
      currentSimStatus = status;
      elements.numInput.value = lat;
      elements.slider.value = lat;
      let msg = status === "up" ? `Verified connectivity with ${lat} ms RTT` : `High latency spike: ${lat} ms`;
      elements.msgInput.value = msg;
      postTelemetry(status, lat, msg);
    });
  });

  elements.button.addEventListener("click", refresh);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  focusTarget(currentFocusedTarget);
  refresh();
  timer = setInterval(() => { if (!document.hidden) refresh(); }, Math.max(2500, config.refreshIntervalMs));
  window.addEventListener("beforeunload", () => clearInterval(timer));
})();
