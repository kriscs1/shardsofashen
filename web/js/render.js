// Drawing the world (the desktop game's ui.render, its first half): the ground, the things and people in the order
// their feet are down the screen, tree tops over them, the weather, the night, the fog of war and the effects.
import { G, S, mapAt, mapByPos, cellOf, myPlayer, tileAt } from "./state.js";
import { A, sprite, size, has, entityIni, tileIni, frames, animFrame, isDecorTile, configRead } from "./assets.js";
import { chunkOf, updateChunk, endFrame, setHiddenRoof, clearHiddenRoofs, forgetChunks, tileInfo } from "./ground.js";
import { drawSky, drawWeather, drawFog, fogUpdate, fogCovers, drawFlash, weatherTick } from "./sky.js";
import { val, clamp, drawText, textWidth, setFont } from "./util.js";
import { T } from "./verbs.js";
import { lookImage } from "./look.js";

export const V = {
  zoom: 1, zooms: [0.75, 1, 1.5, 2, 3],
  cam: { x: 0, y: 0, fx: 0, fy: 0, snap: true },
  smooth: 8,
  ww: 800, wh: 672,           // the world canvas (the playfield divided by the zoom)
  pick: [],                   // [x, y, w, h, entity] in world pixels, front last
  underRoof: 0,
  seen: new Set(),              // (what was drawn last frame)
  playerC: null,
  fx: [],
};

export function setZoom(z) {
  V.zoom = V.zooms.includes(z) ? z : 1;
  V.cam.snap = true;
  try { localStorage.setItem("ds.zoom", String(V.zoom)); } catch (e) { /* (private window) */ }
}

export function changeZoom(step) {
  let i = V.zooms.indexOf(V.zoom);
  if (i < 0) i = 1;
  i = clamp(i + step, 0, V.zooms.length - 1);
  if (V.zooms[i] === V.zoom) return false;
  setZoom(V.zooms[i]);
  return true;
}

// ----- the camera: centred on the player, as far as there are maps
function updateCamera(viewW, viewH, dt) {
  V.ww = viewW / V.zoom;
  V.wh = viewH / V.zoom;
  const p = S.pos;
  const m = mapAt(p.z, p.dx + 16, p.dy + 28) || S.maps.get(S.mapName);
  if (!m) return;
  const z = m.mz;
  const left = mapByPos(m.mx - 1, m.my, z) ? m.ox - G.sw : m.ox;
  const right = mapByPos(m.mx + 1, m.my, z) ? m.ox + 2 * G.sw : m.ox + G.sw;
  const top = mapByPos(m.mx, m.my - 1, z) ? m.oy - G.sh : m.oy;
  const bottom = mapByPos(m.mx, m.my + 1, z) ? m.oy + 2 * G.sh : m.oy + G.sh;
  const pw = size(p.i);
  let wx = p.dx + pw[0] / 2 - V.ww / 2, wy = p.dy + pw[1] / 2 - V.wh / 2;
  wx = right - left >= V.ww ? clamp(wx, left, right - V.ww) : (left + right - V.ww) / 2;
  wy = bottom - top >= V.wh ? clamp(wy, top, bottom - V.wh) : (top + bottom - V.wh) / 2;
  const c = V.cam;
  if (c.snap || V.smooth <= 0) {
    c.fx = wx; c.fy = wy; c.snap = false;
  } else {
    const k = 1 - Math.exp(-V.smooth * dt);
    c.fx += (wx - c.fx) * k;
    c.fy += (wy - c.fy) * k;
    if (Math.abs(wx - c.fx) < 0.3) c.fx = wx;
    if (Math.abs(wy - c.fy) < 0.3) c.fy = wy;
  }
  c.x = Math.round(c.fx * V.zoom) / V.zoom;
  c.y = Math.round(c.fy * V.zoom) / V.zoom;
}

// ----- roofs: standing under one hides every roof tile of its group (on the map you're on)
function updateRoofs() {
  const p = S.pos;
  const pw = size(p.i);
  const fx = p.dx + pw[0] / 2, fy = p.dy + pw[1] - 1;
  const t = tileAt(p.z, fx, fy);
  let group = 0;
  if (t && t.m.name === S.mapName) {
    const [tile] = cellOf(t.m, t.tx, t.ty);
    const inDoor = !!tileIni(tile, "Open.Tile", "") || !["", "0"].includes(tileIni(tile, "Door", "").trim());
    for (const py of inDoor ? [fy, p.dy + pw[1] / 4] : [fy]) {
      const ty = Math.floor((py - t.m.oy) / G.th) + 1;
      if (ty < 1 || ty > G.yt) continue;
      const c = cellOf(t.m, t.tx, ty);
      if (c[2]) { group = c[3]; break; }
    }
  }
  const m = S.maps.get(S.mapName);
  if (m) {
    clearHiddenRoofs(m);
    setHiddenRoof(m, group);
  }
  V.underRoof = group;
}

export function roofCovers(x, y) {
  const t = tileAt(S.mapZ, x, y);
  if (!t || t.tx < 1 || t.ty < 1 || t.tx > G.xt || t.ty > G.yt) return false;
  const c = cellOf(t.m, t.tx, t.ty);
  if (!c[2]) return false;
  return !(V.underRoof && t.m.name === S.mapName && c[3] === V.underRoof);
}

// ----- effects (the server says what happened; they're drawn here)
export function addFx(ev, nowMs) {
  const f = { ...ev, start: nowMs };
  if (ev.t === "splat") {
    f.image = ev.kind === "Miss" ? "Miss" : ev.kind + Math.min(99, Math.max(1, ev.n));
    const [w] = size(f.image);
    f.x = ev.x - w / 2 + ev.dx;
    f.end = nowMs + 900;
  } else if (ev.t === "anim") {
    const [w, h] = size(ev.base + "1");
    f.x = ev.x - w / 2; f.y = ev.y - h / 2;
    f.end = nowMs + Math.max(100, ev.ms);
  } else if (ev.t === "shot") {
    const src = entityAt(ev.from);
    const [w, h] = size(ev.image);
    f.w = w; f.h = h;
    f.x = (src ? src.dx + src.w / 2 : ev.x) - w / 2;
    f.y = (src ? src.dy + src.h / 2 : ev.y) - h / 2;
    f.end = nowMs + 3000;
  } else if (ev.t === "nudge") {
    f.end = nowMs + ev.ms;
  } else if (ev.t === "skillpop") {
    f.end = nowMs + 1600;
    V.fx = V.fx.filter((o) => !(o.t === "skillpop" && o.uid === ev.uid));
  } else if (ev.t === "burst") {
    f.end = nowMs + 1400;
  } else return;
  if (V.fx.length < 60) V.fx.push(f);
}

function entityAt(uid) {
  if (uid === S.uid) return myPlayer();
  return S.ents.get(uid) || null;
}

function nudgeOf(uid, now) {
  for (const f of V.fx) if (f.t === "nudge" && f.uid === uid && now < f.end) return [f.dx, f.dy];
  return [0, 0];
}

function updateFx(now, dt) {
  V.fx = V.fx.filter((f) => {
    if (now >= f.end) return false;
    if (f.t === "shot") {
      const t = entityAt(f.to);
      if (!t) return false;
      const tx = t.dx + t.w / 2 - f.w / 2, ty = t.dy + t.h / 2 - f.h / 2;
      const d = Math.hypot(tx - f.x, ty - f.y), travel = 420 * dt;
      if (d <= travel + 4) return false;
      f.mirror = tx < f.x;
      f.x += (tx - f.x) * travel / d;
      f.y += (ty - f.y) * travel / d;
    }
    return true;
  });
}

// ----- objects that animate where they stand, decor tiles placed as objects
function entityImage(e, now) {
  let image = e.i || e.n;
  if (e.k === T.STATICOBJECT) {
    const fr = frames(e.n, "e");
    if (fr) image = e.n + ((Math.floor(now / fr[1]) + e.u * 3) % fr[0] + 1);
    else if (isDecorTile(e.n)) {
      const info = tileInfo(e.n);
      if (info.dkind === "sway") {
        const n = info.anim.d, sp = +configRead("Animation", "Sway.Speed", "230") || 230;
        const k = ((Math.floor(now / sp) - Math.floor(Math.floor(e.x / G.tw) / 2)) % n + n) % n;
        return animFrame(e.n, "d", k) || sprite(image);
      }
      if (info.dkind === "flame") {
        const sp = +configRead("Animation", "Flame.Speed", "140") || 140;
        return animFrame(e.n, "F", Math.floor(now / sp) % info.anim.F) || sprite(image);
      }
    }
  }
  warmWalk(image);
  return sprite(image);
}

// ----- a creature's walking frames are fetched together, the first time one is wanted: a frame still on its way
// would leave a gap mid-stride (it keeps the picture it had meanwhile; see draw)
const warmed = new Set();
const lastImage = new Map();                      // uid -> the picture it was drawn with last
function warmWalk(image) {
  const w = /^(.+)[1248][abc]$/.exec(image || "");
  if (!w || warmed.has(w[1])) return;
  warmed.add(w[1]);
  for (const d of "1248") for (const f of "abc") sprite(w[1] + d + f);
}

function healthImage(hp, max) {
  const m = Math.max(1, max);
  const pc = Math.min(100, Math.max(0, Math.floor((Math.max(0, hp) * 10 + m - 1) / m) * 10));
  return sprite(pc + "PCHealth");
}

// ================================================================================================================
// A frame of the world: ctx is already scaled to the logical screen; the playfield is 0,0 .. viewW, viewH
// ================================================================================================================
export function drawWorld(ctx, viewW, viewH, now, dt, smoothing) {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, viewW, viewH);
  if (!S.pos || !S.maps.size) return;
  updateCamera(viewW, viewH, dt);
  updateRoofs();
  const cam = V.cam;
  const me = myPlayer();
  const pc = me ? [me.dx + me.w / 2, me.dy + me.h / 2] : null;
  V.playerC = pc;
  fogUpdate(pc);
  weatherTick(dt);
  updateFx(now, dt);
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, viewW, viewH);
  ctx.clip();
  ctx.scale(V.zoom, V.zoom);
  ctx.imageSmoothingEnabled = smoothing && V.zoom !== Math.floor(V.zoom);
  // ----- the ground
  const keep = new Set();
  for (const name of S.viewMaps) {
    const m = S.maps.get(name);
    if (!m || m.mz !== S.mapZ) continue;
    keep.add(name);
    const ch = chunkOf(m);
    updateChunk(ch, now);
    const x = m.ox - cam.x, y = m.oy - cam.y;
    if (x < V.ww && y < V.wh && x + G.sw > 0 && y + G.sh > 0) ctx.drawImage(ch.canvas, Math.round(x), Math.round(y));
  }
  forgetChunks(keep);
  endFrame();
  // ----- things and people
  const pick = [];
  const shown = [];
  for (const e of S.ents.values()) {
    if (!e.a) continue;
    const cx = e.dx + e.w / 2, cy = e.dy + e.h / 2;
    if (e.dx - cam.x > V.ww + 64 || e.dy - cam.y > V.wh + 64 || e.dx + e.w - cam.x < -64 || e.dy + e.h - cam.y < -64) continue;
    if (roofCovers(cx, cy) || fogCovers(cx, cy, pc, V.seen.has(e.u) ? FOG_KEEP : 0)) continue;
    shown.push(e);
  }
  V.seen = new Set(shown.map((e) => e.u));
  if (lastImage.size > 600) lastImage.clear();
  const draw = (e) => {
    let im = e.k === T.PLAYER && e.look ? (warmWalk(e.i), lookImage(e.i, e.look)) : entityImage(e, now);
    if (im) lastImage.set(e.u, im);               // (a frame not loaded yet: the one before it, not a "?")
    else im = lastImage.get(e.u) || sprite(has("Placeholder") ? "Placeholder" : "");
    const [nx, ny] = nudgeOf(e.u, now);
    const x = Math.round(e.dx - cam.x + nx), y = Math.round(e.dy - cam.y + ny);
    if (im && e.k === T.MAPITEM) {                // (things on the ground: smaller than in your hand)
      const w = Math.round(e.w * MAPITEM_SCALE), h = Math.round(e.h * MAPITEM_SCALE);
      ctx.drawImage(im, x + Math.round((e.w - w) / 2), y + (e.h - h), w, h);
    } else if (im) ctx.drawImage(im, x, y);
    if (e.k === T.PLAYER) drawWorn(ctx, e, x, y);
    pick.push([e.dx, e.dy, e.w, e.h, e]);
  };
  for (const e of shown) if (e.k === T.NPC && e.un) draw(e);
  for (const e of shown) if (e.k === T.MAPITEM) draw(e);
  const standing = shown.filter((e) => e.k === T.STATICOBJECT || e.k === T.PLAYER || (e.k === T.NPC && !e.un));
  if (me && me.a) standing.push(me);
  standing.sort((a, b) => (a.dy + a.h) - (b.dy + b.h));
  for (const e of standing) draw(e);
  for (const e of shown) if (e.k === T.MISSILE || e.k === T.TEMPORARY) draw(e);
  // tree tops over everyone
  drawInfront(ctx, cam, pick, pc);
  // ----- the weather, the night, the fog
  drawWeather(ctx, cam, V.ww, V.wh, dt, now, V.underRoof);
  drawSky(ctx, cam, V.ww, V.wh, now, V.underRoof, pc);
  drawFog(ctx, cam, V.ww, V.wh, pc);
  // ----- effects, health bars, names
  for (const f of V.fx) {
    if (f.t !== "skillpop" && fogCovers(f.x + 16, f.y + 16, pc)) continue;   // (a fight in the fog stays unseen)
    if (f.t === "splat") {
      const t = (now - f.start) / 900;
      const im = sprite(f.image);
      if (im) ctx.drawImage(im, Math.round(f.x - cam.x), Math.round(f.y - 14 * Math.min(1, t * 1.6) - cam.y));
    } else if (f.t === "anim") {
      const k = Math.min(4, 1 + Math.floor(4 * (now - f.start) / Math.max(1, f.end - f.start)));
      const im = sprite(f.base + k);
      if (im) ctx.drawImage(im, Math.round(f.x - cam.x), Math.round(f.y - cam.y));
    } else if (f.t === "shot") {
      const im = sprite(f.image);
      if (im) {
        ctx.save();
        if (f.mirror) {
          ctx.translate(Math.round(f.x - cam.x) + f.w, Math.round(f.y - cam.y));
          ctx.scale(-1, 1);
          ctx.drawImage(im, 0, 0);
        } else ctx.drawImage(im, Math.round(f.x - cam.x), Math.round(f.y - cam.y));
        ctx.restore();
      }
    } else if (f.t === "skillpop") drawSkillPop(ctx, f, now, cam);
    else if (f.t === "burst") drawBurst(ctx, f, now, cam);
  }
  drawStatusIcons(ctx, me, cam);
  for (const e of [...shown, ...(me && me.a ? [me] : [])]) {
    if (e.b && (e.k === T.NPC || e.k === T.PLAYER)) {
      const im = healthImage(e.hp, e.mh);
      if (im) ctx.drawImage(im, Math.round(e.dx + (e.w - 26) / 2 - cam.x), Math.round(e.dy - 12 - cam.y));
    }
    if (e.k === T.PLAYER && !e.self) drawNameTag(ctx, e, cam);
  }
  drawFlash(ctx, V.ww, V.wh, now);
  ctx.restore();
  V.pick = pick;
}

function drawWorn(ctx, e, x, y) {
  const worn = e.worn || [];
  if (!worn.length) return;
  let suffix = (e.i || "").slice(-2);
  if (!/^[1248][abc]$/.test(suffix)) suffix = "4a";
  for (const item of worn) {
    warmWalk("Worn_" + item + suffix);
    const g = sprite("Worn_" + item + suffix);
    if (g) ctx.drawImage(g, x, y);
  }
}

function drawNameTag(ctx, e, cam) {
  const x = e.dx + e.w / 2 - cam.x, y = e.dy - (e.b ? 24 : 14) - cam.y;
  const w = textWidth(ctx, e.n, 7, true) + 8;
  ctx.fillStyle = "rgba(24,14,8,0.65)";
  ctx.fillRect(Math.round(x - w / 2), Math.round(y), Math.round(w), 12);
  drawText(ctx, e.n, Math.round(x - w / 2 + 4), Math.round(y + 1), 7, true, e.zz ? [160, 160, 200] : [255, 236, 170]);
}

function drawInfront(ctx, cam, pick, pc) {
  const tx0 = Math.floor(cam.x / G.tw), ty0 = Math.floor(cam.y / G.th);
  const tx1 = Math.floor((cam.x + V.ww - 1) / G.tw), ty1 = Math.floor((cam.y + V.wh - 1) / G.th);
  for (let ty = ty0; ty <= ty1; ty++) {
    for (let tx = tx0; tx <= tx1; tx++) {
      const m = mapByPos(Math.floor(tx / G.xt), Math.floor(ty / G.yt), S.mapZ);
      if (!m) continue;
      const lx = tx - m.mx * G.xt + 1, ly = ty - m.my * G.yt + 1;
      const c = cellOf(m, lx, ly);
      if (!c[4]) continue;
      const im = sprite(c[4]);
      if (!im) continue;
      const x = tx * G.tw, y = ty * G.th;
      ctx.drawImage(im, Math.round(x - cam.x), Math.round(y - cam.y));
      if (m.name === S.mapName && !fogCovers(x + G.tw / 2, y + G.th / 2, pc)) {
        pick.push([x, y, G.tw, G.th, { k: T.INFRONT, n: c[4], x, y, w: G.tw, h: G.th, map: m.name, tx: lx, ty: ly,
          misc: tileIni(c[4], "Show.Name", "0"), uw: tileIni(c[4], "Use.Words", ""), dx: x, dy: y }]);
      }
    }
  }
}

const MAPITEM_SCALE = 0.75;
const FOG_KEEP = 24;            // (in sight already: it stays until this far past the edge of what you can see)
const STATUS_COLOURS = { Poison: [90, 200, 60], Burn: [255, 128, 30], Bleed: [200, 24, 24], Chill: [120, 196, 255] };

function drawStatusIcons(ctx, me, cam) {
  const st = S.me?.status || [];
  if (!st.length || !me) return;
  const names = ["Poison", "Burn", "Bleed", "Chill"].filter((n) => st.includes(n));
  const x0 = Math.round(me.dx + me.w / 2 - cam.x - names.length * 7), y = Math.round(me.dy - cam.y) - 26;
  names.forEach((n, i) => {
    const cx = x0 + i * 14 + 6, cy = y + 6, col = STATUS_COLOURS[n];
    ctx.fillStyle = "rgba(20,14,10,0.86)";
    ctx.beginPath(); ctx.arc(cx, cy, 6, 0, 6.283); ctx.fill();
    ctx.fillStyle = `rgb(${col})`;
    ctx.beginPath(); ctx.arc(cx, cy + 1, 3, 0, 6.283); ctx.fill();
  });
}

function drawSkillPop(ctx, f, now, cam) {
  const e = entityAt(f.uid);
  if (!e) return;
  const icon = configRead("Skills", "Icon." + f.skill, "").trim();
  const rise = Math.min(6, Math.floor((now - f.start) / 40));
  const x = Math.round(e.dx + e.w / 2 - 14 - cam.x), y = Math.round(e.dy - 30 - rise - cam.y);
  ctx.fillStyle = "rgb(214,170,70)";
  ctx.beginPath(); ctx.roundRect ? ctx.roundRect(x, y, 28, 28, 5) : ctx.rect(x, y, 28, 28); ctx.fill();
  ctx.fillStyle = "rgb(51,34,27)";
  ctx.beginPath(); ctx.roundRect ? ctx.roundRect(x + 2, y + 2, 24, 24, 4) : ctx.rect(x + 2, y + 2, 24, 24); ctx.fill();
  const im = sprite(icon);
  if (im) {
    const s = Math.min(20 / im.width, 20 / im.height);
    ctx.drawImage(im, x + 4 + (20 - im.width * s) / 2, y + 4 + (20 - im.height * s) / 2, im.width * s, im.height * s);
  }
}

function drawBurst(ctx, f, now, cam) {
  const e = entityAt(f.uid);
  if (!e) return;
  const t = now - f.start;
  const cx = e.dx + e.w / 2 - cam.x, cy = e.dy + e.h / 2 - cam.y;
  for (let k = 0; k < 3; k++) {
    const tt = t - k * 220;
    if (tt < 0 || tt >= 900) continue;
    const fr = tt / 900;
    ctx.strokeStyle = `rgba(255,214,92,${0.9 * (1 - fr)})`;
    ctx.lineWidth = Math.max(2, 6 * (1 - fr));
    ctx.beginPath(); ctx.arc(cx, cy, 14 + 70 * fr, 0, 6.283); ctx.stroke();
  }
  if (t < 700) {
    ctx.fillStyle = `rgba(255,236,160,${0.43 * (1 - t / 700)})`;
    ctx.beginPath(); ctx.arc(cx, cy, 26, 0, 6.283); ctx.fill();
  }
  for (let k = 0; k < 10; k++) {
    if (t + k * 97 > 1400) continue;
    const fr = ((t + k * 97) % 1100) / 1100;
    ctx.fillStyle = `rgba(255,240,170,${0.86 * (1 - fr)})`;
    ctx.beginPath();
    ctx.arc(cx + 30 * Math.sin(k * 2.4) + 6 * Math.sin(fr * 9 + k), cy + 10 - 80 * fr, 2, 0, 6.283);
    ctx.fill();
  }
}

// ----- what's under the mouse in the world (world pixels)
export function screenToWorld(sx, sy) {
  return [V.cam.x + sx / V.zoom, V.cam.y + sy / V.zoom];
}

export function entityUnder(wx, wy) {
  for (let i = V.pick.length - 1; i >= 0; i--) {
    const [x, y, w, h, e] = V.pick[i];
    if (wx >= x && wx < x + w && wy >= y && wy < y + h) return e;
  }
  return null;
}
