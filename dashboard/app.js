(() => {
  "use strict";
  const config = Object.assign({ apiUrl: "", source: "vm-a", target: "vm-b", refreshIntervalMs: 5000 }, window.NETPULSE_CONFIG);
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
    sparkline: $("latency-sparkline"), uptime: $("uptime-val")
  };

  let timer;
  let previousStatus = null;
  let currentSimStatus = "up";
  let checkHistory = [];
  let audioEnabled = localStorage.getItem("netpulse_audio") !== "false";

  $("source").textContent = config.source;
  $("target").textContent = config.target;
  $("connection-id").textContent = `${config.source} → ${config.target}`;

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

  function updateTelemetry(item) {
    checkHistory.push({ status: item.status, latency: item.latency_ms });
    if (checkHistory.length > 10) checkHistory.shift();

    const upCount = checkHistory.filter(c => c.status === "up" || c.status === "degraded").length;
    const uptimePct = Math.round((upCount / checkHistory.length) * 100);
    if (elements.uptime) {
      elements.uptime.textContent = `${uptimePct}%`;
      elements.uptime.style.color = uptimePct >= 90 ? "var(--green)" : (uptimePct >= 50 ? "var(--amber)" : "var(--red)");
    }

    if (elements.sparkline) {
      elements.sparkline.innerHTML = "";
      checkHistory.forEach(h => {
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

  function render(item) {
    if (item.status !== previousStatus) {
      if (previousStatus !== null) playChime(item.status);
      previousStatus = item.status;
    }

    if (item.status === "up") {
      setState("up", "LINK OPERATIONAL", "VMs are connected", item.message || "Target VM is responding normally to ICMP reachability checks.");
      currentSimStatus = "up";
    } else if (item.status === "degraded") {
      setState("degraded", "LINK DEGRADED · JITTER", "High latency / packet jitter", item.message || "Intermittent network response detected between lab machines.");
      currentSimStatus = "degraded";
    } else {
      setState("down", "CONNECTION LOST", "Target unreachable", item.message || "The latest reachability check could not reach the target VM.");
      currentSimStatus = "down";
    }

    elements.checked.textContent = formatChecked(item.checked_at);
    elements.latency.textContent = item.latency_ms == null ? "No response" : `${Number(item.latency_ms).toFixed(item.latency_ms < 10 ? 2 : 1)} ms`;
    updateTelemetry(item);
  }

  async function postTelemetry(status, latency, message) {
    const base = (config.apiUrl || "").replace(/\/$/, "");
    const payload = {
      source: config.source,
      target: config.target,
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
      render(payload);
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
    const query = new URLSearchParams({ source: config.source, target: config.target });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch(`${base}/status?${query}`, { cache: "no-store", signal: controller.signal });
      const data = await response.json().catch(() => ({}));
      if (response.status === 404) {
        setState("unknown", "WAITING FOR DATA", "No status yet", "Start the Python monitor on VM A to publish the first check.");
        elements.checked.textContent = "—";
        elements.latency.textContent = "—";
      } else if (!response.ok || !data.item) {
        throw new Error(data.error || `Dashboard API returned HTTP ${response.status}`);
      } else {
        render(data.item);
      }
      elements.refreshLabel.textContent = `Auto-refresh active (every ${Math.round(config.refreshIntervalMs / 1000)}s)`;
    } catch (error) {
      setState("unknown", "DASHBOARD OFFLINE", "Cannot retrieve status", "The dashboard API is unavailable. This does not by itself mean the VM link is down.");
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

  // Teacher Demo Action Buttons
  if (elements.btnConnect) {
    elements.btnConnect.addEventListener("click", () => {
      currentSimStatus = "up";
      const lat = parseFloat(elements.numInput.value) || 1.25;
      const msg = elements.msgInput.value || "VMs connected via VirtualBox host-only adapter";
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
      const msg = "High network latency / packet jitter detected between lab VMs";
      elements.msgInput.value = msg;
      postTelemetry("degraded", lat, msg);
    });
  }

  if (elements.btnDisconnect) {
    elements.btnDisconnect.addEventListener("click", () => {
      currentSimStatus = "down";
      const msg = "Destination Host Unreachable · Virtual cable disconnected";
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
  refresh();
  timer = setInterval(() => { if (!document.hidden) refresh(); }, Math.max(2500, config.refreshIntervalMs));
  window.addEventListener("beforeunload", () => clearInterval(timer));
})();
