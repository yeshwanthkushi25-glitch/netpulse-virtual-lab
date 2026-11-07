(() => {
  "use strict";
  const config = Object.assign({ apiUrl: "", source: "vm-a", target: "vm-b", refreshIntervalMs: 10000 }, window.NETPULSE_CONFIG);
  const $ = (id) => document.getElementById(id);
  const elements = {
    panel: $("status-panel"), kicker: $("status-kicker"), title: $("status-title"),
    message: $("status-message"), checked: $("checked-at"), latency: $("latency"),
    button: $("refresh-button"), refreshLabel: $("refresh-label"), refreshDot: $("refresh-dot")
  };
  let timer;

  $("source").textContent = config.source;
  $("target").textContent = config.target;
  $("connection-id").textContent = `${config.source} → ${config.target}`;

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

  function render(item) {
    if (item.status === "up") {
      setState("up", "LINK OPERATIONAL", "VMs are connected", item.message || "The target VM is responding to connectivity checks.");
    } else {
      setState("down", "CONNECTION LOST", "Target unreachable", item.message || "The latest check could not reach the target VM.");
    }
    elements.checked.textContent = formatChecked(item.checked_at);
    elements.latency.textContent = item.latency_ms == null ? "No response" : `${Number(item.latency_ms).toFixed(item.latency_ms < 10 ? 2 : 1)} ms`;
  }

  async function refresh() {
    elements.button.disabled = true;
    elements.refreshLabel.textContent = "Checking for updates…";
    elements.refreshDot.classList.remove("error");
    const base = (config.apiUrl || "").replace(/\/$/, "");
    const query = new URLSearchParams({ source: config.source, target: config.target });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
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
      elements.refreshLabel.textContent = `Auto-refresh every ${Math.round(config.refreshIntervalMs / 1000)} seconds`;
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
    const base = (config.apiUrl || "").replace(/\/$/, "");
    const payload = {
      source: config.source,
      target: config.target,
      status: status,
      checked_at: new Date().toISOString(),
      latency_ms: isUp ? Number((Math.random() * 1.5 + 0.9).toFixed(2)) : null,
      message: isUp ? "VMs connected · Link verified via interactive simulation" : "Target unreachable · Link severed via interactive simulation"
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
  const btnDown = $("btn-simulate-down");
  if (btnUp) btnUp.addEventListener("click", () => simulateStatus("up"));
  if (btnDown) btnDown.addEventListener("click", () => simulateStatus("down"));

  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  refresh();
  timer = setInterval(() => { if (!document.hidden) refresh(); }, Math.max(3000, config.refreshIntervalMs));
  window.addEventListener("beforeunload", () => clearInterval(timer));
})();
