// The small things on the ground, drawn here only (the server knows nothing of them): a shadow under whoever stands
// there, the prints they leave in snow, sand and mud, the rings round a swimmer or a boat, a person's likeness in the
// water at their feet, and the sparks over a fire. All cheap: nothing worked out again that needn't be, and Options
// can turn them off (the rain's splashes too: sky.js).
import { G, S, cellAtTile, cellOf } from "./state.js";
import { entityIni, tileIni } from "./assets.js";
import { shadowLight, fogCovers, SPLASH } from "./sky.js";
import { val } from "./util.js";
import { T } from "./verbs.js";

export const FX = { on: true };

export function setEffects(on) {
  FX.on = !!on;
  SPLASH.on = FX.on;
  if (!FX.on) { prints.length = 0; rings.length = 0; walked.clear(); }
}

const kinds = new Map();                      // kind -> { shadow, lift, embers, vehicle }
function kindOf(e) {
  const name = e.k === T.PLAYER ? "" : e.n;   // (a player's n is their name: a person, as drawn)
  let k = kinds.get(name);
  if (!k) {
    k = name ? { shadow: entityIni(name, "Shadow", "1").trim() !== "0", lift: val(entityIni(name, "Shadow.Lift", "0")),
      embers: val(entityIni(name, "Embers", "0")), vehicle: entityIni(name, "Vehicle", "0").trim() === "1",
      swarm: val(entityIni(name, "Swarm", "0")) > 0 } : { shadow: true, lift: 0, embers: 0, vehicle: false, swarm: false };
    kinds.set(name, k);
  }
  return k;
}

const grounds = new Map();                    // tile -> { water, prints: [r, g, b, a, ms] | null, embers }
function groundOf(tile) {
  let g = grounds.get(tile);
  if (!g) {
    const p = tileIni(tile, "Prints", "").trim().split(/\s+/).map(Number);
    g = { water: tileIni(tile, "Water", "0").trim() === "1", prints: p.length === 5 && p.every((n) => !Number.isNaN(n))
      ? [p[0], p[1], p[2], p[3] / 255, p[4] * 1000] : null, embers: val(tileIni(tile, "Embers", "0")) };
    grounds.set(tile, g);
  }
  return g;
}

function groundAt(x, y) {
  const c = cellAtTile(S.mapZ, Math.floor(x / G.tw), Math.floor(y / G.th));
  return c && c[0] ? groundOf(c[0]) : null;
}

// ----- shadows: an oval, darker in its middle, made once for each size
const ovals = new Map();
function oval(rx, ry) {
  const key = rx * 100 + ry;
  let c = ovals.get(key);
  if (!c) {
    c = document.createElement("canvas");
    c.width = rx * 2; c.height = ry * 2;
    const g = c.getContext("2d"), im = g.createImageData(c.width, c.height);
    for (let y = 0; y < c.height; y++) {
      for (let x = 0; x < c.width; x++) {
        const dx = (x + 0.5 - rx) / rx, dy = (y + 0.5 - ry) / ry, d = dx * dx + dy * dy;
        if (d > 1) continue;
        im.data.set([16, 12, 8, d < 0.45 ? 255 : d < 0.8 ? 190 : 110], (y * c.width + x) * 4);
      }
    }
    g.putImageData(im, 0, 0);
    ovals.set(key, c);
  }
  return c;
}

const SHADOW = 0.32;                          // (how dark at noon on a clear day)
const ITEM_SCALE = 0.75;                      // (render.js MAPITEM_SCALE: things on the ground are drawn smaller)

// Under everyone in view (shown, and you): drawn after the ground, before anything stands on it
export function drawShadows(ctx, ents, cam, now, underRoof, riding) {
  if (!FX.on) return;
  const light = shadowLight(now, underRoof);
  if (light <= 0.05) return;
  for (const e of ents) {
    if (e.gh || e.zz || riding(e)) continue;
    let rx, ry, y, a = SHADOW * light;
    if (e.k === T.MAPITEM) {
      rx = Math.max(3, Math.round(e.w * ITEM_SCALE * 0.34));
      ry = Math.max(1, Math.round(rx * 0.4));
      y = e.dy + e.h - 1;
      a *= 0.8;
    } else if (e.k === T.PLAYER || e.k === T.NPC) {
      const k = kindOf(e);
      if (!k.shadow || k.swarm) continue;
      const feet = e.dy + e.h - 2;
      if (!k.lift && !k.vehicle) {
        const g = groundAt(e.dx + e.w / 2, feet);
        if (g && g.water) continue;           // (a swimmer: its rings instead)
      }
      rx = Math.max(4, Math.round(e.w * (k.lift ? 0.2 : 0.3)));
      ry = Math.max(2, Math.round(rx * 0.38));
      y = feet + k.lift;
      if (k.lift) a *= 0.6;
    } else continue;
    ctx.globalAlpha = a;
    ctx.drawImage(oval(rx, ry), Math.round(e.dx + e.w / 2 - rx - cam.x), Math.round(y - ry - cam.y));
  }
  ctx.globalAlpha = 1;
}

// ----- prints and rings: left as things move (yours and everyone's in view), kept a while, then they fade
const prints = [];                            // [x, y, z, born, r, g, b, a, ms]
const rings = [];                             // [x, y, z, born, size]
const walked = new Map();                     // uid -> [x, y, gone, side, still since]
const STRIDE = 10, RIPPLE_EVERY = 16, RING_MS = 1300, IDLE_RING_MS = 2400;

export function trackGround(ents, now, riding) {
  if (!FX.on) return;
  if (walked.size > 400) walked.clear();
  for (const e of ents) {
    if ((e.k !== T.PLAYER && e.k !== T.NPC) || e.gh || riding(e)) continue;
    const k = kindOf(e);
    if (k.lift || k.swarm) continue;
    const fx = e.dx + e.w / 2, fy = e.dy + e.h - 3;
    let w = walked.get(e.u);
    if (!w || Math.abs(fx - w[0]) > 64 || Math.abs(fy - w[1]) > 64) {
      walked.set(e.u, [fx, fy, 0, 1, now]);
      continue;
    }
    const step = Math.hypot(fx - w[0], fy - w[1]);
    const g = groundAt(fx, fy);
    if (step < 0.01) {
      if (g && g.water && now - w[4] > IDLE_RING_MS) {      // (floating still: a ring now and then)
        w[4] = now + (e.u % 7) * 120;
        ring(fx, fy, now, k.vehicle ? e.w * 0.3 : 4);
      }
      continue;
    }
    w[2] += step;
    const dx = (fx - w[0]) / step, dy = (fy - w[1]) / step;
    w[0] = fx; w[1] = fy; w[4] = now;
    if (!g) continue;
    if (g.water && w[2] >= RIPPLE_EVERY) {
      w[2] = 0;
      ring(fx, fy, now, k.vehicle ? e.w * 0.3 : 4);
    } else if (g.prints && !k.vehicle && w[2] >= STRIDE) {
      w[2] = 0;
      w[3] = -w[3];                           // (left foot, right foot: either side of the way it goes)
      const o = w[3] * Math.max(2, Math.round(e.w * 0.08));
      if (prints.length >= 240) prints.shift();
      prints.push([fx - dy * o, fy + dx * o, S.mapZ, now, ...g.prints]);
    }
  }
}

function ring(x, y, now, size) {
  if (rings.length >= 60) rings.shift();
  rings.push([x, y, S.mapZ, now, size]);
}

export function drawGroundMarks(ctx, cam, now, ww, wh) {
  if (!FX.on) return;
  let keep = 0;
  for (const p of prints) {
    const t = (now - p[3]) / p[8];
    if (t >= 1) continue;
    prints[keep++] = p;
    if (p[2] !== S.mapZ) continue;
    const x = Math.round(p[0] - cam.x), y = Math.round(p[1] - cam.y);
    if (x < -4 || y < -4 || x > ww + 4 || y > wh + 4) continue;
    ctx.fillStyle = `rgba(${p[4]},${p[5]},${p[6]},${p[7] * (t < 0.6 ? 1 : (1 - t) / 0.4)})`;
    ctx.fillRect(x - 1, y - 1, 2, 3);
  }
  prints.length = keep;
  keep = 0;
  ctx.lineWidth = 1;
  for (const r of rings) {
    const t = (now - r[3]) / RING_MS;
    if (t >= 1 || t < 0) { if (t < 0) rings[keep++] = r; continue; }
    rings[keep++] = r;
    if (r[2] !== S.mapZ) continue;
    const rx = r[4] + t * 12;
    ctx.strokeStyle = `rgba(226,240,255,${0.55 * (1 - t)})`;
    ctx.beginPath();
    ctx.ellipse(Math.round(r[0] - cam.x) + 0.5, Math.round(r[1] - cam.y) + 0.5, rx, rx * 0.45, 0, 0, 6.283);
    ctx.stroke();
  }
  rings.length = keep;
}

// ----- a person at the water's edge: their likeness in it, upside down and faint, only on the water
export function drawReflections(ctx, ents, cam, imageOf, riding) {
  if (!FX.on) return;
  for (const e of ents) {
    if ((e.k !== T.PLAYER && e.k !== T.NPC) || e.gh || e.zz || riding(e)) continue;
    const k = kindOf(e);
    if (k.vehicle || k.swarm || !k.shadow) continue;
    const cx = e.dx + e.w / 2, feet = e.dy + e.h - 1;
    const here = groundAt(cx, feet - 2);
    if (here && here.water && !k.lift) continue;          // (a swimmer is in it, not over it)
    const below = groundAt(cx, feet + 12);
    if (!below || !below.water) continue;
    const im = imageOf(e);
    if (!im) continue;
    // (the water cells it falls on: the reflection is cut to them, so it never shows on the bank)
    const gx0 = Math.floor(e.dx / G.tw), gx1 = Math.floor((e.dx + e.w - 1) / G.tw);
    const gy0 = Math.floor(feet / G.th), gy1 = Math.floor((feet + e.h) / G.th);
    ctx.save();
    ctx.beginPath();
    for (let gy = gy0; gy <= gy1; gy++) {
      for (let gx = gx0; gx <= gx1; gx++) {
        const c = cellAtTile(S.mapZ, gx, gy);
        if (c && c[0] && groundOf(c[0]).water) ctx.rect(gx * G.tw - cam.x, gy * G.th - cam.y, G.tw, G.th);
      }
    }
    ctx.clip();
    ctx.globalAlpha = 0.26;
    ctx.translate(Math.round(e.dx - cam.x), Math.round(feet - cam.y + (k.lift ? k.lift * 2 : 0)));
    ctx.scale(1, -1);
    ctx.drawImage(im, 0, -im.height);
    ctx.restore();
  }
}

// ----- sparks rising from a fire, a forge, a hearth (Embers=N): each its own time, from the frame's clock alone
export function drawEmbers(ctx, ents, cam, now, ww, wh, pc, roofHides) {
  if (!FX.on) return;
  for (const e of ents) {
    if (e.k !== T.STATICOBJECT && e.k !== T.NPC) continue;
    const n = kindOf(e).embers;
    if (n > 0) sparks(ctx, e.dx + e.w / 2 - cam.x, e.dy + e.h * 0.3 - cam.y, n, e.u, now);
  }
  for (const name of S.viewMaps) {
    const m = S.maps.get(name);
    if (!m || m.mz !== S.mapZ) continue;
    if (m.ox - cam.x > ww || m.oy - cam.y > wh || m.ox + G.sw - cam.x < 0 || m.oy + G.sh - cam.y < 0) continue;
    for (const [wx, wy, n, seed] of embersOf(m, now)) {
      if (wx - cam.x < -16 || wy - cam.y < -24 || wx - cam.x > ww + 16 || wy - cam.y > wh + 8) continue;
      if (roofHides(wx, wy) || fogCovers(wx, wy, pc)) continue;
      sparks(ctx, wx - cam.x, wy - cam.y, n, seed, now);
    }
  }
  ctx.globalAlpha = 1;
}

// (a map's fires, found once and again every few seconds: a tile that changes is rare)
const emberCells = new WeakMap();
function embersOf(m, now) {
  let c = emberCells.get(m);
  if (c && now - c.at < 3000) return c.list;
  const list = [];
  for (let y = 1; y <= G.yt; y++) {
    for (let x = 1; x <= G.xt; x++) {
      const t = cellOf(m, x, y);
      const n = Math.max(t[0] ? groundOf(t[0]).embers : 0, t[1] ? groundOf(t[1]).embers : 0);
      if (n) list.push([m.ox + (x - 0.5) * G.tw, m.oy + (y - 1) * G.th + G.th * 0.35, n, x * 31 + y * 17]);
    }
  }
  emberCells.set(m, { at: now, list });
  return list;
}

const SPARK_MS = 1500;
function sparks(ctx, x, y, n, seed, now) {
  for (let i = 0; i < n; i++) {
    const s = (seed * 0.618 + i * 0.37) % 1;
    const t = (now / (SPARK_MS * (0.8 + 0.4 * s)) + s + i / n) % 1;
    const sx = Math.round(x + Math.sin(t * 7 + seed + i * 2.1) * 3 + (s - 0.5) * 8);
    const sy = Math.round(y - t * 26);
    ctx.globalAlpha = t < 0.55 ? 1 : 1 - (t - 0.55) / 0.45;
    ctx.fillStyle = t < 0.35 ? "rgb(255,236,150)" : t < 0.7 ? "rgb(255,160,60)" : "rgb(220,80,30)";
    ctx.fillRect(sx, sy, t < 0.4 ? 2 : 1, t < 0.4 ? 2 : 1);
  }
}
