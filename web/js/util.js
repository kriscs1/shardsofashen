// Small helpers, as the desktop game's lb.py has them (val, word$, Strip.Digits$...), and colours and text.

export const FONT = '"Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif';

export function val(text) {
  if (typeof text === "number") return text;
  if (text == null) return 0;
  const m = /^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)/.exec(String(text));
  return m ? parseFloat(m[1]) : 0;
}

export function word(text, n, delim = " ") {
  if (text == null || n < 1) return "";
  const parts = String(text).split(delim).filter((p) => p !== "");
  return n <= parts.length ? parts[n - 1] : "";
}

export function trim(s) { return String(s).replace(/^ +| +$/g, ""); }

export function stripDigits(name) {
  return name.length > 3 && /^\d{3}$/.test(name.slice(-3)) ? name.slice(0, -3) : name;
}

// (what the player sees a thing called: its Entities.ini / Tiles.ini Display.Name=, else its name tidied; assets.js
// fills it. The name itself stays what scripts, saves and pictures go by)
export const DISPLAY_NAMES = new Map();
export function pretty(name) {
  const n = String(name || "");
  if (DISPLAY_NAMES.size) {
    const shown = DISPLAY_NAMES.get(n.toUpperCase()) || DISPLAY_NAMES.get(stripDigits(n).toUpperCase());
    if (shown) return shown;
  }
  return stripDigits(n).replace(/_/g, " ");
}

export function lbstr(x) {
  if (typeof x === "string") return x;
  if (Number.isInteger(x)) return String(x);
  return String(parseFloat(x.toFixed(9)));
}

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const dist = (x1, y1, x2, y2) => Math.hypot(x1 - x2, y1 - y2);

const NAMED = {
  buttonface: [240, 240, 240], yellow: [255, 255, 0], brown: [128, 128, 0], red: [255, 0, 0],
  darkred: [128, 0, 0], pink: [255, 0, 255], darkpink: [128, 0, 128], blue: [0, 0, 255], darkblue: [0, 0, 128],
  green: [0, 255, 0], darkgreen: [0, 128, 0], cyan: [0, 255, 255], darkcyan: [0, 128, 128], white: [255, 255, 255],
  black: [0, 0, 0], lightgray: [192, 192, 192], lightgrey: [192, 192, 192], darkgray: [128, 128, 128],
  darkgrey: [128, 128, 128],
};

export function colour(text, dflt = [0, 0, 0]) {
  if (Array.isArray(text)) return text;
  const t = String(text).trim().toLowerCase();
  const parts = t.split(/\s+/);
  if (parts.length >= 3) {
    const c = parts.slice(0, 3).map((p) => clamp(Math.round(parseFloat(p)), 0, 255));
    return c.some(Number.isNaN) ? dflt : c;
  }
  return NAMED[t] || dflt;
}

export const rgb = (c, a = 1) => (a >= 1 ? `rgb(${c[0]},${c[1]},${c[2]})` : `rgba(${c[0]},${c[1]},${c[2]},${a})`);

// The message colours of the chat (ui.display_message)
export function messageColour(kind) {
  const t = String(kind).toUpperCase();
  if (["ERROR", "WARNING", "FAIL"].includes(t)) return "darkred";
  if (["INFORMATION", "SUCCESS"].includes(t)) return "darkblue";
  if (t === "ACHIEVEMENT") return "darkgreen";
  if (t === "LOG") return "darkcyan";
  if (["INFO", "EXAMINE"].includes(t)) return "black";
  if (t === "COMBAT") return "brown";
  if (t === "DAMAGE") return "205 18 18";
  if (t === "LEVELUP") return "140 82 0";
  const c = t.toLowerCase();
  if (["white", "black", "lightgray", "darkgray", "red", "darkred", "pink", "darkpink", "blue", "darkblue", "green",
    "darkgreen", "darkcyan", "brown"].includes(c)) return c;
  if (c === "cyan") return "darkblue";
  if (c === "yellow") return "darkgreen";
  if (val(word(c, 1)) > 0 || word(c, 3) !== "") return c;
  return "darkgray";
}

// ----- text on a canvas: sizes are the desktop game's points
export function fontPx(size) { return Math.max(6, Math.round(size * 4 / 3)); }

export function setFont(ctx, size, bold = false) {
  ctx.font = `${bold ? "bold " : ""}${fontPx(size)}px ${FONT}`;
}

export function textWidth(ctx, text, size, bold = false) {
  if (!text) return 0;
  setFont(ctx, size, bold);
  return ctx.measureText(text).width;
}

// Text with its top at y (the desktop game's draw_text)
export function drawText(ctx, text, x, y, size, bold, col) {
  if (!text) return 0;
  setFont(ctx, size, bold);
  ctx.textBaseline = "top";
  ctx.fillStyle = typeof col === "string" && !col.startsWith("rgb") && !col.startsWith("#") ? rgb(colour(col)) :
    (Array.isArray(col) ? rgb(col) : col);
  ctx.fillText(text, x, y);
  return ctx.measureText(text).width;
}

// Text whose capitals are centred between top and top+h: the font's own capital height, measured (not guessed
// from its size - fonts differ, and a guess sat the text too high)
const capHeights = new Map();
export function drawTextMid(ctx, text, x, top, h, size, bold, col) {
  if (!text) return 0;
  setFont(ctx, size, bold);
  ctx.textBaseline = "alphabetic";                // (measured from the baseline the text sits on)
  let cap = capHeights.get(ctx.font);
  if (cap === undefined) {
    cap = ctx.measureText("H").actualBoundingBoxAscent || fontPx(size) * 0.7;
    if (document.fonts && document.fonts.status === "loaded") capHeights.set(ctx.font, cap);   // (once it's real)
  }
  ctx.fillStyle = typeof col === "string" && !col.startsWith("rgb") && !col.startsWith("#") ? rgb(colour(col)) :
    (Array.isArray(col) ? rgb(col) : col);
  ctx.fillText(text, x, Math.round(top + (h + cap) / 2));
  ctx.textBaseline = "top";
  return ctx.measureText(text).width;
}

export function centreText(ctx, xm, y, text, size, bold, col) {
  const w = textWidth(ctx, text, size, bold);
  drawText(ctx, text, Math.round(xm - w / 2), y, size, bold, col);
}

export function fitText(ctx, text, maxW, size, bold = false) {
  if (maxW <= 0 || !text) return "";
  if (textWidth(ctx, text, size, bold) <= maxW) return text;
  let n = text.length;
  while (n > 0 && textWidth(ctx, text.slice(0, n).trim() + "...", size, bold) > maxW) n--;
  return n > 0 ? text.slice(0, n).trim() + "..." : "";
}

export function wrapLines(ctx, text, w, size, bold = false) {
  const lines = [];
  let line = "";
  for (const wd of String(text).split(/\s+/).filter(Boolean)) {
    const attempt = line ? line + " " + wd : wd;
    if (textWidth(ctx, attempt, size, bold) > w && line) {
      lines.push(line);
      line = wd;
    } else line = attempt;
  }
  if (line) lines.push(line);
  return lines.length ? lines : [""];
}

export function roundBox(ctx, x, y, w, h, fill, border = null, width = 1, radius = 10) {
  const r = Math.max(0, radius / 2);
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
  if (fill) {
    ctx.fillStyle = Array.isArray(fill) ? rgb(fill) : fill;
    ctx.fill();
  }
  if (border && width > 0) {
    ctx.lineWidth = width;
    ctx.strokeStyle = Array.isArray(border) ? rgb(border) : border;
    ctx.stroke();
  }
}

export function now() { return performance.now(); }
