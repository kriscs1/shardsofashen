// The ground: each map's tiles painted once into a picture of its own (a "chunk"), as the desktop game's world.py
// paint_window_cell did: the tile (or its part of a big texture), the edges of higher-Blend neighbours blended over it,
// its decor, foam where water meets land, a flickering flame, a plant in the wind, its roof (unless you're under it)
// and its tree top. Cells that move are painted again when their frame changes.
import { G, S, cellOf, cellAtTile, mapByPos } from "./state.js";
import { A, sprite, animFrame, mask, texture, tileIni, isDecorTile, tileAnim, frames, animSetting, foamColour, has,
  onLoaded } from "./assets.js";
import { val, trim } from "./util.js";

const chunks = new Map();           // map name -> chunk
let anyLoaded = false;
onLoaded(() => { anyLoaded = true; });

const DIRS = [[0, -1, "N"], [1, 0, "E"], [0, 1, "S"], [-1, 0, "W"], [1, -1, "NE"], [1, 1, "SE"], [-1, 1, "SW"], [-1, -1, "NW"]];
const cache = { blend: new Map(), info: new Map(), land: null };

function info(name) {
  // What the ground painter needs to know about a tile (Tiles.ini), worked out once
  let i = cache.info.get(name);
  if (i) return i;
  const decor = isDecorTile(name);
  const anim = tileAnim(name) || {};
  const fr = frames(name, "t");
  const flag = (k) => ["1", "yes", "Yes", "true"].includes(tileIni(name, k, "0").trim());
  let kind = null;
  if (name && !decor) {
    if (flag("Water")) kind = "water";
    else if (fr) kind = "frames";
    else if (anim.f) kind = "flame";
    else if (anim.s) kind = "sway";
  }
  let dkind = null;
  if (decor || !kind) {
    if (fr) dkind = "frames";
    else if (anim.d) dkind = "sway";
    else if (anim.F) dkind = "flame";
  }
  i = {
    decor, kind, dkind, frames: fr, anim,
    blend: Math.min(9, Math.max(0, Math.floor(val(tileIni(name, "Blend", "0"))))),
    tex: tileIni(name, "Blend.Texture", name) || name,
    texture: tileIni(name, "Texture", ""),
    water: flag("Water"),
    wade: decor && tileIni(name, "Foam", "1").trim() === "0",   // (Foam=0: reeds, lily pads - in the water, not land)
  };
  cache.info.set(name, i);
  return i;
}

export function tileInfo(name) { return info(name); }

function hasLand(name) {
  if (!cache.land) cache.land = new Set(A.m.land || []);
  return cache.land.has(name);
}

// ----- the frame of the moment (anim.py anim_frame / frames_image)
function swayFrame(gx1, now) {
  const n = animSetting("Sway.Frames");
  return ((Math.floor(now / animSetting("Sway.Speed")) - Math.floor(gx1 / 2)) % n + n) % n;
}
const flameFrame = (now) => Math.floor(now / animSetting("Flame.Speed")) % animSetting("Flame.Frames");
const waterFrame = (now) => Math.floor(now / animSetting("Water.Speed")) % animSetting("Water.Frames");

function framesName(name, fr, gx1, gy1, now) {
  return name + ((Math.floor(now / fr[1]) + gx1 * 3 + gy1 * 5) % fr[0] + 1);
}

// ----- chunks
class Chunk {
  constructor(m) {
    this.m = m;
    this.canvas = document.createElement("canvas");
    this.canvas.width = G.sw;
    this.canvas.height = G.sh;
    this.ctx = this.canvas.getContext("2d");
    this.version = -1;
    this.full = true;               // paint every cell
    this.dirty = new Set();         // cells (index) to paint again
    this.missing = false;           // a picture it needed hadn't loaded
    this.anim = [];                 // [cell index, kinds...] cells that move
    this.foam = new Map();          // cell index -> {dist, frames: Map}
    this.hidden = 0;                // the roof group hidden (the player is under it)
    this.counters = {};
  }
}

export function chunkOf(m) {
  let c = chunks.get(m.name);
  if (!c || c.m !== m) {
    const old = c;
    c = new Chunk(m);
    if (old) c.hidden = old.hidden;   // (the map sent again: the roof you're under stays hidden - no flash of it)
    chunks.set(m.name, c);
  }
  return c;
}

export function forgetChunks(keep) {
  for (const name of [...chunks.keys()]) if (!keep.has(name)) chunks.delete(name);
}

export function invalidateCell(name, x, y) {
  // A cell changed (and its neighbours' edges may have): paint them again, across map edges too
  const m = S.maps.get(name);
  if (!m) return;
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      const gx = m.mx * G.xt + x - 1 + dx, gy = m.my * G.yt + y - 1 + dy;
      const n = mapByPos(Math.floor(gx / G.xt), Math.floor(gy / G.yt), m.mz);
      if (!n) continue;
      const c = chunks.get(n.name);
      if (c) {
        const lx = gx - n.mx * G.xt, ly = gy - n.my * G.yt;
        c.dirty.add(ly * G.xt + lx);
        c.foam.delete(ly * G.xt + lx);
      }
    }
  }
}

export function mapCells(d) {
  // A few of a map's tiles changed (a door opened, a tree was chopped): those, and only those, painted again
  const m = S.maps.get(d.name);
  if (!m) return;
  for (const [c, tile, decor, under] of d.cells) {
    m.tile[c - 1] = tile; m.decor[c - 1] = decor;
    if (m.under) m.under[c - 1] = under;
    invalidateCell(d.name, (c - 1) % G.xt + 1, Math.floor((c - 1) / G.xt) + 1);
  }
  const ch = chunks.get(d.name);
  if (ch && ch.version === m.v) ch.version = d.v;   // (up to date: no need to paint it all again)
  m.v = d.v;
}

export function invalidateMap(name) {
  const c = chunks.get(name);
  if (c) { c.full = true; c.foam.clear(); }
  // the maps beside it paint their edges again (blending reaches over the seam)
  const m = S.maps.get(name);
  if (!m) return;
  for (const [dx, dy] of DIRS) {
    const n = mapByPos(m.mx + dx, m.my + dy, m.mz);
    const nc = n && chunks.get(n.name);
    if (nc) { nc.full = true; nc.foam.clear(); }                  // (its shore may meet this map's land)
  }
}

// ----- painting one cell
function blendSurface(texName, maskName, gx, gy) {
  const big = info(texName).texture ? texture(info(texName).texture) : null;
  let key = texName + "|" + maskName;
  let sx = 0, sy = 0;
  if (big) {
    sx = ((gx * G.tw) % big.width + big.width) % big.width;
    sy = ((gy * G.th) % big.height + big.height) % big.height;
    key += "|" + sx + "," + sy;
  }
  let c = cache.blend.get(key);
  if (c) return c;
  const t = big || sprite(texName);
  const mk = mask(maskName);
  if (!t || !mk) return null;
  c = document.createElement("canvas");
  c.width = G.tw;
  c.height = G.th;
  const x = c.getContext("2d");
  if (big) drawTextureCell(x, big, sx, sy, 0, 0);
  else x.drawImage(t, 0, 0);
  x.globalCompositeOperation = "destination-in";
  x.drawImage(mk, 0, 0);
  cache.blend.set(key, c);
  return c;
}

function drawTextureCell(ctx, tex, sx, sy, dx, dy) {
  const w = tex.width, h = tex.height, tw = G.tw, th = G.th;
  if (sx + tw <= w && sy + th <= h) {
    ctx.drawImage(tex, sx, sy, tw, th, dx, dy, tw, th);
    return;
  }
  for (const ox of [0, w]) for (const oy of [0, h]) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(dx, dy, tw, th);
    ctx.clip();
    ctx.drawImage(tex, dx + ox - sx, dy + oy - sy);
    ctx.restore();
  }
}

function blendLevelAt(z, gx, gy) {
  const c = cellAtTile(z, gx, gy);
  if (!c || !c[0]) return [0, ""];
  const i = info(c[0]);
  return [i.blend, i.blend > 0 ? i.tex : ""];
}

function paintBlendEdges(ctx, z, gx, gy, b, dx, dy, ch) {
  const found = [];
  DIRS.forEach(([ddx, ddy, side], k) => {
    let [level, tex] = blendLevelAt(z, gx + ddx, gy + ddy);
    if (level > b && k >= 4) {
      if (blendLevelAt(z, gx + ddx, gy)[0] >= level || blendLevelAt(z, gx, gy + ddy)[0] >= level) level = 0;
    }
    if (level > b && tex) {
      const variant = 1 + (Math.abs((gx + 1) * 7 + (gy + 1) * 13) % 2);
      found.push([level, found.length, tex, "Blend_" + side + variant]);
    }
  });
  found.sort((a, b2) => a[0] - b2[0] || a[1] - b2[1]);
  for (const [, , tex, maskName] of found) {
    const s = blendSurface(tex, maskName, gx, gy);
    if (s) ctx.drawImage(s, dx, dy);
    else ch.missing = true;
  }
}

function img(name, ch) {
  const i = sprite(name);
  if (!i && has(name)) ch.missing = true;
  return i;
}

// Trees, bushes, rocks, grass and flowers aren't all stood in the middle of their tile in rows: each its own size
// (trees and bushes) and nudged its own way, always inside its cell (a neighbour painting again would cut it)
const GROWN = /^(Tree|Oak_Tree|Snow_Pine|Willow_Tree|Dead_Tree|Yew_Tree|Pine|Birch|Bush|Berry_Bush|Cactus|Bog_Myrtle)\d/;
const LYING = /^(Tall_Grass|Flowers|Pebbles|Rock|Desert_Rock|Reeds|Snow_Rock|Fern|Mushrooms?)\d/;
const SIZES = [1, 1, 0.875, 0.75];

function margins(name, pic) {
  // How far it can move each way inside its 32 x 32 (its see-through rows and columns), worked out once
  let m = cache.margins?.get(name);
  if (m) return m;
  if (!cache.margins) cache.margins = new Map();
  const c = document.createElement("canvas");
  c.width = G.tw; c.height = G.th;
  const x = c.getContext("2d", { willReadFrequently: true });
  x.drawImage(pic, 0, 0);
  const d = x.getImageData(0, 0, G.tw, G.th).data;
  let l = G.tw, r = -1, t = G.th, b = -1;
  for (let yy = 0; yy < G.th; yy++) for (let xx = 0; xx < G.tw; xx++) {
    if (d[(yy * G.tw + xx) * 4 + 3] > 20) { l = Math.min(l, xx); r = Math.max(r, xx); t = Math.min(t, yy); b = Math.max(b, yy); }
  }
  m = r < 0 ? [0, 0, 0, 0] : [l, G.tw - 1 - r, t, G.th - 1 - b];
  cache.margins.set(name, m);
  return m;
}

function paintDecor(ctx, name, gx1, now, dx, dy, ch, gy1 = 0, vary = false) {
  const i = info(name);
  let pic = null;
  if (i.dkind === "frames") pic = img(framesName(name, i.frames, gx1, 0, now), ch);
  else if (i.dkind === "sway") pic = animFrame(name, "d", swayFrame(gx1, now) % i.anim.d);
  else if (i.dkind === "flame") pic = animFrame(name, "F", flameFrame(now) % i.anim.F);
  if (!pic) pic = img(name, ch);
  if (!pic) return;
  const grown = vary && GROWN.test(name), lying = vary && !grown && LYING.test(name);
  if (!grown && !lying) { ctx.drawImage(pic, dx, dy); return; }
  const h = ((gx1 * 73856093) ^ (gy1 * 19349663)) >>> 0;        // (the same each time this cell is painted)
  const k = grown ? SIZES[h % SIZES.length] : 1;
  const w = Math.round(G.tw * k), ht = Math.round(G.th * k);
  const [l, r, t, b] = margins(name, img(name, ch) || pic).map((v) => Math.floor(v * k));
  const roomX = G.tw - w, roomY = G.th - ht;
  const lo = -l, hi = roomX + r, up = -t, down = roomY + b;      // (how far left/right, up/down it may go)
  const ox = lo + ((h >>> 3) % (hi - lo + 1)), oy = Math.max(up, Math.min(down, roomY - ((h >>> 9) % 4)));
  const smooth = ctx.imageSmoothingEnabled;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(pic, dx + ox, dy + oy, w, ht);
  ctx.imageSmoothingEnabled = smooth;
}

function foamSides(z, gx, gy) {
  let out = "";
  for (const [side, dx, dy] of [["N", 0, -1], ["E", 1, 0], ["S", 0, 1], ["W", -1, 0]]) {
    const c = cellAtTile(z, gx + dx, gy + dy);
    if (c && c[0] && !info(c[0]).water) out += side;
  }
  return out;
}

function foamDistance(ctx, dx, dy, sides) {
  // How far (0-5) each pixel of the cell is from land (anim.py foam_distance)
  const tw = G.tw, th = G.th, W = tw + 8, H = th + 8;
  if (!cache.scratch) {
    cache.scratch = document.createElement("canvas");
    cache.scratch.width = tw; cache.scratch.height = th;
    cache.scratchCtx = cache.scratch.getContext("2d", { willReadFrequently: true });
  }
  const sc = cache.scratchCtx;
  sc.clearRect(0, 0, tw, th);
  sc.drawImage(ctx.canvas, dx, dy, tw, th, 0, 0, tw, th);
  const data = sc.getImageData(0, 0, tw, th).data;
  let land = new Uint8Array(W * H);
  let any = false;
  for (let y = 0; y < th; y++) for (let x = 0; x < tw; x++) {
    const p = (y * tw + x) * 4;
    const r = data[p], g = data[p + 1], b = data[p + 2];
    const isLand = !((b > r + 20) && (b >= g - 10));
    if (isLand) { land[(y + 4) * W + x + 4] = 1; any = true; }
  }
  const fill = (x0, y0, x1, y1) => { for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) land[y * W + x] = 1; any = true; };
  if (sides.includes("N")) fill(0, 0, W, 4);
  if (sides.includes("S")) fill(0, th + 4, W, H);
  if (sides.includes("W")) fill(0, 0, 4, H);
  if (sides.includes("E")) fill(tw + 4, 0, W, H);
  if (!any) return null;
  const d = new Int8Array(W * H).fill(9);
  for (let i = 0; i < W * H; i++) if (land[i]) d[i] = 0;
  let cur = land;
  for (let k = 1; k <= 5; k++) {
    const grown = cur.slice();
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (cur[y * W + x]) continue;
      for (let j = -1; j <= 1 && !grown[y * W + x]; j++) for (let i = -1; i <= 1; i++) {
        const xx = x + i, yy = y + j;
        if (xx >= 0 && yy >= 0 && xx < W && yy < H && cur[yy * W + xx]) { grown[y * W + x] = 1; d[y * W + x] = k; break; }
      }
    }
    cur = grown;
  }
  const out = new Int8Array(tw * th);
  for (let y = 0; y < th; y++) for (let x = 0; x < tw; x++) out[y * tw + x] = d[(y + 4) * W + x + 4];
  return out;
}

function foamOverlay(dist, k) {
  const tw = G.tw, th = G.th;
  const c = document.createElement("canvas");
  c.width = tw; c.height = th;
  const x = c.getContext("2d");
  const im = x.createImageData(tw, th);
  const col = foamColour();
  const phase = k * 2 * Math.PI / animSetting("Water.Frames");
  const swell = Math.sin(phase) > 0.3 ? 1 : 0;
  for (let yy = 0; yy < th; yy++) for (let xx = 0; xx < tw; xx++) {
    const di = dist[yy * tw + xx];
    const wave = 0.5 + 0.5 * Math.sin(2 * Math.PI * (xx + yy) / 16 + phase);
    const d = di - swell;
    let a = 0;
    if (d >= 0 && d <= 1 && di > 0) a = 140;
    else if (d === 2) a = 70;
    else if (d === 3) a = 30;
    a *= 0.55 + 0.45 * wave;
    if (d === 3 && wave > 0.85) a = 120;
    if (di === 0) a = 0;
    const p = (yy * tw + xx) * 4;
    im.data[p] = col[0]; im.data[p + 1] = col[1]; im.data[p + 2] = col[2]; im.data[p + 3] = Math.min(255, a);
  }
  x.putImageData(im, 0, 0);
  return c;
}

function paintCell(ch, ci, now) {
  const m = ch.m, ctx = ch.ctx;
  const x = (ci % G.xt) + 1, y = Math.floor(ci / G.xt) + 1;
  const dx = (x - 1) * G.tw, dy = (y - 1) * G.th;
  const gx = m.mx * G.xt + x - 1, gy = m.my * G.yt + y - 1;
  const gx1 = gx + 1, gy1 = gy + 1;
  const [tile, decor, roof, group, infront, under] = cellOf(m, x, y);
  ctx.clearRect(dx, dy, G.tw, G.th);
  if (!tile) {
    ctx.fillStyle = "#000";
    ctx.fillRect(dx, dy, G.tw, G.th);
    return;
  }
  const ti = info(tile);
  if (ti.texture) {
    const t = texture(ti.texture);
    if (t) drawTextureCell(ctx, t, ((gx * G.tw) % t.width + t.width) % t.width, ((gy * G.th) % t.height + t.height) % t.height, dx, dy);
    else ch.missing = true;
  } else {
    let pic = null;
    if (ti.kind === "frames") pic = img(framesName(tile, ti.frames, gx1, gy1, now), ch);
    else if (ti.kind === "sway") pic = animFrame(tile, "s", swayFrame(gx1, now) % ti.anim.s);
    if (!pic) pic = img(tile, ch);
    if (pic) ctx.drawImage(pic, dx, dy);
    else { ctx.fillStyle = "#000"; ctx.fillRect(dx, dy, G.tw, G.th); }
  }
  if (ti.blend > 0) paintBlendEdges(ctx, m.mz, gx, gy, ti.blend, dx, dy, ch);
  const roofShown = !!roof && !(ch.hidden && group === ch.hidden);
  const sea = decor && ti.kind === "water" && !info(decor).wade;   // (a rock: the foam goes round it)
  if (sea) paintDecor(ctx, decor, gx1, now, dx, dy, ch);
  if (ti.kind === "water") {
    let f = ch.foam.get(ci);
    if (f === undefined) {
      const sides = foamSides(m.mz, gx, gy);
      f = null;
      if (sides || hasLand(tile) || sea) {
        const dist = foamDistance(ctx, dx, dy, sides);
        f = dist ? { dist, frames: new Map() } : null;
      }
      if (!ch.missing) ch.foam.set(ci, f);                        // (not on a picture still loading: it'd all be land)
    }
    if (f) {
      const k = waterFrame(now);
      let o = f.frames.get(k);
      if (!o) { o = foamOverlay(f.dist, k); f.frames.set(k, o); }
      ctx.drawImage(o, dx, dy);
    }
  } else if (ti.kind === "flame") {
    const fr = animFrame(tile, "f", flameFrame(now) % ti.anim.f);
    if (fr) ctx.drawImage(fr, dx, dy);
  }
  if (under) paintDecor(ctx, under, gx1, now, dx, dy, ch);      // (a rug, then what stands on it)
  if (decor && !sea) paintDecor(ctx, decor, gx1, now, dx, dy, ch, gy1, !roofShown);
  if (roofShown) {
    const r = img(roof, ch);
    if (r) ctx.drawImage(r, dx, dy);
  }
  if (infront) {
    const t = img(infront, ch);
    if (t) ctx.drawImage(t, dx, dy);
  }
}

function animKinds(ch, ci) {
  // How a cell moves: its counters' names ("" = it doesn't)
  const m = ch.m;
  const x = (ci % G.xt) + 1, y = Math.floor(ci / G.xt) + 1;
  const [tile, decor] = cellOf(m, x, y);
  if (!tile) return "";
  const ti = info(tile);
  let kinds = "";
  if (ti.kind === "water") {
    const f = ch.foam.get(ci);
    if (f) kinds += "w";
  } else if (ti.kind === "frames") kinds += "t" + ti.frames[1];
  else if (ti.kind === "flame") kinds += "f";
  else if (ti.kind === "sway") kinds += "s";
  if (decor) {
    const di = info(decor);
    if (di.dkind === "frames") kinds += "t" + di.frames[1];
    else if (di.dkind === "sway") kinds += "s";
    else if (di.dkind === "flame") kinds += "f";
  }
  return kinds;
}

function counter(kind, now) {
  if (kind[0] === "t") return Math.floor(now / +kind.slice(1));
  if (kind === "s") return Math.floor(now / animSetting("Sway.Speed"));
  if (kind === "w") return waterFrame(now);
  return flameFrame(now);
}

function kindList(kinds) {
  const out = [];
  for (let i = 0; i < kinds.length; i++) {
    if (kinds[i] === "t") {
      let j = i + 1;
      while (j < kinds.length && /\d/.test(kinds[j])) j++;
      out.push(kinds.slice(i, j));
      i = j - 1;
    } else out.push(kinds[i]);
  }
  return out;
}

export function updateChunk(ch, now) {
  const m = ch.m;
  if (ch.version !== m.v) { ch.version = m.v; ch.full = true; ch.foam.clear(); }
  if (anyLoaded && ch.missing) { ch.full = true; ch.foam.clear(); }   // (foam measured on a missing picture was wrong)
  const n = G.xt * G.yt;
  if (ch.full) {
    ch.full = false;
    ch.missing = false;
    ch.dirty.clear();
    for (let ci = 0; ci < n; ci++) paintCell(ch, ci, now);
    ch.anim = [];
    for (let ci = 0; ci < n; ci++) {
      const k = animKinds(ch, ci);
      if (k) ch.anim.push([ci, kindList(k)]);
    }
    ch.counters = {};
    return;
  }
  for (const ci of ch.dirty) paintCell(ch, ci, now);
  if (ch.dirty.size) {
    ch.dirty.clear();
    ch.anim = [];
    for (let ci = 0; ci < n; ci++) {
      const k = animKinds(ch, ci);
      if (k) ch.anim.push([ci, kindList(k)]);
    }
  }
  const changed = new Set();
  for (const [, kinds] of ch.anim) for (const k of kinds) {
    if (!(k in ch.counters) || ch.counters[k] !== counter(k, now)) changed.add(k);
  }
  if (!changed.size) return;
  for (const k of changed) ch.counters[k] = counter(k, now);
  for (const [ci, kinds] of ch.anim) if (kinds.some((k) => changed.has(k))) paintCell(ch, ci, now);
}

export function endFrame() { anyLoaded = false; }

export function setHiddenRoof(m, group) {
  const ch = chunks.get(m.name);
  if (!ch || ch.hidden === group) return;
  const old = ch.hidden;
  ch.hidden = group;
  for (let ci = 0; ci < G.xt * G.yt; ci++) {
    const g = m.group[ci];
    if (m.roof[ci] && (g === old || g === group)) ch.dirty.add(ci);
  }
}

export function clearHiddenRoofs(except) {
  for (const ch of chunks.values()) if (ch.m !== except && ch.hidden) setHiddenRoof(ch.m, 0);
}
