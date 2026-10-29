// The interface round the world (the desktop game's ui.py, the rest of render): the sidebar (minimap, clock, buttons,
// Stats / Gear / Quests, the inventory), the chat bar, your level, health and Shards (top left) and what's under the
// mouse (top middle), the ActionBox and its responses, the right-click menu, the hotbar, the level-up banner. Laid
// out at 768 high, as wide as the screen's shape wants (1024 to 1792); on a phone (mobile.js) the world fills the
// screen and the rest sits over it.
import { G, S, cellOf, isHomeMap } from "./state.js";
import { A, sprite, size, has, entityIni, spellIni, configRead, preload } from "./assets.js";
import { val, word, trim, lbstr, pretty, clamp, colour, rgb, drawText, drawTextMid, centreText, textWidth, fitText,
  wrapLines, roundBox, fontPx, setFont } from "./util.js";
import { dayFraction, isNight, timeText, fogEnabled, fogSeeAll } from "./sky.js";
import { fogCell } from "./state.js";
import { T, getVerbs, verbLabel, canSellHere, displayName, skillLevel, itemPrice, spellTaught, knowsSpell,
  cooldownLeft, spellAt, spellTitle, castCost } from "./verbs.js";
import { lookImage } from "./look.js";
import { entityTip, itemLines } from "./tips.js";
import { M } from "./mobile.js";

export const TAB_TEXT = [243, 232, 136];
const PARCHMENT = [212, 191, 126];
const INK = [243, 232, 136];

export const L = {};

export function layout(W, H = 768) {
  L.W = W;
  L.H = H;
  L.DX = W - 1024;
  const [abw, abh] = size("AB_Conversation");
  const [, rbh] = size("ResponseBox");
  if (M.on) {
    // (a phone: the world all over the screen; the minimap top right, the buttons under it; the bag, when it's
    // open, the Stats box beside the pack, left of the buttons)
    L.VW = W;
    L.VH = H;
    L.mmSize = 92;
    L.mmX = W - 8 - L.mmSize / 2;
    L.mmY = 26 + L.mmSize / 2;
    L.btnX = W - 30;
    L.btnY = L.mmY + L.mmSize / 2 + 30;
    L.packW = 190;
    L.packH = 14 + 32 * 7 + 12;
    L.bagW = 224 + L.packW;
    L.bagX = Math.min(W - 64, L.mmX - L.mmSize / 2 - 8) - L.bagW;   // (clear of the minimap)
    L.bagY = Math.max(6, Math.floor((H - L.packH) / 2));
    L.statX = L.bagX;
    L.statY = L.bagY;
    L.packX = L.bagX + 224;
    L.invX = L.packX + 15;
    L.invY = L.bagY + 14;
    L.chatY = H - 96;
    L.chatW = W - 64;                                // (clear of the buttons)
    L.chatR = L.chatW - 44;
    L.boostR = L.mmX - L.mmSize / 2 - 10;
    L.abX = Math.max(4, Math.min(Math.floor((L.VW - abw) / 2), L.packX - abw - 6));
    L.packY = L.bagY;
    L.bagH = Math.max(200, L.packH);
    L.upright = H > W;
    if (L.upright) {
      // (held upright: one column under the minimap - a box and its answers over the pack, or in the bag, the Stats
      // box over the pack)
      L.abX = Math.max(4, Math.floor((W - abw) / 2));
      L.abY = L.mmY + L.mmSize / 2 + 12;
      L.packY = L.abY + abh + rbh + 14;
      L.bagW = 224;
      L.bagX = Math.max(6, Math.floor((W - 64 - L.bagW) / 2));
      L.bagY = Math.max(L.mmY + L.mmSize / 2 + 12, L.packY - 208);
      L.bagH = L.packY + L.packH - L.bagY;
      L.statX = L.bagX;
      L.statY = L.bagY;
      L.packX = L.bagX + Math.floor((L.bagW - L.packW) / 2);
      L.invX = L.packX + 15;
      L.invY = L.packY + 14;
    }
  } else {
    L.VW = W - 224;
    L.VH = 672;
    L.statX = L.VW;
    L.statY = 175;
    L.invX = L.VW + 34;
    L.invY = 413;
    L.mmX = L.VW + 140;
    L.mmY = 84;
    L.mmSize = 160;
    L.chatY = L.VH;
    L.chatW = W;
    L.chatR = W - 44;
    L.boostR = L.VW - 8;
    L.abX = Math.floor((L.VW - abw) / 2);
    L.upright = false;
  }
  if (!L.upright) L.abY = Math.floor((L.VH - (abh + rbh)) / 2);
  L.rbX = L.abX;                                    // (the answers line up with the box above them)
  L.rbY = L.abY + abh;
  L.helpX = L.VW + 18;
  L.helpY = 18;
}

// (on a phone the pack shows while the bag's open, or beside a shop, the bank or crafting; the Stats box only in
// the bag)
export function packShown() { return !M.on || M.bag || (!!S.box.mode && S.box.mode !== "Conversation"); }
export function statsShown() { return !M.on || (M.bag && !S.box.mode); }

export const U = {
  statsView: 0, questsPage: 1, questHover: 0, equipHover: 0, skillHover: 0, statRows: 1, statRowTop: 41,
  statRowH: 33, cursorSize: 22, chatLine: 1, qm: "", qmKind: "", rcm: null, hotHover: -1, minimapZoom: 0, rbHover: 0,
  hover: null, onlineShownUntil: 0, banner: null, markers: true, topY: 8,
  stones: null, stoneHits: [], stoneHover: "",   // (the travel map: worldMap === "stones" - shardcraft.py stone_map)
  wm: null, wmZoom: 1, wmCx: 0, wmCy: 0, wmShown: 0,   // (the world map's box, how far it's zoomed in and its middle)
};

const SLOT_OUTLINES = { Weapon: "Iron_Sword", Shield: "Iron_Shield", Head: "Iron_Helm", Body: "Iron_Platebody",
  Legs: "Iron_Platelegs", Feet: "Iron_Boots", Hands: "Iron_Gauntlets", Ring: "Gold_Ring" };
const SLOT_NAMES = ["", "Weapon", "Shield", "Head", "Body", "Legs", "Feet", "Hands", "Ring"];
const EQUIP_GRID = [[0, 1], [2, 1], [1, 0], [1, 1], [1, 2], [1, 3], [0, 2], [2, 2]];
export const EQUIP_BOX = 28;
export const equipX = (s) => 49 + EQUIP_GRID[s - 1][0] * 50;
export const equipY = (s) => 41 + EQUIP_GRID[s - 1][1] * 32;
export const HOTBAR_SIZE = 38;

export const INTERFACE = ["SideBar", "SideBarBorder", "StatBox", "ChatBar", "InfoBox", "AB_Conversation", "AB_Bank",
  "AB_Craft", "ResponseBox", "MinimapMarker", "Mana", "Heart", "Placeholder", "Hurt_Top", "Hurt_Bottom", "Hurt_Left",
  "Hurt_Right", "Player4a"];

export function preloadInterface() {
  const names = [...INTERFACE];
  for (let i = 0; i <= 100; i += 10) names.push(i + "PCHealth");
  for (const c of "0123456789+") names.push("InterfaceNumber" + c);
  return preload(names);
}

function blit(ctx, name, x, y) {
  const im = sprite(name);
  if (im) ctx.drawImage(im, x, y);
  return im;
}

function icon(ctx, name, x, y, sz) {
  const im = sprite(name);
  if (!im) return;
  const s = Math.min(sz / im.width, sz / im.height);
  const w = Math.max(1, Math.floor(im.width * s)), h = Math.max(1, Math.floor(im.height * s));
  ctx.drawImage(im, x + Math.floor((sz - w) / 2), y + Math.floor((sz - h) / 2), w, h);
}

const greyCache = new Map();
function greyed(name) {
  let c = greyCache.get(name);
  if (c) return c;
  const im = sprite(name);
  if (!im) return null;
  c = document.createElement("canvas");
  c.width = im.width; c.height = im.height;
  const x = c.getContext("2d");
  x.drawImage(im, 0, 0);
  const d = x.getImageData(0, 0, c.width, c.height);
  for (let i = 0; i < d.data.length; i += 4) {
    const l = (d.data[i] * 0.3 + d.data[i + 1] * 0.59 + d.data[i + 2] * 0.11) * 0.55 + 20;
    d.data[i] = d.data[i + 1] = d.data[i + 2] = l;
  }
  x.putImageData(d, 0, 0);
  greyCache.set(name, c);
  return c;
}

// ================================================================================================================
// The frame's interface
// ================================================================================================================
export function drawUI(ctx, now) {
  if (!S.me) return;
  if (M.on) { drawTouchUI(ctx, now); return; }
  const { VW, VH } = L;
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, VW, VH);
  ctx.clip();
  drawHurt(ctx, now);
  drawHotbar(ctx);
  drawBanner(ctx, now);
  drawVitals(ctx);
  drawOnline(ctx, now);
  drawHoverTop(ctx);
  drawArena(ctx, now);
  drawWave(ctx, now);
  drawSleep(ctx, now);
  ctx.restore();
  drawMinimap(ctx);
  blit(ctx, "SideBar", VW, 0);
  const mm = sprite("MinimapMarker");
  if (mm) ctx.drawImage(mm, L.mmX - 4, L.mmY - 4);
  drawClock(ctx, now);
  sidebarButton(ctx, L.helpX, L.helpY, "Journal", U.hover === "help", [[126, 77, 63], [160, 104, 80]],
    [[243, 232, 136], [255, 255, 255]], [77, 43, 33]);
  if (S.admin) sidebarButton(ctx, L.helpX, L.helpY + 26, "Admin", U.hover === "admin", [[48, 76, 104], [70, 110, 150]],
    [[210, 230, 250], [255, 255, 255]], [30, 40, 60]);
  const border = sprite("SideBarBorder");
  if (border) ctx.drawImage(border, 0, 0, border.width, VH + 96, VW, 0, border.width, VH + 96);
  drawStats(ctx);
  drawBox(ctx);
  drawInventory(ctx);
  if (S.box.mode) drawResponses(ctx);
  drawChat(ctx);
  drawQuestPopup(ctx);
  if (U.rcm) drawMenu(ctx);
}

function sidebarButton(ctx, x, y, label, hot, fills, inks, edge) {
  roundBox(ctx, x, y, 52, 22, fills[hot ? 1 : 0], edge, 2, 10);
  const w = textWidth(ctx, label, 9, true);
  drawTextMid(ctx, label, x + Math.floor((52 - w) / 2), y, 22, 9, true, inks[hot ? 1 : 0]);
}

// ----- the minimap (sprites\Interface\Minimap<Z>, Config [Minimap])
function minimapGeometry() {
  const z = S.mapZ;
  const name = "Minimap" + z;
  if (!has(name)) {
    // A homestead (made as the game runs, so the asset export has no minimap of it): drawn from its tiles
    const m = S.maps.get(S.mapName);
    if (!m || !isHomeMap(m.name)) return null;
    if (U.minimapZoom <= 0) U.minimapZoom = 1;
    return { name: "live:" + m.name, ps: 4, ox: m.mx, oy: m.my, zoom: U.minimapZoom, live: m };
  }
  let ps = val(configRead("Minimap", "Pixel.Size", "0"));
  const origin = configRead("Minimap", "Origin." + z, "");
  let ox, oy;
  if (origin) { ox = val(word(origin, 1, ",")); oy = val(word(origin, 2, ",")); } else {
    const maps = A.m.maps.filter((n) => +n.split(",")[2] === z).map((n) => n.split(",").map(Number));
    ox = Math.min(...maps.map((m) => m[0])); oy = Math.min(...maps.map((m) => m[1]));
  }
  const [w] = size(name);
  if (ps <= 0) ps = Math.max(1, Math.floor(w / G.xt));
  if (U.minimapZoom <= 0) U.minimapZoom = Math.max(1, 4 / ps);
  return { name, ps, ox, oy, zoom: U.minimapZoom };
}

const mmCacheMini = { key: "", canvas: null, at: 0 };
const wmCache = { key: "", canvas: null, at: 0 };     // (the world map's copy: the unexplored hatched, not black)

function hatchPattern(ctx) {
  // (the world map's "not yet seen": dark brown, hatched like an old map's unknown parts - no land is ever this)
  const t = document.createElement("canvas");
  t.width = t.height = 6;
  const c = t.getContext("2d");
  c.fillStyle = "rgb(46,34,24)";
  c.fillRect(0, 0, 6, 6);
  c.fillStyle = "rgb(72,56,38)";
  for (let i = 0; i < 6; i++) c.fillRect(i, 5 - i, 1, 1);
  return ctx.createPattern(t, "repeat");
}
const liveCache = { key: "", canvas: null, at: 0 };
function liveMinimap(g) {
  // A map's tiles, decor and roofs drawn small (a homestead's minimap); again when it changes, or while pictures load
  const m = g.live;
  const now = performance.now();
  const key = m.name + "|" + m.v;
  if (liveCache.key === key && (liveCache.complete || now - liveCache.at < 1000)) return liveCache.canvas;
  const ps = g.ps;
  const c = liveCache.canvas || document.createElement("canvas");
  c.width = G.xt * ps; c.height = G.yt * ps;
  const x = c.getContext("2d");
  x.imageSmoothingEnabled = true;
  let complete = true;
  for (let ty = 1; ty <= G.yt; ty++) {
    for (let tx = 1; tx <= G.xt; tx++) {
      const [tile, decor, roof] = cellOf(m, tx, ty);
      for (const n of roof ? [roof] : [tile, decor]) {
        if (!n) continue;
        const im = sprite(n);
        if (im) x.drawImage(im, 0, 0, im.width, im.height, (tx - 1) * ps, (ty - 1) * ps, ps, ps);
        else complete = false;
      }
    }
  }
  liveCache.key = key; liveCache.canvas = c; liveCache.at = now; liveCache.complete = complete;
  return c;
}

function minimapImage(g, hatched = false) {
  // The minimap with what you haven't seen blacked out, tile by tile: a tile shows once any of its fog-of-war cells
  // has been uncovered (the same cells that take the black off the world)
  if (g.live) return liveMinimap(g);
  const im = sprite(g.name);
  if (!im) return null;
  const mmCache = hatched ? wmCache : mmCacheMini;
  const key = g.name + "|" + S.explored.size + "|" + (S.exploredVersion || 0) + "|" + fogEnabled() + "|" + fogSeeAll();
  if (mmCache.key === key) return mmCache.canvas;
  const now = performance.now();
  if (mmCache.canvas && mmCache.key.split("|")[0] === g.name && now - mmCache.at < 400) return mmCache.canvas;
  const c = mmCache.canvas && mmCache.canvas.width === im.width && mmCache.canvas.height === im.height ?
    mmCache.canvas : document.createElement("canvas");
  c.width = im.width; c.height = im.height;
  const x = c.getContext("2d");
  x.clearRect(0, 0, c.width, c.height);
  x.drawImage(im, 0, 0);
  if (val(configRead("Minimap", "Blackout", "1")) === 1 && fogEnabled() && !fogSeeAll()) {
    x.fillStyle = "#000";                                // (the minimap: the same black as where there's no map)
    // (the world map: see-through, so the one hatching behind it shows - the same as where there's no map at all)
    const hide = hatched ? (a, b, w, h) => x.clearRect(a, b, w, h) : (a, b, w, h) => x.fillRect(a, b, w, h);
    const ps = g.ps, n = fogCell(), fxt = Math.ceil(G.sw / n);
    for (const name of A.m.maps) {
      const [mx, my, mz] = name.split(",").map(Number);
      if (mz !== S.mapZ) continue;
      const bx = (mx - g.ox) * G.xt * ps, by = (my - g.oy) * G.yt * ps;
      const seen = S.explored.get(name);
      if (seen === "all") continue;
      if (!seen || !seen.size) { hide(bx, by, G.xt * ps, G.yt * ps); continue; }
      for (let ty = 0; ty < G.yt; ty++) {
        const cy0 = Math.floor(ty * G.th / n), cy1 = Math.floor(((ty + 1) * G.th - 1) / n);
        for (let tx = 0; tx < G.xt; tx++) {
          const cx0 = Math.floor(tx * G.tw / n), cx1 = Math.floor(((tx + 1) * G.tw - 1) / n);
          let shown = false;
          for (let cy = cy0; cy <= cy1 && !shown; cy++)
            for (let cx = cx0; cx <= cx1 && !shown; cx++) if (seen.has(cy * fxt + cx + 1)) shown = true;
          if (!shown) hide(bx + tx * ps, by + ty * ps, ps, ps);
        }
      }
    }
  }
  mmCache.key = key;
  mmCache.canvas = c;
  mmCache.at = now;
  return c;
}

// ----- the quest you're following: its marker on the minimap and the world map (one at a time)
function savedTrack() {
  try { return localStorage.getItem("ds.track") || ""; } catch (e) { return ""; }
}

export function trackedQuest() {
  // (one you picked, begun or not, till it is done; else your main quest in hand, else the first in hand; "-": none)
  if (U.tracked === undefined) U.tracked = savedTrack();
  if (U.tracked === "-") return "";
  const active = (S.quests || []).filter((q) => q.status === 0);
  if (U.tracked && (S.quests || []).some((q) => q.title === U.tracked && q.status !== 2)) return U.tracked;   // (begun or not)
  const q = active.find((x) => x.main) || active[0];
  return q ? q.title : "";
}

export function toggleTracked(title) {
  const now = trackedQuest() === title ? "-" : title;
  U.tracked = now;
  try { localStorage.setItem("ds.track", now); } catch (e) { /* */ }
  S.addLocal(now === "-" ? "Not following a quest: no marker on the map." : `Following: ${title} (its place is marked on the map).`,
    "black");
}

function trackedMarks() {
  const t = trackedQuest();
  return t ? (S.marks || []).filter((mk) => mk[3] === t) : [];
}

function drawMinimap(ctx) {
  const g = minimapGeometry();
  const half = L.mmSize / 2;
  const vx = L.mmX - half, vy = L.mmY - half;
  ctx.fillStyle = "#000";
  if (M.on) { ctx.beginPath(); ctx.arc(L.mmX, L.mmY, half, 0, 6.283); ctx.fill(); }
  else ctx.fillRect(vx, vy, L.mmSize, L.mmSize);
  if (!g || !S.pos) return;
  const im = minimapImage(g);
  if (!im) return;
  const k = g.ps * g.zoom;
  const pw = size(S.pos.i);
  const u = ((S.pos.dx + pw[0] / 2) / G.tw - g.ox * G.xt) * k;
  const v = ((S.pos.dy + pw[1] / 2) / G.th - g.oy * G.yt) * k;
  ctx.save();
  ctx.beginPath();
  if (M.on) ctx.arc(L.mmX, L.mmY, half, 0, 6.283);
  else ctx.rect(vx, vy, L.mmSize, L.mmSize);
  ctx.clip();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(im, Math.round(L.mmX - u), Math.round(L.mmY - v), im.width * g.zoom, im.height * g.zoom);
  if (U.markers) {
    for (const [m, qx, qy] of trackedMarks()) {
      const [mx, my, mz] = String(m).split(",").map(Number);
      if (mz !== S.mapZ) continue;
      const px = Math.round(L.mmX - u + ((mx - g.ox) * G.xt + qx - 0.5) * k);
      const py = Math.round(L.mmY - v + ((my - g.oy) * G.yt + qy - 0.5) * k);
      if (px < vx + 5 || px > vx + L.mmSize - 6 || py < vy + 5 || py > vy + L.mmSize - 6) continue;
      cross(ctx, [0, 0, 0], px, py, 5, 2);
      cross(ctx, [255, 220, 40], px, py, 4, 1);
    }
  }
  for (const p of S.where || []) {                // the other players: a blue dot each (at the edge, if far off)
    if (p.name === S.name || p.z !== S.mapZ) continue;
    let px = L.mmX - u + (p.x / G.tw - g.ox * G.xt) * k;
    let py = L.mmY - v + (p.y / G.th - g.oy * G.yt) * k;
    const dx = px - L.mmX, dy = py - L.mmY, far = Math.hypot(dx, dy), edge = L.mmSize / 2 - 8;
    if (far > edge) { px = L.mmX + dx / far * edge; py = L.mmY + dy / far * edge; }
    ctx.fillStyle = "#000";
    ctx.beginPath(); ctx.arc(Math.round(px), Math.round(py), 4.5, 0, 6.283); ctx.fill();
    ctx.fillStyle = far > edge ? "rgb(120,170,220)" : "rgb(90,190,255)";
    ctx.beginPath(); ctx.arc(Math.round(px), Math.round(py), 3.2, 0, 6.283); ctx.fill();
  }
  const gr = S.me.grave;                          // your grave: a gravestone on the minimap (at its edge, if far off)
  if (gr && gr.map) {
    const [mx, my, mz] = String(gr.map).split(",").map(Number);
    if (mz === S.mapZ) {
      let px = L.mmX - u + ((mx - g.ox) * G.xt + (gr.x + 16) / G.tw) * k;
      let py = L.mmY - v + ((my - g.oy) * G.yt + (gr.y + 28) / G.th) * k;
      const dx = px - L.mmX, dy = py - L.mmY, far = Math.hypot(dx, dy), edge = L.mmSize / 2 - 10;
      if (far > edge) { px = L.mmX + dx / far * edge; py = L.mmY + dy / far * edge; }
      const stone = sprite("Gravestone");
      if (stone) ctx.drawImage(stone, Math.round(px - 7), Math.round(py - 9), 14, 18);
      else cross(ctx, [230, 230, 230], Math.round(px), Math.round(py), 4, 1);
    }
  }
  ctx.restore();
}

// ----- the world map (M): the level you're on as far as you've seen it, its places named, where your quest is
export function drawWorldMap(ctx, now) {
  const W = L.VW, H = L.VH;
  ctx.fillStyle = "rgba(12,8,6,0.94)";
  ctx.fillRect(0, 0, W, H);
  const levelName = S.mapZ === 0 ? "The world" : S.mapZ < 0 ? "Underground" : "Above ground";
  const travel = U.worldMap === "stones" && U.stones;
  drawText(ctx, travel ? "Shardstones" : "World map", 24, 12, 16, true, [255, 230, 140]);
  drawText(ctx, travel ? `From the ${U.stones.title} shardstone · ${U.stones.cost} Shards a journey` : levelName, 24, 34, 9,
    false, [212, 191, 126]);
  centreText(ctx, W / 2, H - 24, travel ? (M.on ? "Tap a shardstone to travel there · tap elsewhere to stay" :
    "Click a shardstone to travel there · Esc to stay") : M.on ? "Tap to close" : "M or Esc: close", 8, false,
    [212, 191, 126]);
  U.stoneHits = [];
  const g = minimapGeometry();
  const im = g && !g.live ? minimapImage(g, true) : null;
  if (!im) { centreText(ctx, W / 2, H / 2, "No map of this place.", 12, true, [212, 191, 126]); return; }
  const top = 56, bottom = 40, side = 30;
  // A level under or over the world is drawn in the world's frame, at the world's scale, so a cave lies just where
  // the land over it is (and stairs line up); a level of its own (worldFrame: the arena, the Shardrealm...) fills it
  const f = worldFrame(g, im);
  const fit = Math.min((W - 2 * side) / f.w, (H - top - bottom) / f.h);
  const iw = f.w * fit, ih = f.h * fit;
  const ox = Math.round((W - iw) / 2), oy = Math.round(top + (H - top - bottom - ih) / 2);
  // (zoomed in: the box stays, the map under it is bigger, its middle where you were when it opened, then dragged)
  const per0 = g.ps;
  const fx0 = f.dx - g.ox * G.xt * per0, fy0 = f.dy - g.oy * G.yt * per0;   // (a world tile 0,0 in the frame)
  if (now - U.wmShown > 300) {
    U.wmZoom = 1;
    const pw = S.pos ? size(S.pos.i) : [0, 0];
    U.wmCx = S.pos ? fx0 + (S.pos.dx + pw[0] / 2) / G.tw * per0 : f.w / 2;
    U.wmCy = S.pos ? fy0 + (S.pos.dy + pw[1] / 2) / G.th * per0 : f.h / 2;
  }
  U.wmShown = now;
  U.wm = { ox, oy, iw, ih, fit, fw: f.w, fh: f.h };
  wmClamp();
  const k = fit * U.wmZoom;
  const cx0 = ox + iw / 2 - U.wmCx * k, cy0 = oy + ih / 2 - U.wmCy * k;
  roundBox(ctx, ox - 6, oy - 6, iw + 12, ih + 12, [30, 20, 14], [150, 104, 62], 2, 8);
  ctx.fillStyle = hatchPattern(ctx);              // (where there's no map at all looks just as unexplored land does)
  ctx.fillRect(ox - 4, oy - 4, iw + 8, ih + 8);
  ctx.save();
  ctx.beginPath(); ctx.rect(ox - 4, oy - 4, iw + 8, ih + 8); ctx.clip();
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(im, cx0 + f.dx * k, cy0 + f.dy * k, im.width * k, im.height * k);
  ctx.restore();
  drawWorldMapOver(ctx, now, g, f, k, cx0, cy0, ox, oy, iw, ih, travel);
  ctx.restore();
  drawZoomButtons(ctx);
}

// ----- the world map's zoom: the wheel or a pinch about a point, the + and - buttons about the middle, a drag
const WM_MOST = 8;
function wmClamp() {
  const w = U.wm;
  if (!w) return;
  U.wmZoom = clamp(U.wmZoom, 1, WM_MOST);
  const k = w.fit * U.wmZoom, hx = w.iw / 2 / k, hy = w.ih / 2 / k;
  U.wmCx = clamp(U.wmCx, hx, Math.max(hx, w.fw - hx));
  U.wmCy = clamp(U.wmCy, hy, Math.max(hy, w.fh - hy));
}

export function wmZoomAt(factor, x, y) {
  const w = U.wm;
  if (!w) return;
  if (x === undefined) {                         // (the buttons: about you, if you're on it, else the middle)
    const you = w.you && wmInBox(...w.you);
    [x, y] = you ? w.you : [w.ox + w.iw / 2, w.oy + w.ih / 2];
  }
  const k = w.fit * U.wmZoom;
  const px = U.wmCx + (x - w.ox - w.iw / 2) / k, py = U.wmCy + (y - w.oy - w.ih / 2) / k;
  U.wmZoom = clamp(U.wmZoom * factor, 1, WM_MOST);
  const k2 = w.fit * U.wmZoom;
  U.wmCx = px - (x - w.ox - w.iw / 2) / k2;
  U.wmCy = py - (y - w.oy - w.ih / 2) / k2;
  wmClamp();
}

export function wmPan(dx, dy) {
  const w = U.wm;
  if (!w) return;
  const k = w.fit * U.wmZoom;
  U.wmCx -= dx / k;
  U.wmCy -= dy / k;
  wmClamp();
}

export function wmInBox(x, y) {
  const w = U.wm;
  return !!w && x >= w.ox && x <= w.ox + w.iw && y >= w.oy && y <= w.oy + w.ih;
}

function zoomButtons() {
  const s = M.on ? 34 : 24, y = 12, x = L.VW - 12 - s;
  return [["in", x - s - 6, y, s], ["out", x, y, s]];
}

export function wmButtonAt(x, y) {
  // (the world map's + and - : "in", "out" or "")
  const b = zoomButtons().find(([, bx, by, s]) => x >= bx && x <= bx + s && y >= by && y <= by + s);
  return b ? b[0] : "";
}

function drawZoomButtons(ctx) {
  for (const [what, bx, by, s] of zoomButtons()) {
    const off = what === "in" ? U.wmZoom >= WM_MOST : U.wmZoom <= 1;
    roundBox(ctx, bx, by, s, s, [40, 26, 20], [150, 104, 62], 2, 6);
    const col = off ? "rgb(110,90,70)" : "rgb(255,230,140)";
    const c = s / 2, arm = Math.round(s * 0.28);
    ctx.fillStyle = col;
    ctx.fillRect(bx + c - arm, by + c - 1.5, arm * 2, 3);
    if (what === "in") ctx.fillRect(bx + c - 1.5, by + c - arm, 3, arm * 2);
  }
}

function drawWorldMapOver(ctx, now, g, f, k, cx0, cy0, ox, oy, iw, ih, travel) {
  const per = g.ps * k;                            // (screen pixels a map tile)
  const toScreen = (gx, gy) => [cx0 + f.dx * k + (gx / G.tw - g.ox * G.xt) * per,
    cy0 + f.dy * k + (gy / G.th - g.oy * G.yt) * per];
  const seen = (name) => !fogEnabled() || fogSeeAll() || S.explored.has(name);
  // the names of the places you've been: towns first, then the lands, then the rest, each where it doesn't cover
  // another (above its dot, below, right, left); a place with no room left keeps its dot, its name for a bigger map
  const style = { t: [11, true, [255, 238, 176]], r: [10, true, [214, 180, 110]], p: [8, true, [226, 216, 196]] };
  const stoneNames = new Set(travel ? U.stones.stones.map((s) => s.t.toUpperCase()) : []);   // (named by their stone)
  const shown = (S.labels || []).filter((l) => l.z === S.mapZ && seen(l.m) && !stoneNames.has(l.n.toUpperCase())).map((l) => {
    const [sx, sy] = toScreen(l.x, l.y);
    return { l, sx, sy };
  }).filter((d) => d.sx >= ox && d.sx <= ox + iw && d.sy >= oy && d.sy <= oy + ih);
  const taken = shown.filter((d) => d.l.k !== "r").map((d) => [d.sx - 3, d.sy - 3, d.sx + 3, d.sy + 3]);
  if (S.pos) {                                     // (you, and your name: drawn over the map last)
    const pw = size(S.pos.i);
    const [px, py] = toScreen(S.pos.dx + pw[0] / 2, S.pos.dy + pw[1] / 2);
    taken.push([px - 12, py - 6, px + 12, py + 19]);
  }
  const free = (b) => taken.every((t) => b[2] <= t[0] || b[0] >= t[2] || b[3] <= t[1] || b[1] >= t[3]);
  const clear = (b) => b[0] >= ox - 4 && b[2] <= ox + iw + 4 && b[1] >= oy - 4 && b[3] <= oy + ih + 4 && free(b);
  const order = { t: 0, r: 1, p: 2 };
  for (const { l, sx, sy } of [...shown].sort((a, b) => (order[a.l.k] ?? 2) - (order[b.l.k] ?? 2))) {
    const [size, bold, col] = style[l.k] || style.p;
    const text = l.k === "r" ? l.n.toUpperCase() : l.n;
    const w = textWidth(ctx, text, size, bold), h = size + 3;
    const spots = l.k === "r"
      ? [[sx, sy - h / 2], [sx, sy - h * 1.5], [sx, sy + h / 2], [sx - w / 3, sy - h / 2], [sx + w / 3, sy - h / 2]]
      : [[sx, sy - h - 4], [sx, sy + 5], [sx + w / 2 + 6, sy - h / 2], [sx - w / 2 - 6, sy - h / 2],
        [sx + w / 2 + 4, sy - h - 2], [sx - w / 2 - 4, sy - h - 2], [sx + w / 2 + 4, sy + 3], [sx - w / 2 - 4, sy + 3]];
    const box = ([cx, ty]) => [cx - w / 2 - 1, ty, cx + w / 2 + 1, ty + h];
    const spot = spots.find((s) => clear(box(s))) ||   // (a town is always named: past the frame, if need be)
      (l.k === "t" ? spots.find((s) => free(box(s))) || spots[0] : null);
    if (l.k !== "r") {
      ctx.fillStyle = "rgb(30,20,12)";
      ctx.beginPath(); ctx.arc(sx, sy, 3, 0, 6.283); ctx.fill();
      ctx.fillStyle = rgb(col);
      ctx.beginPath(); ctx.arc(sx, sy, 2, 0, 6.283); ctx.fill();
    }
    if (!spot) continue;
    const [cx, ty] = spot;
    taken.push([cx - w / 2 - 1, ty, cx + w / 2 + 1, ty + h]);
    centreText(ctx, cx + 1, ty + 1, text, size, bold, [10, 6, 4]);
    centreText(ctx, cx, ty, text, size, bold, col);
  }
  const pulse = 0.5 + 0.5 * Math.sin(now / 250);
  if (travel) { drawStones(ctx, toScreen, pulse, ox, oy, iw, ih); return; }
  // the quest you're following: where it wants you next
  let named = false;
  for (const [m, qx, qy, title] of trackedMarks()) {
    const [mx, my, mz] = String(m).split(",").map(Number);
    if (mz !== S.mapZ) continue;
    const [sx, sy] = toScreen((mx * G.xt + qx - 0.5) * G.tw, (my * G.yt + qy - 0.5) * G.th);
    ctx.fillStyle = `rgba(255,214,90,${0.25 + 0.3 * pulse})`;
    ctx.beginPath(); ctx.arc(sx, sy, 9 + 3 * pulse, 0, 6.283); ctx.fill();
    cross(ctx, [0, 0, 0], Math.round(sx), Math.round(sy), 6, 2);
    cross(ctx, [255, 220, 40], Math.round(sx), Math.round(sy), 5, 1);
    if (!named) {
      centreText(ctx, sx + 1, sy + 13, title, 8, true, [10, 6, 4]);
      centreText(ctx, sx, sy + 12, title, 8, true, [255, 220, 90]);
      named = true;
    }
  }
  // the others, and you
  for (const p of S.where || []) {
    if (p.name === S.name || p.z !== S.mapZ) continue;
    const [sx, sy] = toScreen(p.x, p.y);
    ctx.fillStyle = "#000"; ctx.beginPath(); ctx.arc(sx, sy, 5, 0, 6.283); ctx.fill();
    ctx.fillStyle = "rgb(90,190,255)"; ctx.beginPath(); ctx.arc(sx, sy, 3.5, 0, 6.283); ctx.fill();
    centreText(ctx, sx, sy + 6, p.name, 7, true, [170, 220, 255]);
  }
  if (S.pos) {
    const pw = size(S.pos.i);
    const [sx, sy] = toScreen(S.pos.dx + pw[0] / 2, S.pos.dy + pw[1] / 2);
    if (U.wm) U.wm.you = [sx, sy];
    ctx.fillStyle = "#000"; ctx.beginPath(); ctx.arc(sx, sy, 6, 0, 6.283); ctx.fill();
    ctx.fillStyle = `rgb(255,${Math.round(90 + 120 * pulse)},90)`; ctx.beginPath(); ctx.arc(sx, sy, 4.5, 0, 6.283); ctx.fill();
    centreText(ctx, sx + 1, sy + 9, "You", 8, true, [10, 6, 4]);
    centreText(ctx, sx, sy + 8, "You", 8, true, [255, 240, 220]);
  }
}

// The world map's frame for this level's picture im: {w, h} in the picture's pixels, and where the picture goes in it
// (dx, dy). The levels of their own (CLAUDE.md: the arena 10, the dragon's lair -9, the Shardrealm -10, the Shifting
// Deep -11 down; homesteads have no picture) are just their picture; the others share the surface's frame (both
// pictures' extents together).
function worldFrame(g, im) {
  const own = { w: im.width, h: im.height, dx: 0, dy: 0 };
  if (S.mapZ === 0 || S.mapZ >= 10 || S.mapZ <= -9 || !has("Minimap0")) return own;
  const origin = configRead("Minimap", "Origin.0", "");
  if (!origin) return own;
  const sx = val(word(origin, 1, ",")), sy = val(word(origin, 2, ","));
  const [sw, sh] = size("Minimap0");
  const mw = G.xt * g.ps, mh = G.yt * g.ps;          // (a map's pixels)
  const x0 = Math.min(g.ox * mw, sx * mw), y0 = Math.min(g.oy * mh, sy * mh);
  const x1 = Math.max(g.ox * mw + im.width, sx * mw + sw), y1 = Math.max(g.oy * mh + im.height, sy * mh + sh);
  return { w: x1 - x0, h: y1 - y0, dx: g.ox * mw - x0, dy: g.oy * mh - y0 };
}

// ----- the travel map's shardstones (the ones you've activated), and the ways home: what's clicked is in U.stoneHits
function drawStones(ctx, toScreen, pulse, ox, oy, iw, ih) {
  const r = M.on ? 16 : 11;                        // (a finger's reach on the phone)
  for (const s of U.stones.stones) {
    if (s.z !== S.mapZ) continue;
    const [sx, sy] = toScreen(s.x, s.y);
    const hot = U.stoneHover === s.k;
    if (sx < ox - r || sx > ox + iw + r || sy < oy - r || sy > oy + ih + r) continue;   // (zoomed in: off the box)
    if (!s.here) U.stoneHits.push({ k: s.k, x: sx, y: sy, r, t: s.t });
    const glow = s.here ? [255, 214, 90] : [120, 200, 255];
    ctx.fillStyle = `rgba(${glow.join(",")},${(hot ? 0.45 : 0.22) + 0.2 * pulse})`;
    ctx.beginPath(); ctx.arc(sx, sy, (hot ? 11 : 8) + 2 * pulse, 0, 6.283); ctx.fill();
    const d = hot ? 7 : 5;                          // (a diamond: the rune)
    ctx.fillStyle = "#000";
    ctx.beginPath(); ctx.moveTo(sx, sy - d - 1); ctx.lineTo(sx + d + 1, sy); ctx.lineTo(sx, sy + d + 1); ctx.lineTo(sx - d - 1, sy); ctx.fill();
    ctx.fillStyle = s.here ? "rgb(255,226,120)" : "rgb(200,240,255)";
    ctx.beginPath(); ctx.moveTo(sx, sy - d); ctx.lineTo(sx + d, sy); ctx.lineTo(sx, sy + d); ctx.lineTo(sx - d, sy); ctx.fill();
    const label = s.here ? `${s.t} (you're here)` : s.t;     // (every stone named: a phone has no hover)
    centreText(ctx, sx + 1, sy + d + 5, label, hot ? 10 : 9, true, [10, 6, 4]);
    centreText(ctx, sx, sy + d + 4, label, hot ? 10 : 9, true, s.here ? [255, 230, 140] : hot ? [255, 255, 255] : [220, 245, 255]);
  }
  // (your homestead, and the homesteads you may visit: a stone's journey to an anchored pocket - homes.py)
  const ways = [];
  if (U.stones.home) ways.push(["home", "Your homestead"]);
  if (U.stones.visit) ways.push(["visit", "Visit a homestead..."]);
  let bx = ox + 8;
  const bh = M.on ? 34 : 24, by = oy + ih - bh - 8;
  for (const [k, label] of ways) {
    const bw = textWidth(ctx, label, 10, true) + 24;
    const hot = U.stoneHover === k;
    roundBox(ctx, bx, by, bw, bh, hot ? [70, 52, 110] : [40, 30, 64], [170, 150, 230], 2, 6);
    drawTextMid(ctx, label, bx + 12, by, bh, 10, true, [236, 228, 255]);
    U.stoneHits.push({ k, box: [bx, by, bw, bh], t: label });
    bx += bw + 10;
  }
  if (!U.stones.stones.some((s) => !s.here) && !ways.length) {
    centreText(ctx, ox + iw / 2, oy + ih - 22, "No other shardstone knows you yet.", 10, true, [212, 191, 126]);
  }
}

export function stoneAt(x, y) {
  // The travel map's stone (or way home) under x,y: its key, or ""
  for (const h of U.stoneHits) {
    if (h.box ? x >= h.box[0] && x <= h.box[0] + h.box[2] && y >= h.box[1] && y <= h.box[1] + h.box[3]
      : Math.hypot(x - h.x, y - h.y) <= h.r) return h.k;
  }
  return "";
}

export function minimapHit(x, y) {
  // (on the minimap's face, not its + and - buttons: it opens the world map)
  return Math.hypot(x - L.mmX, y - L.mmY) < L.mmSize / 2 - 8;
}

function cross(ctx, col, px, py, arm, half) {
  ctx.fillStyle = rgb(col);
  ctx.fillRect(px - arm, py - half, 2 * arm + 1, 2 * half + 1);
  ctx.fillRect(px - half, py - arm, 2 * half + 1, 2 * arm + 1);
}

export function changeMinimapZoom(f) {
  const g = minimapGeometry();
  if (!g) return;
  const n = g.ps * g.zoom * f;
  if (n < 1 || n > 32) return;
  U.minimapZoom *= f;
}

export function clockRect() { return [L.mmX - 11, 1, 22, 22]; }

function drawClock(ctx, now) {
  if (!S.clock.on) return;
  const [x, y] = clockRect();
  const cx = x + 11, cy = y + 11;
  const t = dayFraction(now);
  ctx.fillStyle = "rgb(34,22,14)";
  ctx.beginPath(); ctx.arc(cx, cy, 11, 0, 6.283); ctx.fill();
  ctx.strokeStyle = "rgb(214,170,70)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, 10.5, 0, 6.283); ctx.stroke();
  if (isNight(t)) {
    ctx.fillStyle = "rgb(226,228,240)";
    ctx.beginPath(); ctx.arc(cx, cy, 7, 0, 6.283); ctx.fill();
    ctx.fillStyle = "rgb(34,22,14)";
    ctx.beginPath(); ctx.arc(cx + 3, cy - 2, 6, 0, 6.283); ctx.fill();
  } else {
    const k = Math.sin(Math.PI * (t - 0.21) / 0.62);
    const col = `rgb(255,${Math.round(170 + 70 * k)},${Math.round(60 + 60 * k)})`;
    ctx.strokeStyle = col; ctx.fillStyle = col;
    for (let i = 0; i < 8; i++) {
      const a = i * Math.PI / 4;
      ctx.beginPath();
      ctx.moveTo(cx + 6 * Math.cos(a), cy + 6 * Math.sin(a));
      ctx.lineTo(cx + 9 * Math.cos(a), cy + 9 * Math.sin(a));
      ctx.stroke();
    }
    ctx.beginPath(); ctx.arc(cx, cy, 5, 0, 6.283); ctx.fill();
  }
}

// ----- the Stats box: Stats, Gear, Quests
function drawStats(ctx) {
  const x0 = L.statX, y0 = L.statY;
  ctx.save();
  ctx.translate(x0, y0);
  const bg = sprite("StatBox");
  if (bg) ctx.drawImage(bg, 0, 0);
  else { ctx.fillStyle = "rgb(51,34,27)"; ctx.fillRect(0, 0, 224, 200); }
  if (U.statsView === 1) drawGear(ctx);
  else if (U.statsView === 2) drawQuestsTab(ctx);
  else drawSkillsTab(ctx);
  ctx.fillStyle = "rgb(51,31,25)";
  ctx.fillRect(28, 13, 170, 27);
  [[31, 81, "Stats"], [84, 135, "Gear"], [138, 194, "Quests"]].forEach(([x1, x2, label], t) => {
    const on = t === U.statsView;
    ctx.fillStyle = on ? "rgb(126,77,63)" : "rgb(61,40,31)";
    ctx.fillRect(x1, 15, x2 - x1 + 1, 22);
    ctx.strokeStyle = "rgb(126,77,63)";
    ctx.lineWidth = 1;
    ctx.strokeRect(x1 + 0.5, 15.5, x2 - x1, 21);
    const w = textWidth(ctx, label, 9, true);
    drawTextMid(ctx, label, x1 + Math.floor((x2 - x1 + 1 - w) / 2), 15, 22, 9, true, on ? TAB_TEXT : [190, 160, 110]);
  });
  ctx.restore();
}

export function skillShown(i) {
  const name = A.m.skills[i - 1] || "";
  return name.toUpperCase() !== "HITPOINTS" && !(S.me.skill_off || [])[i - 1];
}

export function skillOfRow(row) {
  for (let i = 1; i <= A.m.skills.length; i++) {
    if (skillShown(i) && --row === 0) return i;
  }
  return 0;
}

export function statTileRect(k) {
  // (tile 2 on: the skills, three to a row; your health and Shards are top left of the view)
  const j = k - 2;
  return [29 + (j % 3) * 56, U.statRowTop + Math.floor(j / 3) * U.statRowH, 54];
}

export function statTileAt(px, py) {
  if (U.statRowH <= 0) return -1;
  for (let k = 2; k < 2 + 3 * U.statRows; k++) {
    const [x, y, w] = statTileRect(k);
    if (px >= x && px < x + w && py >= y && py < y + U.statRowH) return k;
  }
  return -1;
}

const maxLevel = () => Math.max(2, Math.floor(val(configRead("Gameplay", "Skill.Max.Level", "25"))));
export const levelOfXp = (xp) => Math.min(maxLevel(), Math.max(1, Math.floor(xp)));

export function levelProgress(xp) {
  const level = levelOfXp(xp);
  if (level >= maxLevel()) return 100;
  const base = xp >= 1 ? level : 0;
  return clamp(Math.floor((xp - base) / (level + 1 - base) * 100), 0, 99);
}

function drawSkillsTab(ctx) {
  const me = S.me, skills = A.m.skills;
  const shown = skills.filter((_, i) => skillShown(i + 1)).length;
  U.statRows = Math.max(1, Math.floor((shown + 2) / 3));
  U.statRowTop = 41;
  U.statRowH = Math.min(33, Math.floor(150 / U.statRows));
  let k = 1;
  skills.forEach((name, i) => {
    if (!skillShown(i + 1)) return;
    k++;
    const lv = levelOfXp(me.xp[i]);
    const now = (me.skill_now || [])[i] ?? lv;
    // (always as it is now out of its usual level, 20/20: drained red, 18/20, or boosted green, 23/20, a potion
    //  or spell boosting your blows counted in)
    const boost = (me.boosts || {})[{ Strength: "attack", Defence: "defence", Channeling: "magic" }[name]] || 0;
    const shown = now + boost;
    const text = `${shown}/${lv}`;
    const colour = shown < lv ? [240, 110, 100] : shown > lv ? [120, 235, 120] : lv >= maxLevel() ? [255, 215, 60] : TAB_TEXT;
    skillTile(ctx, k, configRead("Skills", "Icon." + name, "").trim(), text, colour, levelProgress(me.xp[i]));
  });
}

function skillTile(ctx, k, ic, value, valueColour, progress) {
  const [x, y, w] = statTileRect(k);
  const h = U.statRowH - 2;
  const isz = Math.min(24, h - 4);
  roundBox(ctx, x, y, w, h, [40, 26, 20], [126, 77, 63], 1, 6);
  icon(ctx, ic, x + 3, y + Math.floor((h - isz) / 2), isz);
  let main = value, small = "";
  if (value.includes("/")) { [main, small] = value.split("/"); small = "/" + small; }
  const barY = y + h - 4;
  const left = x + isz + 4, right = x + w - 2, xm = (left + right) / 2;
  const top = y + 2, bottom = barY - 1;
  if (!small) {
    let s = 10;
    while (s > 7 && textWidth(ctx, main, s, true) > right - left) s--;
    shadowCentre(ctx, xm, top, bottom - top, main, s, valueColour);
  } else {
    const big = w > 60 ? 9 : 8, little = w > 60 ? 7 : 6;
    shadowCentre(ctx, xm, top - 1, (bottom - top) / 2 + 1, main, big, valueColour);
    shadowCentre(ctx, xm, top + (bottom - top) / 2 - 1, (bottom - top) / 2 + 1, small, little, [212, 191, 126]);
  }
  const barX = x + isz + 5, barLen = w - isz - 8;
  ctx.fillStyle = "rgb(25,16,12)";
  ctx.fillRect(barX, barY, barLen, 2);
  const bw = Math.floor(barLen * clamp(progress, 0, 100) / 100);
  if (bw > 0) {
    ctx.fillStyle = ic === "Mana" ? "rgb(80,140,255)" : progress >= 100 ? "rgb(255,215,60)" : "rgb(21,171,75)";
    ctx.fillRect(barX, barY, bw, 2);
  }
}

function shadowCentre(ctx, xm, top, h, text, s, col) {
  const w = textWidth(ctx, text, s, true);
  const x = Math.round(xm - w / 2);
  drawTextMid(ctx, text, x + 1, top + 1, h, s, true, [0, 0, 0]);
  drawTextMid(ctx, text, x, top, h, s, true, col);
}

export function durText(name, wear) {
  const m = Math.max(0, Math.floor(val(entityIni(name, "Durability", "0"))));
  if (m <= 0) return "";
  const left = Math.max(0, m - wear);
  return left === 0 ? "broken!" : Math.ceil(100 * left / m) + "%";
}

function wearBar(ctx, name, wear, x, y, w) {
  const m = Math.max(0, Math.floor(val(entityIni(name, "Durability", "0"))));
  if (m <= 0 || wear <= 0) return;
  const k = Math.max(0, (m - wear) / m);
  ctx.fillStyle = "rgb(24,14,10)";
  ctx.fillRect(x + 3, y + w - 5, w - 6, 3);
  ctx.fillStyle = k > 0 ? `rgb(${Math.round(220 - 160 * k)},${Math.round(60 + 150 * k)},40)` : "rgb(200,30,30)";
  ctx.fillRect(x + 3, y + w - 5, k > 0 ? Math.max(1, Math.floor((w - 6) * k)) : w - 6, k > 0 ? 3 : 1);
}

function drawGear(ctx) {
  const me = S.me, box = EQUIP_BOX;
  ctx.fillStyle = "rgb(30,19,15)";
  for (const [a, b] of [[3, 4], [4, 5], [5, 6], [1, 4], [4, 2], [7, 5], [5, 8]]) {
    const ax = equipX(a), ay = equipY(a), bx = equipX(b), by = equipY(b);
    if (ax === bx) ctx.fillRect(ax + box / 2 - 3, ay + box, 6, by - ay - box);
    else ctx.fillRect(ax + box, ay + box / 2 - 3, bx - ax - box, 6);
  }
  for (let s = 1; s <= 8; s++) {
    const x = equipX(s), y = equipY(s);
    const item = me.equipped[s - 1];
    const hot = s === U.equipHover;
    roundBox(ctx, x, y, box, box, hot ? [58, 38, 30] : [40, 26, 20], hot ? [250, 220, 140] : item ? [176, 120, 80] : [110, 74, 58], 1, 8);
    if (item) {
      icon(ctx, item, x + 1, y + 1, box - 2);
      wearBar(ctx, item, me.wear[s - 1], x + 1, y + 1, box - 2);
    } else {
      ctx.save();
      ctx.globalAlpha = 0.25;
      icon(ctx, SLOT_OUTLINES[SLOT_NAMES[s]], x + 3, y + 3, box - 6);
      ctx.restore();
    }
  }
  const [atk, def, mag] = me.totals;
  const totals = [[63, 44, "Attack", atk], [163, 44, "Defence", def]];
  if (mag > 0) totals.push([63, 139, "Magic", mag]);
  for (const [xm, y, label, v] of totals) {
    centreText(ctx, xm, y, label, 7, true, [190, 160, 110]);
    centreText(ctx, xm, y + 10, "+" + lbstr(v), 11, true, TAB_TEXT);
  }
}

export function equipSlotInfo(s) {
  // (the hover box's lines for a Gear slot: what's worn there, its bonuses and its condition)
  const item = S.me.equipped[s - 1];
  if (!item) return `#${SLOT_NAMES[s]}|~Nothing worn here`;
  const lines = ["#" + pretty(item), SLOT_NAMES[s]];
  const bonus = ["Attack", "Defence", "Magic"].map((k) => [k, val(entityIni(item, k, "0"))]).filter(([, v]) => v)
    .map(([k, v]) => `+${lbstr(v)} ${k}`);
  if (bonus.length) lines.push(bonus.join(", "));
  const d = durText(item, S.me.wear[s - 1]);
  if (d) lines.push((d === "broken!" ? "!" : "") + "Condition: " + d);
  return lines.join("|");
}

export const QUESTS_PER_PAGE = 7, QUEST_ROW_TOP = 58, QUEST_ROW_H = 16;
const QUEST_COLOURS = { 0: [255, 214, 90], 1: [160, 140, 118], 2: [120, 205, 105] };

export function questLook(q) {
  if (q.status === 1) return q.needs && q.needs.length ? [[150, 110, 100], "Locked"] : [[110, 200, 235], "Can start"];
  return [QUEST_COLOURS[q.status] || PARCHMENT, { 0: "In progress", 2: "Complete" }[q.status] || ""];
}

export function questPages() { return Math.max(1, Math.ceil(S.quests.length / QUESTS_PER_PAGE)); }

function drawQuestsTab(ctx) {
  const total = S.quests.length;
  U.questsPage = clamp(U.questsPage, 1, questPages());
  if (!total) {
    centreText(ctx, 112, 90, "No quests yet.", 7, true, [212, 191, 126]);
    centreText(ctx, 112, 104, "Talk to people: some will need your help.", 7, true, [170, 150, 120]);
    return;
  }
  const done = S.quests.filter((q) => q.status === 2).length;
  drawText(ctx, fitText(ctx, `Level ${S.level}  -  ${done}/${total} done`, 108, 7, true), 34, 43, 7, true, [212, 191, 126]);
  if (questPages() > 1) {
    roundBox(ctx, 147, 43, 12, 12, U.questsPage > 1 ? TAB_TEXT : [96, 70, 56], null, 0, 4);
    roundBox(ctx, 183, 43, 12, 12, U.questsPage < questPages() ? TAB_TEXT : [96, 70, 56], null, 0, 4);
    centreText(ctx, 153, 42, "<", 7, true, [51, 31, 25]);
    centreText(ctx, 189, 42, ">", 7, true, [51, 31, 25]);
    centreText(ctx, 171, 43, `${U.questsPage}/${questPages()}`, 7, true, [212, 191, 126]);
  }
  const first = (U.questsPage - 1) * QUESTS_PER_PAGE;
  for (let row = 1; row <= QUESTS_PER_PAGE; row++) {
    const q = S.quests[first + row - 1];
    if (!q) break;
    const y = QUEST_ROW_TOP + (row - 1) * QUEST_ROW_H;
    const [c] = questLook(q);
    const dot = { 0: [240, 190, 50], 2: [70, 170, 80] }[q.status] || [70, 160, 205];
    if (row === U.questHover) roundBox(ctx, 30, y, 165, QUEST_ROW_H - 1, [74, 48, 38], c, 1, 6);
    ctx.fillStyle = rgb(q.main ? dot : dot);
    if (q.needs && q.needs.length) padlock(ctx, 39, y + 8, q.main ? [210, 170, 80] : c);
    else if (q.main) {
      ctx.beginPath(); ctx.moveTo(39, y + 3); ctx.lineTo(44, y + 8); ctx.lineTo(39, y + 13); ctx.lineTo(34, y + 8);
      ctx.closePath(); ctx.fill();
    } else { ctx.beginPath(); ctx.arc(39, y + 8, 4, 0, 6.283); ctx.fill(); }
    const followed = q.title === trackedQuest();
    if (followed) {                                // (the quest followed: a gold target at the row's end)
      ctx.strokeStyle = "rgb(255,214,90)"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(188, y + 8, 5, 0, 6.283); ctx.stroke();
      ctx.fillStyle = "rgb(255,214,90)";
      ctx.beginPath(); ctx.arc(188, y + 8, 2, 0, 6.283); ctx.fill();
    }
    const title = fitText(ctx, q.title, followed ? 130 : 142, 8, true);
    const tw = drawText(ctx, title, 49, y + 1, 8, true, c);
    if (q.status === 2) {
      ctx.strokeStyle = "rgb(100,150,90)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(48, y + 7.5); ctx.lineTo(50 + tw, y + 7.5); ctx.stroke();
    }
  }
}

export function padlock(ctx, cx, cy, col) {
  ctx.strokeStyle = rgb(col); ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx - 2, cy - 1); ctx.lineTo(cx - 2, cy - 5); ctx.lineTo(cx + 2, cy - 5); ctx.lineTo(cx + 2, cy - 1);
  ctx.stroke();
  roundBox(ctx, cx - 4, cy - 1, 9, 7, col, null, 0, 2);
}

// ----- the inventory
export function invSlotPos(i) {
  const cols = Math.max(1, val(configRead("Interface", "InventoryItems.Columns", "5")));
  return [L.invX + G.tw * (i % cols), L.invY + G.tw * Math.floor(i / cols)];
}

function digits(ctx, text, x, y) {
  let dx = x;
  for (let ch of text) {
    if (ch === "K" || ch === "M") ch = "+";
    const d = sprite("InterfaceNumber" + ch);
    if (d) { ctx.drawImage(d, dx, y + 2); dx += d.width + 1; }
  }
}

function qtyText(q) {
  if (q === "+" || q === "") return q;
  const n = val(q);
  if (n >= 10000000) return Math.floor(n / 1000000) + "M";
  if (n >= 100000) return Math.floor(n / 1000) + "K";
  return String(q);
}

function slotItem(ctx, name, x, y, qty, { dim = false, badge = "", cross: x2 = false, wear = 0, inv = false,
  badgeInk = null } = {}) {
  const broken = inv && durText(name, wear) === "broken!";
  const im = dim || broken ? greyed(name) : sprite(name);   // (not loaded yet: nothing, till it is)
  if (im) ctx.drawImage(im, x, y);
  if (inv) wearBar(ctx, name, wear, x, y, G.tw);
  if (x2) {
    const x0 = x + G.tw - 11, y0 = y + 1, s = 8;
    for (const [col, w] of [[[40, 8, 6], 4], [[214, 40, 32], 2]]) {
      ctx.strokeStyle = rgb(col); ctx.lineWidth = w;
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + s, y0 + s); ctx.moveTo(x0 + s, y0); ctx.lineTo(x0, y0 + s);
      ctx.stroke();
    }
  }
  if (badge) {
    const w = textWidth(ctx, badge, 7, true) + 4;
    ctx.fillStyle = "rgb(60,18,14)";
    ctx.fillRect(x + G.tw - w, y + G.th - 10, w, 10);
    drawText(ctx, badge, x + G.tw - w + 2, y + G.th - 10, 7, true, badgeInk || [255, 150, 120]);
  }
  const q = qtyText(String(qty));
  if (q !== "1" && q !== "") digits(ctx, q, x, y);
}

function drawInventory(ctx) {
  if (!packShown()) return;
  const shop = S.box.mode === "Shop";
  S.me.inv.forEach(([uid, name, qty, wear], i) => {
    const [x, y] = invSlotPos(i);
    slotItem(ctx, name, x, y, qty, { dim: shop && !canSellHere(name), wear, inv: true });
    if (uid === S.itemInUse) {
      ctx.strokeStyle = rgb(TAB_TEXT); ctx.lineWidth = 1;
      ctx.strokeRect(x - 0.5, y - 0.5, G.tw + 1, G.th + 1);
    }
  });
}

export function invItemAt(x, y) {
  if (!packShown()) return null;
  const inv = S.me?.inv || [];
  for (let i = 0; i < inv.length; i++) {
    const [ix, iy] = invSlotPos(i);
    const [w, h] = size(inv[i][1]);
    if (x >= ix && x < ix + Math.max(w, 1) && y >= iy && y < iy + Math.max(h, 1)) {
      const [u, n, q, wear] = inv[i];
      return { k: T.INVITEM, u, n, q, wear, i };
    }
  }
  return null;
}

// ----- the ActionBox: a conversation, a shop, the bank, crafting
export function boxBackground() {
  // (every box has the conversation's frame: the item lists' own pictures had a close button over the edge;
  // what's inside an item list is drawn here instead)
  return has("AB_Conversation") ? "AB_Conversation" : "AB_Bank";
}

function drawBox(ctx) {
  const b = S.box;
  if (!b.mode) return;
  const bgName = boxBackground();
  const bg = sprite(bgName);
  const [w, h] = size(bgName);
  const x0 = L.abX, y0 = L.abY;
  // (the frame goes on down round the answers: one panel. Its middle - plain planks - is drawn again for the extra)
  const full = h + responseBoxH() - FRAME_LAP;
  if (bg) {
    const foot = 26, band = [64, 140];
    ctx.drawImage(bg, 0, 0, w, h - foot, x0, y0, w, h - foot);
    for (let y = y0 + h - foot; y < y0 + full - foot;) {
      const n = Math.min(band[1] - band[0], y0 + full - foot - y);
      ctx.drawImage(bg, 0, band[0], w, n, x0, y, w, n);
      y += n;
    }
    ctx.drawImage(bg, 0, h - foot, w, foot, x0, y0 + full - foot, w, foot);
    // (the picture's bottom edge is a thin line: its top border, upside down, makes the bottom match the rest)
    // (its right end from the top-left corner, mirrored: the top-right has the close button in it)
    const corner = 60;
    ctx.save();
    ctx.translate(0, y0 + full);
    ctx.scale(1, -1);
    ctx.drawImage(bg, 0, 0, w - corner, BOX_BORDER, x0, 0, w - corner, BOX_BORDER);
    ctx.restore();
    ctx.save();
    ctx.translate(x0 + w, y0 + full);
    ctx.scale(-1, -1);
    ctx.drawImage(bg, 0, 0, corner, BOX_BORDER, 0, 0, corner, BOX_BORDER);
    ctx.restore();
  } else roundBox(ctx, x0, y0, w, full, [51, 34, 27], [126, 77, 63], 2, 10);
  const portrait = /^Player/.test(b.image || "") && S.me.look ? lookImage(b.image, S.me.look) : sprite(b.image);
  const [pw, ph] = size(b.image);
  let titleX, titleY;
  if (b.mode === "Conversation") {
    if (portrait) {
      ctx.save(); ctx.imageSmoothingEnabled = false;
      ctx.drawImage(portrait, x0 + 24, y0 + 20, pw * 2, ph * 2);
      ctx.restore();
    }
    titleX = 24 + Math.max(32, pw) * 2 + 16; titleY = 25;
  } else {
    // the trader (or the chest, the board) in a frame on the left
    roundBox(ctx, x0 + 13, y0 + 44, 46, 52, [30, 19, 14], [150, 104, 62], 2, 8);
    if (portrait) {
      ctx.save(); ctx.imageSmoothingEnabled = false;
      const k = pw <= 24 && ph <= 24 ? 2 : 1;
      ctx.drawImage(portrait, x0 + 36 - Math.floor(pw * k / 2), y0 + 70 - Math.floor(ph * k / 2), pw * k, ph * k);
      ctx.restore();
    }
    titleX = 22; titleY = 23;
  }
  const searchable = ["Shop", "Craft", "Bank"].includes(b.mode);     // (its search box sits at the right of the title)
  const title = searchable ? fitText(ctx, b.title, 120, 12, true) : b.title;
  const tw = drawText(ctx, title, x0 + titleX, y0 + titleY, 12, true, TAB_TEXT);
  const lift = Math.round((fontPx(12) - fontPx(9)) * 0.8);           // (the kind sits on the title's baseline)
  const kind = { Shop: "Shop", Bank: "Bank", Craft: "Crafting", Market: "everyone's goods", Chest: "take what you want" }[b.mode];
  if (kind && !(searchable && tw > 100)) drawText(ctx, "- " + kind, x0 + titleX + tw + 10, y0 + titleY + lift, 9, false, [212, 191, 126]);
  if (b.mode === "Conversation") {
    const maxW = w - titleX - 28;
    let parts = String(b.text).split("|").filter(Boolean);
    // (a notice's first line in capitals - THE OLD BRICK HOUSE - is its heading: gold, and a gap after it)
    let heading = "";
    if (parts.length > 1 && /[A-Z]/.test(parts[0]) && parts[0] === parts[0].toUpperCase()) heading = parts.shift();
    let sz = 9, lineH = 14, lines = [];
    for (sz of [11, 10, 9]) {
      lineH = Math.max(14, fontPx(sz) + 3);
      lines = [];
      for (const part of parts) lines.push(...wrapLines(ctx, part, maxW, sz, true));
      if (lines.length * lineH + (heading ? lineH + 8 : 0) <= h - 64) break;
    }
    let y = 54;
    if (heading) {
      drawText(ctx, heading, x0 + titleX, y0 + y, 11, true, [255, 214, 110]);
      y += lineH + 8;
    }
    for (const ln of lines) {
      if (y + lineH > h - 10) break;
      drawText(ctx, ln, x0 + titleX, y0 + y, sz, true, [250, 240, 210]);
      y += lineH;
    }
    return;
  }
  const cols = Math.min(9, Math.max(1, val(configRead("Interface", "ActionBox.Columns", "9"))));
  const rows = Math.min(3, Math.max(1, val(configRead("Interface", "ActionBox.Rows", "3"))));
  const gap = G.tw + 5;
  // the tray the things sit in, a slot for each place
  roundBox(ctx, x0 + 61, y0 + 40, gap * cols + 6, gap * rows + 6, [26, 16, 12], [150, 104, 62], 2, 8);
  const hover = boxItemAt(U.mx ?? -1, U.my ?? -1);
  for (let n = 0; n < cols * rows; n++) {
    const x = x0 + 64 + gap * (n % cols), y = y0 + 43 + gap * Math.floor(n / cols);
    const hot = hover && b.items[n] && hover.i === b.items[n].i;
    roundBox(ctx, x, y, G.tw + 4, G.th + 4, hot ? [70, 48, 34] : [44, 30, 22], hot ? [236, 196, 92] : [74, 52, 38], 1, 6);
  }
  if (!b.items.length && (b.filter || b.ready)) {
    centreText(ctx, x0 + 64 + gap * cols / 2, y0 + 40 + gap * rows / 2 - 6,
      b.filter ? `Nothing here matches "${b.filter}".` : "Nothing you can make yet.", 10, true, [212, 191, 126]);
  }
  b.items.forEach((it, n) => {
    const x = x0 + 66 + gap * (n % cols), y = y0 + 45 + gap * Math.floor(n / cols);
    // each thing's price on it: the market's (the seller's), a shop's (what it costs here)
    const price = b.mode === "Market" ? (b.prices || [])[it.i] :
      b.mode === "Shop" ? itemPrice(it.name, b.buy_rate || 1.2) : 0;
    slotItem(ctx, it.name, x, y, it.qty, { dim: it.short > 0, badge: it.short ? "Lv" + it.short : price ? price + "g" : "",
      cross: !!(it.short || it.missing), badgeInk: price ? [255, 222, 90] : null });
  });
  // the pages: up and down buttons, and which page this is
  const arrow = (y, up, on) => {
    roundBox(ctx, x0 + 405, y, 20, 18, on ? [74, 50, 36] : [40, 28, 22], on ? [236, 196, 92] : [90, 64, 46], 1, 6);
    ctx.fillStyle = on ? "rgb(250,230,170)" : "rgb(110,84,62)";
    ctx.beginPath();
    if (up) { ctx.moveTo(x0 + 409, y + 13); ctx.lineTo(x0 + 421, y + 13); ctx.lineTo(x0 + 415, y + 5); }
    else { ctx.moveTo(x0 + 409, y + 5); ctx.lineTo(x0 + 421, y + 5); ctx.lineTo(x0 + 415, y + 13); }
    ctx.fill();
  };
  arrow(y0 + 42, true, b.page > 1);
  arrow(y0 + 144, false, b.page < b.pages);
  centreText(ctx, x0 + 415, y0 + 92, `${b.page || 1}/${b.pages || 1}`, 8, true, [212, 191, 126]);
}

export function boxItemAt(x, y) {
  const b = S.box;
  if (!b.mode || b.mode === "Conversation") return null;
  const cols = Math.min(9, Math.max(1, val(configRead("Interface", "ActionBox.Columns", "9"))));
  const gap = G.tw + 5;
  for (let n = 0; n < b.items.length; n++) {
    const ix = L.abX + 66 + gap * (n % cols), iy = L.abY + 45 + gap * Math.floor(n / cols);
    if (x >= ix && x < ix + G.tw && y >= iy && y < iy + G.th) {
      const it = b.items[n];
      return { k: T.RACKITEM, n: it.name, q: it.qty, i: it.i, short: it.short, missing: it.missing,
        price: (b.prices || [])[it.i], seller: (b.sellers || [])[it.i], mine: !!(b.mine || [])[it.i] };
    }
  }
  return null;
}

export function boxRect() {
  if (!S.box.mode) return null;
  const [w, h] = size(boxBackground());
  return [L.abX, L.abY, w, h];
}

export function boxArrow(x, y) {
  if (!S.box.mode || S.box.mode === "Conversation") return 0;
  if (x < L.abX + 406 || x > L.abX + 424) return 0;
  if (y >= L.abY + 43 && y <= L.abY + 59) return -1;
  if (y >= L.abY + 145 && y <= L.abY + 161) return 1;
  return 0;
}

export function boxCloseAt(x, y) {
  return S.box.mode && x >= L.abX + 430 && x <= L.abX + 450 && y >= L.abY + 10 && y <= L.abY + 25;
}

// ----- the answers, inside the box's frame below what it shows: a row each, numbered (press the number, or click)
const RB_TOP = 6, RB_ROW = 24, FRAME_LAP = 0, BOX_BORDER = 17, RB_SIDE = 24;

function responseBoxH() {
  // (the rows, then as much room under the last as over the first, then the frame's bottom border)
  return Math.max(40, RB_TOP + S.box.responses.length * RB_ROW - 4 + RB_TOP + BOX_BORDER);
}

function numberBadge(ctx, cx, cy, text, hot) {
  ctx.fillStyle = hot ? "rgb(236,196,92)" : "rgb(176,124,72)";
  ctx.beginPath(); ctx.arc(cx, cy, 8, 0, 6.283); ctx.fill();
  ctx.strokeStyle = "rgb(60,38,24)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, 8, 0, 6.283); ctx.stroke();
  const tw = textWidth(ctx, text, 8, true);
  drawTextMid(ctx, text, Math.round(cx - tw / 2), cy - 8, 16, 8, true, [40, 24, 14]);
}

function drawResponses(ctx) {
  const b = S.box;
  const [w] = size(boxBackground());
  const x0 = L.rbX, y0 = L.rbY - FRAME_LAP;
  const left = x0 + RB_SIDE, right = x0 + w - RB_SIDE;   // (as far in from the frame on the right as on the left)
  b.responses.forEach((r, i) => {
    const y = y0 + RB_TOP + i * RB_ROW;
    const hot = U.rbHover === i + 1;
    roundBox(ctx, left, y, right - left, RB_ROW - 4, hot ? [76, 52, 36] : [38, 25, 18], hot ? [236, 196, 92] : [110, 78, 52], 1, 8);
    numberBadge(ctx, left + 14, y + (RB_ROW - 4) / 2, String(i + 1), hot);
    drawTextMid(ctx, r, left + 30, y, RB_ROW - 4, 10, true, hot ? [255, 242, 196] : [238, 224, 190]);
  });
}

export function responseAt(x, y) {
  if (!S.box.mode) return 0;
  const [w] = size(boxBackground());
  if (x < L.rbX + RB_SIDE || x > L.rbX + w - RB_SIDE) return 0;
  const top = L.rbY - FRAME_LAP + RB_TOP;
  const n = Math.floor((y - top) / RB_ROW) + 1;
  const inRow = (y - top) % RB_ROW < RB_ROW - 4;
  return y >= top && inRow && n >= 1 && n <= S.box.responses.length ? n : 0;
}

export function responseBoxRect() {
  if (!S.box.mode) return null;
  return [L.rbX, L.rbY - FRAME_LAP, size(boxBackground())[0], responseBoxH()];
}

// ----- the chat bar and the hover box
function drawChat(ctx) {
  // (the bar's picture: its left end, its parchment stretched as wide as the screen, then its scroll arrows and the
  // wood at its right end)
  const y0 = L.chatY, W = L.chatW;
  const bar = sprite("ChatBar");
  ctx.fillStyle = "rgb(212,191,126)";
  ctx.fillRect(0, y0, W, 96);
  if (bar) {
    ctx.drawImage(bar, 0, 0, 10, 96, 0, y0, 10, 96);
    ctx.drawImage(bar, 10, 0, 760, 96, 10, y0, W - 64, 96);
    ctx.drawImage(bar, 770, 0, 30, 96, W - 54, y0, 30, 96);
    ctx.drawImage(bar, 1000, 0, 24, 96, W - 24, y0, 24, 96);
  }
  const lineH = 15;
  let y = y0 + 8;
  for (let i = U.chatLine + 4; i >= U.chatLine; i--) {
    const m = S.messages[i - 1];
    if (m) drawText(ctx, fitText(ctx, m[0], W - 74, 9, false), 10, y, 9, false, colour(m[1]));
    y += lineH;
  }
  drawThumb(ctx);
}

export function chatTrack() { return [L.chatR, L.chatY + 19, 15, 60]; }
export function chatArrow(x, y) {
  // (the chat's scroll arrows: 1 up, -1 down)
  if (x < L.chatR || x > L.chatR + 14) return 0;
  if (y >= L.chatY + 4 && y <= L.chatY + 18) return 1;
  if (y >= L.chatY + 78 && y <= L.chatY + 92) return -1;
  return 0;
}

function drawThumb(ctx) {
  const [tx, ty, tw, th] = chatTrack();
  const most = Math.max(0, S.messages.length - 5), back = Math.min(U.chatLine - 1, most);
  const h = S.messages.length <= 5 || most <= 0 ? th : Math.max(10, Math.floor(th * 5 / S.messages.length));
  const frac = most <= 0 ? 0 : (most - back) / most;
  const r = [tx + 2, ty + Math.floor((th - h) * frac), tw - 4, h];
  roundBox(ctx, r[0], r[1], r[2], r[3], [174, 118, 79], [102, 30, 21], 1, 6);
}

export function scrollChat(n) {
  if (n === 0) U.chatLine = 1;
  else U.chatLine = clamp(U.chatLine + n, 1, Math.max(1, S.messages.length - 4));
}

// What's under the mouse (or the finger), at the top of the view where the eye already is: a heading, then lines in
// their own sizes and colours. A line's first character says how it looks (tips.js): # the name, ~ a hint, ! a need
// not met, + a need met, $ a price. Plain text (the interface's own hover messages) has its first line as the heading.
const QUICK_STYLES = {
  "#": { size: 11, bold: true, col: [255, 230, 140] },
  "~": { size: 8, bold: false, col: [212, 191, 126] },
  "!": { size: 9, bold: true, col: [255, 128, 100] },
  "+": { size: 9, bold: true, col: [140, 226, 120] },
  "$": { size: 9, bold: true, col: [255, 208, 90] },
  "": { size: 9, bold: false, col: [236, 226, 206] },
};

const QUICK_MAX = 4;

function drawHoverTop(ctx) {
  U.topY = 8;
  if (!U.qm || U.rcm) return;
  const raw = U.qm.split("|").map((part) => trim(part)).filter(Boolean);
  if (!raw.length) return;
  const styled = raw.map((part, i) => {
    const mark = "#~!+$".includes(part[0]) ? part[0] : "";
    return [QUICK_STYLES[mark || (i === 0 ? "#" : "")], mark ? trim(part.slice(1)) : part];
  });
  if (U.qmKind === "ERROR" || U.qmKind === "WARNING") styled[0][0] = QUICK_STYLES["!"];
  // (between your health top left and the effects or minimap top right)
  const left = 190, right = M.on ? L.mmX - L.mmSize / 2 - 8 : L.VW - 8;
  const width = Math.max(140, Math.min(300, right - left - 24)), room = 76;
  // At most QUICK_MAX lines (wrapped lines count): the name always, then what matters most - a need not met or a
  // wait ("!"), then what it is, then the click hint ("~") - each kept only while it all still fits
  const rank = (i) => (i === 0 ? 0 : { "!": 1, "~": 3 }[raw[i][0]] || 2);
  const wrapped = styled.map(([st, text]) => wrapLines(ctx, text, width, st.size, st.bold));
  const keep = new Set();
  let used = 0;
  for (const i of styled.map((_, i) => i).sort((a, b) => rank(a) - rank(b) || a - b)) {
    const n = wrapped[i].length;
    if (used + n <= QUICK_MAX || keep.size === 0) { keep.add(i); used += n; }
  }
  const chosen = styled.filter((_, i) => keep.has(i));
  let scale = 1, lines = [];
  for (;;) {                                      // (smaller, until it fits)
    lines = [];
    for (const [st, text] of chosen) {
      const size = Math.max(6, Math.round(st.size * scale));
      for (const ln of wrapLines(ctx, text, width, size, st.bold)) lines.push([st, size, ln]);
    }
    const h = lines.reduce((sum, [, size]) => sum + fontPx(size) + 3, 0);
    if (h <= room || scale < 0.7) break;
    scale -= 0.1;
  }
  if (lines.length > QUICK_MAX) {                 // (one very long line on its own: cut short)
    lines = lines.slice(0, QUICK_MAX);
    const last = lines[QUICK_MAX - 1];
    last[2] = last[2].replace(/\s*\S*$/, "") + "...";
  }
  const total = lines.reduce((sum, [, size]) => sum + fontPx(size) + 3, 0) - 3;
  const w = Math.ceil(Math.max(...lines.map(([st, size, ln]) => textWidth(ctx, ln, size, st.bold)))) + 24;
  const cx = Math.round((left + right) / 2), x0 = Math.round(cx - w / 2), y0 = 6;
  roundBox(ctx, x0, y0, w, total + 12, "rgba(24,14,8,0.82)", [126, 77, 63], 1, 10);
  let y = y0 + 6;
  for (const [st, size, ln] of lines) {
    centreText(ctx, cx, y, ln, size, st.bold, st.col);
    y += fontPx(size) + 3;
  }
  U.topY = y0 + total + 18;                       // (the arena's and a wave's banners go under it)
}

// ----- your level, health and Shards: top left of the view
export const VITALS = { x: 8, y: 8, r: 19, barX: 52, barW: 124, barH: 13 };

function vitalBar(ctx, y, frac, fill, icon_, text) {
  const { barX, barW, barH } = VITALS;
  roundBox(ctx, barX, y, barW, barH, "rgba(24,14,8,0.85)", [126, 77, 63], 1, 6);
  const w = Math.floor((barW - 4) * clamp(frac, 0, 1));
  if (w > 0) { ctx.fillStyle = fill; ctx.fillRect(barX + 2, y + 2, w, barH - 4); }
  icon(ctx, icon_, barX - 7, y - 2, 16);
  const tw = textWidth(ctx, text, 8, true);
  drawTextMid(ctx, text, barX + barW - 6 - tw, y, barH, 8, true, [255, 246, 222]);
}

function shardRow(ctx, y, n) {
  // (your Shards: what magic is spent from - a count, not a bar: they don't come back by themselves)
  const { barX, barW, barH } = VITALS;
  roundBox(ctx, barX, y, barW, barH, "rgba(24,14,8,0.85)", [126, 77, 63], 1, 6);
  const im = sprite("Shard");
  if (im) ctx.drawImage(im, barX - 10, y - 4, 20, 20);
  const text = `${n} Shard${n === 1 ? "" : "s"}`;
  drawTextMid(ctx, text, barX + barW - 6 - textWidth(ctx, text, 8, true), y, barH, 8, true, [214, 200, 255]);
}

function drawVitals(ctx) {
  const me = S.me, { x, y, r } = VITALS;
  const lv = me.level || S.level || 1;
  ctx.fillStyle = "rgba(40,27,20,0.92)";
  ctx.beginPath(); ctx.arc(x + r, y + r, r, 0, 6.283); ctx.fill();
  ctx.strokeStyle = "rgb(214,170,70)"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(x + r, y + r, r - 1, 0, 6.283); ctx.stroke();
  centreText(ctx, x + r, y + 7, "LEVEL", 6, true, [212, 191, 126]);
  centreText(ctx, x + r, y + 15, String(lv), 13, true, [255, 230, 140]);
  const hp = me.hp, mhp = Math.max(1, me.max_hp);
  const hpFill = hp < mhp * 0.33 ? "rgb(210,50,36)" : hp < mhp * 0.66 ? "rgb(214,130,36)" : "rgb(196,40,40)";
  vitalBar(ctx, y + 4, hp / mhp, hpFill, configRead("Skills", "Icon.Hitpoints", "Heart") || "Heart", `${hp}/${me.max_hp}`);
  shardRow(ctx, y + 21, me.shards || 0);
}

export function vitalsAt(x, y) {
  // (what's under the mouse in them: "level", "hp", "shards" or "")
  const v = VITALS;
  if (Math.hypot(x - v.x - v.r, y - v.y - v.r) <= v.r) return "level";
  if (x >= v.barX - 8 && x < v.barX + v.barW) {
    if (y >= v.y + 2 && y < v.y + 19) return "hp";
    if (y >= v.y + 19 && y < v.y + 36) return "shards";
  }
  return "";
}

// ----- the right-click menu
export function openMenu(target, sx, sy, worldXY) {
  let verbs = getVerbs(target);
  if (!verbs.length) {
    if (sx < 0 || sy < 0 || sx >= L.VW || sy >= L.VH) return;
    verbs = ["Walk here"];
  }
  verbs = verbs.slice(0, 20);
  const labels = verbs.map((v) => verbLabel(v, target));
  verbs.push("Cancel");
  labels.push("Cancel");
  const ctx = document.createElement("canvas").getContext("2d");
  const font = M.on ? 11 : 9;
  const longest = Math.max(...labels.map((l) => textWidth(ctx, l, font, true)));
  const w = Math.max(M.on ? 150 : 110, Math.ceil(longest) + 28), rowH = M.on ? 28 : 18, rowTop = 6;
  const h = rowTop * 2 + verbs.length * rowH;
  U.rcm = { verbs, labels, target, worldXY, w, h, rowH, rowTop, hi: 0, font,
    x: clamp(sx - 10, 0, L.W - w), y: clamp(sy - 8, 0, L.VH - h) };
}

export function menuRowAt(x, y) {
  const r = U.rcm;
  if (!r) return 0;
  if (x < r.x || x > r.x + r.w || y < r.y + r.rowTop || y >= r.y + r.rowTop + r.verbs.length * r.rowH) return 0;
  return Math.floor((y - r.y - r.rowTop) / r.rowH) + 1;
}

function drawMenu(ctx) {
  const r = U.rcm;
  roundBox(ctx, r.x, r.y, r.w, r.h, [51, 34, 27], [126, 77, 63], 2, 12);
  r.verbs.forEach((v, i) => {
    const ry = r.y + r.rowTop + i * r.rowH;
    let c = TAB_TEXT;
    if (v === "Cancel") {
      c = [190, 160, 110];
      ctx.strokeStyle = "rgb(92,60,46)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(r.x + 10, ry + 0.5); ctx.lineTo(r.x + r.w - 10, ry + 0.5); ctx.stroke();
    }
    if (i + 1 === r.hi) {
      roundBox(ctx, r.x + 5, ry + 1, r.w - 10, r.rowH - 1, [126, 77, 63], [160, 104, 80], 1, 8);
      c = [255, 255, 255];
    }
    drawTextMid(ctx, r.labels[i], r.x + 14, ry + 1, r.rowH - 1, r.font || 9, true, c);
  });
}

// ----- the hotbar
export function hotbarRect(k) {
  const total = 5 * HOTBAR_SIZE + 4 * 4;
  const x0 = Math.floor((L.VW - total) / 2);
  return [x0 + k * (HOTBAR_SIZE + 4), L.VH - HOTBAR_SIZE - 8, HOTBAR_SIZE, HOTBAR_SIZE];   // (along the bottom)
}

export function hotbarAt(x, y) {
  if (S.box.mode || (M.on && (M.chat || M.bag))) return -1;
  for (let k = 0; k < 5; k++) {
    const [hx, hy, w, h] = hotbarRect(k);
    if (x >= hx && x < hx + w && y >= hy && y < hy + h) return k;
  }
  return -1;
}

function held(name) {
  return S.me.inv.filter((i) => i[1] === name).reduce((a, i) => a + i[2], 0);
}

function drawHotbar(ctx) {
  if (S.box.mode || (M.on && (M.chat || M.bag))) return;
  for (let k = 0; k < 5; k++) {
    const [x, y, w, h] = hotbarRect(k);
    ctx.fillStyle = "rgba(24,14,8,0.67)";
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = U.hotHover === k ? "rgba(255,240,180,1)" : "rgba(214,170,70,0.9)";
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    const name = (S.me.hotbar || [])[k];
    if (name) {
      const n = held(name);
      const sp = spellTaught(name), known = sp && knowsSpell(sp);
      const im = n || known ? sprite(name) : greyed(name);
      if (im) ctx.drawImage(im, x + Math.floor((w - im.width) / 2), y + Math.floor((h - im.height) / 2));
      if (known) {                                // (a spell you know: its cooldown, or that you're short of Shards)
        const left = cooldownLeft(sp), total = val(spellAt(sp, "Cooldown", "0")) * 1000;
        if (left > 0 && total > 0) {
          ctx.fillStyle = "rgba(10,6,4,0.62)";
          const ch = Math.ceil(h * Math.min(1, left / total));
          ctx.fillRect(x + 1, y + h - ch - 1, w - 2, ch);
          centreText(ctx, x + w / 2, y + h / 2 - 5, String(Math.ceil(left / 1000)), 10, true, [255, 240, 200]);
        } else if ((S.me.shards || 0) < castCost(sp)) {
          ctx.fillStyle = "rgba(150,30,20,0.45)";
          ctx.fillRect(x + 1, y + 1, w - 2, h - 2);
        }
      } else if (n !== 1) {
        const t = String(n);
        drawText(ctx, t, x + w - 3 - textWidth(ctx, t, 8, true), y + h - 12, 8, true, n ? [255, 240, 200] : [200, 90, 80]);
      }
    }
    drawText(ctx, String(k + 1), x + 3, y + 1, 8, true, [214, 170, 70]);
  }
}

export function hotbarLabel(k) {
  const name = (S.me.hotbar || [])[k];
  if (!name) return `#Hotbar slot ${k + 1}|~Right-click an item in your pack: Hotbar`;
  const sp = spellTaught(name);
  if (sp && knowsSpell(sp)) return [`#${spellTitle(sp)}  (a spell you know)`, ...itemLines(name), `~Press ${k + 1} or click to cast it`].join("|");
  return [`#${pretty(name)}  (${held(name)})`, ...itemLines(name), `~Press ${k + 1} or click to use it`].join("|");
}

// ----- the hurt flash, the level-up banner, who's online, sleeping
function drawHurt(ctx, now) {
  if (now > S.hurtUntil) return;
  for (const [name, x, y, w, h] of [["Hurt_Top", 0, 0, L.VW, 0], ["Hurt_Bottom", 0, -1, L.VW, 0],
    ["Hurt_Left", 0, 0, 0, L.VH], ["Hurt_Right", -1, 0, 0, L.VH]]) {
    const im = sprite(name);
    if (!im) continue;
    const dw = w || im.width, dh = h || im.height;
    ctx.drawImage(im, x < 0 ? L.VW - dw : x, y < 0 ? L.VH - dh : y, dw, dh);
  }
}

export function showBanner(skill, level, now) {
  const b = U.banner;
  if (b && now - b.start < 3400 - 800) {
    b.skills = b.skills.filter((s) => s[0] !== skill).concat([[skill, level]]);
    b.start = Math.max(b.start, now - 300);
  } else U.banner = { start: now, skills: [[skill, level]] };
}

function drawBanner(ctx, now) {
  const b = U.banner;
  if (!b) return;
  const t = now - b.start;
  if (t < 0 || t >= 3400) { U.banner = null; return; }
  const alpha = Math.min(1, t / 220, (3400 - t) / 650);
  const drop = Math.floor(18 * Math.max(0, 1 - t / 260));
  const sub = b.skills.length === 1 ? `Your ${b.skills[0][0]} level is now ${b.skills[0][1]}!` :
    b.skills.map(([s, l]) => `${s} ${l}`).join("   ·   ");
  const w = Math.max(360, textWidth(ctx, sub, 16, true) + 120), h = 96;
  const x0 = Math.floor((L.VW - w) / 2), y0 = Math.floor(L.VH * 0.2) - drop;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = "rgba(24,14,8,0.78)";
  ctx.fillRect(x0, y0, w, h);
  ctx.strokeStyle = "rgb(214,170,70)"; ctx.lineWidth = 2;
  ctx.strokeRect(x0 + 1, y0 + 1, w - 2, h - 2);
  ctx.strokeStyle = "rgb(120,84,30)"; ctx.lineWidth = 1;
  ctx.strokeRect(x0 + 4.5, y0 + 4.5, w - 9, h - 9);
  const title = "LEVEL UP!";
  const tw = textWidth(ctx, title, 30, true);
  for (const [dx, dy] of [[-2, 0], [2, 0], [0, -2], [0, 2], [2, 2]]) drawText(ctx, title, x0 + (w - tw) / 2 + dx, y0 + 10 + dy, 30, true, [40, 22, 8]);
  drawText(ctx, title, x0 + (w - tw) / 2, y0 + 10, 30, true, [255, 214, 92]);
  const ic = configRead("Skills", "Icon." + b.skills[b.skills.length - 1][0].replace(/ /g, "_"), "").trim();
  if (ic) { icon(ctx, ic, x0 + 16, y0 + (h - 40) / 2, 40); icon(ctx, ic, x0 + w - 56, y0 + (h - 40) / 2, 40); }
  const stw = textWidth(ctx, sub, 16, true);
  drawText(ctx, sub, x0 + (w - stw) / 2 + 1, y0 + 59, 16, true, [20, 10, 4]);
  drawText(ctx, sub, x0 + (w - stw) / 2, y0 + 58, 16, true, [246, 232, 196]);
  ctx.restore();
}

function drawOnline(ctx, now) {
  if (!S.players.length) return;
  const names = S.players.map((p) => p.name);
  const text = `Online ${names.length}/${S.max}: ${names.join(", ")}`;
  const w = textWidth(ctx, text, 8, true) + 12;
  const oy = 52;                                  // (under your health and Shards)
  ctx.fillStyle = "rgba(24,14,8,0.55)";
  ctx.fillRect(4, oy, w, 16);
  drawText(ctx, text, 10, oy + 2, 8, true, [243, 232, 136]);
  if (M.app) { U.fullscreenRect = null; return; }  // (the app's already full screen)
  // the full-screen button beside it
  const fx = 4 + w + 6;
  ctx.fillStyle = U.hover === "fullscreen" ? "rgba(126,77,63,0.95)" : "rgba(24,14,8,0.55)";
  ctx.fillRect(fx, oy, 16, 16);
  ctx.strokeStyle = "rgb(243,232,136)"; ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (const [a, b, c, d] of [[3, 7, 3, 3], [3, 3, 7, 3], [13, 9, 13, 13], [13, 13, 9, 13], [9, 3, 13, 3], [13, 3, 13, 7],
    [3, 9, 3, 13], [3, 13, 7, 13]]) { ctx.moveTo(fx + a, oy + b); ctx.lineTo(fx + c, oy + d); }
  ctx.stroke();
  U.fullscreenRect = [fx, oy, 16, 16];
}

function drawArena(ctx, now) {
  // On the arena's sand: you can fight other players here, and they can fight you
  if (!S.me.arena) return;
  const text = "ARENA  -  other players can fight you here";
  const w = textWidth(ctx, text, 10, true) + 28;
  const x = Math.floor((L.VW - w) / 2), y = U.topY;
  const pulse = 0.75 + 0.25 * Math.sin(now / 300);
  roundBox(ctx, x, y, w, 24, `rgba(70,10,8,${0.82 * pulse})`, [214, 90, 60], 2, 10);
  drawTextMid(ctx, text, x + 14, y, 24, 10, true, [255, 220, 170]);
}

function drawWave(ctx, now) {
  // Monsters attacking in waves (the server's waves.py): which wave, how many are left, the time
  const v = S.wave;
  if (!v || !v.name) return;
  const secs = Math.max(0, v.secs - Math.floor((now - v.at) / 1000));
  const clock = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
  const next = v.next ? Math.max(0, v.next - Math.floor((now - v.at) / 1000)) : 0;
  const line2 = next ? `Wave ${v.wave} beaten! Wave ${v.wave + 1} of ${v.waves} in ${next}s`
    : `Wave ${v.wave} of ${v.waves}  -  ${v.left} left  -  ${clock} to hold them off`;
  const w = Math.max(textWidth(ctx, v.name.toUpperCase(), 11, true), textWidth(ctx, line2, 9, true)) + 32;
  const x = Math.floor((L.VW - w) / 2), y = U.topY + (S.me.arena ? 30 : 0);
  const pulse = 0.8 + 0.2 * Math.sin(now / 220);
  roundBox(ctx, x, y, w, 40, `rgba(60,12,6,${0.85 * pulse})`, [230, 120, 40], 2, 10);
  centreText(ctx, x + w / 2, y + 4, v.name.toUpperCase(), 11, true, [255, 200, 120]);
  centreText(ctx, x + w / 2, y + 21, line2, 9, true, [255, 235, 200]);
}

// ----- what potions and spells are doing for you now: an icon each, the time left, and what it does (hover)
const BOOST_WORDS = { attack: (n) => `+${n} Attack`, defence: (n) => `+${n} Defence`,
  magic: (n) => `+${n} spell damage`, sight: () => "far sight" };

// ----- the effects on you (top right of the view): buffs from potions and scrolls, and what's hurting you
const DEBUFFS = {
  Poison: { title: "Poisoned", col: [90, 200, 60] },
  Burn: { title: "Burning", col: [255, 128, 30] },
  Bleed: { title: "Bleeding", col: [210, 30, 30] },
  Chill: { title: "Chilled", col: [120, 196, 255] },
  Weaken: { title: "Weakened", col: [200, 150, 90] },               // (drains: a skill lower for a while)
  Daze: { title: "Dazed", col: [180, 130, 255] },
  Frailty: { title: "Frail", col: [170, 170, 180] },
  Drained: { title: "Drained", col: [240, 110, 100] },              // (a script's Boost.Skill down)
  Boosted: { title: "Boosted", col: [120, 235, 120] },              // (... and up)
};
const EFFECT_BOX = 40, EFFECT_GAP = 6;

function clockText(ms) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function debuffIcon(ctx, name, cx, cy) {
  // (drawn, not a sprite: a drop of poison, a flame, a drop of blood, a snowflake)
  const col = DEBUFFS[name].col, c = `rgb(${col})`;
  ctx.save();
  ctx.fillStyle = c; ctx.strokeStyle = c; ctx.lineWidth = 2;
  if (DEBUFFS[name].title.match(/Weakened|Dazed|Frail|Drained|Boosted/)) {   // (an arrow: down, or up)
    const up = name === "Boosted" ? -1 : 1;
    ctx.beginPath();
    ctx.moveTo(cx - 4, cy - 10 * up); ctx.lineTo(cx + 4, cy - 10 * up); ctx.lineTo(cx + 4, cy + 1 * up);
    ctx.lineTo(cx + 9, cy + 1 * up); ctx.lineTo(cx, cy + 11 * up); ctx.lineTo(cx - 9, cy + 1 * up);
    ctx.lineTo(cx - 4, cy + 1 * up); ctx.closePath();
    ctx.fill();
  } else if (name === "Chill") {
    for (let i = 0; i < 3; i++) {
      const a = i * Math.PI / 3;
      ctx.beginPath();
      ctx.moveTo(cx - 10 * Math.cos(a), cy - 10 * Math.sin(a));
      ctx.lineTo(cx + 10 * Math.cos(a), cy + 10 * Math.sin(a));
      ctx.stroke();
    }
  } else if (name === "Burn") {
    ctx.beginPath();
    ctx.moveTo(cx, cy - 12);
    ctx.quadraticCurveTo(cx + 11, cy, cx + 6, cy + 9);
    ctx.quadraticCurveTo(cx, cy + 12, cx - 6, cy + 9);
    ctx.quadraticCurveTo(cx - 11, cy, cx, cy - 12);
    ctx.fill();
    ctx.fillStyle = "rgb(255,220,90)";
    ctx.beginPath(); ctx.arc(cx, cy + 4, 4, 0, 6.283); ctx.fill();
  } else {                                        // (a drop: poison green, blood red)
    ctx.beginPath();
    ctx.moveTo(cx, cy - 12);
    ctx.quadraticCurveTo(cx + 10, cy + 2, cx, cy + 10);
    ctx.quadraticCurveTo(cx - 10, cy + 2, cx, cy - 12);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.beginPath(); ctx.arc(cx - 3, cy + 1, 2, 0, 6.283); ctx.fill();
  }
  ctx.restore();
}

export function drawBoosts(ctx, now, mx, my) {
  const me = S.me;
  if (!me || !S.boostAt) return;
  const since = now - S.boostAt;
  const shown = [];                               // [kind "buff"/"debuff", key, ms left, lines for the hover]
  const groups = new Map();                       // the potion (or scroll) -> [kinds, ms left]
  for (const [kind, ms] of Object.entries(me.boost_left || {})) {
    const left = ms - since;
    if (left <= 0 || !(me.boosts || {})[kind]) continue;
    const from = (me.boost_from || {})[kind] || "Magic_Burst";
    const g = groups.get(from) || { kinds: [], left: 0 };
    g.kinds.push(kind);
    g.left = Math.max(g.left, left);
    groups.set(from, g);
  }
  for (const [from, g] of groups) {
    shown.push(["buff", from, g.left, [`#${pretty(from)}`, "+" + g.kinds.map((k) => BOOST_WORDS[k](me.boosts[k])).join(", ")]]);
  }
  for (const [name, ms] of Object.entries(me.status_left || {})) {
    const left = ms - since;
    if (left <= 0 || !DEBUFFS[name]) continue;
    shown.push(["debuff", name, left, [`#${DEBUFFS[name].title}`, "!" + ((me.status_info || {})[name] || "")]]);
  }
  if (me.invisible_left && me.invisible_left - since > 0) {           // (tricks.py: unseen, and in another body)
    shown.push(["buff", "Invisibility_Potion", me.invisible_left - since, ["#Invisible", "+No monster sees you (strike or cast and it's over)"]]);
  }
  if (me.swap && me.swap.left - since > 0) {
    shown.push(["buff", me.swap.form + "2a", me.swap.left - since, [`#A ${pretty(me.swap.form).toLowerCase()} for now`, "+You snap back into your own body when it runs out"]]);
  }
  for (const [skill, b] of Object.entries(me.skill_boosts || {})) {   // (a script's Boost.Skill: up or down)
    const left = b.ms - since;
    if (left <= 0) continue;
    const key = b.n < 0 ? "Drained" : "Magic_Burst";
    shown.push([b.n < 0 ? "debuff" : "buff", key, left, [`#${pretty(skill)} ${b.n > 0 ? "+" : ""}${b.n}`,
      (b.n < 0 ? "!" : "+") + `${pretty(skill)} ${b.n > 0 ? "up" : "down"} for a while`]]);
  }
  if (!shown.length) return;
  // right to left from the top right corner of the view: what hurts you first (nearest the corner), then the buffs
  shown.sort((p, q) => (p[0] === q[0] ? 0 : p[0] === "debuff" ? -1 : 1));
  let x = L.boostR - EFFECT_BOX;
  const y = 8;
  let tip = null;
  for (const [kind, key, left, lines] of shown) {
    const bad = kind === "debuff";
    const blink = left < 10000 && Math.floor(now / 300) % 2 === 0;
    const edge = blink ? [255, 220, 120] : bad ? [220, 70, 60] : [120, 230, 120];
    roundBox(ctx, x, y, EFFECT_BOX, EFFECT_BOX + 10, [34, 22, 16, 0.88], edge, 2, 7);
    if (bad) debuffIcon(ctx, key, x + EFFECT_BOX / 2, y + 19);
    else {
      const im = sprite(key) || sprite("Magic_Burst");
      if (im) ctx.drawImage(im, x + 4, y + 3, 32, 32);
    }
    centreText(ctx, x + EFFECT_BOX / 2, y + 36, clockText(left), 8, true, blink ? [255, 200, 120] : [235, 245, 220]);
    if (mx >= x && mx < x + EFFECT_BOX && my >= y && my < y + EFFECT_BOX + 10) {
      tip = [x + EFFECT_BOX, y + EFFECT_BOX + 14, [...lines, `~${clockText(left)} left`]];
    }
    x -= EFFECT_BOX + EFFECT_GAP;
  }
  if (tip) {                                      // the hover: its name, what it does, the time left
    const style = (ln) => (ln[0] === "#" ? [11, true, [255, 230, 140]] : ln[0] === "!" ? [9, true, [255, 150, 130]]
      : ln[0] === "+" ? [9, true, [160, 240, 150]] : [8, false, [212, 191, 126]]);
    const rows = tip[2].filter((ln) => ln.length > 1).map((ln) => [ln.slice(1), ...style(ln)]);
    const w = Math.max(...rows.map(([t, size, bold]) => textWidth(ctx, t, size, bold))) + 16;
    const h = rows.reduce((sum, [, size]) => sum + size + 6, 0) + 8;
    const bx = Math.max(4, tip[0] - w), by = tip[1];
    roundBox(ctx, bx, by, w, h, [20, 14, 10, 0.94], [212, 191, 126], 1, 6);
    let ty = by + 5;
    for (const [t, size, bold, col] of rows) {
      drawText(ctx, t, bx + 8, ty, size, bold, col);
      ty += size + 6;
    }
  }
}

function drawSleep(ctx, now) {
  const s = S.sleep;
  if (!s) return;
  const t = now - s.start;
  let k;
  if (t < s.fade) k = t / s.fade;
  else if (t < s.fade + s.hold) k = 1;
  else k = Math.max(0, 1 - (t - s.fade - s.hold) / s.fade);
  if (t > 2 * s.fade + s.hold) { S.sleep = null; return; }
  ctx.fillStyle = `rgba(0,0,0,${k})`;
  ctx.fillRect(0, 0, L.VW, L.VH);
  if (s.text && k > 0.6) {
    ctx.save();
    ctx.globalAlpha = (k - 0.6) / 0.4;
    centreText(ctx, L.VW / 2, L.VH / 2 - 10, s.text, 16, true, [200, 200, 220]);
    ctx.restore();
  }
}

// ----- the quest checklist, while a quest in the Quests tab is pointed at
function drawQuestPopup(ctx) {
  if (U.statsView !== 2 || U.questHover <= 0) return;
  const q = S.quests[(U.questsPage - 1) * QUESTS_PER_PAGE + U.questHover - 1];
  if (!q) return;
  const w = 300;
  const rows = questRows(ctx, q, w, "Click: open the journal.  Right-click: in the chat.");
  const h = 16 + rows.reduce((a, r) => a + ROW_H[r[0]], 0);
  const rowY = L.statY + QUEST_ROW_TOP + (U.questHover - 1) * QUEST_ROW_H;
  const y = clamp(rowY - 12, 6, L.VH - h - 6);
  drawChecklist(ctx, q, rows, M.on ? Math.max(4, L.statX - w - 6) : L.VW - w - 6, y, w, h);
}

export const ROW_H = { title: 22, giver: 16, heading: 20, item: 15, "item+": 15, footer: 18 };

export function questRows(ctx, q, w, footer) {
  const rows = [["title", q.title, 0, 0]];
  if (q.giver) rows.push(["giver", "Given by " + pretty(q.giver), 0, 0]);
  const steps = q.steps || [];
  const open = steps.map((s, i) => (s[1] ? -1 : i)).filter((i) => i >= 0);
  for (const [heading, items, current] of [["Steps", steps, open.length ? open[open.length - 1] : -1], ["Notes", q.notes || [], -1]]) {
    if (!items.length) continue;
    rows.push(["heading", heading, 0, 0]);
    items.forEach(([text, done], i) => {
      wrapLines(ctx, text, w - 40, 9, i === current).forEach((ln, j) => rows.push([j ? "item+" : "item", ln, done, i === current]));
    });
  }
  if (q.status === 2) rows.push(["heading", "Quest complete!", 0, 0]);
  if (footer) rows.push(["footer", footer, 0, 0]);
  while (rows.length > 6 && rows.reduce((a, r) => a + ROW_H[r[0]], 0) + 20 > 600) {
    const k = rows.findIndex((r) => r[0] === "item" && r[2]);
    if (k < 0) break;
    rows.splice(k, 1);
    while (k < rows.length && rows[k][0] === "item+") rows.splice(k, 1);
  }
  return rows;
}

export function badge(ctx, edge, y, text, col, lock = false) {
  const pad = lock ? 13 : 0;
  const w = textWidth(ctx, text, 9, true) + 16 + pad;
  roundBox(ctx, edge - w, y, w, 18, [40, 26, 20], col, 1, 9);
  if (lock) padlock(ctx, edge - w + 12, y + 8, col);
  drawTextMid(ctx, text, edge - w + 8 + pad, y, 18, 9, true, col);
  return w;
}

export function drawChecklist(ctx, q, rows, x, y, w, h) {
  const [sc, label] = questLook(q);
  roundBox(ctx, x + 4, y + 4, w, h, [0, 0, 0], null, 0, 14);
  roundBox(ctx, x, y, w, h, [46, 30, 23], sc, 2, 14);
  let cy = y + 8;
  for (const [kind, text, done, current] of rows) {
    if (kind === "title") {
      const bw = badge(ctx, x + w - 10, cy + 1, label, sc, !!(q.needs && q.needs.length));
      drawText(ctx, fitText(ctx, text, w - 34 - bw, 11, true), x + 12, cy, 11, true, sc);
    } else if (kind === "giver") drawText(ctx, fitText(ctx, text, w - 24, 8), x + 12, cy, 8, false, [190, 160, 110]);
    else if (kind === "heading") {
      drawText(ctx, text, x + 12, cy + 4, 8, true, text === "Quest complete!" ? sc : [190, 160, 110]);
      ctx.strokeStyle = "rgb(92,60,46)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x + 18 + textWidth(ctx, text, 8, true), cy + 10.5); ctx.lineTo(x + w - 12, cy + 10.5); ctx.stroke();
    } else if (kind === "item" || kind === "item+") {
      const col = done ? [128, 112, 96] : current ? [255, 214, 90] : PARCHMENT;
      if (kind === "item") {
        if (done) roundBox(ctx, x + 14, cy + 3, 10, 10, [60, 120, 60], [90, 160, 90], 1, 4);
        else roundBox(ctx, x + 14, cy + 3, 10, 10, [30, 20, 16], col, 1, 4);
      }
      const tw = drawText(ctx, text, x + 30, cy, 9, current && !done, col);
      if (done) {
        ctx.strokeStyle = "rgb(150,130,110)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x + 29, cy + 7.5); ctx.lineTo(x + 31 + tw, cy + 7.5); ctx.stroke();
      }
    } else if (kind === "footer") drawText(ctx, text, x + 12, cy + 4, 8, false, [150, 125, 95]);
    cy += ROW_H[kind];
  }
}

// ----- the hover box's text for things in the world
export function hoverText(e) {
  if (!e) return "";
  if (S.itemInUse) {
    const it = (S.me.inv || []).find((i) => i[0] === S.itemInUse);
    const name = it ? pretty(it[1]) : "";
    const spell = it ? entityIni(it[1], "Spell", "").trim() : "";
    if (spell && entityIni(it[1], "Use.Words", "").includes("Cast")) {          // (a spell held ready: who it's for)
      return e.k === T.INVITEM && e.u === S.itemInUse ? `#Cast ${pretty(spell)}|~Click who to cast it at`
        : `#Cast ${pretty(spell)} at ${displayName(e)}|~Click to cast`;
    }
    return e.k === T.INVITEM && e.u === S.itemInUse ? `Use ${name} with ...` : `Use ${name} with ${displayName(e)}`;
  }
  return entityTip(e);
}

export function skillInfo(i, long) {
  const name = A.m.skills[i - 1];
  const xp = S.me.xp[i - 1];
  const level = levelOfXp(xp);
  const pts = (x) => Math.floor(x * 100 + 1e-6).toLocaleString("en");
  const now = (S.me.skill_now || [])[i - 1] ?? level;
  if (long && now !== level) {
    return `${pretty(name)}: ${now} just now (usually ${level}): ${now < level ? "drained" : "boosted"} for a while.`;
  }
  if (long) {
    if (level >= maxLevel()) return `You have the highest ${pretty(name)} level possible (${maxLevel()})!`;
    return `${pretty(name)}: ${pts(xp)} xp / ${pts(level + 1)} xp to level ${level + 1}.`;
  }
  const prog = level >= maxLevel() ? "the highest level" : `${pts(xp)} xp / ${pts(level + 1)} xp`;
  return `${name}: level ${level} / ${maxLevel()}|${prog}`;
}

// ================================================================================================================
// A phone's interface (mobile.js): over the world, which fills the screen
// ================================================================================================================
export const TOUCH_BUTTONS = [["bag", "Bag"], ["chat", "Chat"], ["journal", "Journal"], ["menu", "Menu"]];
export const JOY = { r: 46, knob: 20 };
export const joyCentre = () => [16 + JOY.r, L.VH - 16 - JOY.r];

export function touchButtonRect(i) { return [L.btnX, L.btnY + i * 50, 20]; }

export function touchButtonAt(x, y) {
  if (L.upright && S.box.mode) return "";          // (held upright, a box covers them)
  const list = touchButtons();
  for (let i = 0; i < list.length; i++) {
    const [cx, cy, r] = touchButtonRect(i);
    if (Math.hypot(x - cx, y - cy) <= r + 6) return list[i][0];
  }
  return "";
}

function touchButtons() { return S.admin ? [...TOUCH_BUTTONS, ["admin", "Admin"]] : TOUCH_BUTTONS; }

export function journalOrigin() {
  // (where the journal's 1024 x 768 page is drawn: in the middle; on a phone, dragged about under the finger)
  return M.on ? [-M.panX, -M.panY] : [Math.floor((L.W - 1024) / 2), 0];
}

export function bagRect() { return [L.bagX - 6, L.bagY - 6, L.bagW + 12, L.bagH + 12]; }

function drawTouchButton(ctx, cx, cy, r, key, label, on) {
  ctx.fillStyle = on ? "rgba(126,77,63,0.95)" : "rgba(40,27,20,0.88)";
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, 6.283); ctx.fill();
  ctx.strokeStyle = "rgb(214,170,70)"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(cx, cy, r - 1, 0, 6.283); ctx.stroke();
  ctx.strokeStyle = "rgb(243,232,136)"; ctx.fillStyle = "rgb(243,232,136)"; ctx.lineWidth = 2;
  ctx.beginPath();
  if (key === "bag") {                             // (a satchel)
    ctx.roundRect ? ctx.roundRect(cx - 8, cy - 4, 16, 12, 3) : ctx.rect(cx - 8, cy - 4, 16, 12);
    ctx.moveTo(cx - 4, cy - 4); ctx.arc(cx, cy - 4, 4, Math.PI, 0);
    ctx.moveTo(cx - 8, cy + 1); ctx.lineTo(cx + 8, cy + 1);
  } else if (key === "chat") {                     // (a speech bubble)
    ctx.ellipse(cx, cy - 1, 9, 6.5, 0, 0, 6.283);
    ctx.moveTo(cx - 4, cy + 5); ctx.lineTo(cx - 7, cy + 9); ctx.lineTo(cx, cy + 5.5);
  } else if (key === "journal") {                  // (a book)
    ctx.rect(cx - 8, cy - 7, 16, 14);
    ctx.moveTo(cx, cy - 7); ctx.lineTo(cx, cy + 7);
  } else if (key === "menu") {                     // (three bars)
    for (const dy of [-5, 0, 5]) { ctx.moveTo(cx - 8, cy + dy); ctx.lineTo(cx + 8, cy + dy); }
  } else {                                         // (admin: a key)
    ctx.arc(cx - 4, cy, 4, 0, 6.283);
    ctx.moveTo(cx, cy); ctx.lineTo(cx + 9, cy); ctx.moveTo(cx + 6, cy); ctx.lineTo(cx + 6, cy + 4);
  }
  ctx.stroke();
  centreText(ctx, cx + 1, cy + r + 2, label, 7, true, [10, 6, 4]);
  centreText(ctx, cx, cy + r + 1, label, 7, true, [243, 232, 136]);
}

function drawJoystick(ctx) {
  if (S.box.mode || M.chat || M.bag) return;
  const [cx, cy] = joyCentre();
  ctx.fillStyle = "rgba(24,14,8,0.28)";
  ctx.beginPath(); ctx.arc(cx, cy, JOY.r, 0, 6.283); ctx.fill();
  ctx.strokeStyle = "rgba(243,232,136,0.45)"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(cx, cy, JOY.r - 1, 0, 6.283); ctx.stroke();
  const j = M.joy;
  const kx = cx + (j ? j.dx : 0), ky = cy + (j ? j.dy : 0);
  ctx.fillStyle = j ? "rgba(243,232,136,0.75)" : "rgba(243,232,136,0.4)";
  ctx.beginPath(); ctx.arc(kx, ky, JOY.knob, 0, 6.283); ctx.fill();
}

function drawToasts(ctx, now) {
  // (the newest lines of the chat, for a few seconds, over the hotbar: the log itself is under Chat)
  if (M.chat) return;
  const fresh = S.messages.slice(0, 3).filter((m) => now - m[2] < 7000);
  let y = L.VH - HOTBAR_SIZE - 26;
  for (const m of fresh) {
    const a = Math.min(1, (7000 - (now - m[2])) / 800);
    const text = fitText(ctx, m[0], Math.min(520, L.VW - 260), 9, true);
    ctx.save();
    ctx.globalAlpha = a;
    centreText(ctx, L.VW / 2 + 1, y + 1, text, 9, true, [10, 6, 4]);
    centreText(ctx, L.VW / 2, y, text, 9, true, brighter(m[1]));
    ctx.restore();
    y -= 14;
  }
}

function brighter(name) {
  // (a chat colour made light enough to read over the world)
  const c = colour(name);
  if (c[0] + c[1] + c[2] < 30) return [243, 232, 136];       // (black, the usual: parchment yellow)
  const l = c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11;
  if (l >= 140) return c;
  const k = (140 - l) / (255 - l);
  return c.map((v) => Math.round(v + (255 - v) * k));
}

function drawTouchUI(ctx, now) {
  drawHurt(ctx, now);
  drawHotbar(ctx);
  drawJoystick(ctx);
  drawToasts(ctx, now);
  drawBanner(ctx, now);
  drawVitals(ctx);
  drawOnline(ctx, now);
  drawHoverTop(ctx);
  drawArena(ctx, now);
  drawWave(ctx, now);
  drawSleep(ctx, now);
  drawMinimap(ctx);
  ctx.strokeStyle = "rgb(214,170,70)"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(L.mmX, L.mmY, L.mmSize / 2, 0, 6.283); ctx.stroke();
  const mm = sprite("MinimapMarker");
  if (mm) ctx.drawImage(mm, L.mmX - 4, L.mmY - 4);
  drawClock(ctx, now);
  if (!(L.upright && S.box.mode)) {
    touchButtons().forEach(([key, label], i) => {
      const [cx, cy, r] = touchButtonRect(i);
      drawTouchButton(ctx, cx, cy, r, key, label, (key === "bag" && M.bag) || (key === "chat" && M.chat));
    });
  }
  if (M.bag || (S.box.mode && S.box.mode !== "Conversation")) {
    const [bx, by, bw, bh] = M.bag && !S.box.mode ? bagRect() : [L.packX - 6, L.packY - 6, L.packW + 12, L.packH + 12];
    roundBox(ctx, bx, by, bw, bh, "rgba(51,34,27,0.96)", [126, 77, 63], 2, 12);
    if (statsShown()) drawStats(ctx);
    ctx.strokeStyle = "rgb(92,60,46)"; ctx.lineWidth = 1;
    ctx.strokeRect(L.invX - 2.5, L.invY - 2.5, 32 * 5 + 5, 32 * 7 + 5);
  }
  drawBox(ctx);
  drawInventory(ctx);
  if (S.box.mode) drawResponses(ctx);
  if (M.chat) drawChat(ctx);
  drawQuestPopup(ctx);
  if (U.rcm) drawMenu(ctx);
}
