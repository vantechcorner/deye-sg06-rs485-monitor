/* Same topic map / stale windows as the LCD firmware. */
const PLACEHOLDER = "—";
const SOC_R = 50;
const SOC_CIRC = 2 * Math.PI * SOC_R;
const SOC_ARC = SOC_CIRC * 0.75;
const BATT_PWR_MAX_W = 3500;
const BATT_PWR_SEGS = 10;
const GRID_ON_V_MIN = 80;
const GRID_ON_HZ_MIN = 45;
const GRID_ON_HZ_MAX = 66;
const STORAGE_KEY = "deye-mqtt-web";
const HISTORY_MAX = 90;
const HISTORY_MS = 2000;

const METRICS = {
  status: { staleMs: 25000 },
  "battery/voltage": { staleMs: 10000, kind: "v2" },
  "battery/soc": { staleMs: 10000, kind: "soc" },
  "battery/power": { staleMs: 10000, kind: "w" },
  "battery/current": { staleMs: 10000, kind: "a" },
  "battery/temperature": { staleMs: 25000, kind: "c" },
  "battery/charge_today": { staleMs: 90000, kind: "kwh" },
  "battery/discharge_today": { staleMs: 90000, kind: "kwh" },
  "pv1/voltage": { staleMs: 10000, kind: "v1" },
  "pv1/current": { staleMs: 10000, kind: "a" },
  "pv1/power": { staleMs: 10000, kind: "w" },
  "pv2/voltage": { staleMs: 10000, kind: "v1" },
  "pv2/current": { staleMs: 10000, kind: "a" },
  "pv2/power": { staleMs: 10000, kind: "w" },
  "pv/energy_today": { staleMs: 90000, kind: "kwh" },
  "grid/frequency": { staleMs: 10000, kind: "hz" },
  "grid/voltage": { staleMs: 10000, kind: "v1" },
  "grid/current": { staleMs: 10000, kind: "a" },
  "grid/power_ct": { staleMs: 10000, kind: "w" },
  "grid/buy_today": { staleMs: 90000, kind: "kwh" },
  "grid/sell_today": { staleMs: 90000, kind: "kwh" },
  "inverter/temperature": { staleMs: 25000, kind: "c" },
  "inverter/voltage": { staleMs: 10000, kind: "v1" },
  "inverter/power": { staleMs: 10000, kind: "w" },
  "inverter/frequency": { staleMs: 10000, kind: "hz" },
  "load/power": { staleMs: 10000, kind: "w" },
  "load/current": { staleMs: 10000, kind: "a" },
  "load/voltage": { staleMs: 10000, kind: "v1" },
  "load/energy_today": { staleMs: 90000, kind: "kwh" },
};

const STATUS_TEXT = {
  0: "Standby",
  1: "Self-Test",
  2: "Normal",
  3: "Alarm",
  4: "Fault",
};

const STATUS_EMOJI = {
  0: "⏸️",
  1: "🔄",
  2: "✅",
  3: "⚠️",
  4: "❌",
};

const samples = {};
const history = { pv: [], load: [], grid: [], batt: [] };
let client = null;
let mqttOk = false;
let prefix = "iriv/ivt";
let lastHistAt = 0;

function defaultUrl() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const host = location.hostname || "iriv-pi-control";
  return `${proto}//${host}:9001`;
}

function loadSettings() {
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    saved = {};
  }
  return {
    url: saved.url || defaultUrl(),
    user: saved.user || "",
    pass: saved.pass || "",
    prefix: saved.prefix || "iriv/ivt",
    view: ["simple", "full", "minimal"].includes(saved.view) ? saved.view : "simple",
  };
}

function saveSettings(cfg) {
  const prev = loadSettings();
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...prev, ...cfg }));
}

function applyView(view) {
  document.body.dataset.view = view;
  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
  saveSettings({ view });
}

function isFresh(key) {
  const spec = METRICS[key];
  const s = samples[key];
  if (!spec || !s || !s.valid) {
    return false;
  }
  return Date.now() - s.at <= spec.staleMs;
}

function valueOf(key) {
  return isFresh(key) ? samples[key].value : null;
}

function fmtNum(v, digits, unit) {
  return `${v.toFixed(digits)} ${unit}`;
}

function formatWatts(v) {
  if (v === null || v === undefined) {
    return PLACEHOLDER;
  }
  return `${v >= 0 ? "+" : ""}${v.toFixed(0)} W`;
}

function gridPowerW() {
  return valueOf("grid/power_ct");
}

function formatMetric(key, signed) {
  const spec = METRICS[key];
  if (key === "grid/power_ct") {
    const g = gridPowerW();
    return g === null ? PLACEHOLDER : formatWatts(g);
  }
  const v = valueOf(key);
  if (v === null) {
    return PLACEHOLDER;
  }
  if (key === "status") {
    return STATUS_TEXT[v | 0] || "Unknown";
  }
  if (spec.kind === "w") {
    return formatWatts(v);
  }
  const sign = signed && v >= 0 ? "+" : "";
  switch (spec.kind) {
    case "v2":
      return fmtNum(v, 2, "V");
    case "v1":
      return fmtNum(v, 1, "V");
    case "a":
      return `${sign}${v.toFixed(2)} A`;
    case "c":
      return fmtNum(v, 1, "C");
    case "hz":
      return fmtNum(v, 2, "Hz");
    case "kwh":
      return fmtNum(v, 1, "kWh");
    case "soc":
      return `${v.toFixed(0)}%`;
    default:
      return signed ? formatWatts(v) : fmtNum(v, 0, "W");
  }
}

function formatFlowPower(v) {
  if (v === null) {
    return PLACEHOLDER;
  }
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 1000) {
    return `${sign}${(abs / 1000).toFixed(2)} kW`;
  }
  return `${sign}${abs.toFixed(0)} W`;
}

function formatClock() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "short",
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const g = {};
  parts.forEach((p) => {
    if (p.type !== "literal") {
      g[p.type] = p.value;
    }
  });
  return `${g.weekday}, ${g.month} ${g.day}, ${g.year}  ${g.hour}:${g.minute}:${g.second}`;
}

function batteryState() {
  const v = valueOf("battery/power");
  const i = valueOf("battery/current");
  const n = v !== null ? v : i;
  if (n === null) {
    return "unknown";
  }
  const thr = v !== null ? 0.5 : 0.05;
  if (n < -thr) {
    return "charging";
  }
  if (n > thr) {
    return "discharging";
  }
  return "idle";
}

function signedColor(key) {
  if (key === "grid/power_ct") {
    const g = gridPowerW();
    if (g === null) {
      return "muted";
    }
    if (g > 0.5) {
      return "neg";
    }
    if (g < -0.5) {
      return "pos";
    }
    return "";
  }
  const v = valueOf(key);
  if (v === null) {
    return "muted";
  }
  if (key === "battery/power" || key === "battery/current") {
    if (v < -0.5 && key === "battery/power") {
      return "pos";
    }
    if (v < -0.05 && key === "battery/current") {
      return "pos";
    }
    if (v > 0.5 && key === "battery/power") {
      return "neg-batt";
    }
    if (v > 0.05 && key === "battery/current") {
      return "neg-batt";
    }
    return "";
  }
  if (v > 0.5) {
    return "pos";
  }
  if (v < -0.5) {
    return "neg";
  }
  return "";
}

function socColor(soc) {
  if (soc < 20) {
    return "#f85149";
  }
  if (soc < 40) {
    return "#e3b341";
  }
  return "#3fb950";
}

function statusInfo() {
  const v = valueOf("status");
  if (v === null) {
    return { text: PLACEHOLDER, cls: "muted", emoji: "❔" };
  }
  const n = v | 0;
  const text = STATUS_TEXT[n] || "Unknown";
  const cls = n === 2 ? "ok" : n === 3 ? "warn" : n === 4 ? "danger" : n === 1 ? "info" : "muted";
  return { text, cls, emoji: STATUS_EMOJI[n] || "❔" };
}

function gridMode() {
  const volts = valueOf("grid/voltage");
  const hz = valueOf("grid/frequency");
  if (volts === null && hz === null) {
    return { text: "--", cls: "muted", emoji: "❔" };
  }
  let on = false;
  if (volts !== null && volts >= GRID_ON_V_MIN) {
    on = true;
  } else if (hz !== null) {
    on = hz >= GRID_ON_HZ_MIN && hz <= GRID_ON_HZ_MAX;
  }
  return on
    ? { text: "On-Grid", cls: "ok", emoji: "⚡" }
    : { text: "Off-Grid", cls: "danger", emoji: "🔌" };
}

function acVoltage() {
  const inv = valueOf("inverter/voltage");
  if (inv !== null) {
    return { value: inv, key: "inverter/voltage" };
  }
  const loadV = valueOf("load/voltage");
  if (loadV !== null) {
    return { value: loadV, key: "load/voltage" };
  }
  const gridV = valueOf("grid/voltage");
  if (gridV !== null) {
    return { value: gridV, key: "grid/voltage" };
  }
  return { value: null, key: null };
}

function loadCurrent() {
  const direct = valueOf("load/current");
  if (direct !== null) {
    return { value: direct, derived: false };
  }
  return { value: null, derived: false };
}

function pvTotal() {
  const p1 = valueOf("pv1/power");
  const p2 = valueOf("pv2/power");
  if (p1 === null && p2 === null) {
    return null;
  }
  return (p1 || 0) + (p2 || 0);
}

function ageText(key) {
  const s = samples[key];
  if (!s || !s.valid) {
    return "no data";
  }
  const sec = Math.max(0, Math.round((Date.now() - s.at) / 1000));
  if (sec < 3) {
    return "live";
  }
  if (sec < 60) {
    return `${sec}s`;
  }
  return `${Math.floor(sec / 60)}m`;
}

function paintSegs(rootId) {
  const segs = document.querySelectorAll(`#${rootId} span`);
  const v = valueOf("battery/power");
  let lit = 0;
  let color = "var(--pos)";
  if (v !== null) {
    const mag = Math.abs(v);
    if (mag > 0.5) {
      lit = Math.ceil((mag / BATT_PWR_MAX_W) * BATT_PWR_SEGS);
      lit = Math.min(BATT_PWR_SEGS, Math.max(1, lit));
      color = v < 0 ? "var(--pos)" : "var(--danger)";
    }
  }
  segs.forEach((el, i) => {
    el.style.background = i < lit ? color : "var(--seg-off)";
  });
}

function paintSocRing(indId, labelId) {
  const v = valueOf("battery/soc");
  const ind = document.getElementById(indId);
  const label = document.getElementById(labelId);
  if (!ind || !label) {
    return;
  }
  const pct = v === null ? 0 : Math.max(0, Math.min(100, v));
  const col = v === null ? "#8b949e" : socColor(pct);
  ind.style.stroke = col;
  ind.style.strokeDasharray = `${SOC_ARC} ${SOC_CIRC}`;
  ind.style.strokeDashoffset = String(SOC_ARC * (1 - pct / 100));
  label.textContent = v === null ? PLACEHOLDER : `${pct.toFixed(0)}%`;
  label.style.color = col;
}

function setText(id, text, extraClass) {
  const el = document.getElementById(id);
  if (!el) {
    return;
  }
  el.textContent = text;
  if (el.dataset.baseClass !== undefined) {
    el.className = `${el.dataset.baseClass} ${extraClass || ""}`.trim();
  }
}

function pushHistory() {
  const now = Date.now();
  if (now - lastHistAt < HISTORY_MS) {
    return;
  }
  lastHistAt = now;
  const snapshot = {
    pv: pvTotal(),
    load: valueOf("load/power"),
    grid: gridPowerW(),
    batt: valueOf("battery/power"),
  };
  Object.keys(snapshot).forEach((key) => {
    const series = history[key];
    series.push(snapshot[key]);
    if (series.length > HISTORY_MAX) {
      series.shift();
    }
  });
}

function drawSpark(svgId, series, color) {
  const svg = document.getElementById(svgId);
  if (!svg) {
    return;
  }
  const nums = series.filter((v) => v !== null && Number.isFinite(v));
  if (nums.length < 2) {
    svg.innerHTML = "";
    return;
  }
  const min = Math.min(...nums, 0);
  const max = Math.max(...nums, 0);
  const span = max - min || 1;
  const w = 120;
  const h = 28;
  const pts = series.map((v, i) => {
    const x = series.length === 1 ? 0 : (i / (series.length - 1)) * w;
    const val = v === null ? min : v;
    const y = h - ((val - min) / span) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  svg.innerHTML = `<polyline points="${pts.join(" ")}" stroke="${color}"/>`;
}

function setWireHot(id, hot, kind) {
  const el = document.getElementById(id);
  if (!el) {
    return;
  }
  el.classList.remove("hot", "idle");
  el.classList.add(kind === "red" ? "wire-red" : "wire-cyan");
  el.classList.add(hot ? "hot" : "idle");
}

function setNodeHot(id, state) {
  const el = document.getElementById(id);
  if (!el) {
    return;
  }
  el.classList.remove("hot", "warn", "alarm");
  if (state) {
    el.classList.add(state);
  }
}

function paintMinimal() {
  const pv = valueOf("pv1/power");
  const load = valueOf("load/power");
  const grid = gridPowerW();
  const batt = valueOf("battery/power");
  const inv = valueOf("inverter/power");
  const soc = valueOf("battery/soc");
  const gm = gridMode();
  const st = statusInfo();
  const bState = batteryState();

  const fmtMw = (w) => {
    if (w === null) {
      return PLACEHOLDER;
    }
    return (w / 1000).toFixed(3);
  };

  setText("scada-pv", fmtMw(pv));
  setText("scada-load", fmtMw(load === null ? null : Math.abs(load)));
  setText("scada-grid", fmtMw(grid));
  setText("scada-soc", soc === null ? PLACEHOLDER : `${soc.toFixed(0)}`);
  setText("scada-mode", gm.text.replace("-", " ").toUpperCase());
  setText("scada-inv-st", st.text.toUpperCase());

  setText("scada-tag-pv", formatFlowPower(pv));
  setText("scada-tag-load", formatFlowPower(load));
  setText("scada-tag-grid", formatFlowPower(grid));
  setText("scada-tag-batt", formatFlowPower(batt));
  setText("scada-tag-soc", soc === null ? PLACEHOLDER : `${soc.toFixed(0)}%`);
  setText("scada-tag-inv", st.text.toUpperCase());
  let gridDir = "IDLE";
  if (grid !== null && grid > 0.5) {
    gridDir = "IMPORT";
  } else if (grid !== null && grid < -0.5) {
    gridDir = "EXPORT";
  } else if (grid === null) {
    gridDir = PLACEHOLDER;
  }
  setText("scada-tag-grid-dir", gridDir);

  setWireHot("scada-wire-pv", pv !== null && pv > 5, "cyan");
  setWireHot("scada-wire-batt", bState === "charging" || bState === "discharging", "cyan");
  setWireHot("scada-wire-load", load !== null && Math.abs(load) > 5, "red");
  setWireHot("scada-wire-grid", grid !== null && Math.abs(grid) > 5, "red");

  setNodeHot("scada-node-pv", pv !== null && pv > 5 ? "hot" : "");
  setNodeHot("scada-node-load", load !== null && Math.abs(load) > 5 ? "hot" : "");
  setNodeHot("scada-node-grid", grid !== null && Math.abs(grid) > 5 ? (grid > 0 ? "warn" : "hot") : "");
  setNodeHot(
    "scada-node-batt",
    bState === "charging" ? "hot" : bState === "discharging" ? "alarm" : ""
  );
  setNodeHot(
    "scada-node-inv",
    st.cls === "ok" || (inv !== null && Math.abs(inv) > 5) ? "hot" : st.cls === "danger" ? "alarm" : ""
  );
  setNodeHot("scada-node-bus", "hot");

  const acV = acVoltage();
  const acText = acV.value === null ? PLACEHOLDER : `${acV.value.toFixed(1)} V`;
  setText("scada-ac-v", acText, acV.value === null ? "dim" : "");
  setText("scada-inv-v", acText, acV.value === null ? "dim" : "");
  const loadI = loadCurrent();
  const loadIText = loadI.value === null
    ? PLACEHOLDER
    : `${loadI.value >= 0 ? "+" : ""}${loadI.value.toFixed(2)} A`;
  setText("scada-load-i", loadIText, loadI.value === null ? "dim" : "");
}

function paintFull() {
  const pv = pvTotal();
  const load = valueOf("load/power");
  const grid = gridPowerW();
  const batt = valueOf("battery/power");
  const p1 = valueOf("pv1/power");
  const p2 = valueOf("pv2/power");

  setText("full-kpi-pv", pv === null ? PLACEHOLDER : `${pv.toFixed(0)} W`, pv === null ? "muted" : "");
  setText("full-kpi-load", formatWatts(load), load === null ? "muted" : "");
  setText("full-kpi-grid", formatWatts(grid), signedColor("grid/power_ct"));
  setText("full-kpi-batt", formatWatts(batt), signedColor("battery/power"));

  let gridDir = "Idle";
  if (grid !== null && grid > 0.5) {
    gridDir = "Import (+)";
  } else if (grid !== null && grid < -0.5) {
    gridDir = "Export (−)";
  } else if (grid === null) {
    gridDir = PLACEHOLDER;
  }
  setText("full-kpi-grid-dir", gridDir);

  const bState = batteryState();
  let battDir = PLACEHOLDER;
  if (bState === "charging") {
    battDir = "Charging";
  } else if (bState === "discharging") {
    battDir = "Discharging";
  } else if (bState === "idle") {
    battDir = "Idle";
  }
  setText("full-kpi-batt-dir", battDir);

  setText("flow-pv", formatFlowPower(p1));
  const pvNote = document.getElementById("flow-pv-share");
  if (pvNote) {
    pvNote.hidden = true;
  }
  setText("flow-inv-head", "Inverter");
  const invHz = formatMetric("inverter/frequency");
  const invT = formatMetric("inverter/temperature");
  setText("flow-inv-meta", `${invHz} · ${invT}`);
  setText("flow-batt", formatFlowPower(batt));
  setText("flow-batt-meta", battDir);
  const soc = valueOf("battery/soc");
  setText("flow-batt-soc", soc === null ? PLACEHOLDER : `${soc.toFixed(0)}%`);
  const fill = document.getElementById("batt-fill");
  if (fill) {
    const pct = soc === null ? 0 : Math.max(0, Math.min(100, soc));
    fill.setAttribute("width", String(34 * (pct / 100)));
    fill.setAttribute("fill", socColor(pct));
  }
  setText("flow-load", formatFlowPower(load));
  setText("flow-load-meta", "Home");
  setText("flow-grid", formatFlowPower(grid));
  const gm = gridMode();
  setText("flow-grid-meta", gm.text);
  const ok = document.getElementById("grid-ok");
  if (ok) {
    ok.classList.toggle("hidden", gm.cls !== "ok");
  }

  let cover = PLACEHOLDER;
  if (pv !== null && load !== null && Math.abs(load) > 1) {
    cover = `${Math.max(0, (pv / Math.abs(load)) * 100).toFixed(0)}%`;
  }
  let selfUse = PLACEHOLDER;
  if (pv !== null && load !== null) {
    const used = Math.min(Math.max(pv, 0), Math.abs(load));
    selfUse = `${used.toFixed(0)} W`;
  }
  const st = statusInfo();
  setText("full-cover", cover);
  setText("full-self", selfUse);
  setText("full-grid-mode", `${gm.emoji} ${gm.text}`);
  setText("full-status", `${st.emoji} ${st.text}`);

  const pv1w = p1 || 0;
  const pv2w = p2 || 0;
  const sum = pv1w + pv2w;
  const share = sum > 1 ? (pv1w / sum) * 100 : 0;
  document.getElementById("pv1-share").style.width = `${share}%`;
  setText("full-pv1w", p1 === null ? PLACEHOLDER : `${pv1w.toFixed(0)} W`);
  setText("full-pv2w", p2 === null ? PLACEHOLDER : `${pv2w.toFixed(0)} W`);

  drawSpark("spark-pv", history.pv, "#e3b341");
  drawSpark("spark-load", history.load, "#58a6ff");
  drawSpark("spark-grid", history.grid, "#3fb950");
  drawSpark("spark-batt", history.batt, bState === "discharging" ? "#f85149" : "#3fb950");

  document.querySelectorAll("[data-age]").forEach((el) => {
    el.textContent = ageText(el.dataset.age);
  });

  const loadI = loadCurrent();
  const loadIText = loadI.value === null
    ? PLACEHOLDER
    : `${loadI.value >= 0 ? "+" : ""}${loadI.value.toFixed(2)} A`;
  setText("full-load-i", loadIText, loadI.value === null ? "muted" : "");
  setText("simple-load-i", loadIText, loadI.value === null ? "muted" : "");
  const loadIAge = document.getElementById("full-load-i-age");
  if (loadIAge) {
    loadIAge.textContent = loadI.value === null ? "—" : (loadI.derived ? "est." : ageText("load/current"));
  }

  const acV = acVoltage();
  const acText = acV.value === null ? PLACEHOLDER : `${acV.value.toFixed(1)} V`;
  setText("full-ac-v", acText, acV.value === null ? "muted" : "");
  setText("simple-ac-v", acText, acV.value === null ? "muted" : "");
  const acAge = document.getElementById("full-ac-v-age");
  if (acAge) {
    acAge.textContent = acV.key ? ageText(acV.key) : "—";
  }

  paintMinimal();
}

function paint() {
  const mqttEl = document.getElementById("sb-mqtt");
  mqttEl.textContent = mqttOk ? "📡 MQTT OK" : "📴 MQTT --";
  mqttEl.className = `sb-item ${mqttOk ? "ok" : "muted"}`;

  const st = statusInfo();
  const stEl = document.getElementById("sb-status");
  stEl.textContent = `${st.emoji} ${st.text}`;
  stEl.className = `sb-item ${st.cls}`;

  const gm = gridMode();
  const gEl = document.getElementById("sb-grid");
  gEl.textContent = `${gm.emoji} ${gm.text}`;
  gEl.className = `sb-item ${gm.cls}`;

  document.getElementById("sb-clock").textContent = formatClock();

  const pv = pvTotal();
  const pvEl = document.getElementById("home-pv");
  pvEl.textContent = pv === null ? PLACEHOLDER : `${pv.toFixed(0)} W`;
  pvEl.className = `hero pv${pv === null ? " muted" : ""}`;

  const battP = document.getElementById("home-batt-p");
  battP.textContent = formatMetric("battery/power", true);
  battP.className = `hero ${signedColor("battery/power") || ""}`;

  const gridP = document.getElementById("home-grid");
  gridP.textContent = formatMetric("grid/power_ct", true);
  gridP.className = `hero ${signedColor("grid/power_ct") || ""}`;

  const loadP = document.getElementById("home-load");
  loadP.textContent = formatMetric("load/power", true);
  loadP.className = `hero accent ${valueOf("load/power") === null ? "muted" : ""}`;

  document.querySelectorAll("[data-m]").forEach((el) => {
    const key = el.dataset.m;
    const signed = el.hasAttribute("data-signed");
    el.textContent = formatMetric(key, signed);
    const extra = signed ? signedColor(key) : valueOf(key) === null ? "muted" : "";
    el.className = `${el.dataset.baseClass} ${extra}`.trim();
  });

  paintSocRing("soc-ind", "home-soc");
  paintSocRing("soc-ind-full", "full-soc");
  const bar = document.getElementById("batt-soc-bar");
  const soc = valueOf("battery/soc");
  const pct = soc === null ? 0 : Math.max(0, Math.min(100, soc));
  bar.style.width = `${pct}%`;
  bar.style.background = soc === null ? "#8b949e" : socColor(pct);
  paintSegs("batt-segs");
  paintSegs("full-batt-segs");

  pushHistory();
  paintFull();
}

function ingest(topic, payload) {
  if (!topic.startsWith(`${prefix}/`)) {
    return;
  }
  const key = topic.slice(prefix.length + 1);
  if (!METRICS[key]) {
    return;
  }
  let value;
  try {
    const parsed = JSON.parse(payload);
    value = Number(parsed.value);
  } catch {
    return;
  }
  if (!Number.isFinite(value)) {
    return;
  }
  samples[key] = { value, at: Date.now(), valid: true };
}

function disconnect() {
  if (client) {
    client.end(true);
    client = null;
  }
  mqttOk = false;
  paint();
}

function connect() {
  if (typeof mqtt === "undefined") {
    alert("mqtt.js failed to load. Keep vendor/mqtt.min.js next to this page.");
    return;
  }
  const cfg = loadSettings();
  prefix = (cfg.prefix || "iriv/ivt").replace(/\/+$/, "");
  disconnect();
  const opts = {
    clientId: `deye-web-${Math.random().toString(16).slice(2, 10)}`,
    keepalive: 30,
    reconnectPeriod: 4000,
    clean: true,
  };
  if (cfg.user) {
    opts.username = cfg.user;
  }
  if (cfg.pass) {
    opts.password = cfg.pass;
  }
  client = mqtt.connect(cfg.url, opts);
  client.on("connect", () => {
    mqttOk = true;
    client.subscribe(`${prefix}/#`, { qos: 1 });
    paint();
  });
  client.on("reconnect", () => {
    mqttOk = false;
    paint();
  });
  client.on("close", () => {
    mqttOk = false;
    paint();
  });
  client.on("error", () => {
    mqttOk = false;
    paint();
  });
  client.on("message", (topic, payload) => {
    ingest(topic, payload.toString());
  });
}

function fillSettingsForm() {
  const cfg = loadSettings();
  document.getElementById("cfg-url").value = cfg.url;
  document.getElementById("cfg-user").value = cfg.user;
  document.getElementById("cfg-pass").value = cfg.pass;
  document.getElementById("cfg-prefix").value = cfg.prefix;
}

function fillSegs(id) {
  const root = document.getElementById(id);
  root.innerHTML = "";
  for (let i = 0; i < BATT_PWR_SEGS; i++) {
    root.appendChild(document.createElement("span"));
  }
}

function initUi() {
  fillSegs("batt-segs");
  fillSegs("full-batt-segs");
  document.querySelectorAll("[data-m], .hero, .soc-val, .kpi-val, .kpi-sub, #simple-load-i, #full-load-i, #simple-ac-v, #full-ac-v, .scada-v, #scada-ac-v, #scada-inv-v, #scada-load-i").forEach((el) => {
    el.dataset.baseClass = el.className;
  });

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });

  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", () => applyView(btn.dataset.view));
  });
  applyView(loadSettings().view);

  const dlg = document.getElementById("settings");
  document.getElementById("btn-settings").addEventListener("click", () => {
    fillSettingsForm();
    dlg.showModal();
  });
  document.getElementById("btn-close").addEventListener("click", () => dlg.close());
  document.getElementById("btn-disconnect").addEventListener("click", () => {
    disconnect();
    dlg.close();
  });
  document.getElementById("settings-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const cfg = {
      url: document.getElementById("cfg-url").value.trim(),
      user: document.getElementById("cfg-user").value.trim(),
      pass: document.getElementById("cfg-pass").value,
      prefix: document.getElementById("cfg-prefix").value.trim() || "iriv/ivt",
    };
    saveSettings(cfg);
    dlg.close();
    connect();
  });
}

initUi();
fillSettingsForm();
connect();
setInterval(paint, 250);
paint();
