// Building on your homestead (the server's dsengine/homes.py): the Build button and B, a panel of what you can build
// (Data/Buildables.ini, sent as "buildables"), a ghost of it on the tile under the mouse, click or drag to build,
// and a tool that takes things down again (the top thing first: the roof, an object, what's on the ground, the ground).
import { G, S, tileAt } from "./state.js";
import { A, sprite } from "./assets.js";
import { send } from "./net.js";
import { V, screenToWorld } from "./render.js";
import { L } from "./ui.js";
import { pretty } from "./util.js";

export const B = { on: false, pieces: [], byId: new Map(), protected: new Set(), cat: "", piece: "", remove: false,
  last: "", drag: false };
const $ = (id) => document.getElementById(id);
const CATS = ["Floors", "Walls", "Doors", "Windows", "Roofs", "Furniture", "Lights", "Garden", "Workshops"];

export function onBuildables(m) {
  B.pieces = m.pieces || [];
  B.byId = new Map(B.pieces.map((p) => [p.id, p]));
  B.protected = new Set((m.protected || []).map(([x, y]) => x + "," + y));
  B.cat = B.cat || (B.pieces[0] && B.pieces[0].cat) || "";
  fillTabs();
}

const onOwnHome = () => !!(S.me && S.me.home && S.me.home.own);

export function constructionLevel() {
  const i = A.m ? A.m.skills.indexOf("Construction") : -1;
  return i >= 0 && S.me ? Math.max(1, Math.floor(S.me.xp[i])) : 1;
}

function held(name) {
  let n = 0;
  for (const it of (S.me && S.me.inv) || []) if (it[1] === name) n += it[2];
  return n;
}

function canAfford(p) { return p.needs.every(([item, q]) => held(item) >= q); }

// ----- the button and the panel
export function updateBuild() {
  // After the server says where the player is: the button shows on their own homestead only
  const own = onOwnHome();
  $("build-button").hidden = !own || B.on;
  if (B.on && !own) setBuild(false);
  if (B.on) fillInfo();
}

export function setBuild(on) {
  B.on = on && onOwnHome();
  $("build-panel").hidden = !B.on;
  $("build-button").hidden = !onOwnHome() || B.on;
  B.last = "";
  if (B.on) { fillTabs(); fillGrid(); }
}

export function toggleBuild() { setBuild(!B.on); }

function fillTabs() {
  const tabs = $("build-tabs");
  if (!tabs) return;
  tabs.textContent = "";
  const cats = CATS.filter((c) => B.pieces.some((p) => p.cat === c))
    .concat([...new Set(B.pieces.map((p) => p.cat))].filter((c) => !CATS.includes(c)));
  for (const c of cats) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = c;
    b.className = c === B.cat ? "on" : "";
    b.onclick = () => { B.cat = c; B.remove = false; fillTabs(); fillGrid(); };
    tabs.appendChild(b);
  }
  $("build-remove").className = B.remove ? "on" : "";
}

function fillGrid() {
  const grid = $("build-grid");
  grid.textContent = "";
  const level = constructionLevel();
  for (const p of B.pieces.filter((q) => q.cat === B.cat)) {
    const b = document.createElement("button");
    b.type = "button";
    b.title = p.name;
    b.className = (p.id === B.piece && !B.remove ? "on " : "") + (level < p.level ? "locked" : canAfford(p) ? "" : "short");
    const img = document.createElement("img");
    img.src = "/assets/sprites/" + encodeURIComponent(p.image) + ".png";
    img.alt = p.name;
    b.appendChild(img);
    if (level < p.level) {
      const s = document.createElement("span");
      s.textContent = p.level;
      b.appendChild(s);
    }
    b.onclick = () => { B.piece = p.id; B.remove = false; fillTabs(); fillGrid(); };
    grid.appendChild(b);
  }
  fillInfo();
}

function fillInfo() {
  const info = $("build-info");
  if (!info) return;
  if (B.remove) {
    info.innerHTML = "<b>Take down</b><br>Click to take down the top thing on a tile: a roof, a workshop, what's " +
      "on the ground, then the ground. You get half the materials back.";
    return;
  }
  const p = B.byId.get(B.piece);
  if (!p) { info.textContent = "Choose something to build, then click (or drag) on your land."; return; }
  const level = constructionLevel();
  const needs = p.needs.length ? p.needs.map(([item, q]) => {
    const h = held(item);
    return `<span class="${h >= q ? "ok" : "bad"}">${q} ${pretty(item)} (${h})</span>`;
  }).join(", ") : "nothing";
  info.innerHTML = `<b>${esc(p.name)}</b><br>Needs: ${needs}<br>` +
    `<span class="${level >= p.level ? "ok" : "bad"}">Construction ${p.level}</span> (you: ${level})` +
    (p.on ? `<br>Goes on ${p.on.toLowerCase() === "wall" ? "a wall" : "a " + esc(pretty(p.on).replace(/\d+$/, "").toLowerCase())}` : "");
}

function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]); }

export function initBuildUI() {
  $("build-button").onclick = () => setBuild(true);
  $("build-done").onclick = () => setBuild(false);
  $("build-remove").onclick = () => { B.remove = !B.remove; fillTabs(); fillGrid(); };
}

// ----- the mouse on the land
function tileUnder(x, y) {
  if (x < 0 || y < 0 || x >= L.VW || y >= L.VH) return null;
  const [wx, wy] = screenToWorld(x, y);
  const t = tileAt(S.mapZ, wx, wy);
  if (!t || t.m.name !== S.mapName || t.tx < 1 || t.ty < 1 || t.tx > G.xt || t.ty > G.yt) return null;
  return t;
}

function act(t) {
  const key = t.tx + "," + t.ty;
  if (key === B.last) return;
  B.last = key;
  if (B.remove) send({ t: "unbuild", x: t.tx, y: t.ty });
  else if (B.piece) send({ t: "build", x: t.tx, y: t.ty, piece: B.piece });
}

export function buildMouseDown(button, x, y) {
  // True if build mode took the click
  if (!B.on || S.box.mode) return false;
  const t = tileUnder(x, y);
  if (!t) return false;
  if (button === 2) { setBuild(false); return true; }
  if (button !== 0) return false;
  B.last = "";
  B.drag = true;
  act(t);
  return true;
}

export function buildMouseMove(x, y, held) {
  if (!B.on || !held || !B.drag) { B.drag = false; return; }
  const p = B.byId.get(B.piece);
  if (!B.remove && p && p.kind === "Object") return;      // (workshops one at a time)
  const t = tileUnder(x, y);
  if (t) act(t);
}

// ----- the ghost
export function drawBuild(ctx, mx, my, smoothing) {
  if (!B.on) return;
  const t = tileUnder(mx, my);
  if (!t) return;
  const cam = V.cam;
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, L.VW, L.VH);
  ctx.clip();
  ctx.scale(V.zoom, V.zoom);
  ctx.imageSmoothingEnabled = smoothing && V.zoom !== Math.floor(V.zoom);
  const x = t.m.ox + (t.tx - 1) * G.tw - cam.x, y = t.m.oy + (t.ty - 1) * G.th - cam.y;
  const edge = t.tx < 2 || t.ty < 2 || t.tx > G.xt - 1 || t.ty > G.yt - 1 || B.protected.has(t.tx + "," + t.ty);
  let ok = !edge;
  if (B.remove) {
    ctx.strokeStyle = ok ? "rgba(230,90,70,0.95)" : "rgba(120,120,120,0.8)";
    ctx.lineWidth = 2;
    ctx.strokeRect(x + 1, y + 1, G.tw - 2, G.th - 2);
    ctx.beginPath();
    ctx.moveTo(x + 8, y + 8); ctx.lineTo(x + G.tw - 8, y + G.th - 8);
    ctx.moveTo(x + G.tw - 8, y + 8); ctx.lineTo(x + 8, y + G.th - 8);
    ctx.stroke();
  } else {
    const p = B.byId.get(B.piece);
    if (p) {
      ok = ok && constructionLevel() >= p.level && canAfford(p);
      const img = sprite(p.image);
      if (img) {
        ctx.globalAlpha = 0.7;
        const w = img.width, h = img.height;
        ctx.drawImage(img, x + (G.tw - w) / 2, y + G.th - h);
        ctx.globalAlpha = 1;
      }
    }
    ctx.strokeStyle = ok ? "rgba(90,230,120,0.95)" : "rgba(230,90,70,0.95)";
    ctx.lineWidth = 2;
    ctx.strokeRect(x + 1, y + 1, G.tw - 2, G.th - 2);
  }
  ctx.restore();
}
