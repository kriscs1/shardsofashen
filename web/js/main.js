// Dragon Sword in the browser: logging in, the server's messages, the screen (full screen, any size: the game is laid
// out 768 high and scaled to fit, drawn at the screen's own resolution so text stays sharp) and the frame loop.
import { A, loadManifest, configRead, onLoaded } from "./assets.js";
import { G, S, setGeometry, resetWorld, addMap, applySnap, glide, addMessage, myPlayer } from "./state.js";
import { N, connect, send } from "./net.js";
import { V, drawWorld, addFx, setZoom, changeZoom } from "./render.js";
import { invalidateMap, invalidateCell } from "./ground.js";
import { L, U, layout, drawUI, drawBoosts, preloadInterface, showBanner, levelOfXp } from "./ui.js";
import { I, mouseMove, mouseDown, mouseDrag, wheel, keyDown, keyUp, releaseKeys, updateCursor, closeJournal } from "./input.js";
import { J, drawJournal } from "./journal.js";
import { O, loadOptions, saveOptions, playSound, musicTick, ambientTick, unlock, stopMusic } from "./audio.js";
import { setWeather, fogInit, revealCell } from "./sky.js";
import { messageColour, clamp, val, pretty } from "./util.js";
import { buildPicker, DEFAULT_LOOK } from "./look.js";
import { preload, entityIni } from "./assets.js";
import { B, onBuildables, updateBuild, toggleBuild, setBuild, initBuildUI, buildMouseDown, buildMouseMove, drawBuild } from "./build.js";

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

function openChat(start) {
  if (typeof start === "string") $("chat-input").value = start;
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
  return ["options", "quit", "admin", "message", "login", "loading", "appearance", "price", "password", "death"].some((id) => !$(id).hidden) || !$("chat-entry").hidden;
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
  $("opt-sound").checked = O.sound; $("opt-volume").value = O.volume; $("opt-chat-sound").checked = O.chatSound;
  $("opt-music").checked = O.music; $("opt-music-volume").value = O.musicVolume;
  $("opt-ambient").checked = O.ambient; $("opt-ambient-volume").value = O.ambientVolume;
  $("opt-markers").checked = U.markers; $("opt-smooth").checked = smoothing;
  $("opt-camera").value = V.smooth;
  $("opt-cursor").value = String(U.cursorSize || 22);
  $("options").hidden = false;
}
for (const [id, key, num] of [["opt-sound", "sound"], ["opt-volume", "volume", 1], ["opt-music", "music"], ["opt-chat-sound", "chatSound"],
  ["opt-music-volume", "musicVolume", 1], ["opt-ambient", "ambient"], ["opt-ambient-volume", "ambientVolume", 1]]) {
  $(id).addEventListener("input", (ev) => { O[key] = num ? +ev.target.value : ev.target.checked; saveOptions(); });
}
$("opt-markers").addEventListener("input", (ev) => { U.markers = ev.target.checked; saveView(); });
$("opt-smooth").addEventListener("input", (ev) => { smoothing = ev.target.checked; saveView(); });
$("opt-camera").addEventListener("input", (ev) => { V.smooth = +ev.target.value; saveView(); });
$("opt-cursor").addEventListener("input", (ev) => { U.cursorSize = +ev.target.value; saveView(); });
$("opt-fullscreen").onclick = toggleFullscreen;
let appearancePick = null;
$("opt-look").onclick = () => {
  $("options").hidden = true;
  $("appearance").hidden = false;
  appearancePick = buildPicker($("appearance-picker"), S.me && S.me.look);
};
$("appearance-save").onclick = () => {
  if (appearancePick) send({ t: "look", look: appearancePick() });
  $("appearance").hidden = true;
  canvas.focus();
};
$("appearance-cancel").onclick = () => { $("appearance").hidden = true; canvas.focus(); };
$("options-done").onclick = () => { $("options").hidden = true; canvas.focus(); playSound("Coins"); };

function saveView() {
  try { localStorage.setItem("ds.view", JSON.stringify({ markers: U.markers, smooth: smoothing, camera: V.smooth, cursor: U.cursorSize })); } catch (e) { /* */ }
}

function loadView() {
  try {
    const v = JSON.parse(localStorage.getItem("ds.view") || "{}");
    if ("markers" in v) U.markers = v.markers;
    if ("smooth" in v) smoothing = v.smooth;
    if ("camera" in v) V.smooth = v.camera;
    if ("cursor" in v) U.cursorSize = +v.cursor;
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
$("admin-wave-go").onclick = () => send({ t: "admin", do: "wave", name: $("admin-wave").value.trim() });
$("admin-pw-go").onclick = () => {
  send({ t: "admin_password", name: $("admin-pw-name").value.trim(), new: $("admin-pw-new").value });
  $("admin-pw-new").value = "";
};
$("death-respawn").onclick = () => send({ t: "respawn" });
// ----- changing your own password (Options)
$("opt-password").onclick = () => {
  for (const id of ["pw-old", "pw-new", "pw-again"]) $(id).value = "";
  $("pw-status").textContent = "";
  $("options").hidden = true;
  $("password").hidden = false;
  $("pw-old").focus();
};
$("pw-cancel").onclick = () => { $("password").hidden = true; canvas.focus(); };
$("password-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const old = $("pw-old").value, nw = $("pw-new").value;
  const bad = nw.length < 4 ? "Use a new password of at least 4 characters."
    : nw !== $("pw-again").value ? "The two new passwords aren't the same." : "";
  if (bad) { $("pw-status").textContent = bad; $("pw-status").className = "error small"; return; }
  $("pw-status").textContent = "Changing it...";
  $("pw-status").className = "dim small";
  send({ t: "password", old, new: nw });
});
$("admin-goto").onclick = () => send({ t: "admin", do: "goto", place: $("admin-place").value.trim() });
$("admin-god").addEventListener("input", (ev) => send({ t: "admin", do: "god", on: ev.target.checked }));
$("admin-close").onclick = () => { $("admin").hidden = true; canvas.focus(); };
for (const id of ["admin", "options", "quit", "message", "appearance"]) {
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

// ----- a price on the market (Sell on the market, Set price)
let priceDone = null;
function askPrice(e, withQty, done) {
  releaseKeys();
  const have = withQty ? (S.me.inv || []).filter((i) => i[1] === e.n).reduce((a, i) => a + i[2], 0) : 0;
  const worth = Math.max(1, Math.floor(val(entityIni(e.n, "Value", "1")) || 1));
  $("price-title").textContent = (withQty ? "Sell " : "Price of ") + pretty(e.n);
  $("price-each").value = e.price || worth;
  $("price-qty-row").hidden = !withQty;
  $("price-qty").value = have; $("price-qty").max = have;
  $("price-hint").textContent = `A shop would pay about ${Math.max(1, Math.floor(worth * 0.6))} gold each; ` +
    `it sells them for about ${Math.max(1, Math.round(worth * 1.2))}.` + (withQty ? ` You have ${have}.` : "");
  priceDone = done;
  $("price").hidden = false;
  $("price-each").focus(); $("price-each").select();
}
$("price-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const price = Math.floor(+$("price-each").value), qty = Math.floor(+$("price-qty").value || 0);
  $("price").hidden = true;
  canvas.focus();
  if (priceDone && price >= 1) priceDone(price, qty);
  priceDone = null;
});
$("price-cancel").addEventListener("click", () => { $("price").hidden = true; priceDone = null; canvas.focus(); });

window.dsUI = { openQuit, openOptions, openAdmin, openChat, toggleFullscreen, askPrice };
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
let pickLook = null;
$("register-button").onclick = () => {
  unlock();
  if ($("look-section").hidden) {           // first: how they look, then the same button makes them
    $("look-section").hidden = false;
    setLoginError("");
    pickLook = buildPicker($("look-picker"), DEFAULT_LOOK);
    $("register-button").textContent = "Create character";
    $("login-password").setAttribute("autocomplete", "new-password");
    return;
  }
  login("register");
};

function login(mode) {
  loginMode = mode;
  setLoginError("");
  if (!N.open) { setLoginError("Not connected to the server yet..."); return; }
  send({ t: mode, name: $("login-name").value, password: $("login-password").value, invite: $("login-invite").value,
    look: mode === "register" && pickLook ? pickLook() : undefined });
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
      if (m.version) {
        const day = m.date ? new Date(m.date + "T12:00:00").toLocaleDateString(undefined,
          { day: "numeric", month: "short", year: "numeric" }) : "";
        $("login-version").textContent = "Version " + m.version + (day ? "  ·  " + day : "");
        $("login-version").title = m.commit ? "Build " + m.commit : "";
      }
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
      S.boostAt = now;                                        // (boost_left counts down from here)
      S.view = m.view;
      updateBuild();
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
      if (m.whisper === "from") addMessage(`${m.from} whispers: ${m.text}`, "140 40 140");
      else if (m.whisper === "to") addMessage(`You whisper to ${m.to}: ${m.text}`, "140 40 140");
      else addMessage(m.from ? `${m.from}: ${m.text}` : m.text, m.from ? "30 60 140" : "darkgray");
      if (m.from && m.from !== S.name && m.whisper !== "to" && O.chatSound)    // (another player said something)
        playSound(m.whisper === "from" ? "Whisper" : "Chat");
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
    case "buildables": onBuildables(m); break;
    case "died": {
      // (dead: the view goes dark and red; they wake when they choose to)
      const bits = [];
      if (m.lost) bits.push(`You lost ${m.lost} gold.`);
      bits.push("You kept your most valuable things, and anything you can't drop.");
      if (m.grave) bits.push(`Everything else is in your grave, marked on the minimap: get back to it within ${m.minutes} minutes.`);
      bits.push(m.bed ? "You'll wake in your bed at home." : "You'll wake at the start.");
      $("death-text").textContent = bits.join(" ");
      releaseKeys();
      $("death").hidden = false;
      setTimeout(() => $("death-respawn").focus(), 50);
      break;
    }
    case "respawned": $("death").hidden = true; canvas.focus(); break;
    case "password_result":
      $("pw-status").textContent = m.text;
      $("pw-status").className = m.ok ? "ok small" : "error small";
      if (m.ok) setTimeout(() => { $("password").hidden = true; canvas.focus(); }, 1500);
      break;
    case "wave": S.wave = m.name ? { ...m, at: now } : null; break;
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
  if (!running && A.m) musicTick(false, "Title");      // (the login screen: the title music, once a click lets it)
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
    drawBuild(ctx, I.mx, I.my, smoothing);
    if (S.me.dead) { ctx.fillStyle = "rgba(70,0,0,0.55)"; ctx.fillRect(0, 0, L.VW, L.VH); }    // (dead)
    ctx.imageSmoothingEnabled = smoothing;
    drawUI(ctx, now);
    drawBoosts(ctx, now, I.mx, I.my);
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
  if (running && !overlayOpen()) buildMouseMove(x, y, ev.buttons & 1);
});
canvas.addEventListener("mousedown", (ev) => {
  if (!running || overlayOpen()) return;
  canvas.focus();
  const [x, y] = toLogical(ev);
  if (buildMouseDown(ev.button, x, y)) return;
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
  if (B.on && ev.code === "Escape") { ev.preventDefault(); setBuild(false); return; }
  if (ev.code === "KeyB" && !J.open && S.me && S.me.home && S.me.home.own) { ev.preventDefault(); toggleBuild(); return; }
  keyDown(ev);
});
window.addEventListener("keyup", (ev) => { if (running) keyUp(ev); });
window.addEventListener("blur", () => { if (running) releaseKeys(); });
window.addEventListener("resize", resize);
document.addEventListener("fullscreenchange", resize);

// ================================================================================================================
// Starting
// ================================================================================================================
// The login screen's music: browsers only let sound start after a click or a key, so the first one starts it
function loginMusicButton() {
  const b = $("login-music");
  b.textContent = O.music && O.sound ? "♫ Music on" : "♫ Music off";
  b.classList.toggle("off", !(O.music && O.sound));
}
for (const ev of ["pointerdown", "keydown"]) document.addEventListener(ev, () => unlock(), true);
$("login-music").addEventListener("click", () => {
  unlock();
  if (O.music && O.sound) { O.music = false; stopMusic(); } else { O.music = true; O.sound = true; }
  saveOptions();
  loginMusicButton();
});

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
  preload(["Player1a", "Player2a", "Player4a", "Player8a"]);
  layout(screen.W);
  resize();
  fogInit();
  loadOptions();
  loginMusicButton();
  loadView();
  initBuildUI();
  onLoaded(() => {});
  connect();
}

boot();
