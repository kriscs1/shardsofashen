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
  // (a piece where two grounds meet on the slant: its base, and the ground in its corners - build_ground_pieces.py)
  const cBase = tileIni(name, "Corner.Base", "").trim();
  const corner = cBase ? { base: cBase, land: tileIni(name, "Corner.Land", "").trim(),
    mask: tileIni(name, "Corner.Mask", "").split(",").map((c) => c.trim()).filter(Boolean),
    leg: val(tileIni(name, "Corner.Leg", "1")) || 1 } : null;
  i = {
    decor, kind, dkind, frames: fr, anim, corner,
    blend: Math.min(9, Math.max(0, Math.floor(val(tileIni(name, "Blend", "0"))))),
    tex: tileIni(name, "Blend.Texture", name) || name,
    texture: tileIni(name, "Texture", ""),
    texFrames: Math.floor(val(tileIni(name, "Texture.Frames", "0"))),     // (a texture that moves: lava)
    texSpeed: Math.floor(val(tileIni(name, "Texture.Speed", "400"))) || 400,
    // (natural ground, rounded where it meets another: Round=1; its ground, Grass002 Grass001's; which wins a tie)
    round: flag("Round") && !decor ? name.replace(/\d+$/, "") : "",
    rank: Math.min(9, Math.max(0, Math.floor(val(tileIni(name, "Blend", "0"))))),
    water: flag("Water"),
    raised: flag("Raised"),                         // (a boardwalk: up on posts, its shadow on what's round it)
    // (a diagonal shore piece, Water002-009 or <Land>_Water002-009: the corner its land is in - region_tiles.py)
    shore: corner && flag("Water") ? corner.mask.join("") : "",
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
    this.missing = false;           // a picture the cell being painted needed hadn't loaded
    this.gaps = new Set();          // the cells painted without one: they alone are painted again when pictures come
    this.paintAt = 0;               // how far a full paint has got (a map not in view yet is painted over a few frames)
    this.used = 0;                  // when it was last in view
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
  c.used = performance.now();
  return c;
}

const CHUNKS_KEPT = 15;                // (the 3 x 3 in view and those just left: walking back paints nothing)

export function forgetChunks(keep) {
  if (chunks.size <= CHUNKS_KEPT) return;
  const old = [...chunks.entries()].filter(([name]) => !keep.has(name)).sort((a, b) => a[1].used - b[1].used);
  for (const [name] of old.slice(0, chunks.size - CHUNKS_KEPT)) chunks.delete(name);
}

function repaint(c) { c.full = true; c.paintAt = 0; c.foam.clear(); }

function paintEdge(c, dx, dy) {
  // (the map dx,dy from it has come: only the cells near that side look at it, two out for rounded corners)
  if (c.full) return;
  for (let ly = 0; ly < G.yt; ly++) {
    for (let lx = 0; lx < G.xt; lx++) {
      if ((dx > 0 && lx < G.xt - 2) || (dx < 0 && lx >= 2) || (dy > 0 && ly < G.yt - 2) || (dy < 0 && ly >= 2)) continue;
      const ci = ly * G.xt + lx;
      c.dirty.add(ci);
      c.foam.delete(ci);
    }
  }
}

export function invalidateCell(name, x, y) {
  // A cell changed (and its neighbours' edges may have, and their rounded corners two out): paint them again, across
  // map edges too
  const m = S.maps.get(name);
  if (!m) return;
  for (let dy = -2; dy <= 2; dy++) {
    for (let dx = -2; dx <= 2; dx++) {
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
  if (c) repaint(c);
  // the maps beside it paint their edges again (blending reaches over the seam)
  const m = S.maps.get(name);
  if (!m) return;
  for (const [dx, dy] of DIRS) {
    const n = mapByPos(m.mx + dx, m.my + dy, m.mz);
    const nc = n && chunks.get(n.name);
    if (nc) paintEdge(nc, -dx, -dy);                              // (its shore may meet this map's land)
  }
}

// ----- painting one cell
function blendSurface(texName, maskName, gx, gy, taper = "") {
  const big = info(texName).texture ? texture(info(texName).texture) : null;
  let key = texName + "|" + maskName + "|" + taper;
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
  if (taper) taperBand(x, maskName.replace(/^Blend_/, "").replace(/\d$/, ""), taper);
  cache.blend.set(key, c);
  return c;
}

// (a straight band of land narrowing to nothing at its end, at 45 degrees: the diagonal shore beside it starts at the
// corner they share, so the coast runs on without a step. side: the band's side; ends: "E"/"W" or "N"/"S" along it)
const BAND = 9;
function taperBand(x, side, ends) {
  const S = G.tw;
  const at = (u, v, end) => {                    // (u along the band toward its tapered end, v into the tile)
    const uu = end === "E" || end === "S" ? u : S - u;
    if (side === "N") return [uu, v];
    if (side === "S") return [uu, S - v];
    if (side === "W") return [v, uu];
    return [S - v, uu];
  };
  x.globalCompositeOperation = "destination-out";
  for (const e of ends) {
    // (a capital: narrowing to its end; small: gone from its middle on, where the ground beside it rounds away)
    const end = e.toUpperCase(), u0 = e === end ? S - BAND : S / 2 - 3, u1 = e === end ? S + 1 : S / 2 + BAND / 2;
    const pts = [[u0, S + 1], [u0, BAND], [u1, -1], [S + 1, -1], [S + 1, S + 1]].map(([u, v]) => at(u, v, end));
    x.beginPath();
    x.moveTo(...pts[0]);
    for (const pt of pts.slice(1)) x.lineTo(...pt);
    x.closePath();
    x.fill();
  }
  x.globalCompositeOperation = "source-over";
}

function shoreAt(z, gx, gy) {
  const c = cellAtTile(z, gx, gy);
  return c && c[0] ? info(c[0]).shore : "";
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

// (where two grounds meet, a few flecks of each lie over on the other's side: never along the sea's edge, whose foam goes by
// what's water, and never the same twice)
const FLECK_MIN = 2, FLECK_MAX = 15;

function flecksOf(ctx, tex, gx, gy, k, dx, dy, ch) {
  let h = (Math.imul(gx + 1, 73856093) ^ Math.imul(gy + 1, 19349663) ^ Math.imul(k + 1, 83492791)) >>> 0;
  const roll = (n) => { h = (Math.imul(h, 1664525) + 1013904223) >>> 0; return (h >>> 8) % n; };
  if (roll(10) < 3) return;                                 // (not everywhere)
  const [ddx, ddy] = DIRS[k];
  ctx.beginPath();
  for (let patch = 1 + roll(3); patch > 0; patch--) {
    const along = 3 + roll(G.tw - 6), depth = FLECK_MIN + roll(FLECK_MAX - FLECK_MIN);
    for (let bit = 2 + roll(4); bit > 0; bit--) {
      const a = along + roll(5) - 2, d = depth + roll(4) - 1, w = 1 + roll(3), hh = 1 + roll(2);
      const x = ddx ? (ddx > 0 ? G.tw - d : d) : a, y = ddy ? (ddy > 0 ? G.th - d : d) : a;
      ctx.rect(dx + Math.max(0, Math.min(G.tw - w, x)), dy + Math.max(0, Math.min(G.th - hh, y)), w, hh);
    }
  }
  paintGroundIn(ctx, tex, gx, gy, dx, dy, ch);
}

function paintBlendEdges(ctx, z, gx, gy, b, dx, dy, ch, wet = false) {
  const found = [], flecks = [];
  DIRS.forEach(([ddx, ddy, side], k) => {
    let [level, tex] = blendLevelAt(z, gx + ddx, gy + ddy);
    if (!wet && k < 4 && level > 0 && level !== b && tex && !info(tex).water) flecks.push([tex, k]);
    if (level > b && k >= 4) {
      if (blendLevelAt(z, gx + ddx, gy)[0] >= level || blendLevelAt(z, gx, gy + ddy)[0] >= level) level = 0;
    }
    if (level > b && tex && slantedToward(z, gx + ddx, gy + ddy, side)) level = 0;   // (its corner's cut away)
    if (level > b && k >= 4 && (shoreAt(z, gx + ddx, gy) || shoreAt(z, gx, gy + ddy))) level = 0;   // (a diagonal
    //  shore beside it already runs to that corner: no blob of land filling it)
    if (level > b && k >= 4 && roundedAway(z, gx + ddx, gy + ddy, -ddx, -ddy)) level = 0;   // (its corner here's
    //  another ground's now, rounded into it)
    if (level > b && k < 4 && capped(z, gx, gy, k)) level = 0;   // (a lone tile, a tongue's end: the curve is its edge)
    let taper = "";
    if (level > b && k < 4) {                    // (an end of the band where a diagonal shore's coast starts)
      const along = ddy ? [[1, 0, "E", "W"], [-1, 0, "W", "E"]] : [[0, 1, "S", "N"], [0, -1, "N", "S"]];
      for (const [ex, ey, end, back] of along) {
        // (beside this tile, its land on the band's side and toward that end; or beside the land, its land on the
        //  band's side and back toward it: either way its coast runs from this tile's corner there)
        const by = shoreAt(z, gx + ex, gy + ey), past = shoreAt(z, gx + ex + ddx, gy + ey + ddy);
        if ((by && by.includes(side) && by.includes(end)) || (past && past.includes(side) && past.includes(back))) {
          taper += end;
        }
      }
      for (const [ex, ey, end] of ddy ? [[1, 0, "e"], [-1, 0, "w"]] : [[0, 1, "s"], [0, -1, "n"]]) {
        // (and where its corner's rounded away: gone from the middle on)
        if (!taper.includes(end.toUpperCase()) && roundedAway(z, gx + ddx, gy + ddy, ex || -ddx, ey || -ddy)) taper += end;
      }
    }
    if (level > b && tex) {
      const variant = 1 + (Math.abs((gx + 1) * 7 + (gy + 1) * 13) % 2);
      found.push([level, found.length, tex, "Blend_" + side + variant, taper]);
    }
  });
  found.sort((a, b2) => a[0] - b2[0] || a[1] - b2[1]);
  for (const [, , tex, maskName, taper] of found) {
    const s = blendSurface(tex, maskName, gx, gy, taper);
    if (s) ctx.drawImage(s, dx, dy);
    else ch.missing = true;
  }
  for (const [tex, k] of flecks) flecksOf(ctx, tex, gx, gy, k, dx, dy, ch);
}

// ----- mountains' corners cut on the slant: no right angles where a range turns
const CORNERS = [["N", "E", 0, -1, 1, 0], ["E", "S", 1, 0, 0, 1], ["S", "W", 0, 1, -1, 0], ["W", "N", -1, 0, 0, -1]];

function isRange(name) {
  // A mountain: painted from a range's texture (build_terrain.py), or the cave mouth set in one
  if (!name) return false;
  const i = info(name);
  return (i.texture || "").startsWith("Range_") || name.startsWith("Cave_Mouth");
}

function cornerPath(ctx, k, dx, dy, gx, gy, leg = 1) {
  // The triangle at corner k (0 NE, 1 SE, 2 SW, 3 NW) of a cell, its legs leg of the cell's sides, its long side a
  // little rough
  const w = G.tw, h = G.th;
  const c = [[w, 0], [w, h], [0, h], [0, 0]][k];          // (the corner itself)
  const a0 = [[0, 0], [w, 0], [w, h], [0, h]][k], b0 = [[w, h], [0, h], [0, 0], [w, 0]][k];
  const a = [c[0] + (a0[0] - c[0]) * leg, c[1] + (a0[1] - c[1]) * leg];
  const b = [c[0] + (b0[0] - c[0]) * leg, c[1] + (b0[1] - c[1]) * leg];
  ctx.beginPath();
  ctx.moveTo(dx + c[0], dy + c[1]);
  ctx.lineTo(dx + a[0], dy + a[1]);
  for (let i = 1; i < 6; i++) {
    const t = i / 6, hsh = ((gx * 31 + gy * 17 + k * 7 + i * 13) % 5) - 2;     // (the same each time it's painted)
    const ox = (k === 0 || k === 2 ? 1 : -1) * hsh * 0.7, oy = hsh * 0.7;
    ctx.lineTo(dx + a[0] + (b[0] - a[0]) * t + ox, dy + a[1] + (b[1] - a[1]) * t + oy);
  }
  ctx.lineTo(dx + b[0], dy + b[1]);
  ctx.closePath();
}

// (a corner piece's two tips, 0 NE 1 SE 2 SW 3 NW: the neighbour whose own corner runs on from it along the same
//  edge, and where its land is thickened to so the two round into each other instead of meeting in a point)
const TIPS = [[[-1, 0, "NW", 0, 1], [0, 1, "SE", 1, 0]], [[0, -1, "NE", 1, 0], [-1, 0, "SW", 0, 1]],
  [[1, 0, "SE", 0, 1], [0, -1, "NW", 1, 0]], [[0, 1, "SW", 1, 0], [1, 0, "NE", 0, 1]]];
const JOIN = 0.4;                                  // (how thick the land is where two pieces' corners meet)

function cornerJoins(z, gx, gy, k) {
  // [tip a joined?, tip b joined?] of corner k of the piece at gx, gy: a whole-tile corner whose neighbour has the
  // corner that carries on along that edge
  return TIPS[k].map(([ox, oy, want]) => {
    const c = cellAtTile(z, gx + ox, gy + oy);
    const o = c && c[0] ? info(c[0]).corner : null;
    return !!(o && o.leg >= 1 && o.mask.includes(want));
  });
}

function joinedCornerPath(ctx, k, dx, dy, joins) {
  // The corner's land, thickened at a joined tip and curved between, so it runs on into its neighbour's
  const w = G.tw, h = G.th;
  const c = [[w, 0], [w, h], [0, h], [0, 0]][k];
  const a = [[0, 0], [w, 0], [w, h], [0, h]][k], b = [[w, h], [0, h], [0, 0], [w, 0]][k];
  const ext = (tip, t) => {                       // (in from the tip, along the cell's other edge)
    const [, , , ix, iy] = TIPS[k][t];
    return [tip[0] + (tip[0] ? -1 : 1) * ix * w * JOIN, tip[1] + (tip[1] ? -1 : 1) * iy * h * JOIN];
  };
  const ea = joins[0] ? ext(a, 0) : a, eb = joins[1] ? ext(b, 1) : b;
  ctx.beginPath();
  ctx.moveTo(dx + c[0], dy + c[1]);
  ctx.lineTo(dx + a[0], dy + a[1]);
  ctx.lineTo(dx + ea[0], dy + ea[1]);
  ctx.quadraticCurveTo(dx + (a[0] + b[0]) / 2 + (c[0] - (a[0] + b[0]) / 2) * 0.1,
    dy + (a[1] + b[1]) / 2 + (c[1] - (a[1] + b[1]) / 2) * 0.1, dx + eb[0], dy + eb[1]);
  ctx.lineTo(dx + b[0], dy + b[1]);
  ctx.closePath();
}

function paintGroundIn(ctx, name, gx, gy, dx, dy, ch, clip = true) {
  // name's ground drawn where the path is (a texture: its part for this cell, so it carries on unbroken)
  const i = info(name);
  ctx.save();
  if (clip) ctx.clip();
  if (i.texture) {
    const t = texture(i.texture);
    if (t) drawTextureCell(ctx, t, ((gx * G.tw) % t.width + t.width) % t.width, ((gy * G.th) % t.height + t.height) % t.height, dx, dy);
    else ch.missing = true;
  } else {
    const p = img(name, ch);
    if (p) ctx.drawImage(p, dx, dy);
  }
  ctx.restore();
}

function cutsOf(z, gx, gy, at) {
  // A mountain's corners cut on the slant: where it has open ground on two touching sides and between them
  const out = [];
  CORNERS.forEach(([, , ax, ay, bx, by], k) => {
    const a = at(gx + ax, gy + ay), b = at(gx + bx, gy + by), d = at(gx + ax + bx, gy + ay + by);
    if (a && b && !isRange(a) && !isRange(b) && !isRange(d)) out.push([k, a, b]);
  });
  return out;
}

// (a mountain beside a cell, on its side: the corners of the mountain that touch the cell)
const TOUCHING = { N: [1, 2], E: [2, 3], S: [0, 3], W: [0, 1], NE: [2], SE: [3], SW: [0], NW: [1] };

function slantedToward(z, nx, ny, side) {
  // Is the mountain at nx, ny cut away where it meets the cell on its side? (then it doesn't spill its edge there)
  const at = (x, y) => { const c = cellAtTile(z, x, y); return c ? c[0] : ""; };
  const tile = at(nx, ny);
  if (!isRange(tile) || tile.startsWith("Cave_Mouth")) return false;
  const near = TOUCHING[side];
  return cutsOf(z, nx, ny, at).some(([k]) => near.includes(k));
}

function paintSlants(ctx, z, gx, gy, tile, dx, dy, ch) {
  // Outer corners of a range cut away (a staircase edge becomes a slope); a bay's inner corner, where the
  // mountains either side stay whole, filled with rock (so it isn't a right angle either)
  if (tile.startsWith("Cave_Mouth")) return;                 // (its own picture: left whole)
  const at = (x, y) => { const c = cellAtTile(z, x, y); return c ? c[0] : ""; };
  if (isRange(tile)) {
    for (const [k, a, b] of cutsOf(z, gx, gy, at)) {
      const ground = info(a).kind || isDecorTile(a) ? b : a;
      if (info(ground).kind || isDecorTile(ground)) continue; // (not water, or anything that moves)
      cornerPath(ctx, k, dx, dy, gx, gy);
      paintGroundIn(ctx, ground, gx, gy, dx, dy, ch);
    }
    return;
  }
  if (info(tile).kind || !(info(tile).blend > 0)) return;     // (open ground only: not water, floors or walls)
  CORNERS.forEach(([, , ax, ay, bx, by], k) => {
    const a = at(gx + ax, gy + ay), b = at(gx + bx, gy + by), d = at(gx + ax + bx, gy + ay + by);
    if (!(isRange(a) && isRange(b) && isRange(d))) return;
    if (cutsOf(z, gx + ax, gy + ay, at).length || cutsOf(z, gx + bx, gy + by, at).length) return;
    const rock = [a, b, d].find((n) => !n.startsWith("Cave_Mouth"));
    if (!rock) return;
    cornerPath(ctx, k, dx, dy, gx, gy);
    paintGroundIn(ctx, rock, gx, gy, dx, dy, ch);
  });
}

// ----- where natural grounds meet: rounded, worked out at every corner of the grid from the four cells round it
// (Tiles.ini Round=1). A cell's corner whose two neighbours beside it there are both another ground takes that ground,
// out to the middle of its two edges (where the ground beside it meets it too, so the coast runs on unbroken), on a
// curve: so a lone tile is round, a staircase of them a slope, an inlet's end a bay, and where it's two and two across
// the corner the higher ground (Blend) runs through. The curve leaves each edge along it (no angle where it starts),
// and how full it is is the corner's own (the same from every cell round it), so no two islets are quite alike.
const QUAD = [[1, -1], [1, 1], [-1, 1], [-1, -1]];   // (0 NE, 1 SE, 2 SW, 3 NW: the way to its neighbours there)
const INSET = 5;   // (where the ground filling a corner spills over this one's edges anyway (a higher Blend), its curve
//  runs that far in, round the corner of its bands: else it'd be under them, and the corner square)

function roundOf(z, gx, gy) {
  const c = cellAtTile(z, gx, gy);
  return c && c[0] ? info(c[0]) : null;
}

function roundsAt(z, gx, gy, ti) {
  // [[corner, the tile whose ground fills it]] of a cell
  const out = [];
  if (!ti || !ti.round || ti.corner) return out;
  QUAD.forEach(([sx, sy], k) => {
    const a = roundOf(z, gx + sx, gy), b = roundOf(z, gx, gy + sy), d = roundOf(z, gx + sx, gy + sy);
    if (!a || !b || !a.round || a.round !== b.round || a.round === ti.round) return;
    if (d && d.round === ti.round && (a.rank < ti.rank || (a.rank === ti.rank && a.round < ti.round))) return;
    const c = cellAtTile(z, gx + sx, gy);
    out.push([k, c[0]]);
  });
  return out;
}

function roundedAway(z, gx, gy, sx, sy) {
  // Is the cell's corner toward (sx, sy) another ground's, rounded into it? (then its own doesn't spill out there)
  const k = QUAD.findIndex(([a, b]) => a === sx && b === sy);
  return roundsAt(z, gx, gy, roundOf(z, gx, gy)).some(([kk]) => kk === k);
}

const SIDE_CORNERS = [[0, 3], [0, 1], [1, 2], [2, 3]];   // (N, E, S, W: as DIRS)

function capped(z, gx, gy, side) {
  // Both this cell's corners on that side rounded away? (then that side's all curve: no band along it)
  const fills = roundsAt(z, gx, gy, roundOf(z, gx, gy));
  return SIDE_CORNERS[side].every((k) => fills.some(([kk]) => kk === k));
}

function roundPath(ctx, k, dx, dy, vx, vy, insetH, insetV) {
  // The corner k's fill: from the corner to the middle of its two edges, (inset from them: its north or south edge by
  // insetH, the other by insetV,) a curve between that runs on from each, pulled toward the corner by the grid
  // corner's (vx, vy) own amount
  const w = G.tw, h = G.th;
  const c = [[w, 0], [w, h], [0, h], [0, 0]][k];
  const ix = c[0] ? -insetV : insetV, iy = c[1] ? -insetH : insetH;
  const p = [w / 2, c[1]], q = [c[0], h / 2], p2 = [p[0], p[1] + iy], q2 = [q[0] + ix, q[1]], c2 = [c[0] + ix, c[1] + iy];
  const hsh = ((vx * 73856093) ^ (vy * 19349663)) >>> 0;
  const pull = 0.4 + (hsh % 1000) / 1000 * 0.3;
  ctx.beginPath();
  ctx.moveTo(dx + c[0], dy + c[1]);
  ctx.lineTo(dx + p[0], dy + p[1]);
  ctx.lineTo(dx + p2[0], dy + p2[1]);
  ctx.bezierCurveTo(dx + p2[0] + (c2[0] - p2[0]) * pull, dy + p2[1] + (c2[1] - p2[1]) * pull,
    dx + q2[0] + (c2[0] - q2[0]) * pull, dy + q2[1] + (c2[1] - q2[1]) * pull, dx + q2[0], dy + q2[1]);
  ctx.lineTo(dx + q[0], dy + q[1]);
  ctx.closePath();
}

function paintRounds(ctx, z, gx, gy, ti, dx, dy, ch) {
  // This cell's corners where another ground rounds into it; true if any of them is water
  let wet = false;
  const fills = roundsAt(z, gx, gy, ti);
  const rounded = (k) => fills.some(([kk]) => kk === k);
  for (const [k, other] of fills) {
    const [sx, sy] = QUAD[k];
    // (no bands to run round on a ground with no Blend of its own, nor along an edge rounded at both ends: capped)
    const inset = ti.blend > 0 && info(other).rank > ti.rank ? INSET : 0;
    roundPath(ctx, k, dx, dy, gx + (sx > 0 ? 1 : 0), gy + (sy > 0 ? 1 : 0), rounded(3 - k) ? 0 : inset, rounded(k ^ 1) ? 0 : inset);
    paintGroundIn(ctx, other, gx, gy, dx, dy, ch);
    if (info(other).water && !ti.water) wet = true;
  }
  return wet;
}

// ----- what's raised off the ground (Tiles.ini Raised=1: a boardwalk on its posts): the light from the top left, so
// its shadow falls south and east of it, and its front edge shows where it ends
function raisedAt(z, gx, gy) {
  const c = cellAtTile(z, gx, gy);
  return !!(c && c[0] && info(c[0]).raised);
}

function shadowBand(ctx, x, y, w, h, vertical, a) {
  const g = vertical ? ctx.createLinearGradient(x, y, x + w, y) : ctx.createLinearGradient(x, y, x, y + h);
  g.addColorStop(0, `rgba(10,8,6,${a})`);
  g.addColorStop(1, "rgba(10,8,6,0)");
  ctx.fillStyle = g;
  ctx.fillRect(x, y, w, h);
}

function paintRaised(ctx, z, gx, gy, ti, dx, dy) {
  const tw = G.tw, th = G.th;
  const n = raisedAt(z, gx, gy - 1), s = raisedAt(z, gx, gy + 1), w = raisedAt(z, gx - 1, gy), e = raisedAt(z, gx + 1, gy);
  if (ti.raised) {
    if (!s) {                                      // (its front: the planks' ends and the beam under them)
      ctx.fillStyle = "rgba(150,128,96,0.55)"; ctx.fillRect(dx, dy + th - 4, tw, 1);
      ctx.fillStyle = "rgba(34,24,16,0.9)"; ctx.fillRect(dx, dy + th - 3, tw, 3);
    }
    if (!n) { ctx.fillStyle = "rgba(255,240,210,0.22)"; ctx.fillRect(dx, dy, tw, 1); }
    if (!w) { ctx.fillStyle = "rgba(255,240,210,0.18)"; ctx.fillRect(dx, dy, 1, th); }
    if (!e) { ctx.fillStyle = "rgba(20,14,10,0.5)"; ctx.fillRect(dx + tw - 2, dy, 2, th); }
    return;
  }
  if (n) {                                         // (its shadow, and the posts it stands on going down)
    shadowBand(ctx, dx, dy, tw, 8, false, 0.5);
    for (const px of [5, tw - 8]) {
      ctx.fillStyle = "rgb(56,42,30)"; ctx.fillRect(dx + px, dy, 3, 6);
      ctx.fillStyle = "rgb(30,22,16)"; ctx.fillRect(dx + px + 2, dy, 1, 6);
      ctx.fillStyle = "rgba(20,30,20,0.6)"; ctx.fillRect(dx + px - 1, dy + 6, 5, 1);   // (where it goes in)
    }
  }
  if (w) shadowBand(ctx, dx, dy, 5, th, true, 0.4);
  if (!n && !w && raisedAt(z, gx - 1, gy - 1)) shadowBand(ctx, dx, dy, 5, 5, false, 0.35);
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

// (a water cell's sides beside land: the halves where that land's own corner is water now - rounded into it - get
//  no band of land: [side, half (0 west or north, 1 east or south), the neighbour, its corner touching that half])
const HALVES = [["N", 0, 0, -1, 2], ["N", 1, 0, -1, 1], ["E", 0, 1, 0, 3], ["E", 1, 1, 0, 2],
  ["S", 0, 0, 1, 3], ["S", 1, 0, 1, 0], ["W", 0, -1, 0, 0], ["W", 1, -1, 0, 1]];

function wetHalves(z, gx, gy) {
  const out = new Set();
  for (const [side, half, ox, oy, k] of HALVES) {
    const n = roundOf(z, gx + ox, gy + oy);
    if (!n || n.water) continue;
    const r = roundsAt(z, gx + ox, gy + oy, n).find(([kk]) => kk === k);
    if (r && info(r[1]).water) out.add(side + half);
  }
  return out;
}

function foamDistance(ctx, dx, dy, sides, skip = new Set()) {
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
  const hw = 4 + tw / 2, hh = 4 + th / 2;          // (a side in its two halves: one skipped where it's water now)
  const band = (side, a, b) => { if (!skip.has(side + "0")) a(); if (!skip.has(side + "1")) b(); };
  if (sides.includes("N")) band("N", () => fill(0, 0, hw, 4), () => fill(hw, 0, W, 4));
  if (sides.includes("S")) band("S", () => fill(0, th + 4, hw, H), () => fill(hw, th + 4, W, H));
  if (sides.includes("W")) band("W", () => fill(0, 0, 4, hh), () => fill(0, hh, 4, H));
  if (sides.includes("E")) band("E", () => fill(tw + 4, 0, W, hh), () => fill(tw + 4, hh, W, H));
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
  if (ti.corner) {
    // (two grounds on the slant: the base, then each corner's land from its own ground, so it matches what's beside)
    paintGroundIn(ctx, ti.corner.base, gx, gy, dx, dy, ch, false);
    for (const c of ti.corner.mask) {
      const k = ["NE", "SE", "SW", "NW"].indexOf(c);
      if (k < 0 || !ti.corner.land) continue;
      const joins = ti.corner.leg >= 1 ? cornerJoins(m.mz, gx, gy, k) : [false, false];
      if (joins[0] || joins[1]) joinedCornerPath(ctx, k, dx, dy, joins);
      else cornerPath(ctx, k, dx, dy, gx, gy, ti.corner.leg);
      paintGroundIn(ctx, ti.corner.land, gx, gy, dx, dy, ch);
    }
  } else if (ti.texture) {
    const t = texture(ti.texFrames ? `${ti.texture}_${Math.floor(now / ti.texSpeed) % ti.texFrames}` : ti.texture);
    if (t && ti.raised && !raisedAt(m.mz, gx, gy - 1) && !raisedAt(m.mz, gx, gy + 1) &&
        (raisedAt(m.mz, gx - 1, gy) || raisedAt(m.mz, gx + 1, gy))) {
      // (a boardwalk running east and west: its planks across the way, turned a quarter, carrying on along the run)
      ctx.save();
      ctx.translate(dx + G.tw / 2, dy + G.th / 2);
      ctx.rotate(Math.PI / 2);
      drawTextureCell(ctx, t, ((gy * G.tw) % t.width + t.width) % t.width, ((-gx * G.th) % t.height + t.height) % t.height,
        -G.tw / 2, -G.th / 2);
      ctx.restore();
    } else if (t) drawTextureCell(ctx, t, ((gx * G.tw) % t.width + t.width) % t.width, ((gy * G.th) % t.height + t.height) % t.height, dx, dy);
    else ch.missing = true;
  } else {
    let pic = null;
    if (ti.kind === "frames") pic = img(framesName(tile, ti.frames, gx1, gy1, now), ch);
    else if (ti.kind === "sway") pic = animFrame(tile, "s", swayFrame(gx1, now) % ti.anim.s);
    if (!pic) pic = img(tile, ch);
    if (pic && ti.raised && !raisedAt(m.mz, gx, gy - 1) && !raisedAt(m.mz, gx, gy + 1) &&
        (raisedAt(m.mz, gx - 1, gy) || raisedAt(m.mz, gx + 1, gy))) {
      // (a boardwalk running east and west: its planks across the way, turned a quarter)
      ctx.save();
      ctx.translate(dx + G.tw / 2, dy + G.th / 2);
      ctx.rotate(Math.PI / 2);
      ctx.drawImage(pic, -G.tw / 2, -G.th / 2);
      ctx.restore();
    } else if (pic) ctx.drawImage(pic, dx, dy);
    else { ctx.fillStyle = "#000"; ctx.fillRect(dx, dy, G.tw, G.th); }
  }
  if (ti.blend > 0 && !ti.water) paintBlendEdges(ctx, m.mz, gx, gy, ti.blend, dx, dy, ch);
  else if (ti.blend > 0) paintBlendEdges(ctx, m.mz, gx, gy, ti.blend, dx, dy, ch, true);
  const wet = paintRounds(ctx, m.mz, gx, gy, ti, dx, dy, ch);
  paintSlants(ctx, m.mz, gx, gy, tile, dx, dy, ch);
  paintRaised(ctx, m.mz, gx, gy, ti, dx, dy);
  const roofShown = !!roof && !(ch.hidden && group === ch.hidden);
  const sea = decor && ti.kind === "water" && !info(decor).wade;   // (a rock: the foam goes round it)
  if (sea) paintDecor(ctx, decor, gx1, now, dx, dy, ch);
  if (ti.kind === "water" || wet) {               // (and a corner of water rounded into the land: its foam too)
    let f = ch.foam.get(ci);
    if (f === undefined) {
      const sides = ti.kind === "water" ? foamSides(m.mz, gx, gy) : "";
      f = null;
      if (sides || hasLand(tile) || sea || wet) {
        const dist = foamDistance(ctx, dx, dy, sides, ti.kind === "water" ? wetHalves(m.mz, gx, gy) : undefined);
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
  } else if (ti.kind === "flame" && !ti.texFrames) {
    const fr = animFrame(tile, "f", flameFrame(now) % ti.anim.f);
    if (fr) ctx.drawImage(fr, dx, dy);
    if (fr && ti.round) paintRounds(ctx, m.mz, gx, gy, ti, dx, dy, ch);   // (lava's flames fill the cell: its corners over them)
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
  else if (ti.texFrames) kinds += "t" + ti.texSpeed;
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

function paintKept(ch, ci, now) {
  ch.missing = false;
  paintCell(ch, ci, now);
  if (ch.missing) ch.gaps.add(ci); else ch.gaps.delete(ci);
}

const SLICE_MS = 4;                    // (of a frame, for painting maps not in view yet: walking on never waits for them)
let sliceEnd = 0;

export function updateChunk(ch, now, seen = true) {
  const m = ch.m;
  if (ch.version !== m.v) { ch.version = m.v; repaint(ch); }
  if (anyLoaded && ch.gaps.size) {                                    // (foam measured on a missing picture was wrong)
    for (const ci of ch.gaps) { ch.dirty.add(ci); ch.foam.delete(ci); }
  }
  const n = G.xt * G.yt;
  if (ch.full) {
    if (!ch.paintAt) { ch.dirty.clear(); ch.gaps.clear(); }
    if (!seen && !sliceEnd) sliceEnd = performance.now() + SLICE_MS;
    while (ch.paintAt < n) {
      paintKept(ch, ch.paintAt++, now);
      if (!seen && performance.now() >= sliceEnd) return;             // (carried on next frame)
    }
    ch.full = false;
    ch.paintAt = 0;
    ch.anim = [];
    for (let ci = 0; ci < n; ci++) {
      const k = animKinds(ch, ci);
      if (k) ch.anim.push([ci, kindList(k)]);
    }
    ch.counters = {};
    return;
  }
  for (const ci of ch.dirty) paintKept(ch, ci, now);
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
  for (const [ci, kinds] of ch.anim) if (kinds.some((k) => changed.has(k))) paintKept(ch, ci, now);
}

export function endFrame() { anyLoaded = false; sliceEnd = 0; }

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
