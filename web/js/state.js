// What the browser knows of the game: the maps round the player, the things and people on them, the player.
import { A, configRead } from "./assets.js";

export const G = { tw: 32, th: 32, xt: 25, yt: 21, sw: 800, sh: 672, walkRes: 7 };

export const S = {
  name: "", uid: 0, admin: false,
  me: null,                   // the "me" message: hp, inventory, skills...
  quests: [], marks: [], level: 1,
  labels: [],                 // [{n, k, x, y, z, m}]: the world map's names (data\WorldMap.ini)
  where: [],                  // [{name, x, y, z}]: everyone's place (global pixels), for the minimap's dots
  maps: new Map(),            // name -> map data (mapdata messages), with mx, my, mz, ox, oy
  byPos: new Map(),           // "mx,my,mz" -> map
  cells: new Map(),           // "map,x,y" -> [tile, decor]: this player's own tiles
  locks: new Map(),           // "map,x,y" -> the message of a lock shut for this player
  ents: new Map(),            // uid -> entity (with its drawn position)
  pos: null,                  // the player: {x, y, z, i, d} and drawn position
  viewMaps: [],
  box: { mode: "" },
  messages: [],               // [text, colour, time] newest first
  clock: { day: 0.3, secs: 1440, on: true, at: 0 },
  weather: { kind: "clear", level: 0 },
  explored: new Map(),        // map -> Set of fog cells, or "all"
  exploredNew: new Map(),     // cells seen since the server was last told
  players: [], max: 5,
  itemInUse: 0,               // the inventory item being used (Use, then click what with)
  spellReady: "",             // a spell held ready (Channeling): the next click is who it's cast at
  mapName: "", mapZ: 0,
  journal: null,
  sleep: null, levelBanner: null, hurtUntil: 0, flashAt: 0,
  view: 200,
  mapChanged: 0,
};

export function setGeometry() {
  const g = A.m.geometry;
  G.tw = g.tw; G.th = g.th; G.xt = g.xt; G.yt = g.yt; G.walkRes = g.walk_res;
  G.sw = G.tw * G.xt; G.sh = G.th * G.yt;
}

export function resetWorld() {
  S.maps.clear(); S.byPos.clear(); S.cells.clear(); S.locks.clear(); S.ents.clear();
  S.pos = null; S.box = { mode: "" };
}

export function addMap(d) {
  const [mx, my, mz] = d.name.split(",").map(Number);
  const m = { ...d, mx, my, mz, ox: mx * G.sw, oy: my * G.sh };
  S.maps.set(d.name, m);
  S.byPos.set(mx + "," + my + "," + mz, m);
  return m;
}

export function mapAt(z, x, y) {
  return S.byPos.get(Math.floor(x / G.sw) + "," + Math.floor(y / G.sh) + "," + z) || null;
}

export function mapByPos(mx, my, mz) { return S.byPos.get(mx + "," + my + "," + mz) || null; }

// A map's tile x,y (1-based) as this player sees it: [tile, decor, roof, roof group, tree top]
export function cellOf(m, x, y) {
  const c = (y - 1) * G.xt + (x - 1);
  const o = S.cells.get(m.name + "," + x + "," + y);
  const under = m.under ? m.under[c] : "";        // (a rug: under the decor)
  return o ? [o[0], o[1], m.roof[c], m.group[c], m.infront[c], under] : [m.tile[c], m.decor[c], m.roof[c], m.group[c], m.infront[c], under];
}

// The cell at global tile gx,gy (0-based) on level z, or null
export function cellAtTile(z, gx, gy) {
  const mx = Math.floor(gx / G.xt), my = Math.floor(gy / G.yt);
  const m = mapByPos(mx, my, z);
  if (!m) return null;
  return cellOf(m, gx - mx * G.xt + 1, gy - my * G.yt + 1);
}

export function tileAt(z, x, y) {
  const m = mapAt(z, x, y);
  if (!m) return null;
  return { m, tx: Math.floor((x - m.ox) / G.tw) + 1, ty: Math.floor((y - m.oy) / G.th) + 1 };
}

// ----- the things and people seen, moved smoothly between the server's ticks
const GLIDE_MS = 70;
const SIT_MS = 260;                    // (sitting down or getting up: a step onto the seat, eased, not a jump)
const sitting = (i) => /_Sit[1248]$/.test(i || "");

export function applySnap(msg, now) {
  for (const e of msg.add) {
    e.dx = e.x; e.dy = e.y; e.fx = e.x; e.fy = e.y; e.t0 = now;
    S.ents.set(e.u, e);
  }
  for (const c of msg.chg) {
    const e = S.ents.get(c.u);
    if (!e) continue;
    if ("x" in c || "y" in c) {
      e.fx = e.dx; e.fy = e.dy; e.t0 = now;
      e.gms = "i" in c && sitting(c.i) !== sitting(e.i) ? SIT_MS : 0;
      const jump = Math.abs((c.x ?? e.x) - e.dx) > 96 || Math.abs((c.y ?? e.y) - e.dy) > 96;
      if (jump) { e.fx = c.x ?? e.x; e.fy = c.y ?? e.y; }
    }
    Object.assign(e, c);
  }
  for (const u of msg.del) S.ents.delete(u);
  const me = msg.me;
  if (!S.pos || S.pos.z !== me.z || Math.abs(me.x - S.pos.dx) > 96 || Math.abs(me.y - S.pos.dy) > 96) {
    S.pos = { ...me, dx: me.x, dy: me.y, fx: me.x, fy: me.y, t0: now };
  } else {
    S.pos.fx = S.pos.dx; S.pos.fy = S.pos.dy; S.pos.t0 = now;
    if (me.x !== S.pos.x || me.y !== S.pos.y) S.pos.gms = sitting(me.i) !== sitting(S.pos.i) ? SIT_MS : 0;
    Object.assign(S.pos, me);
  }
  S.viewMaps = msg.maps;
}

export function glide(now) {
  const step = (e) => {
    let k = Math.min(1, (now - e.t0) / (e.gms || GLIDE_MS));
    if (e.gms) k = k * k * (3 - 2 * k);                       // (onto a seat or off it: eased in and out)
    e.dx = e.fx + (e.x - e.fx) * k;
    e.dy = e.fy + (e.y - e.fy) * k;
  };
  for (const e of S.ents.values()) step(e);
  if (S.pos) step(S.pos);
}

export function myPlayer() {
  // The player as an entity to draw (their own sprite, gear and health bar)
  const p = S.pos, me = S.me;
  if (!p || !me) return null;
  const [w, h] = sizeOfImage(p.i);
  // (unseen by monsters but still drawn: invisible, a shimmer; in another body, that body - tricks.py)
  return { u: S.uid, k: 1, n: S.name, i: p.i, x: p.x, y: p.y, dx: p.dx, dy: p.dy, w, h,
    a: me.visible || me.invisible_left || me.swap ? 1 : 0, gh: me.invisible_left ? 1 : 0,
    hp: me.hp, mh: me.max_hp, b: me.hp < me.max_hp ? 1 : 0, worn: me.worn || [], look: me.look, self: true };
}

function sizeOfImage(name) {
  const s = A.m.sprites[name];
  return s || [32, 32];
}

export function addMessage(text, colour, id = 0, of = 0) {
  if (S.messages.length && S.messages[0][0] === text && performance.now() - S.messages[0][2] < 500) return;
  // (of: the id of the line this one finishes - "You place the poultry on the range.." then "..and cook it
  // perfectly!" - one line, in the colour of how it turned out, brought down to the newest)
  const i = of ? S.messages.findIndex((m) => m[3] === of) : -1;
  if (i >= 0) {
    const [line] = S.messages.splice(i, 1);
    S.messages.unshift([line[0].replace(/\.+$/, "") + "... " + text.replace(/^\.+\s*/, ""), colour, performance.now(), id]);
    return;
  }
  S.messages.unshift([text, colour, performance.now(), id]);
  S.messages.length = Math.min(S.messages.length, 100);
}

// ----- fog of war: what this player has seen (16-pixel cells, numbered row by row from 1)
export function fogCell() { return Math.max(4, Math.min(128, Math.floor(+configRead("Interface", "FogOfWar.Cell.Size", "16")) || 16)); }

export function markExplored(name, cell) {
  let s = S.explored.get(name);
  if (s === "all") return false;
  if (!s) { s = new Set(); S.explored.set(name, s); }
  if (s.has(cell)) return false;
  s.add(cell);
  S.exploredVersion = (S.exploredVersion || 0) + 1;
  let n = S.exploredNew.get(name);
  if (!n) { n = []; S.exploredNew.set(name, n); }
  n.push(cell);
  return true;
}

export const isHomeMap = (name) => /^0,0,\d+$/.test(name || "") && Number(name.split(",")[2]) >= 1000;

export function isExplored(name, cell) {
  if (isHomeMap(name)) return true;                 // (a homestead is all known: no fog there)
  const s = S.explored.get(name);
  return s === "all" || (s && s.has(cell));
}
