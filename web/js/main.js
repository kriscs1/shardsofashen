// Dragon Sword in the browser: logging in, the server's messages, the screen (full screen, any size: the game is laid
// out 768 high and scaled to fit, drawn at the screen's own resolution so text stays sharp) and the frame loop.
import { A, loadManifest, configRead, onLoaded } from "./assets.js";
import { G, S, setGeometry, resetWorld, addMap, applySnap, glide, addMessage, myPlayer } from "./state.js";
import { N, connect, send } from "./net.js";
import { V, drawWorld, addFx, setZoom, changeZoom } from "./render.js";
import { invalidateMap, invalidateCell } from "./ground.js";
import { L, U, layout, drawUI, preloadInterface, showBanner, levelOfXp } from "./ui.js";
import { I, mouseMove, mouseDown, mouseDrag, wheel, keyDown, keyUp, releaseKeys, updateCursor, closeJournal } from "./input.js";
import { J, drawJournal } from "./journal.js";
import { O, loadOptions, saveOptions, playSound, musicTick, ambientTick, unlock, stopMusic } from "./audio.js";
import { setWeather, fogInit, revealCell } from "./sky.js";
import { messageColour, clamp, val, pretty } from "./util.js";

const $ = (id) => document.getElementById(id);
const canvas = $("game");
const ctx = canvas.getContext("2d", { alpha: false });
const screen = { k: 1, ox: 0, oy: 0, dpr: 1, W: 1024 };
let smoothing = true;
let running = false;
let lastFrame = performance.now();
let lastSlow = 0;
let lastExplored = 0;
let loginMode = "login";

S.addLocal = (text, col) => addMessage(text, col);

// ================================================================================================================
// The screen
// ================================================================================================================
function resize() {
  const dpr = window.devicePixelRatio || 1;
  const cw = Math.max(1, Math.round(window.innerWidth * dpr));
  const ch = Math.max(1, Math.round(window.innerHeight * dpr));
  canvas.width = cw;
  canvas.height = ch;
  const W = clamp(Math.round(768 * cw / ch / 2) * 2, 1024, 1792);
  const k = Math.min(cw / W, ch / 768);
  screen.k = k; screen.dpr = dpr; screen.W = W;
  screen.ox = Math.round((cw - W * k) / 2);
  screen.oy = Math.round((ch - 768 * k) / 2);
  if (A.m) layout(W);
  placeChat();
}

function toLogical(ev) {
  return [(ev.clientX * screen.dpr - screen.ox) / screen.k, (ev.clientY * screen.dpr - screen.oy) / screen.k];
}

function toggleFullscreen() {
  const d = document;
  if (d.fullscreenElement || d.webkitFullscreenElement) (d.exitFullscreen || d.webkitExitFullscreen).call(d);
  else {
    const el = d.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) req.call(el, { navigationUI: "hide" }).catch?.(() => {});
  }
}

let wakeLock = null;
async function keepAwake() {
  try { if ("wakeLock" in navigator && !wakeLock) wakeLock = await navigator.wakeLock.request("screen"); } catch (e) { /* not allowed */ }
}
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && running) { wakeLock = null; keepAwake(); } });

// ================================================================================================================
// Overlays: the chat line, options, quitting, the admin panel, messages
// ================================================================================================================
function placeChat() {
  const box = $("chat-entry");
  const k = screen.k / screen.dpr;
  box.style.left = (screen.ox / screen.dpr + 8 * k) + "px";
  box.style.width = ((L.VW || 800) - 16) * k + "px";
  box.style.top = (screen.oy / screen.dpr + (672 + 70) * k) + "px";
  box.style.bottom = "auto";
}

function openChat() {
  const box = $("chat-entry");
  box.hidden = false;
  placeChat();
  releaseKeys();
  $("chat-input").focus();
}

$("chat-input").addEventListener("keydown", (ev) => {
  ev.stopPropagation();
  if (ev.key === "Enter") {
    const text = ev.target.value.trim();
    if (text) send({ t: "chat", text });
    ev.target.value = "";
    $("chat-entry").hidden = true;
    canvas.focus();
  } else if (ev.key === "Escape") {
    ev.target.value = "";
    $("chat-entry").hidden = true;
    canvas.focus();
  }
});

function overlayOpen() {
  return ["options", "quit", "admin", "message", "login", "loading"].some((id) => !$(id).hidden) || !$("chat-entry").hidden;
}

function openQuit() { releaseKeys(); $("quit").hidden = false; $("quit-no").focus(); }
$("quit-no").onclick = () => { $("quit").hidden = true; canvas.focus(); };
$("quit-options").onclick = () => { $("quit").hidden = true; openOptions(); };
$("quit-yes").onclick = () => {
  send({ t: "quit" });
  running = false;
  if (N.ws) N.ws.close();
  stopMusic();
  $("quit").hidden = true;
  showMessage("Dragon Sword", "Your game is saved. See you soon!", () => location.reload());
};

function openOptions() {
  releaseKeys();
  $("opt-sound").checked = O.sound; $("opt-volume").value = O.volume;
  $("opt-music").checked = O.music; $("opt-music-volume").value = O.musicVolume;
  $("opt-ambient").checked = O.ambient; $("opt-ambient-volume").value = O.ambientVolume;
  $("opt-markers").checked = U.markers; $("opt-smooth").checked = smoothing;
  $("opt-camera").value = V.smooth;
  $("options").hidden = false;
}
for (const [id, key, num] of [["opt-sound", "sound"], ["opt-volume", "volume", 1], ["opt-music", "music"],
  ["opt-music-volume", "musicVolume", 1], ["opt-ambient", "ambient"], ["opt-ambient-volume", "ambientVolume", 1]]) {
  $(id).addEventListener("input", (ev) => { O[key] = num ? +ev.target.value : ev.target.checked; saveOptions(); });
}
$("opt-markers").addEventListener("input", (ev) => { U.markers = ev.target.checked; saveView(); });
$("opt-smooth").addEventListener("input", (ev) => { smoothing = ev.target.checked; saveView(); });
$("opt-camera").addEventListener("input", (ev) => { V.smooth = +ev.target.value; saveView(); });
$("opt-fullscreen").onclick = toggleFullscreen;
$("options-done").onclick = () => { $("options").hidden = true; canvas.focus(); playSound("Coins"); };

function saveView() {
  try { localStorage.setItem("ds.view", JSON.stringify({ markers: U.markers, smooth: smoothing, camera: V.smooth })); } catch (e) { /* */ }
}

function loadView() {
  try {
    const v = JSON.parse(localStorage.getItem("ds.view") || "{}");
    if ("markers" in v) U.markers = v.markers;
    if ("smooth" in v) smoothing = v.smooth;
    if ("camera" in v) V.smooth = v.camera;
    else V.smooth = val(configRead("Interface", "Camera.Smooth", "8"));
    if (!("smooth" in v)) smoothing = val(configRead("Interface", "Smooth.Scaling", "1")) === 1;
    const z = parseFloat(localStorage.getItem("ds.zoom") || configRead("Interface", "Zoom", "1"));
    setZoom(V.zooms.reduce((a, b) => (Math.abs(b - z) < Math.abs(a - z) ? b : a), 1));
  } catch (e) { setZoom(1); }
}

// ----- the admin panel
let adminItems = [];
function openAdmin() {
  releaseKeys();
  $("admin").hidden = false;
  send({ t: "admin", do: "items" });
  const box = $("admin-skills");
  box.innerHTML = "";
  A.m.skills.forEach((name, i) => {
    const row = document.createElement("label");
    const tick = document.createElement("input");
    tick.type = "checkbox";
    tick.checked = !(S.me.skill_off || [])[i];
    tick.disabled = name.toUpperCase() === "HITPOINTS";
    tick.dataset.i = i;
    const lv = document.createElement("input");
    lv.type = "text";
    lv.value = levelOfXp(S.me.xp[i]);
    lv.dataset.i = i;
    row.append(tick, " " + name + " ", lv);
    box.append(row);
  });
  $("admin-god").checked = !!S.me.god;
}

function fillAdminItems() {
  const f = $("admin-filter").value.toLowerCase();
  const sel = $("admin-items");
  sel.innerHTML = "";
  for (const it of adminItems) {
    if (f && !it.toLowerCase().includes(f) && !it.toLowerCase().replace(/_/g, " ").includes(f)) continue;
    const o = document.createElement("option");
    o.value = it;
    o.textContent = pretty(it);
    sel.append(o);
  }
}
$("admin-filter").addEventListener("input", fillAdminItems);
$("admin-give").onclick = () => {
  const sel = $("admin-items");
  let item = sel.value;
  if (!item && sel.options.length === 1) item = sel.options[0].value;
  send({ t: "admin", do: "give", item, qty: $("admin-qty").value });
};
$("admin-save").onclick = () => {
  const on = [], levels = [];
  for (const el of $("admin-skills").querySelectorAll("input")) {
    if (el.type === "checkbox") on[+el.dataset.i] = el.checked;
    else levels[+el.dataset.i] = el.value;
  }
  send({ t: "admin", do: "skills", on, levels });
};
$("admin-god").addEventListener("input", (ev) => send({ t: "admin", do: "god", on: ev.target.checked }));
$("admin-close").onclick = () => { $("admin").hidden = true; canvas.focus(); };
for (const id of ["admin", "options", "quit", "message"]) {
  $(id).addEventListener("keydown", (ev) => {
    ev.stopPropagation();
    if (ev.key === "Escape") { $(id).hidden = true; canvas.focus(); }
  });
}

function showMessage(title, text, then) {
  $("message-title").textContent = title;
  $("message-text").textContent = text;
  $("message").hidden = false;
  $("message-ok").onclick = () => { $("message").hidden = true; if (then) then(); else canvas.focus(); };
}

window.dsUI = { openQuit, openOptions, openAdmin, openChat, toggleFullscreen };
window.dsDebug = { S, V };     // (for tools/browser_check.py)

// ================================================================================================================
// Logging in
// ================================================================================================================
function setLoginError(text) { $("login-error").textContent = text || ""; }

$("login-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  unlock();
  login("login");
});
$("register-button").onclick = () => { unlock(); login("register"); };

function login(mode) {
  loginMode = mode;
  setLoginError("");
  if (!N.open) { setLoginError("Not connected to the server yet..."); return; }
  send({ t: mode, name: $("login-name").value, password: $("login-password").value, invite: $("login-invite").value });
  $("login-button").disabled = $("register-button").disabled = true;
}

N.onOpen = () => { $("login-online").textContent = "Connected."; };
N.onClose = () => {
  $("login-button").disabled = $("register-button").disabled = false;
  if (running) {
    running = false;
    releaseKeys();
    stopMusic();
    showMessage("Disconnected", "The connection to the server was lost. Your game is saved: log in again to carry on.",
      () => location.reload());
  } else {
    $("login-online").textContent = "Can't reach the server. Trying again...";
    setTimeout(connect, 3000);
  }
};

// ================================================================================================================
// The server's messages
// ================================================================================================================
N.onMessage = (m) => {
  const now = performance.now();
  switch (m.t) {
    case "hello":
      $("login-online").textContent = `${m.online} of ${m.max} adventurers online.`;
      $("invite-row").hidden = !m.invite;
      $("register-button").hidden = m.registration !== "open";
      break;
    case "login_fail":
      setLoginError(m.reason);
      $("login-button").disabled = $("register-button").disabled = false;
      break;
    case "welcome": startGame(m); break;
    case "kicked":
      running = false;
      releaseKeys();
      stopMusic();
      showMessage("Dragon Sword", m.reason, () => location.reload());
      break;
    case "mapdata": addMap(m); invalidateMap(m.name); break;
    case "cells": {
      const old = new Map(S.cells);
      S.cells.clear();
      for (const [map, x, y, tile, decor] of m.cells) S.cells.set(map + "," + x + "," + y, [tile, decor]);
      for (const key of new Set([...old.keys(), ...S.cells.keys()])) {
        const a = old.get(key), b = S.cells.get(key);
        if (!a || !b || a[0] !== b[0] || a[1] !== b[1]) {
          const parts = key.split(",");
          invalidateCell(parts.slice(0, 3).join(","), +parts[3], +parts[4]);
        }
      }
      S.locks.clear();
      for (const [map, x, y, msg] of m.locks || []) S.locks.set(map + "," + x + "," + y, msg);
      break;
    }
    case "me":
      S.me = m;
      S.view = m.view;
      if (S.itemInUse && !m.inv.some((i) => i[0] === S.itemInUse)) S.itemInUse = 0;
      break;
    case "quests": S.quests = m.quests; S.marks = m.marks; S.level = m.level; break;
    case "weather": setWeather(m); break;
    case "snap": applySnap(m, now); break;
    case "box":
      S.box = m;
      if (m.mode) { U.rcm = null; releaseKeys(); }
      break;
    case "msg": addMessage(m.text, messageColour(m.kind)); break;
    case "chat":
      addMessage(m.from ? `${m.from}: ${m.text}` : m.text, m.from ? "30 60 140" : "darkgray");
      if (m.from && m.from !== S.name) playSound("Pickup");
      break;
    case "players": S.players = m.list; S.max = m.max; break;
    case "sound": playSound(m.name, "x" in m ? [m.x, m.y] : null); break;
    case "splat": case "anim": case "shot": case "nudge": case "skillpop": case "burst": addFx(m, now); break;
    case "hurt": S.hurtUntil = now + 240; break;
    case "levelup": showBanner(m.skill, m.level, now); break;
    case "clock": S.clock = { day: m.day, secs: m.secs, on: m.on, at: now }; break;
    case "map":
      if (m.z !== S.mapZ) V.cam.snap = true;
      S.mapName = m.name;
      S.mapZ = m.z;
      break;
    case "teleport": V.cam.snap = true; break;
    case "use": S.itemInUse = m.uid; break;
    case "reveal": revealCell(m.map, m.cell); break;
    case "lightning":
      if (!V.underRoof) {
        S.flashAt = now;
        setTimeout(() => playSound(m.sound), m.thunder);
      }
      break;
    case "sleep": S.sleep = { start: now, fade: m.fade, hold: m.hold, text: m.text }; break;
    case "journal": S.journal = m; break;
    case "admin_items": adminItems = m.items; fillAdminItems(); break;
    case "admin_status": $("admin-status").textContent = m.text; break;
    default: break;
  }
};

async function startGame(m) {
  S.name = m.name;
  S.uid = m.uid;
  S.admin = m.admin;
  S.explored.clear();
  for (const [k, v] of Object.entries(m.explored || {})) S.explored.set(k, v === "all" ? "all" : new Set(v));
  S.clock = { day: m.time.day, secs: m.time.secs, on: m.time.on, at: performance.now() };
  $("login").hidden = true;
  $("loading").hidden = false;
  $("loading-text").textContent = `Loading ${m.name}...`;
  $("loading-bar").style.width = "30%";
  await preloadInterface();
  $("loading-bar").style.width = "100%";
  $("loading").hidden = true;
  running = true;
  canvas.focus();
  keepAwake();
}

// ================================================================================================================
// The frame
// ================================================================================================================
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.1, Math.max(0, (now - lastFrame) / 1000));
  lastFrame = now;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = "#180e0a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!running || !A.m || !S.me) return;
  ctx.setTransform(screen.k, 0, 0, screen.k, screen.ox, screen.oy);
  ctx.imageSmoothingEnabled = smoothing;
  ctx.imageSmoothingQuality = "high";
  glide(now);
  if (J.open) {
    ctx.save();
    ctx.translate(Math.floor((L.W - 1024) / 2), 0);
    drawJournal(ctx);
    ctx.restore();
  } else {
    drawWorld(ctx, L.VW, L.VH, now, dt, smoothing);
    ctx.imageSmoothingEnabled = smoothing;
    drawUI(ctx, now);
  }
  if (I.mx >= 0 && !overlayOpen()) mouseMove(I.mx, I.my);
  updateCursor(canvas, now);
  if (now - lastSlow > 250) {
    lastSlow = now;
    musicTick(V.underRoof, null);
    ambientTick(V.underRoof);
  } else musicTick(V.underRoof, null);
  if (now - lastExplored > 3000) {
    lastExplored = now;
    for (const [map, cells] of S.exploredNew) if (cells.length) send({ t: "explored", map, cells });
    S.exploredNew.clear();
  }
}

// ----- input
canvas.addEventListener("mousemove", (ev) => {
  const [x, y] = toLogical(ev);
  I.mx = x; I.my = y;
  mouseDrag(y, ev.buttons & 1);
});
canvas.addEventListener("mousedown", (ev) => {
  if (!running || overlayOpen()) return;
  canvas.focus();
  const [x, y] = toLogical(ev);
  mouseDown(ev.button, x, y);
});
canvas.addEventListener("contextmenu", (ev) => ev.preventDefault());
canvas.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  if (!running || overlayOpen()) return;
  const [x, y] = toLogical(ev);
  wheel(ev.deltaY, x, y);
}, { passive: false });
window.addEventListener("keydown", (ev) => {
  if (!running || overlayOpen()) return;
  keyDown(ev);
});
window.addEventListener("keyup", (ev) => { if (running) keyUp(ev); });
window.addEventListener("blur", () => { if (running) releaseKeys(); });
window.addEventListener("resize", resize);
document.addEventListener("fullscreenchange", resize);

// ================================================================================================================
// Starting
// ================================================================================================================
async function boot() {
  resize();
  requestAnimationFrame(frame);
  try {
    await loadManifest();
  } catch (e) {
    $("login-online").textContent = e.message;
    return;
  }
  setGeometry();
  layout(screen.W);
  resize();
  fogInit();
  loadOptions();
  loadView();
  onLoaded(() => {});
  connect();
}

boot();
