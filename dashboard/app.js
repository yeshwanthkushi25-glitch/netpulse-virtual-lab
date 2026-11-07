(() => {
  "use strict";
  const config = Object.assign({ apiUrl: "", source: "vm-a", target: "vm-b", refreshIntervalMs: 5000 }, window.NETPULSE_CONFIG);
  const $ = (id) => document.getElementById(id);
  const elements = {
    panel: $("status-panel"), kicker: $("status-kicker"), title: $("status-title"),
    message: $("status-message"), checked: $("checked-at"), latency: $("latency"),
    button: $("refresh-button"), refreshLabel: $("refresh-label"), refreshDot: $("refresh-dot")
  };

  let timer;
  let previousStatus = null;
  let checkHistory = [];
  let audioEnabled = localStorage.getItem("netpulse_audio") !== "false";

  $("source").textContent = config.source;
  $("target").textContent = config.target;
  $("connection-id").textContent = `${config.source} → ${config.target}`;

  // Synthesized Web Audio API Chime (Zero external audio files required)
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

  const btnAudio = $("btn-audio");
  const audioState = $("audio-state");
  const audioIcon = $("audio-icon");
  function syncAudioUI() {
    if (audioState) audioState.textContent = audioEnabled ? "ON" : "OFF";
    if (audioIcon) audioIcon.textContent = audioEnabled ? "🔔" : "🔕";
    if (btnAudio) btnAudio.style.opacity = audioEnabled ? "1" : "0.6";
  }
  if (btnAudio) {
    syncAudioUI();
    btnAudio.addEventListener("click", () => {
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
    const uptimeEl = $("uptime-val");
    if (uptimeEl) {
      uptimeEl.textContent = `${uptimePct}%`;
      uptimeEl.style.color = uptimePct >= 90 ? "var(--green)" : (uptimePct >= 50 ? "var(--amber)" : "var(--red)");
    }

    const sparkEl = $("latency-sparkline");
    if (sparkEl) {
      sparkEl.innerHTML = "";
      checkHistory.forEach(h => {
        const bar = document.createElement("div");
        bar.className = `spark-bar ${h.status}`;
        let heightPct = 50;
        if (h.status === "up" && h.latency != null) {
          heightPct = Math.min(100, Math.max(18, Math.round(h.latency * 28)));
        } else if (h.status === "degraded") {
          heightPct = 85;
        } else {
          heightPct = 100;
        }
        bar.style.height = `${heightPct}%`;
        bar.title = `${h.status.toUpperCase()} · ${h.latency != null ? h.latency + ' ms' : 'Packet Drop'}`;
        sparkEl.appendChild(bar);
      });
    }
  }

  function render(item) {
    if (item.status !== previousStatus) {
      if (previousStatus !== null) playChime(item.status);
      previousStatus = item.status;
    }

    if (item.status === "up") {
      setState("up", "LINK OPERATIONAL", "VMs are connected", item.message || "The target VM is responding to ICMP reachability checks.");
    } else if (item.status === "degraded") {
      setState("degraded", "LINK DEGRADED · JITTER", "High latency / packet loss", item.message || "Intermittent network response detected between lab machines.");
    } else {
      setState("down", "CONNECTION LOST", "Target unreachable", item.message || "The latest check could not reach the target VM.");
    }

    elements.checked.textContent = formatChecked(item.checked_at);
    elements.latency.textContent = item.latency_ms == null ? "No response" : `${Number(item.latency_ms).toFixed(item.latency_ms < 10 ? 2 : 1)} ms`;
    updateTelemetry(item);
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

  elements.button.addEventListener("click", refresh);

  async function simulateStatus(status) {
    const isUp = status === "up";
    const isDegraded = status === "degraded";
    const base = (config.apiUrl || "").replace(/\/$/, "");
    let lat = isUp ? Number((Math.random() * 1.5 + 0.9).toFixed(2)) : (isDegraded ? Number((Math.random() * 40 + 35).toFixed(1)) : null);
    let msg = isUp ? "VMs connected · Link verified via interactive simulation" : (isDegraded ? "Intermittent jitter spike detected" : "Target unreachable · Link severed via interactive simulation");

    const payload = {
      source: config.source,
      target: config.target,
      status: status,
      checked_at: new Date().toISOString(),
      latency_ms: lat,
      message: msg
    };
    try {
      elements.refreshLabel.textContent = `Posting simulated ${status.toUpperCase()} state…`;
      const response = await fetch(`${base}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error(`Simulation failed: HTTP ${response.status}`);
      }
      await refresh();
    } catch (err) {
      console.warn("Direct API call unavailable; rendering local simulation state", err);
      render(payload);
    }
  }

  const btnUp = $("btn-simulate-up");
  const btnDegraded = $("btn-simulate-degraded");
  const btnDown = $("btn-simulate-down");
  if (btnUp) btnUp.addEventListener("click", () => simulateStatus("up"));
  if (btnDegraded) btnDegraded.addEventListener("click", () => simulateStatus("degraded"));
  if (btnDown) btnDown.addEventListener("click", () => simulateStatus("down"));

  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  refresh();
  timer = setInterval(() => { if (!document.hidden) refresh(); }, Math.max(2500, config.refreshIntervalMs));
  window.addEventListener("beforeunload", () => clearInterval(timer));
})();
