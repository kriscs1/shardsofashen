// Over the world: the weather (rain, snow, fog, the lightning), the sky's colour through the day with the lights
// making holes in the dark (daynight.py), and the fog of war over what the player can't see now.
import { G, S, mapAt, cellOf, mapByPos, fogCell, markExplored, isExplored } from "./state.js";
import { iniList, iniValue, tileIni, entityIni, configRead } from "./assets.js";
import { val, clamp, colour } from "./util.js";

// ================================================================================================================
// The time of day (one clock for everyone: the server's)
// ================================================================================================================
export function dayFraction(nowMs) {
  const c = S.clock;
  if (!c.secs) return c.day;
  return (c.day + (nowMs - c.at) / 1000 / c.secs) % 1;
}

export function isNight(t) {
  const from = val(iniValue("daynight", "Night", "From", "0.83"));
  const to = val(iniValue("daynight", "Night", "To", "0.21"));
  return t >= from || t < to;
}

let skyTable = null;
function sky(t) {
  if (!skyTable) {
    skyTable = [];
    for (const [k, v] of iniList("daynight", "Sky")) {
      const tt = parseFloat(k);
      const c = v.replace(/,/g, " ").split(/\s+/).filter(Boolean).map(Number);
      if (!Number.isNaN(tt) && /^\s*[\d.]+\s*$/.test(k) && c.length === 4) skyTable.push([tt, c]);
    }
    skyTable.sort((a, b) => a[0] - b[0]);
  }
  if (!skyTable.length) return [0, 0, 0, 0];
  for (let i = 0; i + 1 < skyTable.length; i++) {
    const [t0, a] = skyTable[i], [t1, b] = skyTable[i + 1];
    if (t0 <= t && t <= t1) {
      let k = (t - t0) / Math.max(1e-6, t1 - t0);
      k = k * k * (3 - 2 * k);
      return a.map((v, j) => Math.round(v + (b[j] - v) * k));
    }
  }
  return skyTable[0][1];
}

export function timeText(t) {
  let name = "Day";
  const periods = iniList("daynight", "Periods").map(([k, v]) => [parseFloat(k), v]).filter(([k]) => !Number.isNaN(k))
    .sort((a, b) => a[0] - b[0]);
  for (const [limit, n] of periods) if (t < limit) { name = n; break; }
  const h = Math.floor(t * 24);
  return `${name}, about ${h % 12 === 0 ? 12 : h % 12} ${h < 12 ? "am" : "pm"}`;
}

const lightCache = new Map();
function lightOf(name, isTile) {
  const key = (isTile ? "t:" : "e:") + name;
  if (!lightCache.has(key)) {
    const v = Math.max(0, Math.floor(val(isTile ? tileIni(name, "Light", "0") : entityIni(name, "Light", "0"))));
    lightCache.set(key, v);
  }
  return lightCache.get(key);
}

const layers = {};
function layer(name, w, h) {
  let c = layers[name];
  if (!c || c.width !== w || c.height !== h) {
    c = layers[name] = document.createElement("canvas");
    c.width = w; c.height = h;
  }
  return c;
}

export function drawSky(ctx, cam, ww, wh, now, underRoof, playerC) {
  if (!S.clock.on || (S.mapZ !== 0 && S.mapZ < 1000)) return;      // (homesteads, 1000 up, are outdoors)
  const t = dayFraction(now);
  let [r, g, b, a] = sky(t);
  if (underRoof) a = Math.floor(a * val(iniValue("daynight", "Night", "Indoors", "0.55")));
  if (a < 4) return;
  const dark = clamp((a - 40) / 110, 0, 1);
  const L = layer("night", Math.ceil(ww), Math.ceil(wh));
  const x = L.getContext("2d");
  x.globalCompositeOperation = "source-over";
  x.clearRect(0, 0, L.width, L.height);
  x.fillStyle = `rgba(${r},${g},${b},${a / 255})`;
  x.fillRect(0, 0, L.width, L.height);
  const lights = dark > 0 ? skyLights(cam, ww, wh, underRoof, playerC) : [];
  x.globalCompositeOperation = "destination-out";
  const hole = (sx, sy, rad, inner) => {
    const gr = x.createRadialGradient(sx, sy, 0, sx, sy, rad);
    gr.addColorStop(0, "rgba(0,0,0,1)");
    gr.addColorStop(inner, "rgba(0,0,0,1)");
    gr.addColorStop(inner + (1 - inner) * 0.5, "rgba(0,0,0,0.5)");
    gr.addColorStop(1, "rgba(0,0,0,0)");
    x.fillStyle = gr;
    x.fillRect(sx - rad, sy - rad, rad * 2, rad * 2);
  };
  for (const [lx, ly, rad] of lights) {
    const sx = lx - cam.x, sy = ly - cam.y;
    if (sx > -rad && sx < ww + rad && sy > -rad && sy < wh + rad) hole(sx, sy, rad, 0.15);
  }
  const pr = Math.max(0, val(configRead("Gameplay", "Night.Light.Radius", "130")));
  if (pr > 0 && playerC) hole(playerC[0] - cam.x, playerC[1] - cam.y, pr, 0.35);
  ctx.drawImage(L, 0, 0);
  if (dark > 0.3) {
    const glow = iniValue("daynight", "Night", "Glow.Colour", "70 38 8").split(/\s+/).map(Number);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    for (const [lx, ly, rad, warm] of lights) {
      if (!warm) continue;
      const gr2 = Math.max(10, Math.floor(rad / 2));
      const sx = lx - cam.x, sy = ly - cam.y;
      if (sx < -gr2 || sx > ww + gr2 || sy < -gr2 || sy > wh + gr2) continue;
      const gr = ctx.createRadialGradient(sx, sy, 0, sx, sy, gr2);
      gr.addColorStop(0, `rgb(${glow[0]},${glow[1]},${glow[2]})`);
      gr.addColorStop(1, "rgb(0,0,0)");
      ctx.fillStyle = gr;
      ctx.fillRect(sx - gr2, sy - gr2, gr2 * 2, gr2 * 2);
    }
    ctx.restore();
  }
}

function skyLights(cam, ww, wh, underRoof, pc) {
  // The lights in view (a fire, a lamp, a lit window), not one under the fog of war: you don't see its glow there
  const out = [];
  const z = S.mapZ;
  const tx0 = Math.floor(cam.x / G.tw) - 2, ty0 = Math.floor(cam.y / G.th) - 2;
  const cols = Math.floor(ww / G.tw) + 5, rows = Math.floor(wh / G.th) + 5;
  for (let ty = ty0; ty < ty0 + rows; ty++) {
    for (let tx = tx0; tx < tx0 + cols; tx++) {
      const m = mapByPos(Math.floor(tx / G.xt), Math.floor(ty / G.yt), z);
      if (!m) continue;
      const lx = tx - m.mx * G.xt + 1, ly = ty - m.my * G.yt + 1;
      const [t, d, roof, group] = cellOf(m, lx, ly);
      const cx = (tx + 0.5) * G.tw, cy = (ty + 0.5) * G.th;
      const roofShown = roof && !(underRoof && m.name === S.mapName && group === underRoof);
      const rr = Math.max(lightOf(t, true), lightOf(d, true));
      if ((rr || (roof && lightOf(roof, true))) && fogCovers(cx, cy, pc)) continue;
      if (rr && (!roof || !roofShown)) out.push([cx, cy, rr, true]);
      if (roof && roofShown && lightOf(roof, true)) out.push([cx, cy, lightOf(roof, true), true]);
    }
  }
  for (const e of S.ents.values()) {             // (a stove's or a lamp's glow: not through a roof you're not under)
    if (!e.a) continue;
    const rr = lightOf(e.n, false);
    if (!rr) continue;
    const cx = e.dx + e.w / 2, cy = e.dy + e.h / 2;
    const tx = Math.floor(cx / G.tw), ty = Math.floor(cy / G.th);
    const m = mapByPos(Math.floor(tx / G.xt), Math.floor(ty / G.yt), z);
    if (m) {
      const [, , roof, group] = cellOf(m, tx - m.mx * G.xt + 1, ty - m.my * G.yt + 1);
      if (roof && !(underRoof && m.name === S.mapName && group === underRoof)) continue;
    }
    if (fogCovers(cx, cy, pc)) continue;
    out.push([cx, cy, flickers(e.n) ? rr * flicker(e.u) : rr, true]);
  }
  return out;
}

// ----- a flame's light isn't steady (Light.Flicker=1): it breathes and gutters, each fire in its own time
const flickerCache = new Map();
function flickers(name) {
  if (!flickerCache.has(name)) flickerCache.set(name, entityIni(name, "Light.Flicker", "0").trim() === "1");
  return flickerCache.get(name);
}

export function flicker(seed) {
  const t = performance.now(), u = (+seed || 0) * 1.7;
  return 0.9 + 0.05 * Math.sin(t / 130 + u) + 0.035 * Math.sin(t / 53 + u * 2.3) + 0.015 * Math.sin(t / 23 + u);
}

// ================================================================================================================
// The weather (the server says what and how much; it fades here between its messages)
// ================================================================================================================
const W = { kind: "clear", level: 0, fading: false, fadeIn: 15, fadeOut: 12, rain: [], snow: [], fogTex: null };

export function setWeather(msg) {
  W.kind = msg.kind;
  W.level = msg.level;
  W.fading = msg.fading;
  W.fadeIn = msg.fade_in || 15;
  W.fadeOut = msg.fade_out || 12;
}

export function weatherTick(dt) {
  if (W.fading) W.level = Math.max(0, W.level - dt / Math.max(0.1, W.fadeOut));
  else if (W.kind !== "clear") W.level = Math.min(1, W.level + dt / Math.max(0.1, W.fadeIn));
}

export function weatherKind() { return [W.kind, W.level]; }

const kindVal = (kind, key, d = "") => iniValue("weather", "Kind." + kind, key, d);

export function weatherAmbient(want, underRoof) {
  if (W.level < 0.3 || S.mapZ !== 0 || underRoof) return want;
  return kindVal(W.kind, "Ambient", "").trim() || want;
}

export function drawWeather(ctx, cam, w, h, dt, nowMs, underRoof) {
  if (S.mapZ !== 0 || W.level <= 0.01 || W.kind === "clear") return;
  const level = W.level;
  const shade = Math.floor(val(kindVal(W.kind, "Shade", "0")) * level * (underRoof ? 0.5 : 1));
  if (shade > 0) {
    const c = colour(iniValue("weather", "Weather", "Shade.Colour", "40 46 58"), [40, 46, 58]);
    ctx.fillStyle = `rgba(${c[0]},${c[1]},${c[2]},${Math.min(255, shade) / 255})`;
    ctx.fillRect(0, 0, w, h);
  }
  if (underRoof) return;
  const draw = kindVal(W.kind, "Draw", "").trim().toLowerCase();
  const amount = level * (val(kindVal(W.kind, "Amount", "1")) || 1);
  if (draw === "rain") drawRain(ctx, w, h, amount, colour(kindVal(W.kind, "Colour", ""), [168, 182, 206]), dt);
  else if (draw === "snow") drawSnow(ctx, w, h, amount, val(kindVal(W.kind, "Wind", "18")), dt, nowMs);
  else if (draw === "fog") drawFogWeather(ctx, cam, w, h, level, nowMs);
}

function particles(list, n, make) {
  while (list.length < n) list.push(make(true));
  list.length = n;
  return list;
}

function drawRain(ctx, w, h, amount, col, dt) {
  const make = (anywhere) => [Math.random() * (w + 80) - 40, anywhere ? Math.random() * h : -5 - Math.random() * 55,
    520 + Math.random() * 240, 9 + Math.floor(Math.random() * 7)];
  const ps = particles(W.rain, Math.floor(150 * amount), make);
  ctx.strokeStyle = `rgb(${col[0]},${col[1]},${col[2]})`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const p of ps) {
    p[1] += p[2] * dt;
    p[0] -= p[2] * dt * 0.22;
    if (p[1] > h || p[0] < -50) p.splice(0, 4, ...make(false));
    ctx.moveTo(p[0], p[1]);
    ctx.lineTo(p[0] + p[3] * 0.22, p[1] - p[3]);
  }
  ctx.stroke();
}

function drawSnow(ctx, w, h, amount, wind, dt, nowMs) {
  const t = nowMs / 1000;
  const blizzard = wind > 60;
  const make = (anywhere) => [Math.random() * (w + 40) - 20, anywhere ? Math.random() * h : -3 - Math.random() * 27,
    30 + Math.random() * 40, [1, 2, 2][Math.floor(Math.random() * 3)], Math.random() * 6.3];
  const ps = particles(W.snow, Math.floor(130 * amount), make);
  for (const p of ps) {
    p[1] += p[2] * dt;
    p[0] += (wind + 14 * Math.sin(t * 1.3 + p[4])) * dt;
    if (p[1] > h || p[0] > w + 30) {
      p.splice(0, 5, ...make(false));
      if (blizzard) p[0] = Math.random() * w * 1.5 - w * 0.5;
    }
    ctx.fillStyle = "rgb(140,150,172)";
    ctx.beginPath(); ctx.arc(p[0] + 1, p[1] + 1, p[3], 0, 6.283); ctx.fill();
    ctx.fillStyle = "rgb(252,253,255)";
    ctx.beginPath(); ctx.arc(p[0], p[1], p[3], 0, 6.283); ctx.fill();
  }
}

function fogTexture() {
  if (W.fogTex) return W.fogTex;
  const n = 256, c = document.createElement("canvas");
  c.width = n; c.height = n;
  const x = c.getContext("2d");
  const small = document.createElement("canvas");
  small.width = 8; small.height = 8;
  const sx = small.getContext("2d");
  const im = sx.createImageData(8, 8);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 64; i++) {
    const v = Math.floor(rnd() * 255);
    im.data.set([220, 224, 228, Math.floor((v / 255) ** 2 * 150 + 25)], i * 4);
  }
  sx.putImageData(im, 0, 0);
  x.imageSmoothingEnabled = true;
  x.imageSmoothingQuality = "high";
  for (let ty = -1; ty <= 1; ty++) for (let tx = -1; tx <= 1; tx++) x.drawImage(small, tx * n, ty * n, n, n);
  W.fogTex = c;
  return c;
}

function drawFogWeather(ctx, cam, w, h, level, nowMs) {
  const tex = fogTexture();
  const drift = Math.floor(nowMs / 1000 * 9);
  const ox = -(((cam.x + drift) % 256) + 256) % 256, oy = -((cam.y % 256) + 256) % 256;
  ctx.save();
  ctx.globalAlpha = Math.min(1, 220 * level / 255);
  for (let y = oy; y < h; y += 256) for (let x = ox; x < w; x += 256) ctx.drawImage(tex, x, y);
  ctx.restore();
}

export function drawFlash(ctx, w, h, nowMs) {
  if (!S.flashAt) return;
  const t = nowMs - S.flashAt;
  if (t > 450 || t < 0) { S.flashAt = 0; return; }
  const a = 170 * (1 - t / 450) * (t > 80 || Math.floor(t / 40) % 2 === 0 ? 1 : 0.4);
  ctx.fillStyle = `rgba(236,240,255,${a / 255})`;
  ctx.fillRect(0, 0, w, h);
}

// ================================================================================================================
// Fog of war: cells near the player are clear (and remembered as seen), seen ones dim, the rest black
// ================================================================================================================
const F = { enabled: true, seen: 130, lastX: -1e9, lastY: -1e9, grid: null, key: "", revealed: new Map() };

export function fogInit() {
  F.enabled = val(configRead("Gameplay", "FogOfWar.Enabled", "0")) === 1;
  F.seen = clamp(val(configRead("Interface", "FogOfWar.Seen.Darkness", "130")), 0, 255);
  F.smooth = val(configRead("Interface", "FogOfWar.Smooth", "1")) === 1;
}

export function fogEnabled() { return F.enabled && S.view > 0; }

export function revealCell(map, cell) {
  const n = fogCell(), fxt = Math.ceil(G.sw / n);
  let x, y;
  if (String(cell).includes(",")) {
    [x, y] = String(cell).split(",").map(Number);
  } else {
    const c = Math.floor(val(cell));
    x = ((c - 1) % fxt) + 1;
    y = Math.floor((c - 1) / fxt) + 1;
  }
  const id = (y - 1) * fxt + x;
  markExplored(map, id);
  let s = F.revealed.get(map);
  if (!s) F.revealed.set(map, (s = new Set()));
  s.add(id);
  F.lastX = -1e9;
}

function inView(cx, cy, pcx, pcy, margin = 0) {
  return Math.hypot(cx - pcx, cy - pcy) < S.view + margin;
}

export function fogCovers(x, y, pc, margin = 0) {
  // Is global point x,y under the fog for this player (not in view now)? margin: a little more view (for something
  // already in sight: it doesn't blink out and in at the edge as you, or it, shuffle a pixel or two)
  if (!fogEnabled() || !pc) return false;
  const n = fogCell();
  const cx = (Math.floor(x / n) + 0.5) * n, cy = (Math.floor(y / n) + 0.5) * n;
  if (inView(cx, cy, pc[0], pc[1], margin)) return false;
  const m = mapAt(S.mapZ, x, y);
  if (!m) return true;
  const fxt = Math.ceil(G.sw / n);
  const id = Math.floor((y - m.oy) / n) * fxt + Math.floor((x - m.ox) / n) + 1;
  const r = F.revealed.get(m.name);
  return !(r && r.has(id));
}

export function fogBlack(x, y) {
  // Never seen (black): the tiles there can't be named or clicked
  if (!fogEnabled()) return false;
  const m = mapAt(S.mapZ, x, y);
  if (!m) return true;
  const n = fogCell(), fxt = Math.ceil(G.sw / n);
  const id = Math.floor((y - m.oy) / n) * fxt + Math.floor((x - m.ox) / n) + 1;
  return !isExplored(m.name, id);
}

export function fogUpdate(pc) {
  // The cells round the player are seen now (remembered for the server)
  if (!fogEnabled() || !pc) return;
  if (Math.abs(pc[0] - F.lastX) < 4 && Math.abs(pc[1] - F.lastY) < 4) return;
  F.lastX = pc[0]; F.lastY = pc[1];
  const n = fogCell(), fxt = Math.ceil(G.sw / n), fyt = Math.ceil(G.sh / n);
  const v = S.view;
  for (let cy = Math.floor((pc[1] - v) / n); cy <= Math.floor((pc[1] + v) / n); cy++) {
    for (let cx = Math.floor((pc[0] - v) / n); cx <= Math.floor((pc[0] + v) / n); cx++) {
      const x = (cx + 0.5) * n, y = (cy + 0.5) * n;
      if (!inView(x, y, pc[0], pc[1])) continue;
      const m = mapAt(S.mapZ, x, y);
      if (!m) continue;
      const lx = cx - Math.floor(m.ox / n), ly = cy - Math.floor(m.oy / n);
      if (lx < 0 || ly < 0 || lx >= fxt || ly >= fyt) continue;
      markExplored(m.name, ly * fxt + lx + 1);
    }
  }
  F.key = "";
}

export function drawFog(ctx, cam, ww, wh, pc) {
  if (!fogEnabled() || !pc) return;
  const n = fogCell(), fxt = Math.ceil(G.sw / n);
  const gx0 = Math.floor(cam.x / n) - 1, gy0 = Math.floor(cam.y / n) - 1;
  const cols = Math.ceil(ww / n) + 3, rows = Math.ceil(wh / n) + 3;
  const key = [gx0, gy0, cols, rows, Math.round(pc[0] / 4), Math.round(pc[1] / 4), S.view, S.mapName].join(",");
  const L = layer("fog", cols, rows);
  if (key !== F.key) {
    F.key = key;
    const x = L.getContext("2d");
    const im = x.createImageData(cols, rows);
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const gx = gx0 + i, gy = gy0 + j;
        const cx = (gx + 0.5) * n, cy = (gy + 0.5) * n;
        let a = 255;
        const m = mapAt(S.mapZ, cx, cy);
        if (m) {
          const lx = gx - Math.floor(m.ox / n), ly = gy - Math.floor(m.oy / n);
          const id = ly * fxt + lx + 1;
          const r = F.revealed.get(m.name);
          if (inView(cx, cy, pc[0], pc[1]) || (r && r.has(id))) a = 0;
          else if (isExplored(m.name, id)) a = F.seen;
        }
        im.data.set([9, 6, 5, a], (j * cols + i) * 4);
      }
    }
    x.putImageData(im, 0, 0);
  }
  ctx.save();
  ctx.imageSmoothingEnabled = F.smooth;
  ctx.imageSmoothingQuality = "high";
  if (F.smooth && "filter" in ctx) ctx.filter = `blur(${Math.round(n * 0.45)}px)`;
  ctx.drawImage(L, gx0 * n - cam.x, gy0 * n - cam.y, cols * n, rows * n);
  ctx.restore();
}
