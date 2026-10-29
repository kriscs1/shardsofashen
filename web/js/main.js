// Shards of Ashen in the browser: logging in, the server's messages, the screen (full screen, any size: the game is laid
// out 768 high and scaled to fit, drawn at the screen's own resolution so text stays sharp; a phone's is laid out
// lower, so everything's bigger: mobile.js) and the frame loop.
import { A, loadManifest, configRead, onLoaded, OWN } from "./assets.js";
import { G, S, setGeometry, resetWorld, addMap, applySnap, glide, addMessage, myPlayer } from "./state.js";
import { N, connect, send } from "./net.js";
import { V, drawWorld, addFx, stopWorkFx, setZoom, changeZoom } from "./render.js";
import { invalidateMap, invalidateCell, mapCells } from "./ground.js";
import { L, U, layout, drawUI, drawBoosts, drawWorldMap, preloadInterface, showBanner, levelOfXp, journalOrigin, joyCentre,
  JOY, wmPan, wmZoomAt, wmInBox } from "./ui.js";
import { I, mouseMove, mouseDown, mouseDrag, wheel, keyDown, keyUp, releaseKeys, updateCursor, closeJournal, stick } from "./input.js";
import { M, layoutChoice, chooseLayout } from "./mobile.js";
import { J, drawJournal } from "./journal.js";
import { O, loadOptions, saveOptions, playSound, musicTick, ambientTick, unlock, stopMusic } from "./audio.js";
import { setWeather, fogInit, revealCell, fogAdmin, setFogAdmin } from "./sky.js";
import { messageColour, clamp, val, pretty } from "./util.js";
import { buildPicker, DEFAULT_LOOK } from "./look.js";
import { preload, entityIni, sprite } from "./assets.js";
import { onGame } from "./games.js";
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
let loginMode = "login";

// ----- the characters logged in from this browser: their names on the login screen (the password, every time)
const NAMES_KEY = "ds.names", MAX_NAMES = 8;
function savedNames() {
  try {
    const old = JSON.parse(localStorage.getItem("ds.login") || "null");    // (the old "remember me": its name only)
    if (old) {
      localStorage.removeItem("ds.login");
      if (old.name) localStorage.setItem(NAMES_KEY, JSON.stringify([old.name]));
    }
    const v = JSON.parse(localStorage.getItem(NAMES_KEY) || "[]");
    return Array.isArray(v) ? v.filter((n) => typeof n === "string" && n) : [];
  } catch (e) { return []; }
}
function saveNames(list) {
  try { localStorage.setItem(NAMES_KEY, JSON.stringify(list.slice(0, MAX_NAMES))); } catch (e) { /* (private window) */ }
}
function rememberName(name) {
  saveNames([name, ...savedNames().filter((n) => n.toLowerCase() !== name.toLowerCase())]);
}

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

// ----- the login screen's film of Northgate: playing while it's there; the still picture for less motion
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
  return ["options", "quit", "admin", "message", "reward", "login", "loading", "appearance", "price", "password", "death", "tavern-game"].some((id) => !$(id).hidden);
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

// (in the Android app: out of the game, to the app's start screen: host, the games on the network, an address)
if (window.DSApp) {
  $("quit-app").hidden = false;
  $("quit-app").onclick = () => {
    if (running) send({ t: "quit" });
    running = false;
    if (N.ws) N.ws.close();
    stopMusic();
    window.DSApp.goHome();
  };
}

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
let adminItems = [], adminPlaces = [], adminCommands = [];
function openAdmin() {
  releaseKeys();
  $("admin").hidden = false;
  send({ t: "admin", do: "items" });
  if (!adminPlaces.length) send({ t: "admin", do: "places" });
  if (!adminCommands.length) send({ t: "admin", do: "commands" });
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
$("admin-goto").onclick = () => send({ t: "admin", do: "goto", place: $("admin-place").value });
$("admin-god").addEventListener("input", (ev) => send({ t: "admin", do: "god", on: ev.target.checked }));
for (const id of ["admin-noblack", "admin-nofog"]) {
  $(id).addEventListener("input", () => setFogAdmin($("admin-noblack").checked, $("admin-nofog").checked));
}
$("admin-close").onclick = () => { $("admin").hidden = true; canvas.focus(); };
for (const id of ["admin", "options", "quit", "message", "appearance"]) {
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
    const c = document.createElement("canvas");
    c.width = c.height = 32;
    if (icon) preload([icon]).then(() => {           // (a picture not seen yet: drawn once it's arrived)
      const im = sprite(icon);
      if (im) c.getContext("2d").drawImage(im, 0, 0, 32, 32);
    });
    li.append(c);
    const span = document.createElement("span");
    span.textContent = text;
    if (cls) span.className = cls;
    li.append(span);
    list.append(li);
  };
  if (m.shards) row("Shard", `${m.shards} Shards`, "shards");
  for (const [item, n] of m.items || []) row(item, `${n > 1 ? n + " x " : ""}${pretty(item)}`);
  for (const [skill, xp] of m.xp || []) row(configRead("Skills", "Icon." + skill, ""), `${xp} ${pretty(skill)} experience`);
  if (!list.children.length) row("", "The thanks of those you helped");
  $("reward-quest").textContent = m.quest;
  releaseKeys();
  $("reward").hidden = false;
  $("reward-ok").focus();
}
$("reward-ok").onclick = () => { $("reward").hidden = true; canvas.focus(); };

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

// The phone's Back button (the app asks the page first): shuts what's open, the topmost first; false when nothing was
// (then the app goes back to its start screen)
window.dsBack = () => {
  const shut = { options: "options-done", quit: "quit-no", admin: "admin-close", price: "price-cancel",
                 password: "pw-cancel", appearance: "appearance-cancel", message: "message-ok", reward: "reward-ok" };
  for (const [id, button] of Object.entries(shut)) if (!$(id).hidden) { $(button).click(); return true; }
  if (!$("chat-entry").hidden) { $("chat-input").value = ""; $("chat-entry").hidden = true; return true; }
  if (J.open) { closeJournal(); return true; }
  if (U.worldMap) { U.worldMap = false; return true; }
  if (U.rcm) { U.rcm = null; return true; }
  if (S.itemInUse) { S.itemInUse = 0; send({ t: "use_cancel" }); return true; }
  if (S.box.mode) { send({ t: "close" }); return true; }
  if (M.bag || M.chat) { M.bag = M.chat = false; return true; }
  return false;
};
window.dsDebug = { S, V, send, layout: () => ({ ...L, k: screen.k / screen.dpr }) };   // (for tools/browser_check.py, and scripted play-throughs)

// ================================================================================================================
// Logging in
// ================================================================================================================
function setLoginError(text) { $("login-error").textContent = text || ""; }

function showNames() {
  // (a button for each character logged in from here: click one, then type its password; x forgets it)
  const box = $("login-names");
  box.textContent = "";
  const names = savedNames();
  box.hidden = !names.length;
  for (const n of names) {
    const b = document.createElement("span");
    b.className = "name";
    b.title = `Log in as ${n}`;
    b.textContent = n;
    b.onclick = () => { $("login-name").value = n; $("login-password").value = ""; $("login-password").focus(); };
    const x = document.createElement("button");
    x.type = "button";
    x.className = "forget";
    x.title = `Forget ${n} on this browser`;
    x.textContent = "\u00d7";
    x.onclick = (ev) => {
      ev.stopPropagation();
      saveNames(savedNames().filter((m) => m !== n));
      if ($("login-name").value === n) $("login-name").value = "";
      showNames();
    };
    b.appendChild(x);
    box.appendChild(b);
  }
}
{
  const names = savedNames();
  if (names.length) $("login-name").value = names[0];
  showNames();
  (names.length ? $("login-password") : $("login-name")).focus();
}

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
  send({ t: mode, name: $("login-name").value, password: $("login-password").value,
    invite: $("login-invite").value, look: mode === "register" && pickLook ? pickLook() : undefined });
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
const workBeats = new Set();         // (the sounds of the swings still to come: cancelled if the work stops)
N.onMessage = (m) => {
  const now = performance.now();
  switch (m.t) {
    case "hello":
      if (A.m && m.assets && A.m.version && m.assets !== A.m.version) {     // (the server's pictures changed under us)
        if (running) showMessage("Shards of Ashen", "The game has been updated. It will load again.", () => location.reload());
        else location.reload();
        break;
      }
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
      for (const [map, x, y, msg] of m.locks || []) S.locks.set(map + "," + x + "," + y, msg);
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
      S.box = m;
      if (m.mode) { U.rcm = null; releaseKeys(); }
      break;
    case "msg": addMessage(m.text, messageColour(m.kind), m.id || 0, m.of || 0); break;
    case "reward": showReward(m); playSound("Quest"); break;
    case "chat":
      if (m.whisper === "from") addMessage(`${m.from} whispers: ${m.text}`, "140 40 140");
      else if (m.whisper === "to") addMessage(`You whisper to ${m.to}: ${m.text}`, "140 40 140");
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
    case "splat": case "anim": case "shot": case "nudge": case "skillpop": case "burst": if (!behind()) addFx(m, now); break;
    case "hurt": S.hurtUntil = now + 240; break;
    case "levelup": showBanner(m.skill, m.level, now); break;
    case "clock": S.clock = { day: m.day, secs: m.secs, on: m.on, at: now }; break;
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
      if (m.ok) {
        setTimeout(() => { $("password").hidden = true; canvas.focus(); }, 1500);
      }
      break;
    case "wave": S.wave = m.name ? { ...m, at: now } : null; break;
    case "game": releaseKeys(); onGame(m, now); break;
    case "admin_items": adminItems = m.items; fillAdminItems(); break;
    case "admin_places": adminPlaces = m.places; fillAdminPlaces(); break;
    case "admin_commands": adminCommands = m.commands; fillAdminCommands(); break;
    case "admin_status": $("admin-status").textContent = m.text; break;
    default: break;
  }
};

async function startGame(m) {
  S.labels = m.labels || [];
  rememberName(m.name);                           // (its name on the login screen next time; never its password)
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
const TP_OUT = 220, TP_IN = 380;
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
  if (t >= TP_OUT + TP_IN) { tpFade = null; return; }
  if (t < TP_OUT) {
    if (tpFade.shot) c.drawImage(tpFade.shot, 0, 0, L.VW, L.VH);
    c.fillStyle = `rgba(0,0,0,${t / TP_OUT})`;
  } else c.fillStyle = `rgba(0,0,0,${1 - (t - TP_OUT) / TP_IN})`;
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
  ctx.imageSmoothingEnabled = smoothing;
  ctx.imageSmoothingQuality = "high";
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
  if (running && !overlayOpen()) buildMouseMove(x, y, ev.buttons & 1);
});
canvas.addEventListener("mousedown", (ev) => {
  if (!running || overlayOpen()) return;
  canvas.focus();
  const [x, y] = toLogical(ev);
  if (U.worldMap && ev.button === 0 && wmInBox(x, y)) { wmDrag = { sx: x, sy: y, x, y, moved: false }; return; }
  if (buildMouseDown(ev.button, x, y)) return;
  mouseDown(ev.button, x, y);
});
window.addEventListener("mouseup", (ev) => {
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
  if (cancelled || t.held || (t.moved && t.kind === "pan")) return;
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
