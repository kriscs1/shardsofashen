// How a character looks: the Player sprite's skin, hair, shirt and trousers in colours of their own. The sprite is drawn
// in a few exact colours (a main one and its shades for each part), so each is swapped for the chosen colour at the
// same brightness; the eyes, mouth and boots, and the armour worn over it, stay as they are.
import { sprite } from "./assets.js";

// part -> [the sprite's main colour, its other shades]
const PARTS = {
  hair: [[102, 55, 10], [[72, 38, 6]]],
  skin: [[244, 184, 221], [[214, 150, 190]]],
  shirt: [[0, 0, 128], [[20, 30, 175], [0, 0, 90]]],
  legs: [[64, 0, 255], [[44, 0, 185]]],
};

export const PART_NAMES = { skin: "Skin", hair: "Hair", shirt: "Shirt", legs: "Trousers" };

export const PRESETS = {
  skin: ["#f4b8dd", "#ffdcc0", "#f1c27d", "#e0ac69", "#c68642", "#8d5524", "#5c3a1e"],
  hair: ["#66370a", "#1c1410", "#3b2412", "#e6c35c", "#a83a1a", "#9a9a9a", "#eeeeee"],
  shirt: ["#000080", "#8b1a1a", "#1f6b2a", "#6b4423", "#5a2a82", "#2f4f4f", "#d8d8c8"],
  legs: ["#4000ff", "#5a3a1e", "#222222", "#2d4a1e", "#6a6a6a", "#2a3f7a", "#a08050"],
};

export const DEFAULT_LOOK = { skin: PRESETS.skin[0], hair: PRESETS.hair[0], shirt: PRESETS.shirt[0], legs: PRESETS.legs[0] };

function hex(c) {
  const n = parseInt(c.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const lum = (c) => 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] + 1;

function swaps(look) {
  // "r,g,b" of each of the sprite's colours -> its new colour
  const out = new Map();
  for (const [part, [main, shades]] of Object.entries(PARTS)) {
    const want = look && look[part];
    if (!want) continue;
    const w = hex(want);
    out.set(main.join(","), w);
    for (const s of shades) {
      const k = Math.min(1.8, lum(s) / lum(main));
      out.set(s.join(","), w.map((v) => Math.max(0, Math.min(255, Math.round(k >= 1 ? v + (255 - v) * (k - 1) * 0.6 : v * k)))));
    }
  }
  return out;
}

const cache = new Map();

export function lookKey(look) {
  return look ? ["skin", "hair", "shirt", "legs"].map((k) => look[k] || "").join("") : "";
}

export function lookImage(name, look) {
  // The sprite name (a Player frame) in these colours: a canvas, or the plain sprite while it loads
  const base = sprite(name);
  if (!base || !look || !/^Player/.test(name)) return base;
  const key = name + "|" + lookKey(look);
  let c = cache.get(key);
  if (c) return c;
  c = document.createElement("canvas");
  c.width = base.width;
  c.height = base.height;
  const x = c.getContext("2d", { willReadFrequently: true });
  x.drawImage(base, 0, 0);
  const d = x.getImageData(0, 0, c.width, c.height);
  const map = swaps(look);
  for (let i = 0; i < d.data.length; i += 4) {
    if (!d.data[i + 3]) continue;
    const to = map.get(d.data[i] + "," + d.data[i + 1] + "," + d.data[i + 2]);
    if (to) { d.data[i] = to[0]; d.data[i + 1] = to[1]; d.data[i + 2] = to[2]; }
  }
  x.putImageData(d, 0, 0);
  if (cache.size > 2000) cache.clear();
  cache.set(key, c);
  return c;
}

// ----- the picker (making a character, and Options > Appearance)
export function buildPicker(root, look, onChange) {
  root.innerHTML = "";
  const cur = { ...DEFAULT_LOOK, ...(look || {}) };
  const preview = document.createElement("canvas");
  preview.width = 96;
  preview.height = 96;
  preview.className = "look-preview";
  const rows = document.createElement("div");
  rows.className = "look-rows";
  for (const part of ["skin", "hair", "shirt", "legs"]) {
    const row = document.createElement("div");
    row.className = "look-row";
    const label = document.createElement("span");
    label.textContent = PART_NAMES[part];
    row.append(label);
    const swatches = [];
    for (const col of PRESETS[part]) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "swatch";
      b.style.background = col;
      b.title = col;
      b.setAttribute("aria-label", `${PART_NAMES[part]} ${col}`);
      b.onclick = () => set(col);
      swatches.push([b, col]);
      row.append(b);
    }
    const custom = document.createElement("input");
    custom.type = "color";
    custom.title = "Any colour";
    custom.setAttribute("aria-label", `${PART_NAMES[part]}: any colour`);
    custom.addEventListener("input", () => set(custom.value));
    row.append(custom);
    const set = (col) => {
      cur[part] = col;
      custom.value = col;
      for (const [b, c] of swatches) b.classList.toggle("on", c === col);
      draw();
      if (onChange) onChange({ ...cur });
    };
    custom.value = cur[part];
    for (const [b, c] of swatches) b.classList.toggle("on", c === cur[part]);
    rows.append(row);
  }
  root.append(preview, rows);
  let turn = 0;
  const frames = ["Player4a", "Player2a", "Player1a", "Player8a"];
  function draw() {
    const x = preview.getContext("2d");
    x.clearRect(0, 0, 96, 96);
    x.imageSmoothingEnabled = false;
    const im = lookImage(frames[turn % 4], cur);
    if (im) x.drawImage(im, 0, 0, 96, 96);
  }
  const timer = setInterval(() => {
    if (!root.isConnected) { clearInterval(timer); return; }
    turn++;
    draw();
  }, 900);
  setTimeout(draw, 300);
  draw();
  return () => ({ ...cur });
}
