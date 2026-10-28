// Phones and tablets: the touch layout. The world fills the screen, drawn bigger; the level, health and Shards sit top
// left, the minimap top right (tap it: the world map), round buttons down the right (the bag, chat, the journal, the
// menu), a stick bottom left and the hotbar along the bottom. Tap: the first thing to do (walk, talk, attack); hold:
// everything you can do with it. The Android app (android/) opens this same page with ?app=android, so whatever the
// server has, the app has too.
const query = new URLSearchParams(location.search);

function detect() {
  if (query.get("app") === "android") return true;
  const want = query.get("touch");               // (?touch=1 or ?touch=0: try it, or leave it, in any browser)
  if (want === "1" || want === "0") {
    try { localStorage.setItem("ds.touch", want); } catch (e) { /* (private window) */ }
    return want === "1";
  }
  try {
    const v = localStorage.getItem("ds.touch");
    if (v === "1" || v === "0") return v === "1";
  } catch (e) { /* (private window) */ }
  const mq = (s) => window.matchMedia && window.matchMedia(s).matches;
  return mq("(pointer: coarse)") && !mq("(any-pointer: fine)");   // (fingers only: a touchscreen laptop has its mouse)
}

// Options' Layout: "" (as the screen suggests), "0" (desktop) or "1" (touch); the page loads again in it
export function layoutChoice() {
  try { return localStorage.getItem("ds.touch") || ""; } catch (e) { return ""; }
}
export function chooseLayout(v) {
  try { if (v) localStorage.setItem("ds.touch", v); else localStorage.removeItem("ds.touch"); } catch (e) { /* (private window) */ }
  const q = new URLSearchParams(location.search);
  q.delete("touch");
  location.search = q.toString();
}

export const M = {
  on: detect(),
  app: query.get("app") === "android",
  bag: false,                                    // (the bag open: your stats, gear, quests and pack)
  chat: false,                                   // (the chat log open)
  joy: null,                                     // (the stick, while a finger's on it: {id, x, y, dx, dy})
  panX: 0, panY: 0,                              // (how far the journal's page is dragged over)
  hoverUntil: 0,                                 // (what was tapped stays named at the top a moment)
};

if (M.on) document.documentElement.classList.add("touch");
