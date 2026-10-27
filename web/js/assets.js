// The pictures and data the server's web/assets has (made by tools/export_web_assets.py). Pictures load the first time
// they are wanted; whoever drew without them is told when they arrive (onLoaded) and draws again.
import { val, trim } from "./util.js";

export const A = { m: null, imgs: new Map(), pending: 0, listeners: [] };
const lower = { tiles: null, entities: null, config: null, spells: null, shards: null };
// (the spell you wrote at the Spellwright's Lectern: its values come from the server, not Spells.ini - main.js sets it)
export const OWN = { spell: "Own_Spell", v: null };

export async function loadManifest() {
  const r = await fetch("/assets/manifest.json", { cache: "no-cache" });
  if (!r.ok) throw new Error("The game's pictures aren't on this server yet (web/assets: run tools/export_web_assets.py).");
  A.m = await r.json();
  for (const k of Object.keys(lower)) lower[k] = indexIni(A.m[k] || {});
  return A.m;
}

function indexIni(sections) {
  // {UPPER section: {UPPER key: value}} like the game's INI reading (any case)
  const out = {};
  for (const [name, items] of Object.entries(sections)) {
    const d = (out[name.toUpperCase()] = out[name.toUpperCase()] || {});
    for (const [k, v] of Object.entries(items)) if (!(k.toUpperCase() in d)) d[k.toUpperCase()] = v;
  }
  return out;
}

function iniRead(table, section, key, dflt) {
  const s = lower[table] && lower[table][String(section).toUpperCase()];
  if (!s) return String(dflt).trim();
  const v = s[String(key).toUpperCase()];
  return v === undefined ? String(dflt).trim() : v;
}

export const tileIni = (name, key, dflt = "") => iniRead("tiles", name, key, dflt);
export const configRead = (section, key, dflt = "") => iniRead("config", section, key, dflt);
export const spellIni = (spell, key, dflt = "") => {
  if (spell === OWN.spell && OWN.v) {
    const k = Object.keys(OWN.v).find((x) => x.toUpperCase() === String(key).toUpperCase());
    return k === undefined ? String(dflt).trim() : String(OWN.v[k]);
  }
  return iniRead("spells", spell, key, dflt);
};
export const shardsIni = (section, key, dflt = "") => iniRead("shards", section, key, dflt);

export function isDecorTile(name) {
  return !!name && tileIni(name, "Layer", "").trim().toLowerCase() === "decor";
}

export function entityIni(name, key, dflt = "") {
  if (isDecorTile(name) && !(lower.entities && lower.entities[String(name).toUpperCase()])) return tileIni(name, key, dflt);
  return iniRead("entities", name, key, dflt);
}

export function iniList(file, section) {
  // [[key, value]...] of a section of a table kept in file order (DayNight.ini, Weather.ini)
  const t = A.m[file] || {};
  for (const [name, items] of Object.entries(t)) if (name.toUpperCase() === section.toUpperCase()) return items;
  return [];
}

export function iniValue(file, section, key, dflt = "") {
  for (const [k, v] of iniList(file, section)) if (k.toUpperCase() === key.toUpperCase()) return v;
  return String(dflt);
}

export function dictIni(file, section, key, dflt = "") {
  const t = A.m[file] || {};
  for (const [name, items] of Object.entries(t)) {
    if (name.toUpperCase() !== section.toUpperCase()) continue;
    for (const [k, v] of Object.entries(items)) if (k.toUpperCase() === key.toUpperCase()) return v;
  }
  return String(dflt);
}

// ----- pictures
export function onLoaded(fn) { A.listeners.push(fn); }

function image(key, url) {
  let e = A.imgs.get(key);
  if (e) return e;
  e = { img: new Image(), ok: false, bad: false };
  A.imgs.set(key, e);
  A.pending++;
  e.img.decoding = "async";
  e.img.onload = () => {
    e.ok = true;
    A.pending--;
    for (const f of A.listeners) f(key);
  };
  e.img.onerror = () => { e.bad = true; A.pending--; };
  e.img.src = url;
  return e;
}

export const has = (name) => !!name && !!A.m && name in A.m.sprites;

export function size(name) {
  const s = A.m && A.m.sprites[name];
  return s ? s : [32, 32];
}

export function sprite(name) {
  // The sprite's image if it has loaded (null while it loads, or if there's no such sprite)
  if (!has(name)) return null;
  const e = image("s:" + name, "/assets/sprites/" + encodeURIComponent(name) + ".png");
  return e.ok ? e.img : null;
}

export function fallback() { return has("Placeholder") ? "Placeholder" : ""; }

export function animFrame(name, prefix, k) {
  const e = image("a:" + name + prefix + k, "/assets/anim/" + encodeURIComponent(name + "~" + prefix + k) + ".png");
  return e.ok ? e.img : null;
}

export function mask(name) {
  const e = image("m:" + name, "/assets/masks/" + encodeURIComponent(name) + ".png");
  return e.ok ? e.img : null;
}

export function texture(name) {
  const e = image("t:" + name, "/assets/textures/" + encodeURIComponent(name) + ".png");
  return e.ok ? e.img : null;
}

export function preload(names) {
  // Starts loading these sprites; resolves when they've all arrived (or failed)
  return Promise.all(names.filter(has).map((n) => new Promise((resolve) => {
    const e = image("s:" + n, "/assets/sprites/" + encodeURIComponent(n) + ".png");
    if (e.ok || e.bad) return resolve();
    e.img.addEventListener("load", resolve, { once: true });
    e.img.addEventListener("error", resolve, { once: true });
  })));
}

export function tileAnim(name) { return (A.m.anim || {})[name] || null; }

export function frames(name, kind) {
  // (n, ms) of a tile or object drawn from its own pictures <Name>1..N (Anim.Frames) or null
  const key = kind + name;
  A.framesCache = A.framesCache || new Map();
  if (A.framesCache.has(key)) return A.framesCache.get(key);
  const read = kind === "t" ? tileIni : entityIni;
  const n = Math.floor(val(read(name, "Anim.Frames", "0")));
  const ms = Math.max(30, Math.floor(val(read(name, "Anim.Speed", "200")) || 200));
  let out = null;
  if (n > 1) {
    let all = true;
    for (let k = 1; k <= n; k++) if (!has(name + k)) all = false;
    if (all) out = [n, ms];
  }
  A.framesCache.set(key, out);
  return out;
}

export function animSetting(key) {
  const d = { "Water.Frames": 6, "Water.Speed": 260, "Flame.Frames": 4, "Flame.Speed": 140, "Sway.Frames": 6,
    "Sway.Speed": 230 }[key];
  return Math.max(1, Math.floor(val(configRead("Animation", key, String(d)))) || d);
}

export function foamColour() {
  const p = trim(configRead("Animation", "Foam.Colour", "234 244 250")).split(/[\s,]+/).map(Number);
  return p.length >= 3 ? p : [234, 244, 250];
}
