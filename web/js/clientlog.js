// The player's own side of Send log: the page's errors and warnings (with where they were), the connection coming and
// going, the page hidden and shown, and what it's running on. Kept in memory only, the last lines; it goes nowhere
// but with Send log, shown first. (Imported first, so it hears the other modules' errors too.)

export const CL = { lines: [], started: Date.now(), frames: 0, since: performance.now(), ping: 0, tick: 0 };
const MOST = 400;                                 // (lines kept)

const clock = () => {                             // (the device's own time, as the server's lines are its own)
  const d = new Date(), two = (n) => String(n).padStart(2, "0");
  return `${two(d.getHours())}:${two(d.getMinutes())}:${two(d.getSeconds())}.${String(d.getMilliseconds()).padStart(3, "0")}`;
};

export function note(text) {
  CL.lines.push(clock() + " " + String(text).slice(0, 4000));
  if (CL.lines.length > MOST) CL.lines.splice(0, CL.lines.length - MOST);
}

function said(args) {
  return args.map((a) => {
    if (a instanceof Error) return a.stack || String(a);
    if (a && typeof a === "object") { try { return JSON.stringify(a).slice(0, 1000); } catch (e) { return String(a); } }
    return String(a);
  }).join(" ");
}

for (const level of ["error", "warn"]) {          // (still to the console as well: only heard, never swallowed)
  const was = console[level].bind(console);
  console[level] = (...args) => { note((level === "warn" ? "WARNING " : "ERROR ") + said(args)); was(...args); };
}
window.addEventListener("error", (ev) => {
  if (ev.target && ev.target !== window) {        // (a picture, a sound or a script that didn't load)
    note("ERROR didn't load: " + (ev.target.currentSrc || ev.target.src || ev.target.href || ev.target.tagName));
  } else {
    note("ERROR " + ((ev.error && ev.error.stack) || `${ev.message} (${ev.filename}:${ev.lineno}:${ev.colno})`));
  }
}, true);
window.addEventListener("unhandledrejection", (ev) => note("ERROR (unhandled) " + said([ev.reason])));
document.addEventListener("visibilitychange", () => note(document.hidden ? "The page was hidden" : "The page was shown"));
window.addEventListener("online", () => note("The device is online"));
window.addEventListener("offline", () => note("The device went offline"));

// (the page's address without what's private in it: a ticket, a joining code)
function page() {
  const q = new URLSearchParams(location.search);
  for (const key of [...q.keys()]) if (key !== "app") q.set(key, "...");
  return location.pathname + (q.toString() ? "?" + q.toString() : "");
}

// The whole of it, as shown and sent: what it's running on, then the lines (more: the game's own, from main.js)
export function clientText(more) {
  const n = navigator, now = performance.now();
  const fps = CL.frames * 1000 / Math.max(1, now - CL.since);
  CL.frames = 0; CL.since = now;
  const mem = performance.memory ? `, ${Math.round(performance.memory.usedJSHeapSize / 1048576)} MB in use` : "";
  const up = Math.round((Date.now() - CL.started) / 60000);
  return [
    `Browser: ${n.userAgent}`,
    `Page: ${page()}; ${window.DSApp ? "in the app" : "in a browser"}; open ${up} min`,
    `Screen: ${screen.width}x${screen.height}, window ${innerWidth}x${innerHeight}, pixel ratio ${devicePixelRatio}, ` +
      `touch ${navigator.maxTouchPoints > 0 ? "yes" : "no"}${mem}`,
    `Running at ${fps.toFixed(0)} frames a second lately; ping ${CL.ping ? Math.round(CL.ping) + " ms" : "not measured"}` +
      (CL.tick ? `; the server's tick ${CL.tick} ms` : ""),
    ...(more || []),
    "",
    ...(CL.lines.length ? CL.lines : ["(nothing noted yet)"]),
  ].join("\n");
}
