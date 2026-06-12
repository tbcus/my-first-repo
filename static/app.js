/* Flights Overhead -- radar display. Vanilla JS, no dependencies. */
"use strict";

// ---------- constants ----------
const POLL_MS = 1000;
const SWEEP_PERIOD_MS = 6000;        // cosmetic sweep, one revolution
const MAX_EXTRAP_S = 10;             // cap dead-reckoning at 10 s
const EARTH_R_KM = 6371;
const KT_TO_KMH = 1.852;
const GREEN = "#33ff66";
const CYAN = "#33ffee";

// ---------- state ----------
let station = { lat: 0, lon: 0, radius_km: 60 };
let aircraft = [];                   // last received list, distance-ascending
let source = "----";
let lastDataMs = 0;                  // performance.now() of last good poll
let lastServerNow = 0;
let haveData = false;
let fetchFailed = false;

// ---------- DOM ----------
const canvas = document.getElementById("radar");
const ctx = canvas.getContext("2d");
const el = (id) => document.getElementById(id);
const stStation = el("st-station"), stSource = el("st-source"),
      stCount = el("st-count"), stNoData = el("st-nodata"), stClock = el("st-clock");
const featured = el("featured"), noTraffic = el("no-traffic"),
      othersWrap = el("others-wrap"), othersBody = el("others-body");

// ---------- canvas sizing (devicePixelRatio aware) ----------
let cw = 0, ch = 0;                  // CSS-pixel size of canvas
function resize() {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  cw = rect.width;
  ch = rect.height;
  canvas.width = Math.round(cw * dpr);
  canvas.height = Math.round(ch * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener("resize", resize);
resize();

// ---------- geo helpers ----------
const rad = (d) => d * Math.PI / 180;

// great-circle distance (km), haversine
function distanceKm(lat1, lon1, lat2, lon2) {
  const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_R_KM * Math.asin(Math.sqrt(a));
}

// initial bearing from point 1 to point 2, degrees 0-360
function bearingDeg(lat1, lon1, lat2, lon2) {
  const y = Math.sin(rad(lon2 - lon1)) * Math.cos(rad(lat2));
  const x = Math.cos(rad(lat1)) * Math.sin(rad(lat2)) -
            Math.sin(rad(lat1)) * Math.cos(rad(lat2)) * Math.cos(rad(lon2 - lon1));
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

// azimuthal equidistant, north-up: lat/lon -> canvas x/y
function project(lat, lon, cx, cy, pxPerKm) {
  const d = distanceKm(station.lat, station.lon, lat, lon);
  const b = rad(bearingDeg(station.lat, station.lon, lat, lon));
  return [cx + Math.sin(b) * d * pxPerKm, cy - Math.cos(b) * d * pxPerKm];
}

// dead-reckoned position: advance along track at ground speed since last poll
function reckon(ac, nowMs) {
  if (!ac.lat && !ac.lon) return null;
  let dt = haveData ? (nowMs - lastDataMs) / 1000 : 0;
  dt = Math.min(dt, MAX_EXTRAP_S);          // freeze after 10 s without data
  if (dt <= 0 || !ac.gs_kt) return [ac.lat, ac.lon];
  const dKm = ac.gs_kt * KT_TO_KMH * dt / 3600;
  const br = rad(ac.track_deg);
  const dLat = (dKm / EARTH_R_KM) * Math.cos(br) * 180 / Math.PI;
  const dLon = (dKm / EARTH_R_KM) * Math.sin(br) * 180 / Math.PI /
               Math.max(Math.cos(rad(ac.lat)), 0.01);
  return [ac.lat + dLat, ac.lon + dLon];
}

function cardinal(deg) {
  const dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                "S","SSW","SW","WSW","W","WNW","NW","NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

// ring interval from {10,20,25,50} yielding 3-5 rings inside radius
function ringStep(radiusKm) {
  for (const s of [10, 20, 25, 50]) {
    const n = Math.floor(radiusKm / s);
    if (n >= 3 && n <= 5) return s;
  }
  return Math.max(10, Math.round(radiusKm / 4 / 5) * 5); // fallback
}

// ---------- polling ----------
async function poll() {
  try {
    const res = await fetch("/api/aircraft", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    station = data.station || station;
    source = data.source || "----";
    lastServerNow = data.now || 0;
    aircraft = (data.aircraft || []).filter((a) => a.lat || a.lon);
    lastDataMs = performance.now();
    haveData = true;
    fetchFailed = false;
    updateSidebar();
  } catch (e) {
    fetchFailed = true;
  }
  updateStatus();
}
setInterval(poll, POLL_MS);
poll();

// ---------- status bar ----------
function updateStatus() {
  stStation.textContent = "STN " + station.lat.toFixed(4) + " " + station.lon.toFixed(4);
  stSource.textContent = "SRC " + source;
  stCount.textContent = aircraft.length + " AIRCRAFT";
  stNoData.classList.toggle("hidden", !fetchFailed);
}

function updateClock() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  stClock.textContent =
    p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + ":" + p(d.getUTCSeconds()) + " UTC";
}
setInterval(updateClock, 250);
updateClock();

// ---------- sidebar ----------
function fmt(v, suffix, fallback = "--") {
  return v ? Math.round(v).toLocaleString("en-US") + suffix : fallback;
}

function updateSidebar() {
  const top = aircraft[0];
  noTraffic.classList.toggle("hidden", !!top);
  featured.classList.toggle("hidden", !top);
  if (top) {
    el("f-callsign").textContent = top.callsign || top.hex.toUpperCase();
    el("f-type").textContent = top.type || "----";
    el("f-alt").textContent = fmt(top.alt_ft, " ft");
    el("f-speed").textContent = top.gs_kt
      ? Math.round(top.gs_kt) + " kt / " + Math.round(top.gs_kt * KT_TO_KMH) + " km/h"
      : "--";
    el("f-heading").textContent = top.track_deg || top.track_deg === 0
      ? Math.round(top.track_deg) + "° " + cardinal(top.track_deg) : "--";
    el("f-vrate").textContent = top.vr_fpm
      ? (top.vr_fpm > 0 ? "+" : "") + Math.round(top.vr_fpm) + " fpm" : "LEVEL";
    el("f-distance").textContent = top.distance_km
      ? top.distance_km.toFixed(1) + " km" : "--";
    el("f-squawk").textContent = top.squawk || "----";
    el("f-hex").textContent = top.hex.toUpperCase();
  }

  const next = aircraft.slice(1, 9);
  othersWrap.classList.toggle("hidden", next.length === 0);
  othersBody.innerHTML = "";
  for (const a of next) {
    const tr = document.createElement("tr");
    for (const text of [
      a.callsign || a.hex.toUpperCase(),
      fmt(a.alt_ft, " ft"),
      a.distance_km ? a.distance_km.toFixed(1) + " km" : "--",
    ]) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.appendChild(td);
    }
    othersBody.appendChild(tr);
  }
}

// ---------- drawing ----------
function drawRings(cx, cy, R, pxPerKm) {
  const step = ringStep(station.radius_km);
  ctx.strokeStyle = "rgba(51,255,102,0.28)";
  ctx.fillStyle = "rgba(51,255,102,0.55)";
  ctx.lineWidth = 1;
  ctx.font = "12px 'JetBrains Mono', Menlo, monospace";
  ctx.textAlign = "left";
  ctx.textBaseline = "bottom";
  for (let km = step; km <= station.radius_km + 0.01; km += step) {
    const r = km * pxPerKm;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillText(km + " km", cx + r * Math.SQRT1_2 + 4, cy - r * Math.SQRT1_2 - 2);
  }

  // crosshair
  ctx.strokeStyle = "rgba(51,255,102,0.15)";
  ctx.beginPath();
  ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy);
  ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R);
  ctx.stroke();

  // cardinal labels
  ctx.fillStyle = "rgba(51,255,102,0.45)";
  ctx.font = "16px 'JetBrains Mono', Menlo, monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("N", cx, cy - R - 12);
  ctx.fillText("S", cx, cy + R + 12);
  ctx.fillText("E", cx + R + 14, cy);
  ctx.fillText("W", cx - R - 14, cy);
}

function drawSweep(cx, cy, R, nowMs) {
  const ang = (nowMs % SWEEP_PERIOD_MS) / SWEEP_PERIOD_MS * Math.PI * 2 - Math.PI / 2;
  const WEDGE = Math.PI / 3; // 60-degree fading trail behind the line
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.clip();
  for (let i = 0; i < 18; i++) {
    const a0 = ang - WEDGE * (i + 1) / 18;
    const a1 = ang - WEDGE * i / 18;
    ctx.fillStyle = "rgba(51,255,102," + (0.10 * (1 - i / 18)) + ")";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, R, a0, a1);
    ctx.fill();
  }
  ctx.strokeStyle = "rgba(51,255,102,0.7)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(ang) * R, cy + Math.sin(ang) * R);
  ctx.stroke();
  ctx.restore();
}

function drawAircraft(ac, isClosest, cx, cy, pxPerKm, nowMs) {
  const pos = reckon(ac, nowMs);
  if (!pos) return;
  const [x, y] = project(pos[0], pos[1], cx, cy, pxPerKm);
  const color = isClosest ? CYAN : GREEN;

  // trail: fading polyline, oldest first / most transparent
  const trail = ac.trail || [];
  if (trail.length > 1) {
    for (let i = 1; i < trail.length; i++) {
      const [x0, y0] = project(trail[i - 1][0], trail[i - 1][1], cx, cy, pxPerKm);
      const [x1, y1] = project(trail[i][0], trail[i][1], cx, cy, pxPerKm);
      ctx.strokeStyle = isClosest
        ? "rgba(51,255,238," + (0.45 * i / trail.length) + ")"
        : "rgba(51,255,102," + (0.40 * i / trail.length) + ")";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
    }
  }

  // dart rotated to track
  const size = isClosest ? 11 : 8;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rad(ac.track_deg || 0));
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.moveTo(0, -size);                 // nose
  ctx.lineTo(size * 0.65, size);        // right tail
  ctx.lineTo(0, size * 0.45);           // notch
  ctx.lineTo(-size * 0.65, size);       // left tail
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // pulsing ring around the closest aircraft
  if (isClosest) {
    const pulse = (nowMs % 1500) / 1500;
    ctx.strokeStyle = "rgba(51,255,238," + (0.8 * (1 - pulse)) + ")";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, 16 + pulse * 18, 0, Math.PI * 2);
    ctx.stroke();
  }

  // label block
  const name = ac.callsign || ac.hex.toUpperCase();
  let arrow = "";
  if (ac.vr_fpm > 300) arrow = " ↑";
  else if (ac.vr_fpm < -300) arrow = " ↓";
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 6;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.font = (isClosest ? "bold 17px" : "15px") + " 'JetBrains Mono', Menlo, monospace";
  ctx.fillText(name + arrow, x + size + 8, y - 7);
  ctx.font = (isClosest ? "13px" : "12px") + " 'JetBrains Mono', Menlo, monospace";
  ctx.globalAlpha = 0.8;
  ctx.fillText(
    (ac.alt_ft ? Math.round(ac.alt_ft) : "--") + " ft  " +
    (ac.gs_kt ? Math.round(ac.gs_kt) : "--") + " kt",
    x + size + 8, y + 9);
  ctx.globalAlpha = 1;
  ctx.shadowBlur = 0;
}

function frame(nowMs) {
  ctx.clearRect(0, 0, cw, ch);
  const cx = cw / 2, cy = ch / 2;
  const margin = 36;
  const R = Math.min(cw, ch) / 2 - margin;
  if (R > 20) {
    const pxPerKm = R / station.radius_km;
    drawRings(cx, cy, R, pxPerKm);
    drawSweep(cx, cy, R, nowMs);
    // farthest first so the closest is drawn on top
    for (let i = aircraft.length - 1; i >= 0; i--) {
      drawAircraft(aircraft[i], i === 0, cx, cy, pxPerKm, nowMs);
    }
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// ---------- fullscreen toggle ----------
document.addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else document.documentElement.requestFullscreen().catch(() => {});
});

// ---------- idle cursor hiding ----------
let idleTimer = null;
function wake() {
  document.body.classList.remove("idle");
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => document.body.classList.add("idle"), 3000);
}
document.addEventListener("mousemove", wake);
wake();
