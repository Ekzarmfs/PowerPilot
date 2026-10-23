/**
 * PowerPilot — Presentation Showcase & Interactive App Simulator
 * Windows 11 Battery Optimization & Telemetry Engine
 */

// ── Application Simulation State ──────────────────────────────────────
const state = {
  batteryPercent: 78,
  isCharging: false,
  powerPlan: "Balanced",
  timeRemainingHours: 5.7,
  healthPercent: 98.4,
  activeLoadout: "work",
  processes: [
    { id: 1, name: "Google Chrome (14 tabs)", pid: 14280, category: "User App", cpu: 4.8, ram: 680, drain: "critical", isSystem: false, icon: "🌐" },
    { id: 2, name: "Discord Voice & Video", pid: 8940, category: "User App", cpu: 2.4, ram: 310, drain: "high", isSystem: false, icon: "💬" },
    { id: 3, name: "Microsoft Teams (Background)", pid: 11204, category: "Microsoft", cpu: 1.8, ram: 240, drain: "high", isSystem: false, icon: "Ⓜ️" },
    { id: 4, name: "Spotify Music Player", pid: 7420, category: "User App", cpu: 1.2, ram: 180, drain: "moderate", isSystem: false, icon: "🎵" },
    { id: 5, name: "Visual Studio Code Server", pid: 16824, category: "User App", cpu: 2.1, ram: 450, drain: "moderate", isSystem: false, icon: "💻" },
    { id: 6, name: "SearchIndexer.exe (WinSearch)", pid: 3204, category: "Windows", cpu: 3.4, ram: 95, drain: "moderate", isSystem: true, icon: "🔍" },
    { id: 7, name: "OneDrive Sync Engine", pid: 5612, category: "Microsoft", cpu: 0.6, ram: 85, drain: "low", isSystem: false, icon: "☁️" },
    { id: 8, name: "Adobe Creative Cloud Core", pid: 9028, category: "Third-Party", cpu: 1.5, ram: 210, drain: "high", isSystem: false, icon: "📦" },
    { id: 9, name: "Steam Client WebHelper", pid: 13912, category: "User App", cpu: 1.1, ram: 195, drain: "moderate", isSystem: false, icon: "🎮" },
    { id: 10, name: "DiagTrack (Windows Telemetry)", pid: 4892, category: "Windows", cpu: 1.4, ram: 64, drain: "moderate", isSystem: true, icon: "🪟" },
    { id: 11, name: "Windows Explorer (explorer.exe)", pid: 2140, category: "System Core", cpu: 0.5, ram: 120, drain: "low", isSystem: true, icon: "📁" },
    { id: 12, name: "Desktop Window Manager (dwm.exe)", pid: 1040, category: "System Core", cpu: 1.1, ram: 88, drain: "low", isSystem: true, icon: "🖥️" },
    { id: 13, name: "PowerPilotNative.exe (Core)", pid: 6180, category: "Telemetry Daemon", cpu: 0.1, ram: 14, drain: "low", isSystem: true, icon: "⚡" },
    { id: 14, name: "Notion Desktop App", pid: 15302, category: "User App", cpu: 1.6, ram: 280, drain: "high", isSystem: false, icon: "📝" },
    { id: 15, name: "Slack Desktop Client", pid: 12844, category: "User App", cpu: 1.4, ram: 260, drain: "high", isSystem: false, icon: "💼" },
    { id: 16, name: "NVIDIA Container (Display)", pid: 3412, category: "Hardware", cpu: 0.8, ram: 72, drain: "low", isSystem: true, icon: "🎮" },
    { id: 17, name: "Windows Audio Device Graph", pid: 4108, category: "System Core", cpu: 0.3, ram: 38, drain: "low", isSystem: true, icon: "🔊" },
    { id: 18, name: "Antivirus Real-Time Shield", pid: 2854, category: "Security", cpu: 0.9, ram: 115, drain: "low", isSystem: true, icon: "🛡️" }
  ],
  currentSlide: 1,
  totalSlides: 6,
  activeFilter: "all",
  searchQuery: "",
  totalOptimizedSavingsMin: 38,
  totalOptimizedWatts: 2.8
};

// Keep a pristine backup of initial processes for the reset button
const INITIAL_PROCESSES = JSON.parse(JSON.stringify(state.processes));

// ── DOM Initialization ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderBatteryGauge();
  renderProcessTable();
  updateDashboardMetrics();
  startClock();
  setupKeyboardShortcuts();
});

// ── Mode Switcher (Simulator vs Slides vs Architecture) ─────────────
function switchMainMode(mode) {
  // Update header navigation buttons
  document.querySelectorAll(".view-switcher .mode-btn").forEach(btn => {
    btn.classList.remove("active");
    btn.setAttribute("aria-selected", "false");
  });

  // Hide all sections
  document.querySelectorAll("section[id^='view-']").forEach(sec => {
    sec.classList.remove("active-view");
  });

  if (mode === "simulator") {
    document.getElementById("btn-mode-simulator").classList.add("active");
    document.getElementById("btn-mode-simulator").setAttribute("aria-selected", "true");
    document.getElementById("view-simulator").classList.add("active-view");
  } else if (mode === "slides") {
    document.getElementById("btn-mode-slides").classList.add("active");
    document.getElementById("btn-mode-slides").setAttribute("aria-selected", "true");
    document.getElementById("view-slides").classList.add("active-view");
    updateSlideView();
  } else if (mode === "arch") {
    document.getElementById("btn-mode-arch").classList.add("active");
    document.getElementById("btn-mode-arch").setAttribute("aria-selected", "true");
    document.getElementById("view-arch").classList.add("active-view");
  }
}

// ── App Tab Switcher (Inside App Window Frame) ──────────────────────
function selectAppTab(tabId) {
  // Update sidebar buttons
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    item.classList.remove("active");
    if (item.getAttribute("data-tab") === tabId) {
      item.classList.add("active");
    }
  });

  // Switch tab content views
  document.querySelectorAll(".app-viewport .app-view").forEach(view => {
    view.classList.remove("active");
  });

  const activeView = document.getElementById(tabId);
  if (activeView) {
    activeView.classList.add("active");
  }
}

// ── Live Battery Gauge Rendering ────────────────────────────────────
function renderBatteryGauge() {
  const arc = document.getElementById("gauge-fill-arc");
  const pctLabel = document.getElementById("hero-percent");
  const statusLabel = document.getElementById("hero-status");
  const chargingTag = document.getElementById("hero-charging-tag");
  const timeLabel = document.getElementById("hero-time-remaining");
  const sbBar = document.getElementById("sb-battery-bar");
  const sbText = document.getElementById("sb-battery-text");
  const dischargeRateTag = document.getElementById("hero-discharge-rate");

  const totalCircumference = 477; // 2 * PI * 76
  const dashoffset = totalCircumference - (totalCircumference * (state.batteryPercent / 100));

  if (arc) {
    arc.style.strokeDashoffset = dashoffset;
    if (state.isCharging) {
      arc.style.stroke = "#00f0ff";
    } else if (state.batteryPercent > 50) {
      arc.style.stroke = "#10b981";
    } else if (state.batteryPercent > 20) {
      arc.style.stroke = "#f59e0b";
    } else {
      arc.style.stroke = "#f43f5e";
    }
  }

  if (pctLabel) pctLabel.textContent = `${state.batteryPercent}%`;

  if (state.isCharging) {
    if (statusLabel) statusLabel.textContent = "AC Power Connected";
    if (chargingTag) chargingTag.style.display = "block";
    if (timeLabel) timeLabel.textContent = "42m to 100%";
    if (dischargeRateTag) {
      dischargeRateTag.textContent = "Charge Rate: +45.2 W (Fast Charge)";
      dischargeRateTag.style.color = "#00f0ff";
    }
  } else {
    if (statusLabel) statusLabel.textContent = "Discharging";
    if (chargingTag) chargingTag.style.display = "none";
    const hours = Math.floor(state.timeRemainingHours);
    const mins = Math.round((state.timeRemainingHours - hours) * 60);
    if (timeLabel) timeLabel.textContent = `${hours}h ${mins}m`;
    if (dischargeRateTag) {
      const watts = state.powerPlan === "High Performance" ? "-18.5 W" : (state.powerPlan === "Extreme Saver" ? "-6.4 W" : "-9.4 W");
      dischargeRateTag.textContent = `Discharge Rate: ${watts} (${state.powerPlan})`;
      dischargeRateTag.style.color = "#38bdf8";
    }
  }

  if (sbBar) sbBar.style.width = `${state.batteryPercent}%`;
  if (sbText) {
    const hours = Math.floor(state.timeRemainingHours);
    const mins = Math.round((state.timeRemainingHours - hours) * 60);
    sbText.textContent = state.isCharging ? `${state.batteryPercent}% • Charging` : `${state.batteryPercent}% • ${hours}h ${mins}m`;
  }
}

// ── Simulate AC Adapter Plug / Unplug ───────────────────────────────
function toggleCharger() {
  state.isCharging = !state.isCharging;
  const icon = document.getElementById("power-state-icon");
  const text = document.getElementById("power-state-text");

  if (state.isCharging) {
    icon.textContent = "⚡";
    text.textContent = "Simulate: Plugged In (Charging)";
    showToast("⚡ AC Adapter Connected — High-speed battery charging active!");
  } else {
    icon.textContent = "🔌";
    text.textContent = "Simulate: Discharging";
    showToast("🔋 Running on Battery Telemetry — Energy conservation active");
  }

  renderBatteryGauge();
}

// ── Dashboard Metrics Updater ───────────────────────────────────────
function updateDashboardMetrics() {
  const totalRam = state.processes.reduce((acc, p) => acc + p.ram, 0);
  const activeCount = state.processes.length;

  const planName = document.getElementById("dash-plan-name");
  const procCount = document.getElementById("dash-proc-count");
  const memUsage = document.getElementById("dash-mem-usage");
  const drainRate = document.getElementById("dash-drain-rate");
  const sbScheme = document.getElementById("sb-power-scheme");
  const sbBadge = document.getElementById("sidebar-proc-badge");

  if (planName) planName.textContent = state.powerPlan;
  if (sbScheme) sbScheme.textContent = state.powerPlan;
  if (procCount) procCount.textContent = `${activeCount} Active`;
  if (sbBadge) sbBadge.textContent = activeCount;
  if (memUsage) memUsage.textContent = `${totalRam.toLocaleString()} MB`;
  if (drainRate) {
    const drainEst = (activeCount * 0.78).toFixed(1);
    drainRate.textContent = `~${drainEst}% Drain`;
  }
}

// ── Clean Sweep Action ──────────────────────────────────────────────
function executeCleanSweep() {
  const sweepBtn = document.getElementById("btn-clean-sweep");
  const sweepText = document.getElementById("sweep-btn-text");
  const feedback = document.getElementById("sweep-feedback");

  if (!sweepBtn) return;

  sweepBtn.disabled = true;
  sweepText.textContent = "Sweeping Non-Essential Tasks...";

  setTimeout(() => {
    // Terminate non-system user applications
    const killedCount = state.processes.filter(p => !p.isSystem).length;
    state.processes = state.processes.filter(p => p.isSystem);

    // Increase runtime estimate by 48 minutes
    state.timeRemainingHours += 0.8;

    updateDashboardMetrics();
    renderProcessTable();
    renderBatteryGauge();

    sweepBtn.disabled = false;
    sweepText.textContent = "Clean Sweep Completed";
    if (feedback) {
      feedback.textContent = `✓ Terminated ${killedCount} apps • Freed 1,280 MB RAM`;
    }

    showToast(`🧹 Clean Sweep finished! Closed ${killedCount} user tasks, +48m runtime gained.`);

    setTimeout(() => {
      sweepText.textContent = "Clean Sweep Now";
      if (feedback) feedback.textContent = "";
    }, 4000);
  }, 750);
}

// ── Process Energy Tracker ──────────────────────────────────────────
function renderProcessTable() {
  const tbody = document.getElementById("processes-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  const query = state.searchQuery.toLowerCase();
  const filtered = state.processes.filter(proc => {
    const matchesSearch = proc.name.toLowerCase().includes(query) || proc.pid.toString().includes(query) || proc.category.toLowerCase().includes(query);
    if (!matchesSearch) return false;

    if (state.activeFilter === "critical") return proc.drain === "critical";
    if (state.activeFilter === "high") return proc.drain === "high" || proc.drain === "critical";
    if (state.activeFilter === "user") return !proc.isSystem;
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-tertiary);">No processes match the active filter or search criteria.</td></tr>`;
    return;
  }

  filtered.forEach(proc => {
    const tr = document.createElement("tr");

    let badgeClass = "badge-low";
    if (proc.drain === "critical") badgeClass = "badge-critical";
    else if (proc.drain === "high") badgeClass = "badge-high";
    else if (proc.drain === "moderate") badgeClass = "badge-moderate";

    const killButton = proc.isSystem 
      ? `<button class="btn-proc-action disabled" title="Protected System Service" disabled>Protected</button>`
      : `<button class="btn-proc-action" onclick="terminateSingleProcess(${proc.id})" title="Terminate Process">End Task</button>`;

    tr.innerHTML = `
      <td>
        <div class="proc-name-cell">
          <span class="proc-icon">${proc.icon}</span>
          <span>${proc.name}</span>
        </div>
      </td>
      <td class="proc-pid">${proc.pid}</td>
      <td>${proc.category}</td>
      <td><strong>${proc.cpu}%</strong></td>
      <td>${proc.ram} MB</td>
      <td><span class="drain-badge ${badgeClass}">${proc.drain.toUpperCase()}</span></td>
      <td style="text-align: right;">${killButton}</td>
    `;
    tbody.appendChild(tr);
  });
}

function terminateSingleProcess(id) {
  const target = state.processes.find(p => p.id === id);
  if (!target) return;

  state.processes = state.processes.filter(p => p.id !== id);
  state.timeRemainingHours += (target.cpu * 0.05);

  updateDashboardMetrics();
  renderProcessTable();
  renderBatteryGauge();

  showToast(`🛑 Terminated ${target.name} (PID: ${target.pid})`);
}

function resetProcesses() {
  state.processes = JSON.parse(JSON.stringify(INITIAL_PROCESSES));
  state.timeRemainingHours = 5.7;
  updateDashboardMetrics();
  renderProcessTable();
  renderBatteryGauge();
  showToast("↺ Process simulation reset to default telemetry state");
}

function filterProcessList() {
  const input = document.getElementById("proc-search-input");
  if (input) {
    state.searchQuery = input.value;
    renderProcessTable();
  }
}

function setProcessFilter(filter, btn) {
  state.activeFilter = filter;
  document.querySelectorAll(".filter-pills .filter-pill").forEach(p => p.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderProcessTable();
}

// ── Loadout Profile Switching ───────────────────────────────────────
function activateLoadout(type) {
  state.activeLoadout = type;

  document.querySelectorAll(".loadout-card").forEach(c => c.classList.remove("active-loadout"));
  const targetCard = document.getElementById(`loadout-${type}`);
  if (targetCard) targetCard.classList.add("active-loadout");

  if (type === "work") {
    state.powerPlan = "Balanced";
    state.timeRemainingHours = 5.7;
    showToast("💼 Work Focus Loadout engaged (Balanced power, 70% brightness)");
  } else if (type === "gaming") {
    state.powerPlan = "High Performance";
    state.timeRemainingHours = 2.5;
    showToast("🎮 Gaming Loadout engaged (High Performance, 100% brightness, max clocks)");
  } else if (type === "saver") {
    state.powerPlan = "Extreme Saver";
    state.timeRemainingHours = 8.2;
    showToast("🔋 Extreme Endurance Loadout engaged (+2.5 hrs extra battery runtime!)");
  } else if (type === "idle") {
    state.powerPlan = "Idle Preservation";
    state.timeRemainingHours = 10.5;
    showToast("😴 Idle Conservation engaged (Deep sleep states active)");
  }

  updateDashboardMetrics();
  renderBatteryGauge();
}

// ── Optimizer Service Toggles ───────────────────────────────────────
function toggleOptimizerService(checkbox, minGain, wattGain) {
  if (checkbox.checked) {
    state.totalOptimizedSavingsMin += minGain;
    state.totalOptimizedWatts += wattGain;
    showToast(`✓ Service optimized: +${minGain}m battery gained`);
  } else {
    state.totalOptimizedSavingsMin = Math.max(0, state.totalOptimizedSavingsMin - minGain);
    state.totalOptimizedWatts = Math.max(0.5, state.totalOptimizedWatts - wattGain);
  }

  const gainLabel = document.getElementById("opt-runtime-gain");
  const wattLabel = document.getElementById("opt-power-gain");
  const countLabel = document.getElementById("opt-disabled-count");

  const checkedCount = document.querySelectorAll(".optimizer-list input[type='checkbox']:checked").length;
  if (gainLabel) gainLabel.textContent = `+${state.totalOptimizedSavingsMin} min`;
  if (wattLabel) wattLabel.textContent = `~${state.totalOptimizedWatts.toFixed(1)} W`;
  if (countLabel) countLabel.textContent = `${checkedCount} of 9`;
}

function optimizeAllServices() {
  document.querySelectorAll(".optimizer-list input[type='checkbox']").forEach(box => {
    box.checked = true;
  });

  state.totalOptimizedSavingsMin = 94;
  state.totalOptimizedWatts = 6.2;

  const gainLabel = document.getElementById("opt-runtime-gain");
  const wattLabel = document.getElementById("opt-power-gain");
  const countLabel = document.getElementById("opt-disabled-count");

  if (gainLabel) gainLabel.textContent = `+94 min`;
  if (wattLabel) wattLabel.textContent = `~6.2 W`;
  if (countLabel) countLabel.textContent = `9 of 9`;

  showToast("⚡ All 9 background telemetry leeches optimized! +1.5h battery extended.");
}

// ── Presentation Deck Controller ────────────────────────────────────
function updateSlideView() {
  document.querySelectorAll(".deck-container .slide").forEach(s => s.classList.remove("active-slide"));
  document.querySelectorAll(".deck-dots .dot").forEach(d => d.classList.remove("active"));

  const targetSlide = document.querySelector(`.slide[data-slide="${state.currentSlide}"]`);
  if (targetSlide) {
    targetSlide.classList.add("active-slide");
    const title = targetSlide.getAttribute("data-title") || "";
    document.getElementById("deck-slide-title").textContent = title;
  }

  const numLabel = document.getElementById("current-slide-num");
  if (numLabel) numLabel.textContent = state.currentSlide;

  const dots = document.querySelectorAll(".deck-dots .dot");
  if (dots[state.currentSlide - 1]) {
    dots[state.currentSlide - 1].classList.add("active");
  }

  const prevBtn = document.getElementById("btn-prev-slide");
  const nextBtn = document.getElementById("btn-next-slide");
  if (prevBtn) prevBtn.disabled = state.currentSlide === 1;
  if (nextBtn) {
    nextBtn.textContent = state.currentSlide === state.totalSlides ? "Finish Presentation" : "Next ▶";
  }
}

function nextSlide() {
  if (state.currentSlide < state.totalSlides) {
    state.currentSlide++;
    updateSlideView();
  } else {
    // Jump straight to interactive simulator on finish
    switchMainMode("simulator");
    selectAppTab("tab-dashboard");
    showToast("🚀 Entering live application simulator!");
  }
}

function prevSlide() {
  if (state.currentSlide > 1) {
    state.currentSlide--;
    updateSlideView();
  }
}

function goToSlide(n) {
  if (n >= 1 && n <= state.totalSlides) {
    state.currentSlide = n;
    updateSlideView();
  }
}

function toggleFullscreen() {
  const elem = document.getElementById("view-slides");
  if (!document.fullscreenElement) {
    if (elem.requestFullscreen) elem.requestFullscreen();
  } else {
    if (document.exitFullscreen) document.exitFullscreen();
  }
}

// ── Keyboard Shortcuts (Presentation ← / → navigation) ──────────────
function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    // Check if in slides mode
    const isSlidesActive = document.getElementById("view-slides").classList.contains("active-view");
    if (!isSlidesActive) return;

    if (e.key === "ArrowRight" || e.key === " ") {
      e.preventDefault();
      nextSlide();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      prevSlide();
    }
  });
}

// ── Toast Notification Helper ───────────────────────────────────────
let toastTimer = null;
function showToast(message) {
  const toast = document.getElementById("toast-notification");
  const msgEl = document.getElementById("toast-message");
  if (!toast || !msgEl) return;

  msgEl.textContent = message;
  toast.classList.add("visible");

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("visible");
  }, 3200);
}

// ── Download Modal ──────────────────────────────────────────────────
function showDownloadModal() {
  const modal = document.getElementById("download-modal");
  if (modal) modal.style.display = "flex";
}

function hideDownloadModal() {
  const modal = document.getElementById("download-modal");
  if (modal) modal.style.display = "none";
}

// ── Live Digital Clock ──────────────────────────────────────────────
function startClock() {
  const clockEl = document.getElementById("live-clock");
  if (!clockEl) return;

  const update = () => {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  update();
  setInterval(update, 1000);
}
