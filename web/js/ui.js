// The interface round the world (the desktop game's ui.py, the rest of render): the sidebar (minimap, clock, buttons,
// Stats / Gear / Quests, the inventory), the chat bar and the hover box, the ActionBox and its responses, the right-click
// menu, the hotbar, the level-up banner. Laid out at 768 high, as wide as the screen's shape wants (1024 to 1792).
import { G, S, cellOf, isHomeMap } from "./state.js";
import { A, sprite, size, has, entityIni, configRead, preload } from "./assets.js";
import { val, word, trim, lbstr, pretty, clamp, colour, rgb, drawText, drawTextMid, centreText, textWidth, fitText,
  wrapLines, roundBox, fontPx, setFont } from "./util.js";
import { dayFraction, isNight, timeText, fogEnabled } from "./sky.js";
import { fogCell } from "./state.js";
import { T, getVerbs, verbLabel, canSellHere, displayName, skillLevel, itemPrice } from "./verbs.js";
import { lookImage } from "./look.js";

export const TAB_TEXT = [243, 232, 136];
const PARCHMENT = [212, 191, 126];
const INK = [243, 232, 136];

export const L = {};

export function layout(W) {
  L.W = W;
  L.VW = W - 224;
  L.VH = 672;
  L.DX = W - 1024;
  L.statY = 175;
  L.invX = L.VW + 34;
  L.invY = 413;
  L.mmX = L.VW + 140;
  L.mmY = 84;
  L.mmSize = 160;
  const [abw, abh] = size("AB_Conversation");
  const [, rbh] = size("ResponseBox");
  L.abX = Math.floor((L.VW - abw) / 2);
  L.abY = Math.floor((L.VH - (abh + rbh)) / 2);
  L.rbX = L.abX;                                    // (the answers line up with the box above them)
  L.rbY = L.abY + abh;
  L.helpX = L.VW + 18;
  L.helpY = 18;
}

export const U = {
  statsView: 0, questsPage: 1, questHover: 0, equipHover: 0, skillHover: 0, statRows: 1, statRowTop: 41,
  statRowH: 33, cursorSize: 22, chatLine: 1, qm: "", qmKind: "", rcm: null, hotHover: -1, minimapZoom: 0, rbHover: 0,
  hover: null, onlineShownUntil: 0, banner: null, markers: true,
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
  const { VW, VH } = L;
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, VW, VH);
  ctx.clip();
  drawHurt(ctx, now);
  drawHotbar(ctx);
  drawBanner(ctx, now);
  drawOnline(ctx, now);
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
  drawLevelBadge(ctx, L.helpX, L.helpY + (S.admin ? 56 : 30));
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

// ----- the minimap (Sprites\Interface\Minimap<Z>, Config [Minimap])
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

const mmCache = { key: "", canvas: null, at: 0 };
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

function minimapImage(g) {
  // The minimap with what you haven't seen blacked out, tile by tile: a tile shows once any of its fog-of-war cells
  // has been uncovered (the same cells that take the black off the world)
  if (g.live) return liveMinimap(g);
  const im = sprite(g.name);
  if (!im) return null;
  const key = g.name + "|" + S.explored.size + "|" + (S.exploredVersion || 0) + "|" + fogEnabled();
  if (mmCache.key === key) return mmCache.canvas;
  const now = performance.now();
  if (mmCache.canvas && mmCache.key.split("|")[0] === g.name && now - mmCache.at < 400) return mmCache.canvas;
  const c = mmCache.canvas && mmCache.canvas.width === im.width && mmCache.canvas.height === im.height ?
    mmCache.canvas : document.createElement("canvas");
  c.width = im.width; c.height = im.height;
  const x = c.getContext("2d");
  x.clearRect(0, 0, c.width, c.height);
  x.drawImage(im, 0, 0);
  if (val(configRead("Minimap", "Blackout", "1")) === 1 && fogEnabled()) {
    x.fillStyle = "rgb(18,18,28)";
    const ps = g.ps, n = fogCell(), fxt = Math.ceil(G.sw / n);
    for (const name of A.m.maps) {
      const [mx, my, mz] = name.split(",").map(Number);
      if (mz !== S.mapZ) continue;
      const bx = (mx - g.ox) * G.xt * ps, by = (my - g.oy) * G.yt * ps;
      const seen = S.explored.get(name);
      if (seen === "all") continue;
      if (!seen || !seen.size) { x.fillRect(bx, by, G.xt * ps, G.yt * ps); continue; }
      for (let ty = 0; ty < G.yt; ty++) {
        const cy0 = Math.floor(ty * G.th / n), cy1 = Math.floor(((ty + 1) * G.th - 1) / n);
        for (let tx = 0; tx < G.xt; tx++) {
          const cx0 = Math.floor(tx * G.tw / n), cx1 = Math.floor(((tx + 1) * G.tw - 1) / n);
          let shown = false;
          for (let cy = cy0; cy <= cy1 && !shown; cy++)
            for (let cx = cx0; cx <= cx1 && !shown; cx++) if (seen.has(cy * fxt + cx + 1)) shown = true;
          if (!shown) x.fillRect(bx + tx * ps, by + ty * ps, ps, ps);
        }
      }
    }
  }
  mmCache.key = key;
  mmCache.canvas = c;
  mmCache.at = now;
  return c;
}

function drawMinimap(ctx) {
  const g = minimapGeometry();
  const half = L.mmSize / 2;
  const vx = L.mmX - half, vy = L.mmY - half;
  ctx.fillStyle = "#000";
  ctx.fillRect(vx, vy, L.mmSize, L.mmSize);
  if (!g || !S.pos) return;
  const im = minimapImage(g);
  if (!im) return;
  const k = g.ps * g.zoom;
  const pw = size(S.pos.i);
  const u = ((S.pos.dx + pw[0] / 2) / G.tw - g.ox * G.xt) * k;
  const v = ((S.pos.dy + pw[1] / 2) / G.th - g.oy * G.yt) * k;
  ctx.save();
  ctx.beginPath();
  ctx.rect(vx, vy, L.mmSize, L.mmSize);
  ctx.clip();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(im, Math.round(L.mmX - u), Math.round(L.mmY - v), im.width * g.zoom, im.height * g.zoom);
  if (U.markers) {
    for (const [m, qx, qy] of S.marks) {
      const [mx, my, mz] = String(m).split(",").map(Number);
      if (mz !== S.mapZ) continue;
      const px = Math.round(L.mmX - u + ((mx - g.ox) * G.xt + qx - 0.5) * k);
      const py = Math.round(L.mmY - v + ((my - g.oy) * G.yt + qy - 0.5) * k);
      if (px < vx + 5 || px > vx + L.mmSize - 6 || py < vy + 5 || py > vy + L.mmSize - 6) continue;
      cross(ctx, [0, 0, 0], px, py, 5, 2);
      cross(ctx, [255, 220, 40], px, py, 4, 1);
    }
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
  const x0 = L.VW, y0 = L.statY;
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
  if (k < 2) return [29 + k * 84, U.statRowTop, 82];
  const j = k - 2;
  return [29 + (j % 3) * 56, U.statRowTop + (1 + Math.floor(j / 3)) * U.statRowH, 54];
}

export function statTileAt(px, py) {
  if (U.statRowH <= 0) return -1;
  for (let k = 0; k < 2 + 3 * Math.max(0, U.statRows - 1); k++) {
    const [x, y, w] = statTileRect(k);
    if (px >= x && px < x + w && py >= y && py < y + U.statRowH) return k;
  }
  return -1;
}

const maxLevel = () => Math.max(2, Math.floor(val(configRead("Gameplay", "Skill.Max.Level", "50"))));
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
  U.statRows = 1 + Math.floor((shown + 2) / 3);
  U.statRowTop = 41;
  U.statRowH = Math.min(33, Math.floor(130 / U.statRows));
  const hp = me.hp, mhp = me.max_hp;
  const hpc = hp < mhp * 0.33 ? [230, 60, 40] : hp < mhp * 0.66 ? [230, 150, 40] : [21, 171, 75];
  skillTile(ctx, 0, configRead("Skills", "Icon.Hitpoints", "Heart") || "Heart", `${hp}/${mhp}`, hpc, 100 * hp / Math.max(1, mhp));
  skillTile(ctx, 1, "Mana", `${Math.floor(me.mana)}/${me.max_mana}`, [140, 180, 255], 100 * me.mana / Math.max(1, me.max_mana));
  let k = 1;
  skills.forEach((name, i) => {
    if (!skillShown(i + 1)) return;
    k++;
    const lv = levelOfXp(me.xp[i]);
    // (a potion or spell boosting it: its level shows "+N", green, while it lasts)
    const boost = (me.boosts || {})[{ Strength: "attack", Defence: "defence", Magic: "magic" }[name]] || 0;
    skillTile(ctx, k, configRead("Skills", "Icon." + name, "").trim(), boost ? `${lv}+${boost}` : String(lv),
      boost ? [120, 235, 120] : lv >= maxLevel() ? [255, 215, 60] : TAB_TEXT, levelProgress(me.xp[i]));
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
  const item = S.me.equipped[s - 1];
  if (!item) return SLOT_NAMES[s] + " (empty)";
  let info = `${pretty(item)} (${SLOT_NAMES[s]}): Attack +${lbstr(val(entityIni(item, "Attack", "0")))}, Defence +${lbstr(val(entityIni(item, "Defence", "0")))}`;
  const m = val(entityIni(item, "Magic", "0"));
  if (m) info += ", Magic +" + lbstr(m);
  const d = durText(item, S.me.wear[s - 1]);
  if (d) info += ". Condition: " + d;
  return info + ". Click to take it off.";
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
    const title = fitText(ctx, q.title, 142, 8, true);
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
  const im = dim || broken ? greyed(name) : sprite(name) || sprite("Placeholder");
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
  if (bg) ctx.drawImage(bg, x0, y0);
  else roundBox(ctx, x0, y0, w, h, [51, 34, 27], [126, 77, 63], 2, 10);
  const portrait = /^Player/.test(b.image || "") && S.me.look ? lookImage(b.image, S.me.look) : sprite(b.image);
  const [pw, ph] = size(b.image);
  let titleX, titleY;
  if (b.mode === "Conversation") {
    if (portrait) {
      ctx.save(); ctx.imageSmoothingEnabled = false;
      ctx.drawImage(portrait, x0 + 24, y0 + 20, pw * 2, ph * 2);
      ctx.restore();
    }
    titleX = 24 + Math.max(32, pw) * 2 + 16; titleY = 18;
  } else {
    // the trader (or the chest, the board) in a frame on the left
    roundBox(ctx, x0 + 13, y0 + 44, 46, 52, [30, 19, 14], [150, 104, 62], 2, 8);
    if (portrait) {
      ctx.save(); ctx.imageSmoothingEnabled = false;
      const k = pw <= 24 && ph <= 24 ? 2 : 1;
      ctx.drawImage(portrait, x0 + 36 - Math.floor(pw * k / 2), y0 + 70 - Math.floor(ph * k / 2), pw * k, ph * k);
      ctx.restore();
    }
    titleX = 22; titleY = 18;
  }
  const tw = drawText(ctx, b.title, x0 + titleX, y0 + titleY, 12, true, TAB_TEXT);
  const kind = { Shop: "Shop", Bank: "Bank", Craft: "Crafting", Market: "everyone's goods", Chest: "take what you want" }[b.mode];
  if (kind) drawText(ctx, "- " + kind, x0 + titleX + tw + 10, y0 + titleY + 5, 9, false, [212, 191, 126]);
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
      if (lines.length * lineH + (heading ? lineH + 8 : 0) <= h - 58) break;
    }
    let y = 48;
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

// ----- the answers under the box: a row each, attached to the box, numbered (press the number, or click it)
const RB_TOP = 6, RB_ROW = 24;

function responseBoxH() {
  return Math.max(54, RB_TOP + S.box.responses.length * RB_ROW + 8);
}

function drawResponses(ctx) {
  const b = S.box;
  const [w] = size(boxBackground());
  const h = responseBoxH();
  const x0 = L.rbX, y0 = L.rbY;
  roundBox(ctx, x0 + 8, y0 - 6, w - 16, h + 6, [40, 27, 20], [150, 104, 62], 2, 12);
  b.responses.forEach((r, i) => {
    const y = y0 + RB_TOP + i * RB_ROW;
    const hot = U.rbHover === i + 1;
    roundBox(ctx, x0 + 18, y, w - 36, RB_ROW - 3, hot ? [96, 64, 42] : [60, 41, 31], hot ? [236, 196, 92] : [98, 70, 52], 1, 8);
    ctx.fillStyle = hot ? "rgb(236,196,92)" : "rgb(160,112,66)";
    ctx.beginPath(); ctx.arc(x0 + 33, y + (RB_ROW - 3) / 2, 8, 0, 6.283); ctx.fill();
    centreText(ctx, x0 + 33, y + 3, String(i + 1), 8, true, [40, 26, 18]);
    drawTextMid(ctx, r, x0 + 48, y, RB_ROW - 3, 10, true, hot ? [255, 242, 196] : [238, 224, 190]);
  });
}

export function responseAt(x, y) {
  if (!S.box.mode) return 0;
  const [w] = size(boxBackground());
  if (x < L.rbX + 18 || x > L.rbX + w - 18) return 0;
  const n = Math.floor((y - L.rbY - RB_TOP) / RB_ROW) + 1;
  const inRow = (y - L.rbY - RB_TOP) % RB_ROW < RB_ROW - 3;
  return y >= L.rbY + RB_TOP && inRow && n >= 1 && n <= S.box.responses.length ? n : 0;
}

export function responseBoxRect() {
  if (!S.box.mode) return null;
  return [L.rbX, L.rbY - 6, size(boxBackground())[0], responseBoxH() + 6];
}

// ----- the chat bar and the hover box
function drawChat(ctx) {
  const y0 = L.VH, dx = Math.max(0, L.DX);
  const bar = sprite("ChatBar");
  ctx.fillStyle = "rgb(212,191,126)";
  ctx.fillRect(0, y0, L.W, 96);
  if (bar) {
    if (dx === 0) ctx.drawImage(bar, 0, y0);
    else {
      ctx.drawImage(bar, 0, 0, 10, 96, 0, y0, 10, 96);
      ctx.drawImage(bar, 10, 0, 760, 96, 10, y0, 760 + dx, 96);
      ctx.drawImage(bar, 770, 0, 254, 96, 770 + dx, y0, 254, 96);
    }
    const x1 = 827 + dx, x2 = 997 + dx;
    ctx.fillStyle = "rgb(49,28,18)"; ctx.fillRect(x1 - 1, y0, x2 - x1 + 3, 1);
    ctx.fillStyle = "rgb(243,210,129)"; ctx.fillRect(x1, y0 + 1, x2 - x1, 1);
  }
  const lineH = 15;
  let y = y0 + 8;
  for (let i = U.chatLine + 4; i >= U.chatLine; i--) {
    const m = S.messages[i - 1];
    if (m) drawText(ctx, fitText(ctx, m[0], 760 + dx, 9, false), 10, y, 9, false, colour(m[1]));
    y += lineH;
  }
  drawThumb(ctx);
  if (U.qm) drawQuick(ctx, y0);
}

export function chatTrack() { return [780 + L.DX, L.VH + 19, 15, 60]; }

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

function drawQuick(ctx, y0) {
  const kindCol = { ERROR: "150 20 20", WARNING: "150 20 20", INFORMATION: "120 70 0", ENTITY: "60 30 20",
    INTERFACE: "30 50 120" }[U.qmKind] || "70 50 40";
  const parts = U.qm.split("|");
  let sz = 10, lines = [], lineH = 0;
  for (;;) {
    sz--;
    lines = [];
    for (const part of parts) for (const ln of wrapLines(ctx, trim(part), 150, sz)) if (lines.length < 10) lines.push(ln);
    lineH = Math.floor(sz * 1.35) + 1;
    if (lines.length * lineH <= 70 || sz <= 6) break;
  }
  let y = y0 + Math.max(lineH - 2, Math.floor(31 - lines.length * lineH / 2 + lineH * 0.8)) - fontPx(sz) + 2;
  lines.forEach((ln, i) => { drawText(ctx, ln, L.VW + 35, y, sz, i === 0, colour(kindCol)); y += lineH; });
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
  const longest = Math.max(...labels.map((l) => textWidth(ctx, l, 9, true)));
  const w = Math.max(110, Math.ceil(longest) + 28), rowH = 18, rowTop = 6;
  const h = rowTop * 2 + verbs.length * rowH;
  U.rcm = { verbs, labels, target, worldXY, w, h, rowH, rowTop, hi: 0,
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
    drawTextMid(ctx, r.labels[i], r.x + 14, ry + 1, r.rowH - 1, 9, true, c);
  });
}

// ----- the hotbar
export function hotbarRect(k) {
  const total = 5 * HOTBAR_SIZE + 4 * 4;
  const x0 = Math.floor((L.VW - total) / 2);
  return [x0 + k * (HOTBAR_SIZE + 4), L.VH - HOTBAR_SIZE - 8, HOTBAR_SIZE, HOTBAR_SIZE];
}

export function hotbarAt(x, y) {
  if (S.box.mode) return -1;
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
  if (S.box.mode) return;
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
      const im = n ? sprite(name) : greyed(name);
      if (im) ctx.drawImage(im, x + Math.floor((w - im.width) / 2), y + Math.floor((h - im.height) / 2));
      if (n !== 1) {
        const t = String(n);
        drawText(ctx, t, x + w - 3 - textWidth(ctx, t, 8, true), y + h - 12, 8, true, n ? [255, 240, 200] : [200, 90, 80]);
      }
    }
    drawText(ctx, String(k + 1), x + 3, y + 1, 8, true, [214, 170, 70]);
  }
}

export function hotbarLabel(k) {
  const name = (S.me.hotbar || [])[k];
  if (!name) return `Hotbar slot ${k + 1}|right-click an item in your inventory to put it here`;
  return `${pretty(name)} (${held(name)})|${k + 1} or click: use it · right-click: take it off`;
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
  const ic = configRead("Skills", "Icon." + b.skills[b.skills.length - 1][0], "").trim();
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
  ctx.fillStyle = "rgba(24,14,8,0.55)";
  ctx.fillRect(4, 4, w, 16);
  drawText(ctx, text, 10, 6, 8, true, [243, 232, 136]);
  // the full-screen button beside it
  const fx = 4 + w + 6;
  ctx.fillStyle = U.hover === "fullscreen" ? "rgba(126,77,63,0.95)" : "rgba(24,14,8,0.55)";
  ctx.fillRect(fx, 4, 16, 16);
  ctx.strokeStyle = "rgb(243,232,136)"; ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (const [a, b, c, d] of [[3, 7, 3, 3], [3, 3, 7, 3], [13, 9, 13, 13], [13, 13, 9, 13], [9, 3, 13, 3], [13, 3, 13, 7],
    [3, 9, 3, 13], [3, 13, 7, 13]]) { ctx.moveTo(fx + a, 4 + b); ctx.lineTo(fx + c, 4 + d); }
  ctx.stroke();
  U.fullscreenRect = [fx, 4, 16, 16];
}

function drawArena(ctx, now) {
  // On the arena's sand: you can fight other players here, and they can fight you
  if (!S.me.arena) return;
  const text = "ARENA  -  other players can fight you here";
  const w = textWidth(ctx, text, 10, true) + 28;
  const x = Math.floor((L.VW - w) / 2), y = 8;
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
  const x = Math.floor((L.VW - w) / 2), y = S.me.arena ? 38 : 8;
  const pulse = 0.8 + 0.2 * Math.sin(now / 220);
  roundBox(ctx, x, y, w, 40, `rgba(60,12,6,${0.85 * pulse})`, [230, 120, 40], 2, 10);
  centreText(ctx, x + w / 2, y + 4, v.name.toUpperCase(), 11, true, [255, 200, 120]);
  centreText(ctx, x + w / 2, y + 21, line2, 9, true, [255, 235, 200]);
}

// ----- what potions and spells are doing for you now: an icon each, the time left, and what it does (hover)
const BOOST_WORDS = { attack: (n) => `+${n} Attack`, defence: (n) => `+${n} Defence`,
  magic: (n) => `+${n} spell damage`, sight: () => "far sight" };

export function drawBoosts(ctx, now, mx, my) {
  const me = S.me;
  if (!me || !me.boost_left || !S.boostAt) return;
  const groups = new Map();                       // the potion (or scroll) -> [kinds, ms left]
  for (const [kind, ms] of Object.entries(me.boost_left)) {
    const left = ms - (now - S.boostAt);
    if (left <= 0 || !(me.boosts || {})[kind]) continue;
    const from = (me.boost_from || {})[kind] || "Magic_Burst";
    const g = groups.get(from) || { kinds: [], left: 0 };
    g.kinds.push(kind);
    g.left = Math.max(g.left, left);
    groups.set(from, g);
  }
  let x = 8;
  const y = L.VH - 58;                            // (the bottom-left corner of the view, clear of the hotbar)
  let tip = null;
  for (const [from, g] of groups) {
    const blink = g.left < 10000 && Math.floor(now / 300) % 2 === 0;
    roundBox(ctx, x, y, 40, 50, [34, 22, 16, 0.88], blink ? [230, 90, 60] : [120, 230, 120], 2, 7);
    const im = sprite(from) || sprite("Magic_Burst");
    if (im) ctx.drawImage(im, x + 4, y + 3, 32, 32);
    const s = Math.ceil(g.left / 1000);
    centreText(ctx, x + 20, y + 36, `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`, 8, true,
      blink ? [255, 140, 110] : [235, 245, 220]);
    if (mx >= x && mx < x + 40 && my >= y && my < y + 50) {
      tip = [x, y - 24, `${pretty(from)}: ${g.kinds.map((k) => BOOST_WORDS[k](me.boosts[k])).join(", ")}` +
        ` (${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")} left)`];
    }
    x += 46;
  }
  if (tip) {
    const w = textWidth(ctx, tip[2], 9, true) + 14;
    roundBox(ctx, tip[0], tip[1], w, 20, [20, 14, 10, 0.92], [212, 191, 126], 1, 5);
    drawText(ctx, tip[2], tip[0] + 7, tip[1] + 4, 9, true, [250, 240, 210]);
  }
}

function drawLevelBadge(ctx, x, y) {
  // Your character's level (the best of your fighting skills: Config [Gameplay] Level.Skills)
  const lv = S.me.level || S.level || 1;
  roundBox(ctx, x, y, 52, 38, [40, 27, 20], [214, 170, 70], 2, 10);
  centreText(ctx, x + 26, y + 3, "LEVEL", 7, true, [212, 191, 126]);
  centreText(ctx, x + 26, y + 15, String(lv), 13, true, [255, 230, 140]);
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
  drawChecklist(ctx, q, rows, L.VW - w - 6, y, w, h);
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
    return e.k === T.INVITEM && e.u === S.itemInUse ? `Use ${name} with ...` : `Use ${name} with ${displayName(e)}`;
  }
  const verbs = getVerbs(e);
  const first = verbs[0] || "";
  if (first === "Walk here") return val(e.misc) === 1 ? displayName(e) : "";
  let msg = first ? verbLabel(first, e) : "";
  if (e.k === T.INVITEM && S.box.mode === "Shop" && !canSellHere(e.n)) msg = displayName(e) + "|Can't be sold here";
  return msg;
}

export function skillInfo(i, long) {
  const name = A.m.skills[i - 1];
  const xp = S.me.xp[i - 1];
  const level = levelOfXp(xp);
  const pts = (x) => Math.floor(x * 100 + 1e-6).toLocaleString("en");
  if (long) {
    if (level >= maxLevel()) return `You have the highest ${name} level possible (${maxLevel()})!`;
    return `${name}: ${pts(xp)} xp / ${pts(level + 1)} xp to level ${level + 1}.`;
  }
  const prog = level >= maxLevel() ? "the highest level" : `${pts(xp)} xp / ${pts(level + 1)} xp`;
  return `${name}: level ${level} / ${maxLevel()}|${prog}`;
}
