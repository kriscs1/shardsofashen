// Shards of Ashen in the browser: logging in, the server's messages, the screen (full screen, any size: the game is laid
// out 768 high and scaled to fit, drawn at the screen's own resolution so text stays sharp; a phone's is laid out
// lower, so everything's bigger: mobile.js) and the frame loop.
import { A, loadManifest, configRead, onLoaded, OWN } from "./assets.js";
import { G, S, setGeometry, resetWorld, addMap, applySnap, glide, addMessage, myPlayer, unpackCells } from "./state.js";
import { N, connect, send } from "./net.js";
import { V, drawWorld, addFx, stopWorkFx, setZoom, changeZoom, markOutcome, markSwing } from "./render.js";
import { invalidateMap, invalidateCell, mapCells, repaintAll } from "./ground.js";
import { L, U, layout, drawUI, drawBoosts, drawWorldMap, preloadInterface, showBanner, levelOfXp, journalOrigin, joyCentre,
  JOY, wmPan, wmZoomAt, wmInBox, shardFly } from "./ui.js";
import { I, mouseMove, mouseDown, mouseDrag, wheel, keyDown, keyUp, releaseKeys, updateCursor, closeJournal, stick, dragStart,
  dragMove, dragEnd } from "./input.js";
import { M, layoutChoice, chooseLayout } from "./mobile.js";
import { J, drawJournal } from "./journal.js";
import { O, loadOptions, saveOptions, playSound, musicTick, ambientTick, nearLoopTick, unlock, stopMusic } from "./audio.js";
import { setWeather, fogInit, revealCell, fogAdmin, setFogAdmin } from "./sky.js";
import { messageColour, clamp, val, pretty, coinHTML } from "./util.js";
import { buildPicker, DEFAULT_LOOK, lookImage, bodyFrame } from "./look.js";
import { preload, entityIni, sprite } from "./assets.js";
import { onGame } from "./games.js";
import { greet } from "./voice.js";
import { B, onBuildables, updateBuild, toggleBuild, setBuild, initBuildUI, buildMouseDown, buildMouseMove, drawBuild } from "./build.js";

const $ = (id) => document.getElementById(id);
const canvas = $("game");
const ctx = canvas.getContext("2d", { alpha: false });
const screen = { k: 1, ox: 0, oy: 0, dpr: 1, W: 1024, H: 768, tall: {} };
let smoothing = true;
let running = false;
let lastFrame = performance.now();
let lastSlow = 0;
let lastExplored = 0;
S.addLocal = (text, col) => addMessage(text, col);

// ================================================================================================================
// The screen
// ================================================================================================================
const PHONE_SHARPNESS = 2;                      // (a phone's canvas: at most this many pixels to a game pixel)
const UPRIGHT_W = 480;                          // (a phone held upright: this many game pixels across, room for a box)

function resize() {
  let dpr = window.devicePixelRatio || 1;
  let W, H = 768;
  if (M.on) {
    // (a phone: about a game pixel to a screen point, so its words are big enough; the height it had before the
    // keyboard came up, so the game doesn't shrink under it. Drawn at no more than twice that, not the screen's
    // own 2.5 or 3 times: as sharp to the eye, and half the pixels to paint every frame)
    const tall = Math.max(window.innerHeight, screen.tall[window.innerWidth] || 0);
    screen.tall[window.innerWidth] = tall;
    if (tall > window.innerWidth) {              // (held upright: as wide as a conversation, as tall as the screen)
      W = UPRIGHT_W;
      H = Math.round(W * tall / window.innerWidth / 2) * 2;
      dpr = Math.min(dpr, PHONE_SHARPNESS * W / window.innerWidth);
    } else {
      H = clamp(Math.round(tall / 1.08 / 2) * 2, 320, 768);
      W = Math.max(560, Math.round(H * window.innerWidth / tall / 2) * 2);
      dpr = Math.min(dpr, PHONE_SHARPNESS * H / tall);
    }
  }
  const cw = Math.max(1, Math.round(window.innerWidth * dpr));
  const ch = Math.max(1, Math.round(window.innerHeight * dpr));
  canvas.width = cw;
  canvas.height = ch;
  if (!M.on) W = clamp(Math.round(768 * cw / ch / 2) * 2, 1024, 1792);
  const k = Math.min(cw / W, ch / H);
  screen.k = k; screen.dpr = dpr; screen.W = W; screen.H = H;
  screen.ox = Math.round((cw - W * k) / 2);
  screen.oy = M.on ? 0 : Math.round((ch - H * k) / 2);
  if (A.m) layout(W, H);
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
  if (M.on) {                                    // (a phone: at the top, clear of the keyboard)
    box.style.left = (screen.ox / screen.dpr + 190 * k) + "px";
    box.style.width = Math.max(200, (L.VW || 800) - 190 - 120) * k + "px";
    box.style.top = (screen.oy / screen.dpr + 8 * k) + "px";
  } else {
    box.style.left = (screen.ox / screen.dpr + 8 * k) + "px";
    box.style.width = ((L.VW || 800) - 16) * k + "px";
    box.style.top = (screen.oy / screen.dpr + (L.chatY + 70) * k) + "px";
  }
  box.style.bottom = "auto";
}

// ----- the login screen's film of Northport: playing while it's there; the still picture for less motion
const loginVideo = $("login-video");
const stillPlease = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
function loginFilm() {
  const want = !running && !$("login").hidden && !stillPlease.matches;
  if (want && loginVideo.paused) loginVideo.play().catch(() => {});      // (muted: a browser lets it start itself)
  else if (!want && !loginVideo.paused) loginVideo.pause();
}

// ----- the item rack's search (shops, crafting, the bank): it filters the whole rack, on the server
let rackSearchFor = "";                          // (the rack it was last shown for: a new one starts with it empty)
let rackSearchTimer = 0;
function placeRackSearch() {
  const box = $("rack-search");
  const mode = S.box && S.box.mode;
  const show = running && !J.open && ["Shop", "Craft", "Bank"].includes(mode);
  if (!show) {
    if (!box.hidden) { box.hidden = true; if (document.activeElement === $("rack-search-input")) canvas.focus(); }
    rackSearchFor = "";
    return;
  }
  const key = mode + "|" + (S.box.rack || "") + "|" + (S.box.title || "");
  if (key !== rackSearchFor) {                   // (a rack just opened: no search yet)
    rackSearchFor = key;
    $("rack-search-input").value = S.box.filter || "";
    $("rack-ready").checked = !!S.box.ready;
  }
  $("rack-ready-row").hidden = mode !== "Craft";
  const k = screen.k / screen.dpr;
  const left = screen.ox / screen.dpr + (L.abX + 236) * k, top = screen.oy / screen.dpr + (L.abY + 14) * k;
  const st = `${left}px|${top}px|${184 * k}px|${22 * k}px`;
  if (box.dataset.at !== st) {
    box.dataset.at = st;
    Object.assign(box.style, { left: left + "px", top: top + "px", width: 184 * k + "px", height: 22 * k + "px" });
  }
  box.hidden = false;
}

function sendRackSearch() {
  clearTimeout(rackSearchTimer);
  rackSearchTimer = setTimeout(() => send({ t: "rack_filter", q: $("rack-search-input").value,
    ready: $("rack-ready").checked }), 150);
}
$("rack-search-input").addEventListener("input", sendRackSearch);
$("rack-ready").addEventListener("change", () => { sendRackSearch(); canvas.focus(); });
$("rack-search-input").addEventListener("keydown", (ev) => {
  ev.stopPropagation();                          // (letters search; they don't walk you or answer the box)
  if (ev.key === "Escape") {
    if (ev.target.value) { ev.target.value = ""; sendRackSearch(); } else canvas.focus();
  } else if (ev.key === "Enter") canvas.focus();
});

function sendChat() {
  const text = $("chat-input").value.trim();
  if (text) send({ t: "chat", text });
  $("chat-input").value = "";
  $("chat-entry").hidden = true;
  canvas.focus();
}

function openChat(start) {
  // (open already, the keys elsewhere - a click in the world took them: Enter sends what's written, or goes back to it)
  if (!$("chat-entry").hidden && typeof start !== "string") {
    if ($("chat-input").value.trim()) sendChat();
    else $("chat-input").focus();
    return;
  }
  if (typeof start === "string") $("chat-input").value = start;
  const box = $("chat-entry");
  box.hidden = false;
  if (M.on) { M.chat = true; M.bag = false; }
  placeChat();
  releaseKeys();
  $("chat-input").focus();
}

$("chat-input").addEventListener("blur", () => {
  // (a phone's keyboard put away with nothing written: the line goes too)
  if (M.on && !$("chat-input").value.trim()) $("chat-entry").hidden = true;
});
$("chat-input").addEventListener("keydown", (ev) => {
  ev.stopPropagation();
  if (ev.key === "Enter") {
    sendChat();
  } else if (ev.key === "Escape") {
    ev.target.value = "";
    $("chat-entry").hidden = true;
    canvas.focus();
  }
});

function overlayOpen() {
  // (not the chat line: you can walk, click and fight with it open)
  return ["options", "quit", "admin", "message", "reward", "login", "loading", "appearance", "price", "count", "death", "tavern-game"].some((id) => !$(id).hidden);
}

function openQuit() { releaseKeys(); $("quit").hidden = false; $("quit-no").focus(); }
$("quit-no").onclick = () => { $("quit").hidden = true; canvas.focus(); };
$("quit-options").onclick = () => { $("quit").hidden = true; openOptions(); };
$("quit-logout").onclick = () => {
  send({ t: "quit" });
  running = false;
  if (N.ws) N.ws.close();
  stopMusic();
  $("quit").hidden = true;
  showMessage("Shards of Ashen", "Your game is saved. See you soon!", () => location.reload());
};

// (in an app - Android, or the desktop one, which says so a moment later - out of the game to its start screen)
function appQuit() {
  if (!window.DSApp) return;
  $("quit-app").hidden = false;
  $("quit-app").onclick = () => {
    if (running) send({ t: "quit" });
    running = false;
    if (N.ws) N.ws.close();
    stopMusic();
    window.DSApp.goHome();
  };
}
appQuit();
window.addEventListener("dsapp", appQuit);
window.addEventListener("dsapp", () => homeRow());

function openOptions() {
  releaseKeys();
  $("opt-sound").checked = O.sound; $("opt-volume").value = O.volume; $("opt-chat-sound").checked = O.chatSound;
  $("opt-voices").checked = O.voices;
  $("opt-music").checked = O.music; $("opt-music-volume").value = O.musicVolume;
  $("opt-ambient").checked = O.ambient; $("opt-ambient-volume").value = O.ambientVolume;
  $("opt-markers").checked = U.markers; $("opt-smooth").checked = smoothing;
  $("opt-camera").value = V.smooth;
  $("opt-cursor").value = String(U.cursorSize || 22);
  $("opt-hotbar").value = String((S.me && S.me.hotbar || []).length || 5);
  $("options").hidden = false;
}
for (const [id, key, num] of [["opt-sound", "sound"], ["opt-volume", "volume", 1], ["opt-music", "music"], ["opt-chat-sound", "chatSound"], ["opt-voices", "voices"],
  ["opt-music-volume", "musicVolume", 1], ["opt-ambient", "ambient"], ["opt-ambient-volume", "ambientVolume", 1]]) {
  $(id).addEventListener("input", (ev) => {
    O[key] = num ? +ev.target.value : ev.target.checked;
    if (key === "musicVolume") O.musicChosen = true;
    saveOptions();
  });
}
$("opt-markers").addEventListener("input", (ev) => { U.markers = ev.target.checked; saveView(); });
$("opt-lan").addEventListener("input", (ev) => send({ t: "lan", open: ev.target.checked }));
$("opt-net").addEventListener("input", (ev) => send({ t: "internet", open: ev.target.checked }));
// (who can reach an app's own game: its host's say. The network's stays on it; the internet's goes through the central
// server, the game still running here, and needs the host signed in)
const reach = {};
function showReach(m) {
  Object.assign(reach, m);
  $("opt-net-row").hidden = !reach.own;
  $("opt-net").checked = !!reach.internet;
  $("opt-net").disabled = !reach.signed;
  $("opt-net-words").textContent = reach.signed ? "Open to the internet (your friends join by a link)" :
    "Open to the internet: sign in on the start screen first";
  $("opt-net-link-row").hidden = !(reach.own && reach.internet && reach.link);
  $("opt-net-link").value = reach.link || "";
  $("opt-lan-at-row").hidden = !(reach.own && $("opt-lan").checked && reach.address);
  $("opt-lan-at").textContent = `Others join from Join a local game, or at ${reach.address || ""}`;
}
$("opt-server-name-save").addEventListener("click", () => send({ t: "server_name", name: $("opt-server-name").value }));

// ----- the trade window (together.py): your pack's things to put in, your offer to take back, theirs; both accept
function tradeRow(name, n, buttons) {
  const row = document.createElement("div");
  row.className = "trade-item";
  const label = document.createElement("span");
  label.innerHTML = name === "Gold_Coin(s)" ? coinHTML(`${n} gold`) : coinHTML(`${pretty(name)}${n > 1 ? " x" + n : ""}`);
  row.append(label);
  for (const [text, msg] of buttons) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    b.addEventListener("click", () => send({ t: "trade", ...msg }));
    row.append(b);
  }
  return row;
}

let tradeV = 0;     // (the offer as last shown: an accept is for that one, not one changed on its way)
function showTrade(m) {
  $("trade").hidden = !m.open;
  if (!m.open) return;
  tradeV = m.v || 0;
  $("trade-title").textContent = `Trading with ${m.with}`;
  $("trade-their-head").textContent = `${m.with} offers`;
  const fill = (id, rows) => { const el = $(id); el.replaceChildren(...rows); };
  fill("trade-mine", (m.mine || []).map(([n, q]) => tradeRow(n, q, [["Back", { do: "back", item: n }]])));
  fill("trade-theirs", (m.theirs || []).map(([n, q]) => tradeRow(n, q, [])));
  fill("trade-stock", (m.stock || []).map(([n, q]) => tradeRow(n, q, n === "Gold_Coin(s)" ?
    [["+10", { do: "add", item: n, n: 10 }], ["+100", { do: "add", item: n, n: 100 }], ["All", { do: "add", item: n, n: q }]] :
    q > 1 ? [["+1", { do: "add", item: n, n: 1 }], ["All", { do: "add", item: n, n: q }]] : [["Put in", { do: "add", item: n, n: 1 }]])));
  $("trade-status").textContent = m.ok && m.their_ok ? "" : m.ok ? `You've accepted. Waiting for ${m.with}...` :
    m.their_ok ? `${m.with} has accepted: accept too, and it's done.` : "When you're both happy, both accept.";
  $("trade-accept").disabled = !!m.ok;
}
$("trade-accept").addEventListener("click", () => send({ t: "trade", do: "accept", v: tradeV }));
$("trade-cancel").addEventListener("click", () => send({ t: "trade", do: "cancel" }));
$("opt-smooth").addEventListener("input", (ev) => { smoothing = ev.target.checked; saveView(); });
$("opt-camera").addEventListener("input", (ev) => { V.smooth = +ev.target.value; saveView(); });
$("opt-cursor").addEventListener("input", (ev) => { U.cursorSize = +ev.target.value; saveView(); });
$("opt-hotbar").addEventListener("input", (ev) => send({ t: "hotbar_slots", n: +ev.target.value }));   // (kept with the character)
$("opt-fullscreen").onclick = toggleFullscreen;
$("login-full").onclick = toggleFullscreen;
$("login-full").hidden = M.app || !(document.fullscreenEnabled || document.webkitFullscreenEnabled);
for (const b of document.querySelectorAll("#options .tabs button")) {
  b.onclick = () => {                                    // (Options in tabs: short enough for a phone's screen)
    for (const t of document.querySelectorAll("#options .tabs button")) t.classList.toggle("on", t === b);
    for (const pane of document.querySelectorAll("#options .pane")) pane.hidden = pane.dataset.pane !== b.dataset.pane;
  };
}
$("opt-layout-row").hidden = M.app;                      // (the app is always the touch layout)
$("opt-layout").value = layoutChoice();
$("opt-layout").addEventListener("input", (ev) => chooseLayout(ev.target.value));
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
let adminItems = [], adminPlaces = [], adminCommands = [], adminMobs = [];
function openAdmin() {
  releaseKeys();
  $("admin").hidden = false;
  send({ t: "admin", do: "items" });
  if (!adminPlaces.length) send({ t: "admin", do: "places" });
  if (!adminCommands.length) send({ t: "admin", do: "commands" });
  send({ t: "admin", do: "standings" });
  send({ t: "admin", do: "quests" });
  send({ t: "admin", do: "forms" });
  send({ t: "admin", do: "spells" });
  if (!adminMobs.length) send({ t: "admin", do: "mobs" });
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
    row.append(tick, " " + pretty(name) + " ", lv);
    box.append(row);
  });
  $("admin-god").checked = !!S.me.god;
  $("admin-fly").checked = !!S.me.fly;
  $("admin-noblack").checked = fogAdmin().noBlack;
  $("admin-nofog").checked = fogAdmin().noFog;
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

function fillAdminPlaces() {
  // Go to: the world map's names, then the places, people and things with an Id (the filter narrows them)
  const f = $("admin-place-filter").value.toLowerCase().replace(/_/g, " ");
  const sel = $("admin-place");
  sel.innerHTML = "";
  const groups = new Map();
  for (const [group, label, where] of adminPlaces) {
    if (f && !label.toLowerCase().replace(/_/g, " ").includes(f)) continue;
    let g = groups.get(group);
    if (!g) {
      g = document.createElement("optgroup");
      g.label = group;
      groups.set(group, g);
      sel.append(g);
    }
    const o = document.createElement("option");
    o.value = where;
    o.textContent = label.replace(/_/g, " ");
    g.append(o);
  }
}
$("admin-place-filter").addEventListener("input", fillAdminPlaces);

function fillAdminCommands() {
  const sel = $("admin-cmd");
  sel.innerHTML = "";
  for (const [name, , help] of adminCommands) {
    const o = document.createElement("option");
    o.value = name;
    o.textContent = name;
    o.title = help;
    sel.append(o);
  }
  showCommandArgs();
}

function showCommandArgs() {
  // A box for each of the command's arguments, named as the script reference names them (its help on hover)
  const c = adminCommands.find((x) => x[0] === $("admin-cmd").value);
  const box = $("admin-cmd-args");
  box.innerHTML = "";
  $("admin-cmd").title = c ? c[2] : "";
  if (!c) return;
  c[1].forEach((kind, i) => {
    const inp = document.createElement("input");
    inp.placeholder = kind.trim().toLowerCase();
    inp.title = c[3][i] || kind;
    inp.maxLength = 200;
    box.append(inp);
  });
}
$("admin-cmd").addEventListener("change", showCommandArgs);
$("admin-cmd-go").onclick = () => send({ t: "admin", do: "script", command: $("admin-cmd").value,
  args: [...$("admin-cmd-args").querySelectorAll("input")].map((i) => i.value) });
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

function fillAdminTowns(towns) {
  // Town standing: each town with yours and its rank (the one picked stays picked; its number to change)
  const sel = $("admin-town"), was = sel.value;
  sel.innerHTML = "";
  for (const [key, name, n, rank] of towns) {
    const o = document.createElement("option");
    o.value = key;
    o.dataset.n = n;
    o.textContent = `${name}: ${n} (${rank})`;
    sel.append(o);
  }
  if (was && towns.some((t) => t[0] === was)) sel.value = was;
  showAdminStanding();
}
function showAdminStanding() {
  const o = $("admin-town").selectedOptions[0];
  $("admin-standing").value = o ? o.dataset.n : "";
}
$("admin-town").addEventListener("change", showAdminStanding);
$("admin-standing-go").onclick = () => send({ t: "admin", do: "standing", town: $("admin-town").value,
  value: $("admin-standing").value.trim() });

let adminQuests = [];
function fillAdminQuests() {
  // Quests: each with its stage (done ticked when it's finished); the one picked stays picked
  const sel = $("admin-quest"), was = sel.value;
  const f = $("admin-quest-filter").value.toLowerCase();
  sel.innerHTML = "";
  for (const [name, attr, stage, done] of adminQuests) {
    if (f && !name.toLowerCase().includes(f) && !attr.toLowerCase().includes(f)) continue;
    const o = document.createElement("option");
    o.value = name;
    o.textContent = `${name}: ${done > 0 && +stage >= done ? "done" : +stage > 0 ? "stage " + stage : "not begun"}`;
    sel.append(o);
  }
  if (was && [...sel.options].some((o) => o.value === was)) sel.value = was;
  showAdminQuest();
}
function showAdminQuest() {
  // the picked quest's stage, and each of its variables to change (Enter in one sets it)
  const q = adminQuests.find((x) => x[0] === $("admin-quest").value);
  const box = $("admin-quest-vars");
  box.innerHTML = "";
  $("admin-quest-stage").value = q ? q[2] : "";
  $("admin-quest-done").checked = !!q && q[3] > 0 && +q[2] >= q[3];
  $("admin-quest-stage").title = q ? `${q[1]}: 0 (not begun) to ${q[3]} (done)` : "";
  for (const [v, value] of q ? q[4] : []) {
    const l = document.createElement("label"), i = document.createElement("input");
    i.value = value;
    i.maxLength = 40;
    i.dataset.v = v;
    i.addEventListener("change", () => send({ t: "admin", do: "quest", quest: q[0], vars: { [v]: i.value.trim() } }));
    l.append(v.replace(/_/g, " "), i);
    box.append(l);
  }
}
function fillAdminForms(forms) {
  // Stance forms: each one learnt or not, bound or not (for nothing, past the six if wanted - forms.py)
  const box = $("admin-forms");
  box.innerHTML = "";
  for (const [key, title, learnt, bound] of forms) {
    const row = document.createElement("div"), name = document.createElement("span");
    name.textContent = `${title} (${key.split(".")[0]})`;
    const tick = (words, on) => {
      const l = document.createElement("label"), i = document.createElement("input");
      i.type = "checkbox";
      i.checked = !!on;
      l.append(i, words);
      return [l, i];
    };
    const [l1, knows] = tick("learnt", learnt), [l2, holds] = tick("bound", bound);
    const set = () => send({ t: "admin", do: "form", form: key, learnt: knows.checked || holds.checked,
      bound: holds.checked });
    knows.addEventListener("input", () => { if (!knows.checked) holds.checked = false; set(); });
    holds.addEventListener("input", set);
    row.append(name, l1, l2);
    box.append(row);
  }
}
function fillAdminSpells(spells) {
  // Spells: each known to a rank, or not at all (for nothing, whatever your Channeling)
  const box = $("admin-spells");
  box.innerHTML = "";
  const roman = ["", "I", "II", "III", "IV", "V"];
  for (const [spell, title, rank, top] of spells) {
    const l = document.createElement("label"), name = document.createElement("span"), sel = document.createElement("select");
    name.textContent = title;
    for (let r = 0; r <= top; r++) {
      const o = document.createElement("option");
      o.value = r;
      o.textContent = r ? (top > 1 ? "rank " + (roman[r] || r) : "known") : "not known";
      sel.append(o);
    }
    sel.value = rank;
    sel.addEventListener("change", () => send({ t: "admin", do: "spell", spell, rank: +sel.value }));
    l.append(name, sel);
    box.append(l);
  }
}
function fillAdminMobs() {
  // Spawn: every creature and person, foes first marked (the filter narrows them; the one picked stays picked)
  const f = $("admin-mob-filter").value.toLowerCase().replace(/_/g, " ");
  const sel = $("admin-mob"), was = sel.value;
  sel.innerHTML = "";
  for (const [name, foe] of adminMobs) {
    if (f && !name.toLowerCase().replace(/_/g, " ").includes(f)) continue;
    const o = document.createElement("option");
    o.value = name;
    o.textContent = pretty(name) + (foe ? " (foe)" : "");
    sel.append(o);
  }
  if (was && [...sel.options].some((o) => o.value === was)) sel.value = was;
}
$("admin-mob-filter").addEventListener("input", fillAdminMobs);
$("admin-spawn").onclick = () => send({ t: "admin", do: "spawn", name: $("admin-mob").value,
  count: $("admin-mob-count").value.trim() });
$("admin-quest-filter").addEventListener("input", fillAdminQuests);
$("admin-quest").addEventListener("change", showAdminQuest);
$("admin-quest-done").addEventListener("input", (ev) => send({ t: "admin", do: "quest", quest: $("admin-quest").value,
  done: ev.target.checked }));
$("admin-quest-go").onclick = () => send({ t: "admin", do: "quest", quest: $("admin-quest").value,
  stage: $("admin-quest-stage").value.trim() });
$("death-respawn").onclick = () => send({ t: "respawn" });
$("admin-goto").onclick = () => send({ t: "admin", do: "goto", place: $("admin-place").value });
$("admin-god").addEventListener("input", (ev) => send({ t: "admin", do: "god", on: ev.target.checked }));
$("admin-fly").addEventListener("input", (ev) => send({ t: "admin", do: "fly", on: ev.target.checked }));
for (const id of ["admin-noblack", "admin-nofog"]) {
  $(id).addEventListener("input", () => setFogAdmin($("admin-noblack").checked, $("admin-nofog").checked));
}
$("admin-close").onclick = () => { $("admin").hidden = true; canvas.focus(); };
for (const id of ["admin", "options", "quit", "message", "appearance", "demo-end", "count"]) {
  $(id).addEventListener("keydown", (ev) => {
    ev.stopPropagation();
    if (ev.key === "Escape") { $(id).hidden = true; canvas.focus(); }
  });
}

// ----- a finished quest's rewards (shards.py reward_tick): what you got, a row each
function showReward(m) {
  const list = $("reward-list");
  list.textContent = "";
  const row = (icon, text, cls) => {
    const li = document.createElement("li");
    if (icon) {
      const c = document.createElement("canvas");
      c.width = c.height = 32;
      preload([icon]).then(() => {                   // (a picture not seen yet: drawn once it's arrived)
        const im = sprite(icon);
        if (im) c.getContext("2d").drawImage(im, 0, 0, 32, 32);
      });
      li.append(c);
    }
    const span = document.createElement("span");
    span.textContent = text;
    if (cls) span.className = cls;
    li.append(span);
    list.append(li);
  };
  if (m.shards) row("Shard", `${m.shards} Shards`, "shards");
  for (const [item, n] of m.items || []) row(item, `${n > 1 ? n + " x " : ""}${pretty(item)}`);
  for (const [skill, xp] of m.xp || []) row(configRead("Skills", "Icon." + skill, ""), `${xp} ${pretty(skill)} experience`);
  if (!list.children.length) row("", "None", "none");
  $("reward-quest").textContent = m.quest;
  releaseKeys();
  $("reward").hidden = false;
  $("reward-ok").focus();
}
$("reward-ok").onclick = () => { $("reward").hidden = true; canvas.focus(); };

// ----- the demo's edge (dsengine/demo.py): said once each time in, in the game's own words, never a character's
const BUY_WORDS = "The full game is bought once, from the start screen, for your Hallisium account: then it's yours " +
  "in the app and in a browser too, and your character keeps everything they've done.";
function showDemo(m) {
  if (m.why === "end") { showDemoEnd(m); return; }
  if (m.why === "border") {
    releaseKeys();
    showMessage("The demo", "That's as far as the demo goes: the full game goes on from here, past the Isle to the " +
      "mainland, its towns and the rest of the story. " + BUY_WORDS);
  } else if (m.why === "level") {
    releaseKeys();
    showMessage("The demo", `That's level ${m.level}, as far as the demo goes. What you learn from here is kept, ` +
      "and counts as soon as you have the full game. " + BUY_WORDS);
  }
}

// the ferry, papers in hand (demo.py demo_end): the Isle's story done, as far as the demo goes
function showDemoEnd(m) {
  const fill = (id, rows) => {
    const list = $(id);
    list.textContent = "";
    for (const [icon, text] of rows) {
      const li = document.createElement("li");
      if (icon) {
        const c = document.createElement("canvas");
        c.width = c.height = 32;
        preload([icon]).then(() => {
          const im = sprite(icon);
          if (im) c.getContext("2d").drawImage(im, 0, 0, 32, 32);
        });
        li.append(c);
      }
      const span = document.createElement("span");
      span.textContent = text;
      li.append(span);
      list.append(li);
    }
    list.previousElementSibling.hidden = list.hidden = !rows.length;
  };
  fill("demo-end-found", m.found || []);
  fill("demo-end-ask", (m.ask || []).map((q) => ["", q]));
  $("demo-end-ahead").textContent = m.ahead || "";
  $("demo-end-buy").textContent = BUY_WORDS;
  releaseKeys();
  $("demo-end").hidden = false;
  $("demo-end").querySelector(".panel").scrollTop = 0;   // (from the top, on a phone too)
  $("demo-end-ok").focus({ preventScroll: true });
}
$("demo-end-ok").onclick = () => { $("demo-end").hidden = true; canvas.focus(); };

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
  $("price-hint").innerHTML = coinHTML(`A shop would pay about ${Math.max(1, Math.floor(worth * 0.6))} gold each; ` +
    `it sells them for about ${Math.max(1, Math.round(worth * 1.2))}.` + (withQty ? ` You have ${have}.` : ""));
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

// ----- how many (Drop X, Deposit X, Withdraw X; a stack dragged out of the bag)
let countDone = null;
function askCount(title, hint, start, done) {
  releaseKeys();
  $("count-title").textContent = title;
  $("count-hint").textContent = hint;
  $("count-qty").value = start ? String(start) : "";
  countDone = done;
  $("count").hidden = false;
  $("count-qty").focus(); $("count-qty").select();
}
$("count-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const qty = Math.floor(+$("count-qty").value || 0);
  $("count").hidden = true;
  canvas.focus();
  if (countDone && qty >= 1) countDone(qty);     // (nothing typed, or 0: nothing done)
  countDone = null;
});
$("count-cancel").addEventListener("click", () => { $("count").hidden = true; countDone = null; canvas.focus(); });

window.dsUI = { openQuit, openOptions, openAdmin, openChat, toggleFullscreen, askPrice, askCount };

// The phone's Back button (the app asks the page first): shuts what's open, the topmost first; false when nothing was
// (then the app goes back to its start screen)
window.dsBack = () => {
  const shut = { options: "options-done", quit: "quit-no", admin: "admin-close", price: "price-cancel",
                 appearance: "appearance-cancel", message: "message-ok", reward: "reward-ok",
                 "demo-end": "demo-end-ok" };
  for (const [id, button] of Object.entries(shut)) if (!$(id).hidden) { $(button).click(); return true; }
  if (!$("chat-entry").hidden) { $("chat-input").value = ""; $("chat-entry").hidden = true; return true; }
  if (J.open) { closeJournal(); return true; }
  if (U.worldMap) { U.worldMap = false; return true; }
  if (U.rcm) { U.rcm = null; return true; }
  if (S.spellReady) { S.spellReady = ""; return true; }
  if (S.itemInUse) { S.itemInUse = 0; send({ t: "use_cancel" }); return true; }
  if (S.box.mode) { send({ t: "close" }); return true; }
  if (M.bag || M.chat) { M.bag = M.chat = false; return true; }
  return false;
};
window.dsDebug = { S, V, N, send, layout: () => ({ ...L, k: screen.k / screen.dpr }) };   // (for tools/browser_check.py, and scripted play-throughs)

// ================================================================================================================
// Who you are, then which of your characters: the server keeps them by your Hallisium account (the start screen's
// ticket) or by this device (a key of its own: each game gets its own from the start screen); no passwords
// ================================================================================================================
const joinArgs = new URLSearchParams(location.hash.slice(1));     // (the start screen's: device, host, account)
if (location.hash) history.replaceState(null, "", location.pathname + location.search);    // (keys off the address)
const randomKey = () => Array.from(crypto.getRandomValues(new Uint8Array(18)), (b) => b.toString(16).padStart(2, "0")).join("");
function deviceKey() {
  let k = joinArgs.get("device") || "";
  try {
    if (k) localStorage.setItem("ds.device", k);
    else k = localStorage.getItem("ds.device") || "";
    if (!k) { k = randomKey(); localStorage.setItem("ds.device", k); }
  } catch (e) { k = k || randomKey(); }     // (a private window: this visit only)
  return k;
}
let ticket = new URLSearchParams(location.search).get("ticket") || "";    // (the central server's: once)
let mine = null, pickLook = null;
let homeUrl = "", pageCode = "";      // (the start screen's address; the page's code as this page was loaded)

function setLoginError(text, ok) {
  $("login-error").textContent = text || "";
  $("login-error").className = ok ? "ok" : "error";
}
function busyLogin(on) {
  for (const b of document.querySelectorAll("#login-form button:not(.music-toggle)")) b.disabled = on;
}

function authenticate() {
  send({ t: "auth", ticket, device: deviceKey(), host: joinArgs.get("host") || "", account: joinArgs.get("account") || "",
         full: joinArgs.get("full") === "1", demo: joinArgs.get("demo") === "1" });   // (the last two: an app's own game's)
  if (ticket) {
    ticket = "";
    const q = new URLSearchParams(location.search);
    q.delete("ticket");
    q.set("joined", "1");                          // (a reload's still welcome: without it, the server shows nothing)
    history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q : ""));
  }
  $("login-who").textContent = "Finding your characters...";
}

function loginShow(which) {         // ("chars" or "make")
  for (const id of ["chars", "make"]) $(id).hidden = id !== which;
  if (which === "make") {
    pickLook = buildPicker($("look-picker"), DEFAULT_LOOK);
    $("invite-row").hidden = !(mine && mine.invite);
    $("make-back").hidden = !(mine && mine.list.length);
    $("login-name").focus();
  }
}

function portrait(look) {
  const c = document.createElement("canvas");
  c.width = c.height = 48;
  c.className = "char-face";
  const draw = () => {
    const im = lookImage(bodyFrame("Player4a", look), look);
    const x = c.getContext("2d");
    x.imageSmoothingEnabled = false;
    x.clearRect(0, 0, 48, 48);
    if (im) x.drawImage(im, 0, 0, 48, 48);
  };
  draw();
  setTimeout(draw, 400);           // (the sprite, once it's come)
  return c;
}

// (what a character is tied to, said where it's made and where it's chosen)
const PLACE_WORDS = {
  public: ["This character will live on this server only, saved online here and not on your device. It can never join another server. " +
    "You can copy it to your own device later, but a copy can never come back.", "Characters here live on this server, saved online here and not on your device."],
  own: ["This character will be saved on this device only, with no copy online. It can only be played in your own game: " +
    "it can never join a public server.", "Characters here are saved on this device only."],
  theirs: ["This character will live in your host's game, saved on their device, and can never move to another game.",
    "Characters here live in your host's game, saved on their device."],
  server: ["This character will live on this server only.", "Characters here live on this server only."],
};
function homeRow() { $("home-row").hidden = !(window.DSApp || homeUrl); }
const CARRIED = "carried";                          // (a character on its way from a public server to this device)
function saveFile(name, text) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  a.download = `${name}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}
function exported(m) {
  busyLogin(false);
  const text = JSON.stringify({ name: m.name, save: m.save });
  if (window.DSApp && window.DSApp.set) {
    window.DSApp.set(CARRIED, text);
    setLoginError(`A copy of ${m.name} is on this device: go back to the main menu and open Single player to find it.`, true);
  } else {
    saveFile(m.name, text);
    setLoginError(`A copy of ${m.name} is downloaded. Open Single player in the Shards of Ashen app, and choose the file there.`, true);
  }
}
function bring(text, fromApp) {
  let got = null;
  try { got = JSON.parse(text); } catch (e) { got = null; }
  if (!got || !got.name || !got.save) { setLoginError("That isn't a character."); return; }
  busyLogin(true);
  send({ t: "import", name: got.name, save: got.save });
  if (fromApp) window.DSApp.set(CARRIED, "");
}
async function offerCarried(box) {
  let text = "";
  try { text = (window.DSApp && window.DSApp.get && await window.DSApp.get(CARRIED)) || ""; } catch (e) { text = ""; }
  if (text) {
    let name = "";
    try { name = JSON.parse(text).name; } catch (e) { name = ""; }
    const b = document.createElement("button");
    b.type = "button";
    b.className = "char new";
    b.textContent = `Bring ${name} here (copied from a public server)`;
    b.onclick = () => bring(text, true);
    box.prepend(b);
  }
  if (!(window.DSApp && window.DSApp.kind && window.DSApp.kind() === "android")) {   // (Android's window can't pick a file)
    const b = document.createElement("button");
    b.type = "button";
    b.className = "char new";
    b.textContent = "Bring a character from a file";
    b.onclick = () => $("bring-file").click();
    box.append(b);
  }
}
$("bring-file").onchange = async () => {
  const f = $("bring-file").files[0];
  $("bring-file").value = "";
  if (f) bring(await f.text());
};

function showCharacters(m) {
  mine = m;
  busyLogin(false);
  if (m.joined) {                                    // (a reload's still welcome here: what's left of the ticket)
    const q = new URLSearchParams(location.search);
    q.set("joined", m.joined);
    history.replaceState(null, "", location.pathname + "?" + q);
  }
  const words = PLACE_WORDS[m.place] || PLACE_WORDS.server;
  $("make-warn").textContent = words[0];
  $("login-place").textContent = words[1];
  homeRow();
  $("login-who").textContent = m.account ? `Signed in as ${m.account}` :
    "Playing without a Hallisium account: your characters here are this device's.";
  const box = $("chars");
  box.textContent = "";
  for (const ch of m.list) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "char";
    b.title = `Play as ${ch.name}`;
    const words = document.createElement("span");
    words.className = "char-words";
    const name = document.createElement("b");
    name.textContent = ch.name;
    const level = document.createElement("small");
    level.textContent = m.demo ? `Level ${Math.min(ch.level || 1, m.demo)} · Demo: the Isle, level ${m.demo}` :
      `Level ${ch.level || 1}`;
    words.append(name, level);
    b.append(portrait(ch.look || DEFAULT_LOOK), words);
    b.onclick = () => { unlock(); setLoginError(""); busyLogin(true); send({ t: "play", name: ch.name }); };
    if (m.place === "public") {                      // (a copy for the player's own device: one way)
      const row = document.createElement("div");
      row.className = "char-row";
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "char-copy";
      copy.textContent = "Copy to device";
      copy.title = `Copy ${ch.name} to your own device. The copy can't come back to this server.`;
      copy.onclick = () => { unlock(); setLoginError(""); busyLogin(true); send({ t: "export", name: ch.name }); };
      row.append(b, copy);
      box.append(row);
    } else box.append(b);
  }
  if (m.make && m.list.length < m.most) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "char new";
    b.textContent = "+ New character";
    b.onclick = () => { unlock(); setLoginError(""); loginShow("make"); };
    box.append(b);
  }
  if (m.place === "own") offerCarried(box);
  if (!m.list.length && !m.make) setLoginError("New characters can't be made on this server.");
  else setLoginError(m.text, true);
  loginShow(!m.list.length && m.make ? "make" : "chars");
}

$("login-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  if ($("make").hidden) return;
  unlock();
  setLoginError("");
  if (!N.open) { setLoginError("Not connected to the server yet..."); return; }
  busyLogin(true);
  send({ t: "create", name: $("login-name").value, invite: $("login-invite").value, look: pickLook ? pickLook() : undefined });
});
$("make-back").onclick = () => { setLoginError(""); loginShow("chars"); };
$("home-link").onclick = (ev) => {
  if (!window.DSApp) return;          // (a browser: the link's own address, the central server's start screen)
  ev.preventDefault();
  if (window.DSApp.goHome) window.DSApp.goHome();
};

N.onOpen = () => { $("login-online").textContent = "Connected."; };
N.onClose = () => {
  busyLogin(false);
  if (running) {
    running = false;
    releaseKeys();
    stopMusic();
    showMessage("Disconnected", "The connection to the server was lost. Your game is saved: come back in to carry on.",
      () => location.reload());
  } else {
    $("login-online").textContent = "Can't reach the server. Trying again...";
    setTimeout(connect, 3000);
  }
};

// ================================================================================================================
// The server's messages
// ================================================================================================================
const workBeats = new Set();         // (the sounds of the swings still to come: cancelled if the work stops)
N.onMessage = (m) => {
  const now = performance.now();
  switch (m.t) {
    case "hello":
      if (!pageCode) pageCode = m.code || "";
      if ((A.m && m.assets && A.m.version && m.assets !== A.m.version) ||   // (the server's pictures changed under us)
          (m.code && m.code !== pageCode)) {                                // (or the page's own code did)
        if (running) showMessage("Shards of Ashen", "The game has been updated. It will load again.", () => location.reload());
        else location.reload();
        break;
      }
      homeUrl = m.home || "";
      $("home-link").href = homeUrl || "#";
      homeRow();
      $("login-online").textContent = `${m.online} of ${m.max} adventurers online.`;
      $("login-server").textContent = m.name || "";            // (the game's name: what its host called it)
      if (m.name) document.title = `${m.name} - Shards of Ashen`;
      if (m.version) {
        const day = m.date ? new Date(m.date + "T12:00:00").toLocaleDateString(undefined,
          { day: "numeric", month: "short", year: "numeric" }) : "";
        $("login-version").textContent = "Version " + m.version + (day ? "  ·  " + day : "");
        $("login-version").title = m.commit ? "Build " + m.commit : "";
      }
      if (!running) authenticate();
      break;
    case "closed":                                 // (the host has closed the game to the network)
      setLoginError(m.text);
      busyLogin(true);
      break;
    case "lan":
      $("opt-lan").checked = !!m.open;
      showReach({});
      break;
    case "internet": showReach({ internet: m.internet }); break;
    case "server_name": $("opt-server-name").value = m.name || ""; break;
    case "trade": showTrade(m); break;
    case "characters": showCharacters(m); break;
    case "exported": exported(m); break;
    case "login_fail":
      setLoginError(m.reason);
      if (m.invite) $("invite-row").hidden = false;
      busyLogin(false);
      if (!mine) {                                   // (not let in at all: nothing here to choose)
        $("login-who").textContent = "";
        homeRow();
      }
      break;
    case "welcome": startGame(m); break;
    case "kicked":
      running = false;
      releaseKeys();
      stopMusic();
      showMessage("Shards of Ashen", m.reason, () => location.reload());
      break;
    case "mapdata": addMap(m); invalidateMap(m.name); break;
    case "mapcells": mapCells(m); break;
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
      S.lockPicks.clear();
      for (const [map, x, y, msg, pick] of m.locks || []) {
        S.locks.set(map + "," + x + "," + y, msg);
        if (pick) S.lockPicks.set(map + "," + x + "," + y, pick);
      }
      break;
    }
    case "stones":                                 // (a shardstone's travel map: the world map, its stones on it)
      U.stones = m;
      U.stoneHover = "";
      U.worldMap = "stones";
      break;
    case "labels":                                 // (the world map's names, when one shows or hides: the Shardgate)
      S.labels = m.labels || [];
      break;
    case "me":
      S.me = m;
      OWN.v = m.own ? m.own.v : null;
      S.boostAt = now;                                        // (boost_left counts down from here)
      S.view = m.view;
      updateBuild();
      if (S.itemInUse && !m.inv.some((i) => i[0] === S.itemInUse)) S.itemInUse = 0;
      break;
    case "quests": S.quests = m.quests; S.marks = m.marks; S.level = m.level; break;
    case "weather": setWeather(m); break;
    case "snap":
      if ("st" in m) {
        const late = now - m.st;
        if (S.catchUpUntil) {
          if (late - S.lagBase < 300 || now > S.catchUpUntil) S.catchUpUntil = 0;     // (caught up)
        } else S.lagBase = Math.min(S.lagBase ?? Infinity, late);
      }
      applySnap(m, now);
      break;
    case "box":
      // (a new speech, or the same one sent again: its words come again only when it's new - voice.js)
      m.fresh = m.mode === "Conversation" && S.box.mode === m.mode && S.box.text === m.text && S.box.title === m.title ?
        S.box.fresh : performance.now();
      greet(S.box, m);                             // (a conversation opening: its speaker's "Hello!")
      S.box = m;
      m.answers = m.responses;                     // (a long speech's pages: the answers wait for its last - ui.js)
      m.tpage = 0;
      if (m.mode) { U.rcm = null; releaseKeys(); }
      break;
    case "msg": addMessage(m.text, messageColour(m.kind), m.id || 0, m.of || 0); break;
    case "reward": showReward(m); break;          // (its jingle came as the quest finished: quests.py)
    case "chat":
      if (m.whisper === "from") addMessage(`${m.from} whispers: ${m.text}`, "140 40 140");
      else if (m.whisper === "to") addMessage(`You whisper to ${m.to}: ${m.text}`, "140 40 140");
      else if (m.party) addMessage(`[Party] ${m.from}: ${m.text}`, "30 110 60");
      else addMessage(m.from ? `${m.from}: ${m.text}` : m.text, m.from ? "30 60 140" : "darkgray");
      if (m.from && m.from !== S.name && m.whisper !== "to" && O.chatSound)    // (another player said something)
        playSound(m.whisper === "from" ? "Whisper" : "Chat");
      break;
    case "players": S.players = m.list; S.max = m.max; break;
    case "where": S.where = m.list || []; break;
    case "sound":
      if (!behind()) {
        const play = () => playSound(m.name, "x" in m ? [m.x, m.y] : null);
        if (m.delay > 0) {                                           // (the later beats of a piece of work)
          const id = setTimeout(() => { workBeats.delete(id); play(); }, m.delay);
          workBeats.add(id);
        } else play();
      }
      break;
    case "work_stop":                                                // (they walked off: no more swings)
      for (const id of workBeats) clearTimeout(id);
      workBeats.clear();
      stopWorkFx(now);
      break;
    case "splat": case "anim": case "shot": case "nudge": case "swing": case "skillpop": case "burst": case "mark": case "bubble":
      if (!behind()) addFx(m, now);
      break;
    case "hurt": S.hurtUntil = now + 240; break;
    case "shardfly": if (!behind()) shardFly(m, now); break;          // (Shards off the ground, to the Shard bar)
    case "act": if (m.swing) markSwing(m.swing, now); else markOutcome(!!m.ok, now); break;   // (how a click went)
    case "levelup": showBanner(m.skill, m.level, now); break;
    case "demo": showDemo(m); break;
    case "clock":
      S.clock = { day: m.day, secs: m.secs, on: m.on, at: now };
      if (m.night) S.night = m.night;
      if (m.season && m.season !== S.season) { S.season = m.season; repaintAll(); }
      break;
    case "map":
      if (m.z !== S.mapZ) V.cam.snap = true;
      S.mapName = m.name;
      S.mapZ = m.z;
      break;
    case "teleport":
      V.cam.snap = true;
      if (m.fade) startTeleportFade(now);
      break;
    case "use": S.itemInUse = m.uid; break;
    case "ready": S.spellReady = m.spell; S.itemInUse = 0; break;
    case "reveal": revealCell(m.map, m.cell); break;
    case "lightning":
      if (!V.underRoof) {
        S.flashAt = now;
        setTimeout(() => playSound(m.sound), m.thunder);
      }
      break;
    case "sleep": S.sleep = { start: now, fade: m.fade, hold: m.hold, text: m.text }; break;
    case "journal": S.journal = m; break;
    case "standing": if (S.journal) S.journal.standing = m.list; break;     // (a town thinks better or worse of you)
    case "buildables": onBuildables(m); break;
    case "died": {
      // (dead: the view goes dark and red; they wake when they choose to)
      const bits = [];
      if (m.lost) bits.push(`You lost ${m.lost} gold.`);
      bits.push("You kept your most valuable things, and anything you can't drop.");
      if (m.grave) bits.push(`Everything else is in your grave, marked on the minimap: get back to it within ${m.minutes} minutes.`);
      bits.push(m.bed ? "You'll wake in your bed at home." : "You'll wake at the start.");
      $("death-text").innerHTML = coinHTML(bits.join(" "));
      releaseKeys();
      $("death").hidden = false;
      setTimeout(() => $("death-respawn").focus(), 50);
      break;
    }
    case "respawned": $("death").hidden = true; canvas.focus(); break;
    case "wave": S.wave = m.name ? { ...m, at: now } : null; break;
    case "game": releaseKeys(); onGame(m, now); break;
    case "admin_items": adminItems = m.items; fillAdminItems(); break;
    case "admin_places": adminPlaces = m.places; fillAdminPlaces(); break;
    case "admin_commands": adminCommands = m.commands; fillAdminCommands(); break;
    case "admin_standings": fillAdminTowns(m.towns); break;
    case "admin_quests": adminQuests = m.quests; fillAdminQuests(); break;
    case "admin_forms": fillAdminForms(m.forms || []); break;
    case "admin_spells": fillAdminSpells(m.spells || []); break;
    case "admin_mobs": adminMobs = m.mobs || []; fillAdminMobs(); break;
    case "admin_status": $("admin-status").textContent = m.text; break;
    default: break;
  }
};

async function startGame(m) {
  S.labels = m.labels || [];
  S.name = m.name;
  S.uid = m.uid;
  S.admin = m.admin;
  $("opt-name-row").hidden = !m.host;              // (the game's name: the host's say, or an admin's)
  $("opt-whose").textContent = (m.account ? `Part of your Hallisium account, ${m.account}` : "This device's") +
    ": it lives on this server only.";
  $("opt-server-name").value = m.server || "";
  $("opt-lan-row").hidden = !(m.reach && m.reach.own);    // (open to the network: an app's own game's host's say)
  $("opt-lan").checked = !!m.lan;
  showReach(m.reach || {});
  S.explored.clear();
  for (const [k, v] of Object.entries(m.explored || {})) S.explored.set(k, unpackCells(v));
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
// (minimised, a browser can stop reading the server; back, it races through what it missed. That's not shown:
// the last picture stays, quiet, until it has caught up - four seconds at most - then it's the world as it is now)
let hiddenAt = 0;
document.addEventListener("visibilitychange", () => {
  if (document.hidden) hiddenAt = performance.now();
  else if (hiddenAt && performance.now() - hiddenAt > 1000) S.catchUpUntil = performance.now() + 4000;
});
function behind() { return document.hidden || !!S.catchUpUntil; }
// (the page closed: say goodbye at once, rather than leave the character standing there until the server notices)
window.addEventListener("pagehide", () => {
  if (running) { send({ t: "quit" }); if (N.ws) N.ws.close(); }
});

const FRAME_MS = 13;                           // (about 60 a second at most: a 120 Hz phone draws every other one)

// ----- off somewhere else (a shardstone, a script, dying): the last view fades to black, then the new one fades in
const TP_OUT = 800, TP_HOLD = 300, TP_IN = 1000;      // (2.1 s in all: out, a breath of black, in)
let tpFade = null;
function startTeleportFade(now) {
  const w = Math.round(L.VW * screen.k), h = Math.round(L.VH * screen.k);
  let shot = null;
  if (w > 0 && h > 0 && running) {                     // (the canvas still holds the frame before the move)
    shot = document.createElement("canvas");
    shot.width = w; shot.height = h;
    shot.getContext("2d").drawImage(canvas, screen.ox, screen.oy, w, h, 0, 0, w, h);
  }
  tpFade = { start: now, shot };
}
function drawTeleportFade(c, now) {
  if (!tpFade) return;
  const t = now - tpFade.start;
  if (t >= TP_OUT + TP_HOLD + TP_IN) { tpFade = null; return; }
  if (t < TP_OUT) {
    if (tpFade.shot) c.drawImage(tpFade.shot, 0, 0, L.VW, L.VH);
    c.fillStyle = `rgba(0,0,0,${t / TP_OUT})`;
  } else c.fillStyle = `rgba(0,0,0,${t < TP_OUT + TP_HOLD ? 1 : 1 - (t - TP_OUT - TP_HOLD) / TP_IN})`;
  c.fillRect(0, 0, L.VW, L.VH);
}

function frame(now) {
  requestAnimationFrame(frame);
  if (now - lastFrame < FRAME_MS && now >= lastFrame) return;
  if (running && S.catchUpUntil) {
    if (now > S.catchUpUntil) S.catchUpUntil = 0;
    else return;
  }
  const dt = Math.min(0.1, Math.max(0, (now - lastFrame) / 1000));
  lastFrame = now;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = "#180e0a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!running && A.m) musicTick(false, "Title");      // (the login screen: the title music, once a click lets it)
  placeRackSearch();
  loginFilm();
  if (!running || !A.m || !S.me) return;
  ctx.setTransform(screen.k, 0, 0, screen.k, screen.ox, screen.oy);
  if (ctx.imageSmoothingEnabled !== smoothing) ctx.imageSmoothingEnabled = smoothing;
  if (ctx.imageSmoothingQuality !== "high") ctx.imageSmoothingQuality = "high";    // (a resize resets it: only then)
  glide(now);
  if (J.open) {
    ctx.save();
    const [jx, jy] = journalOrigin();
    ctx.translate(jx, jy);
    drawJournal(ctx);
    ctx.restore();
  } else {
    drawWorld(ctx, L.VW, L.VH, now, dt, smoothing);
    drawBuild(ctx, I.mx, I.my, smoothing);
    drawTeleportFade(ctx, now);
    if (S.me.dead) { ctx.fillStyle = "rgba(70,0,0,0.55)"; ctx.fillRect(0, 0, L.VW, L.VH); }    // (dead)
    ctx.imageSmoothingEnabled = smoothing;
    drawUI(ctx, now);
    if (U.worldMap) drawWorldMap(ctx, now);
    drawBoosts(ctx, now, I.mx, I.my);
  }
  if (M.on && M.hoverUntil && now > M.hoverUntil && !U.rcm) {   // (a tap's name at the top: gone again)
    M.hoverUntil = 0; I.mx = I.my = -1; U.qm = "";
  }
  if (I.mx >= 0 && !overlayOpen()) mouseMove(I.mx, I.my);
  updateCursor(canvas, now);
  if (now - lastSlow > 250) {
    lastSlow = now;
    musicTick(V.underRoof, null);
    ambientTick(V.underRoof);
    nearLoopTick(V.underRoof);
  } else musicTick(V.underRoof, null);
  if (now - lastExplored > 3000) {
    lastExplored = now;
    for (const [map, cells] of S.exploredNew) if (cells.length) send({ t: "explored", map, cells });
    S.exploredNew.clear();
  }
}

// ----- input
// (the world map dragged about with the mouse: a press that doesn't move is still a click)
let wmDrag = null;
canvas.addEventListener("mousemove", (ev) => {
  const [x, y] = toLogical(ev);
  I.mx = x; I.my = y;
  if (wmDrag) {
    if (!(ev.buttons & 1) || !U.worldMap) wmDrag = null;
    else {
      if (Math.hypot(x - wmDrag.sx, y - wmDrag.sy) > 4) wmDrag.moved = true;
      if (wmDrag.moved) { wmPan(x - wmDrag.x, y - wmDrag.y); wmDrag.x = x; wmDrag.y = y; }
      return;
    }
  }
  mouseDrag(y, ev.buttons & 1);
  if (dragMove(x, y)) return;                    // (a thing dragged: to the hotbar, or out of the bag)
  if (running && !overlayOpen()) buildMouseMove(x, y, ev.buttons & 1);
});
canvas.addEventListener("mousedown", (ev) => {
  if (!running || overlayOpen()) return;
  canvas.focus();
  const [x, y] = toLogical(ev);
  if (U.worldMap && ev.button === 0 && wmInBox(x, y)) { wmDrag = { sx: x, sy: y, x, y, moved: false }; return; }
  if (buildMouseDown(ev.button, x, y)) return;
  if (ev.button === 0 && dragStart(x, y, 5)) return;   // (the bag or the hotbar: a click or a drag, told on letting go)
  mouseDown(ev.button, x, y);
});
window.addEventListener("mouseup", (ev) => {
  if (ev.button === 0 && U.drag) {
    const [x, y] = toLogical(ev), d = U.drag;
    if (!dragEnd(x, y) && running && !overlayOpen()) mouseDown(0, d.sx, d.sy);
    return;
  }
  if (!wmDrag || ev.button !== 0) return;
  const d = wmDrag;
  wmDrag = null;
  if (!d.moved && running && !overlayOpen()) mouseDown(0, d.sx, d.sy);
});
canvas.addEventListener("contextmenu", (ev) => ev.preventDefault());

// ----- a phone's fingers: a tap is a click, a hold (half a second) a right-click; the stick walks; a finger drags the
// journal's page about and scrolls the chat log
const HOLD_MS = 450, SLOP = 12;
const touches = new Map();                       // pointer id -> {x, y, sx, sy, kind: "tap" | "stick" | "pan", ...}
canvas.addEventListener("pointerdown", (ev) => {
  if (ev.pointerType === "mouse") return;
  ev.preventDefault();                           // (no pretend mouse clicks after it)
  if (!running || overlayOpen()) return;
  unlock();
  canvas.focus();
  canvas.setPointerCapture?.(ev.pointerId);
  const [x, y] = toLogical(ev);
  const [jx, jy] = joyCentre();
  if (!J.open && !U.worldMap && !S.box.mode && !M.chat && !M.bag && Math.hypot(x - jx, y - jy) <= JOY.r + 8) {
    M.joy = { id: ev.pointerId, dx: 0, dy: 0 };
    touches.set(ev.pointerId, { kind: "stick" });
    moveStick(x, y);
    return;
  }
  if (U.worldMap && !J.open) {                   // (the world map: dragged, pinched, or tapped)
    const others = [...touches.values()].filter((o) => o.kind === "map");
    others.forEach((o) => { o.pinched = true; });
    touches.set(ev.pointerId, { kind: "map", x, y, sx: x, sy: y, moved: false, pinched: others.length > 0 });
    return;
  }
  const t = { kind: J.open ? "pan" : "tap", x, y, sx: x, sy: y, moved: false, held: false, panX: M.panX, panY: M.panY,
    chatLine: U.chatLine };
  touches.set(ev.pointerId, t);
  I.mx = x; I.my = y;
  M.hoverUntil = performance.now() + 60000;      // (named while the finger's down)
  if (t.kind === "tap") {
    dragStart(x, y, SLOP);                       // (the bag or the hotbar: a finger's drag)
    t.timer = setTimeout(() => {                 // (held: everything you can do with it)
      if (t.moved || !touches.has(ev.pointerId)) return;
      t.held = true;
      mouseDown(2, t.x, t.y);
      M.hoverUntil = performance.now() + 2500;
    }, HOLD_MS);
  }
});
canvas.addEventListener("pointermove", (ev) => {
  const t = touches.get(ev.pointerId);
  if (!t) return;
  ev.preventDefault();
  const [x, y] = toLogical(ev);
  if (t.kind === "stick") { moveStick(x, y); return; }
  if (t.kind === "map") {
    const fingers = [...touches.values()].filter((o) => o.kind === "map");
    if (fingers.length >= 2) {                   // (two fingers: apart is in, together out, about between them)
      const o = fingers.find((f) => f !== t);
      const before = Math.hypot(t.x - o.x, t.y - o.y), after = Math.hypot(x - o.x, y - o.y);
      if (before > 4 && after > 4) wmZoomAt(after / before, (x + o.x) / 2, (y + o.y) / 2);
      wmPan((x - t.x) / 2, (y - t.y) / 2);
    } else {
      if (Math.hypot(x - t.sx, y - t.sy) > SLOP) t.moved = true;
      if (t.moved) wmPan(x - t.x, y - t.y);
    }
    t.x = x; t.y = y;
    return;
  }
  t.x = x; t.y = y;
  if (Math.hypot(x - t.sx, y - t.sy) > SLOP) t.moved = true;
  if (dragMove(x, y)) { I.mx = x; I.my = y; return; }
  if (t.kind === "pan") {
    M.panX = clamp(t.panX - (x - t.sx), 0, Math.max(0, 1024 - L.W));
    M.panY = clamp(t.panY - (y - t.sy), 0, Math.max(0, 768 - L.H));
    return;
  }
  if (M.chat && t.sy >= L.chatY && t.moved) {     // (the log dragged: older lines, or newer)
    U.chatLine = clamp(t.chatLine + Math.round((y - t.sy) / 15), 1, Math.max(1, S.messages.length - 4));
    return;
  }
  I.mx = x; I.my = y;
});
function touchEnd(ev, cancelled) {
  const t = touches.get(ev.pointerId);
  if (!t) return;
  touches.delete(ev.pointerId);
  clearTimeout(t.timer);
  if (t.kind === "stick") { M.joy = null; stick(0, 0); return; }
  if (t.kind === "map") {                          // (a tap, not a drag or a pinch: as a click)
    if (!cancelled && !t.moved && !t.pinched && running && !overlayOpen() && U.worldMap) mouseDown(0, t.sx, t.sy);
    return;
  }
  M.hoverUntil = performance.now() + 2500;
  if (cancelled || t.held) { dragEnd(-1, -1, true); return; }
  if (t.kind === "tap" && dragEnd(t.x, t.y)) return;
  if (t.moved && t.kind === "pan") return;
  if (t.moved && (M.chat && t.sy >= L.chatY)) return;
  if (!running || overlayOpen()) return;
  const x = t.moved ? t.x : t.sx, y = t.moved ? t.y : t.sy;
  if (buildMouseDown(0, x, y)) return;
  mouseDown(0, x, y);
}
canvas.addEventListener("pointerup", (ev) => touchEnd(ev, false));
canvas.addEventListener("pointercancel", (ev) => touchEnd(ev, true));

function moveStick(x, y) {
  const [jx, jy] = joyCentre();
  let dx = x - jx, dy = y - jy;
  const far = Math.hypot(dx, dy), most = JOY.r - JOY.knob / 2;
  if (far > most) { dx *= most / far; dy *= most / far; }
  M.joy = { ...(M.joy || {}), dx, dy };
  stick(dx, dy);
}
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
  preload(["Player1a", "Player2a", "Player4a", "Player8a", "PlayerF1a", "PlayerF2a", "PlayerF4a", "PlayerF8a"]);
  layout(screen.W, screen.H);
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
