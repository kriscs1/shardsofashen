// Drawing the world (the desktop game's ui.render, its first half): the ground, the things and people in the order
// their feet are down the screen, tree tops over them, the weather, the night, the fog of war and the effects.
import { G, S, mapAt, mapByPos, cellOf, myPlayer, tileAt } from "./state.js";
import { A, sprite, size, entityIni, tileIni, frames, animFrame, isDecorTile, configRead } from "./assets.js";
import { chunkOf, updateChunk, endFrame, setHiddenRoof, clearHiddenRoofs, forgetChunks, tileInfo } from "./ground.js";
import { drawSky, drawWeather, drawFog, fogUpdate, fogCovers, drawFlash, weatherTick, flicker } from "./sky.js";
import { val, clamp, drawText, textWidth, setFont } from "./util.js";
import { T } from "./verbs.js";
import { lookImage, npcImage } from "./look.js";
import { playSound } from "./audio.js";

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

// ----- the camera: centred on the player, always (past the last map there's only black)
function updateCamera(viewW, viewH, dt) {
  V.ww = viewW / V.zoom;
  V.wh = viewH / V.zoom;
  const p = S.pos;
  const m = mapAt(p.z, p.dx + 16, p.dy + 28) || S.maps.get(S.mapName);
  if (!m) return;
  const pw = size(p.i);
  const wx = p.dx + pw[0] / 2 - V.ww / 2, wy = p.dy + pw[1] / 2 - V.wh / 2;
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

// (what's on a roof, Layer=Over: a chimney's smoke, a spire: drawn with the roof, and gone with it when you're under it)
function roofHides(x, y) {
  const t = tileAt(S.mapZ, x, y);
  if (!V.underRoof || !t || t.m.name !== S.mapName || t.tx < 1 || t.ty < 1 || t.tx > G.xt || t.ty > G.yt) return false;
  const c = cellOf(t.m, t.tx, t.ty);
  return !!c[2] && c[3] === V.underRoof;
}
const onRoofKinds = new Map();
function onRoof(e) {
  if (e.k !== T.STATICOBJECT) return false;
  if (!onRoofKinds.has(e.n)) onRoofKinds.set(e.n, entityIni(e.n, "Layer", "").trim().toLowerCase() === "over");
  return onRoofKinds.get(e.n);
}

export function roofCovers(x, y) {
  const t = tileAt(S.mapZ, x, y);
  if (!t || t.tx < 1 || t.ty < 1 || t.tx > G.xt || t.ty > G.yt) return false;
  const c = cellOf(t.m, t.tx, t.ty);
  if (!c[2]) return false;
  return !(V.underRoof && t.m.name === S.mapName && c[3] === V.underRoof);
}

// ----- effects (the server says what happened; they're drawn here)
export function stopWorkFx(nowMs) {
  // The beats of work not begun yet (the chips of the next swings, the lunges): gone, the work stopped
  V.fx = V.fx.filter((f) => !(f.delay > 0 && f.start > nowMs && (f.t === "anim" || f.t === "nudge")));
}

export function addFx(ev, nowMs) {
  nowMs += Math.max(0, +ev.delay || 0);          // (a later beat of the same work: the next swing of the axe)
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
  } else if (ev.t === "mark") {                   // (stealth: a ! over one that's seen you, a ? over one that heard)
    f.end = nowMs + (ev.kind === "spotted" ? 1400 : 1700);
  } else return;
  if (V.fx.length < 60) V.fx.push(f);
}

function entityAt(uid) {
  if (uid === S.uid) return myPlayer();
  return S.ents.get(uid) || null;
}

function nudgeOf(uid, now) {
  for (const f of V.fx) if (f.t === "nudge" && f.uid === uid && now >= f.start && now < f.end) return [f.dx, f.dy];
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
const flaps = new Map();                           // kind -> does it flap (Flap=1: a butterfly's wings)
function entityImage(e, now) {
  let image = e.i || e.n;
  if (e.k === T.NPC) {                            // (its wings beat all the time, hovering or not)
    if (!flaps.has(e.n)) flaps.set(e.n, entityIni(e.n, "Flap", "0").trim() === "1");
    const w = flaps.get(e.n) && /^(.+[1248])[abc]$/.exec(image);
    if (w) image = w[1] + "abcb"[(Math.floor(now / 70) + e.u) % 4];
  }
  if (e.k === T.STATICOBJECT) {
    if (e.n === "Shardstone" && !(S.me && (S.me.lit || []).includes(e.u))) return sprite("Shardstone_Dormant");
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
  if (e.k === T.NPC && e.lk) return npcImage(image, e.n, e.lk);   // (one of its trade's other colourings)
  return sprite(image);
}

// ----- a creature's walking frames are fetched together, the first time one is wanted: a frame still on its way
// would leave a gap mid-stride (it keeps the picture it had meanwhile; see draw)
const warmed = new Set();
const lastImage = new Map();                      // uid -> the picture it was drawn with last
const heldLook = [null, new WeakMap(), new WeakMap()];

// A creature a spell holds still: iced over a cold blue (fz 1), or dazed a pale gold (fz 2). Made once a picture.
function held(im, fz) {
  const cache = heldLook[fz] || heldLook[1];
  let c = cache.get(im);
  if (!c) {
    c = document.createElement("canvas");
    c.width = im.width;
    c.height = im.height;
    const g = c.getContext("2d");
    g.drawImage(im, 0, 0);
    g.globalCompositeOperation = "source-atop";
    g.fillStyle = fz === 2 ? "rgba(255,232,130,0.45)" : "rgba(140,210,255,0.6)";
    g.fillRect(0, 0, c.width, c.height);
    cache.set(im, c);
  }
  return c;
}
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
// Ground pieces laid edge to edge (a map's picture, a tile drawn over you): their edges put on whole screen pixels,
// so when the screen's scale isn't a whole number, no faint line shows where two meet
function snapDraw(ctx, im, x, y) {
  const t = ctx.getTransform();
  const x0 = Math.round(t.a * x + t.e), y0 = Math.round(t.d * y + t.f);
  const x1 = Math.round(t.a * (x + im.width) + t.e), y1 = Math.round(t.d * (y + im.height) + t.f);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(im, x0, y0, x1 - x0, y1 - y0);
  ctx.setTransform(t);
}

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
  footsteps();
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
    if (x < V.ww && y < V.wh && x + G.sw > 0 && y + G.sh > 0) snapDraw(ctx, ch.canvas, Math.round(x), Math.round(y));
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
    if ((onRoof(e) ? roofHides(cx, e.dy + e.h - 1) : roofCovers(cx, cy)) ||
        fogCovers(cx, cy, pc, V.seen.has(e.u) ? FOG_KEEP : 0)) continue;
    shown.push(e);
  }
  V.seen = new Set(shown.map((e) => e.u));
  if (lastImage.size > 600) lastImage.clear();
  const draw = (e) => {
    let im = e.k === T.PLAYER && e.look ? (warmWalk(e.i), lookImage(e.i, e.look)) : entityImage(e, now);
    if (im) lastImage.set(e.u, im);               // (a frame not loaded yet: the one before it, or nothing till it has)
    else im = lastImage.get(e.u) || null;
    const [nx, ny] = nudgeOf(e.u, now);
    const x = Math.round(e.dx - cam.x + nx), y = Math.round(e.dy - cam.y + ny);
    if (im && e.k === T.MAPITEM) {                // (things on the ground: smaller than in your hand)
      const w = Math.round(e.w * MAPITEM_SCALE), h = Math.round(e.h * MAPITEM_SCALE);
      ctx.drawImage(im, x + Math.round((e.w - w) / 2), y + (e.h - h), w, h);
    } else if (im) {
      if (e.sc && !e.gh) drawStance(ctx, e, x, y, now, true);
      if (e.gh) ctx.globalAlpha = e === me ? 0.35 : 0.08;     // (invisible: a shimmer to you, all but nothing to others)
      const crouch = e.sc === "Sneaking" && !e.rd && !(e === me && S.me.ride);
      if (crouch) {                               // (sneaking: down low, a little faded)
        ctx.save();
        ctx.translate(0, y + e.h);
        ctx.scale(1, 0.86);
        ctx.translate(0, -(y + e.h));
        if (!e.gh) ctx.globalAlpha = 0.72;
      }
      ctx.drawImage(e.fz ? held(im, e.fz) : im, x, y);
      if (e.k === T.PLAYER) drawWorn(ctx, e, x, y);
      if (crouch) ctx.restore();
      if (e.sc && !e.gh) drawStance(ctx, e, x, y, now, false);
    }
    ctx.globalAlpha = 1;
    pick.push([e.dx, e.dy, e.w, e.h, e]);
  };
  if (S.me && S.me.stance === "Sneaking") drawCones(ctx, shown, cam);
  drawTraps(ctx, cam);
  for (const e of shown) if (e.k === T.NPC && e.un) draw(e);
  for (const e of shown) if (e.k === T.MAPITEM) draw(e);
  drawMarks(ctx, cam, now, false);
  let standing = shown.filter((e) => e.k === T.STATICOBJECT || e.k === T.PLAYER || (e.k === T.NPC && !e.un));
  if (me && me.a) standing.push(me);
  // (in a cart, carts.py: drawn with it, standing in its box - over it above its front panel, hidden below)
  const riders = new Map();
  const rideOf = (e) => (e === me ? S.me && S.me.ride : e.rd) || 0;
  const cartUids = new Set(shown.filter((e) => e.k === T.NPC).map((e) => e.u));
  standing = standing.filter((e) => {
    const c = rideOf(e);
    if (!c || !cartUids.has(c)) return true;
    if (!riders.has(c)) riders.set(c, []);
    riders.get(c).push(e);
    return false;
  });
  standing.sort((a, b) => (a.dy + a.h) - (b.dy + b.h));
  for (const e of standing) {
    draw(e);
    for (const r of riders.get(e.u) || []) {
      const seat = entityIni(e.n, "Seat." + (/([1248])[abc]$/.exec(e.i || "") || [0, "2"])[1], "").split(",");
      const panel = Math.round(e.dy - cam.y + (val(seat[2]) || e.h));
      ctx.save();
      ctx.beginPath();
      ctx.rect(-4096, -4096, 8192 + V.ww, 4096 + panel);
      ctx.clip();
      draw(r);
      ctx.restore();
    }
  }
  drawGlows(ctx, shown, cam);
  drawMarks(ctx, cam, now, true);
  for (const e of shown) if (e.k === T.MISSILE || e.k === T.TEMPORARY) draw(e);
  // tree tops over everyone
  drawInfront(ctx, cam, pick, pc);
  // ----- the weather, the night, the fog
  drawWeather(ctx, cam, V.ww, V.wh, dt, now, V.underRoof);
  drawSky(ctx, cam, V.ww, V.wh, now, V.underRoof, pc);
  drawFog(ctx, cam, V.ww, V.wh, pc);
  // ----- effects, health bars, names
  for (const f of V.fx) {
    if (now < f.start) continue;                  // (not yet: its beat is still to come)
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
    else if (f.t === "mark") drawMark(ctx, f, now, cam);
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

// ----- stealth: lookouts' sight while you sneak (as the server says it is for you: how wide, how far, which way),
// and what they've noticed
const DIR_V = { 1: [0, -1], 2: [1, 0], 4: [0, 1], 8: [-1, 0], 3: [0.71, -0.71], 6: [0.71, 0.71], 12: [-0.71, 0.71],
  9: [-0.71, -0.71] };

function drawCones(ctx, shown, cam) {
  for (const e of shown) {
    if (e.k !== T.NPC || !Array.isArray(e.cone)) continue;
    const [deg, reach, dir, hears] = e.cone;
    const v = DIR_V[dir] || [0, 1];
    const cx = e.dx + e.w / 2 - cam.x, cy = e.dy + e.h - 6 - cam.y;
    const a = Math.atan2(v[1], v[0]), half = Math.min(Math.PI, deg * Math.PI / 360);
    const g = ctx.createRadialGradient(cx, cy, 4, cx, cy, reach);
    g.addColorStop(0, "rgba(255,120,80,0.30)");
    g.addColorStop(1, "rgba(255,120,80,0.04)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, reach, a - half, a + half); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "rgba(255,150,110,0.45)"; ctx.lineWidth = 1;
    ctx.stroke();
    if (hears > 8) {                              // (how far it hears you, moving as you are: a faint dashed ring)
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = "rgba(255,220,150,0.35)";
      ctx.beginPath(); ctx.arc(cx, cy, hears, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
    }
  }
}

function drawTraps(ctx, cam) {
  // (the traps you've spotted: a red-edged plate, a cross over it; green once you've made it safe)
  for (const [mapName, tx, ty, safe] of (S.me && S.me.traps) || []) {
    const m = S.maps.get(mapName);
    if (!m) continue;
    const x = m.ox + (tx - 1) * G.tw - cam.x + 6, y = m.oy + (ty - 1) * G.th - cam.y + 6, w = G.tw - 12;
    ctx.strokeStyle = safe ? "rgba(110,210,110,0.8)" : "rgba(230,70,50,0.85)"; ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, w);
    if (!safe) {
      ctx.beginPath(); ctx.moveTo(x + 4, y + 4); ctx.lineTo(x + w - 4, y + w - 4);
      ctx.moveTo(x + w - 4, y + 4); ctx.lineTo(x + 4, y + w - 4); ctx.stroke();
    }
  }
}

function drawMark(ctx, f, now, cam) {
  const e = entityAt(f.u);
  if (!e) return;
  const t = (now - f.start) / (f.end - f.start);
  const pop = Math.min(1, t * 6);
  const x = e.dx + e.w / 2 - cam.x, y = e.dy - 10 - 6 * pop - cam.y;
  ctx.globalAlpha = t > 0.75 ? (1 - t) * 4 : 1;
  const spotted = f.kind === "spotted";
  ctx.fillStyle = spotted ? "rgb(220,60,40)" : "rgb(240,200,80)";
  ctx.beginPath(); ctx.arc(x, y, 7, 0, 6.283); ctx.fill();
  ctx.strokeStyle = "rgb(40,20,10)"; ctx.lineWidth = 1.5; ctx.stroke();
  const w = textWidth(ctx, spotted ? "!" : "?", 9, true);
  drawText(ctx, spotted ? "!" : "?", Math.round(x - w / 2), Math.round(y - 7), 9, true, [255, 250, 235]);
  ctx.globalAlpha = 1;
}

// ----- footsteps: your own, by the ground underfoot (softer sneaking, none sitting)
const step = { x: null, y: null, gone: 0, n: 0 };

function groundKind(name) {
  const n = String(name || "");
  if (/Plank|Wood|Bridge|Board|Jetty|Pier|Deck/i.test(n)) return "Wood";
  if (/Stone|Cobble|Flag|Pav|Marble|Tile|Brick|Cave|Road|Street|Castle/i.test(n)) return "Stone";
  if (/Snow|Ice/i.test(n)) return "Snow";
  if (/Sand|Desert|Dirt|Gravel|Ash|Scorch|Path|Mud/i.test(n)) return "Sand";
  return "Grass";
}

export function footsteps() {
  const p = S.pos;
  if (!p || !S.me) return;
  if (step.x === null || Math.abs(p.dx - step.x) > 64 || Math.abs(p.dy - step.y) > 64) {
    step.x = p.dx; step.y = p.dy; step.gone = 0;
    return;
  }
  step.gone += Math.hypot(p.dx - step.x, p.dy - step.y);
  step.x = p.dx; step.y = p.dy;
  if (step.gone < 22 || /_Sit[1248]$/.test(p.i || "")) {
    if (step.gone >= 22) step.gone = 0;
    return;
  }
  step.gone = 0;
  const [w, h] = size(p.i);
  const t = tileAt(p.z, p.dx + w / 2, p.dy + h - 2);
  if (!t) return;
  const [tile] = cellOf(t.m, t.tx, t.ty);
  if (tileIni(tile, "Water", "0") === "1") return;
  step.n++;
  const sneaking = S.me.stance === "Sneaking";
  playSound("Step_" + groundKind(tile), null, sneaking ? 0.3 : 0.6);
}

// ----- what was clicked, marked the moment it's clicked (registered: a gold ring closing in on it); the server says
// how it went ("act"): done, a green ring opening out; refused or come to nothing, red, with a shake and a cross. The
// foe you're fighting keeps a red ring at its feet, tightening at each blow, hit or miss.
export function markClick(verb, e, wx, wy) {
  V.mark = { verb, u: e && e.k !== T.TILE ? e.u : 0, x: wx, y: wy, at: performance.now(), ok: null, okAt: 0 };
}

export function markOutcome(ok, now) {
  const m = V.mark;
  if (m && m.ok === null && now - m.at < 15000) { m.ok = ok; m.okAt = now; }
}

export function markSwing(uid, now) { V.swing = { u: uid, at: now }; }

function ring(ctx, x, y, rx, col, a, w = 2) {
  if (a <= 0) return;
  ctx.strokeStyle = `rgba(${col.join(",")},${Math.min(1, a)})`;
  ctx.lineWidth = w;
  ctx.beginPath();
  ctx.ellipse(x, y, Math.max(2, rx), Math.max(1, rx * 0.45), 0, 0, 6.283);
  ctx.stroke();
}

function feetOf(u, cam) {
  const e = u ? (S.pos && S.me && S.me.uid === u ? myPlayer() : S.ents.get(u)) : null;
  if (!e) return null;
  return [e.dx + e.w / 2 - cam.x, e.dy + e.h - 3 - cam.y, Math.max(10, Math.min(30, e.w * 0.45)), e.dy - cam.y];
}

function drawMarks(ctx, cam, now, over) {
  ctx.save();
  const foe = S.me && S.me.target ? feetOf(S.me.target, cam) : null;
  if (foe && !over) {                                   // (the foe: its ring, tightening at a blow)
    const sw = V.swing && V.swing.u === S.me.target ? Math.max(0, 1 - (now - V.swing.at) / 260) : 0;
    ring(ctx, foe[0], foe[1], foe[2] * (1.15 - 0.2 * sw), [235, 70, 40], 0.55 + 0.45 * sw, 2 + sw);
  }
  const m = V.mark;
  if (m) {
    const at = feetOf(m.u, cam);
    const x = at ? at[0] : m.x - cam.x, y = at ? at[1] : m.y - cam.y, r = at ? at[2] : 9;
    const age = now - m.at;
    const attack = m.verb === "Attack";
    if (m.ok === null) {
      const life = m.verb === "Walk here" ? 650 : 3500;
      if (age > life) V.mark = null;
      else if (!over) {
        const k = Math.min(1, age / 180);               // (it closes in, then holds, pulsing, till it's answered)
        const fade = m.verb === "Walk here" ? 1 - age / life : 0.75 + 0.25 * Math.sin(age / 120);
        ring(ctx, x, y, r * (1.7 - 0.7 * k), attack ? [255, 120, 60] : [255, 226, 130], fade, 2);
        if (m.verb === "Walk here") ring(ctx, x, y, r * 0.35, [255, 226, 130], fade, 2);
      }
    } else {
      const t = (now - m.okAt) / (m.ok ? 450 : 700);
      if (t >= 1) V.mark = null;
      else if (m.ok && !over) ring(ctx, x, y, r * (1 + 0.7 * t), [90, 230, 110], 1 - t, 3);
      else if (!m.ok) {
        const shake = Math.sin(t * 40) * 3 * (1 - t);
        if (!over) ring(ctx, x + shake, y, r, [235, 50, 40], 1 - t, 3);
        else {                                          // (a red cross over it: no)
          const cy = at ? at[3] - 6 : y - 18, s = 5;
          ctx.strokeStyle = `rgba(40,6,4,${1 - t})`; ctx.lineWidth = 5;
          ctx.beginPath(); ctx.moveTo(x + shake - s, cy - s); ctx.lineTo(x + shake + s, cy + s);
          ctx.moveTo(x + shake + s, cy - s); ctx.lineTo(x + shake - s, cy + s); ctx.stroke();
          ctx.strokeStyle = `rgba(235,50,40,${1 - t})`; ctx.lineWidth = 2.5;
          ctx.stroke();
        }
      }
    }
  }
  ctx.restore();
}

// ----- a warm halo round what burns (Glow=<radius>: a fire), flickering - by day as well as by night
const glows = new Map();
function drawGlows(ctx, shown, cam) {
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const e of shown) {
    if (e.k !== T.STATICOBJECT) continue;
    if (!glows.has(e.n)) glows.set(e.n, Math.max(0, +entityIni(e.n, "Glow", "0") || 0));
    const r = glows.get(e.n);
    if (!r) continue;
    const f = flicker(e.u);
    const x = e.dx + e.w / 2 - cam.x, y = e.dy + e.h * 0.62 - cam.y, rr = r * f;
    const gr = ctx.createRadialGradient(x, y, 0, x, y, rr);
    gr.addColorStop(0, `rgba(255,150,50,${(0.42 * f).toFixed(3)})`);
    gr.addColorStop(0.45, `rgba(240,100,30,${(0.16 * f).toFixed(3)})`);
    gr.addColorStop(1, "rgba(200,60,20,0)");
    ctx.fillStyle = gr;
    ctx.fillRect(x - rr, y - rr, rr * 2, rr * 2);
  }
  ctx.restore();
}

// ----- a stance shown on whoever's in it (stances.py): Fighting a red ring at the feet; Channelling a blue one and Shard
// motes going round; Sneaking a dark one (and the crouch, in draw). under: the ring, drawn before the body
const STANCE_RING = { Fighting: [200, 60, 40], Channelling: [90, 150, 255], Sneaking: [20, 20, 30] };
function drawStance(ctx, e, x, y, now, under) {
  const col = STANCE_RING[e.sc];
  if (!col) return;
  const cx = x + e.w / 2, fy = y + e.h - 2;
  if (under) {
    const pulse = e.sc === "Sneaking" ? 0.35 : 0.42 + 0.14 * Math.sin(now / 260);
    ctx.save();
    ctx.globalAlpha = pulse;
    ctx.strokeStyle = `rgb(${col[0]},${col[1]},${col[2]})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(cx, fy, 11, 4, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
    return;
  }
  if (e.sc !== "Channelling") return;
  for (let k = 0; k < 3; k++) {                   // (three motes circling at the waist, the one behind dimmer)
    const a = now / 420 + k * 2.094;
    const mx = Math.round(cx + Math.cos(a) * 12), my = Math.round(y + e.h * 0.55 + Math.sin(a) * 4);
    ctx.globalAlpha = Math.sin(a) > 0 ? 0.95 : 0.45;
    ctx.fillStyle = "#bfe0ff";
    ctx.fillRect(mx - 1, my - 1, 2, 2);
    ctx.fillStyle = "#5a96ff";
    ctx.fillRect(mx, my - 2, 1, 1);
  }
  ctx.globalAlpha = 1;
}

function drawWorn(ctx, e, x, y) {
  const worn = e.worn || [];
  if (!worn.length) return;
  const sit = /_Sit[1248]$/.test(e.i || "");                // (sitting: Worn_<Item>_Sit<Dir>)
  let suffix = sit ? (e.i || "").slice(-5) : (e.i || "").slice(-2);
  if (!sit && !/^[1248][abc]$/.test(suffix)) suffix = "4a";
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

const overhead = new Map();      // tile -> drawn over people too (Overhead=1: a gatehouse's arch)
function isOverhead(name) {
  if (!overhead.has(name)) overhead.set(name, tileIni(name, "Overhead", "0").trim() === "1");
  return overhead.get(name);
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
      if (c[0] && isOverhead(c[0])) {                // (you walk under it: drawn again over you)
        const t = sprite(c[0]);
        if (t) snapDraw(ctx, t, Math.round(tx * G.tw - cam.x), Math.round(ty * G.th - cam.y));
      }
      if (!c[4]) continue;
      const im = sprite(c[4]);
      if (!im) continue;
      const x = tx * G.tw, y = ty * G.th;
      snapDraw(ctx, im, Math.round(x - cam.x), Math.round(y - cam.y));
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

// (everything under the mouse, front first: the right-click menu offers what's behind someone too - a tinderbox
// under a villager's feet)
export function entitiesUnder(wx, wy) {
  const out = [];
  for (let i = V.pick.length - 1; i >= 0; i--) {
    const [x, y, w, h, e] = V.pick[i];
    if (wx >= x && wx < x + w && wy >= y && wy < y + h && !out.includes(e)) out.push(e);
  }
  return out;
}

export function entityUnder(wx, wy) {
  for (let i = V.pick.length - 1; i >= 0; i--) {
    const [x, y, w, h, e] = V.pick[i];
    if (wx >= x && wx < x + w && wy >= y && wy < y + h) return e;
  }
  return null;
}
