// Sounds, music and the background sounds (the desktop game's save.py, its second half), in Web Audio. Browsers only
// let a page make sound after a click or a key, so it all starts then.
import { A, configRead, dictIni } from "./assets.js";
import { S } from "./state.js";
import { val, trim, clamp } from "./util.js";
import { weatherAmbient } from "./sky.js";

export const O = {               // the options (kept in the browser)
  sound: true, volume: 100, music: true, musicVolume: 80, ambient: true, ambientVolume: 70, chatSound: true,
};

export const AU = { ctx: null, buffers: new Map(), master: null, music: null, musicGain: null, musicTheme: null,
  musicFile: "", resume: {}, turns: {}, fade: null, want: null, wantAt: 0, ambient: null, ambientWant: "",
  ambientName: "", effect: false };

export function loadOptions() {
  try {
    const o = JSON.parse(localStorage.getItem("ds.audio") || "{}");
    Object.assign(O, o);
  } catch (e) { /* (private window) */ }
  if (localStorage.getItem("ds.audio") === null) {
    O.sound = val(configRead("Sounds", "Enabled", "1")) === 1;
    O.music = val(configRead("Sounds", "Music.On", "1")) === 1;
    O.ambient = val(configRead("Sounds", "Ambient", "1")) === 1;
  }
}

export function saveOptions() {
  try { localStorage.setItem("ds.audio", JSON.stringify(O)); } catch (e) { /* (private window) */ }
  applyVolume();
}

export function unlock() {
  if (AU.ctx) {
    if (AU.ctx.state === "suspended") AU.ctx.resume();
    return;
  }
  const C = window.AudioContext || window.webkitAudioContext;
  if (!C) return;
  AU.ctx = new C();
  AU.master = AU.ctx.createGain();
  AU.master.connect(AU.ctx.destination);
  applyVolume();
}

function file(name) {
  name = trim(name);
  const s = A.m.sounds || {};
  if (name.includes(".")) return s[name] || null;
  return s[name + ".wav"] || s[name + ".mid"] || null;
}

async function buffer(f) {
  if (AU.buffers.has(f)) return AU.buffers.get(f);
  const p = fetch("/assets/sounds/" + encodeURIComponent(f)).then((r) => r.arrayBuffer())
    .then((b) => AU.ctx.decodeAudioData(b)).catch(() => null);
  AU.buffers.set(f, p);
  return p;
}

function place(at) {
  // (gain, pan) of a sound made at global x,y, heard where the player is
  if (!at || !S.pos) return [1, 0];
  const px = S.pos.dx + 16, py = S.pos.dy + 16;
  const dx = at[0] - px, d = Math.hypot(dx, at[1] - py);
  const f = d <= 96 ? 1 : Math.max(0, 1 - (d - 96) / 504);
  return [f, clamp(dx / 400, -1, 1) * 0.7];
}

export async function playSound(name, at = null) {
  if (!O.sound || !AU.ctx || !trim(name)) return;
  const [g, pan] = place(at);
  if (g < 0.03) return;
  const f = file(name);
  if (!f) return;
  if (/\.(ogg|mid)$/i.test(f) && !/\.wav$/i.test(f)) {    // a tune as a sound: it takes the music's place for a while
    playEffectTune(f);
    return;
  }
  const b = await buffer(f);
  if (!b) return;
  const src = AU.ctx.createBufferSource();
  src.buffer = b;
  const gain = AU.ctx.createGain();
  gain.gain.value = g * O.volume / 100;
  let node = gain;
  if (AU.ctx.createStereoPanner) {
    const p = AU.ctx.createStereoPanner();
    p.pan.value = pan;
    gain.connect(p);
    node = p;
  }
  src.connect(gain);
  node.connect(AU.master);
  src.start();
}

// ----- the music: the place's theme (data\Music.ini), Hearth indoors; a tune carries on where it left off
const FADE_OUT = 1100, FADE_IN = 1600;

function musicLevel() { return O.volume / 100 * O.musicVolume / 100; }

export function musicTheme(underRoof, override) {
  if (override) return override;
  let theme = "";
  if (configRead("Sounds", "Music.By.Place", "0") === "1") theme = trim(dictIni("music", "Maps", S.mapName, ""));
  if (underRoof && !["Palace", "Lair"].includes(theme)) return "Hearth";
  return theme;
}

function themeFiles(theme) {
  const files = theme ? dictIni("music", "Themes", theme, "").split(",").map(trim).filter(Boolean) : [];
  if (files.length) return files;
  const own = configRead("Sounds", "Music", "");
  return own ? [own] : [];
}

function startMusic(theme, fadeIn) {
  stopMusicNow();
  AU.musicTheme = theme;
  if (!O.sound || !O.music || !AU.ctx) return;
  const files = themeFiles(theme);
  if (!files.length) return;
  let name, offset = 0;
  const r = AU.resume[theme];
  delete AU.resume[theme];
  if (r && files.includes(r[0])) [name, offset] = r;
  else {
    const n = AU.turns[theme] || 0;
    AU.turns[theme] = n + 1;
    name = files[n % files.length];
  }
  const f = file(name);
  if (!f) return;
  const el = new Audio("/assets/sounds/" + encodeURIComponent(f));
  el.preload = "auto";
  el.volume = fadeIn ? 0 : musicLevel();
  el.addEventListener("ended", () => { if (AU.music === el) { AU.music = null; startMusic(AU.musicTheme, false); } });
  el.addEventListener("loadedmetadata", () => { if (offset > 0 && offset < el.duration - 2) el.currentTime = offset; });
  el.play().catch(() => {});
  AU.music = el;
  AU.musicFile = name;
  AU.fade = fadeIn ? { stage: "in", t0: performance.now() } : null;
}

function stopMusicNow() {
  if (AU.music) { AU.music.pause(); AU.music = null; }
}

function playEffectTune(f) {
  if (!O.music || AU.effect) return;
  if (AU.music) {
    AU.resume[AU.musicTheme] = [AU.musicFile, AU.music.currentTime];
    stopMusicNow();
  }
  const el = new Audio("/assets/sounds/" + encodeURIComponent(f));
  el.volume = O.volume / 100;
  AU.effect = true;
  el.addEventListener("ended", () => { AU.effect = false; AU.musicTheme = null; });
  el.play().catch(() => { AU.effect = false; });
}

export function stopMusic() {
  stopMusicNow();
  AU.musicTheme = null;
}

export function musicTick(underRoof, override) {
  // Every frame: the fades, and the music changing to suit the place (after a moment there)
  if (!AU.ctx || AU.effect) return;
  const now = performance.now();
  const f = AU.fade;
  if (f && AU.music) {
    const t = now - f.t0;
    if (f.stage === "out") {
      if (t < FADE_OUT) { AU.music.volume = clamp(musicLevel() * (1 - t / FADE_OUT), 0, 1); return; }
      startMusic(f.next, true);
      return;
    }
    if (t < FADE_IN) { AU.music.volume = clamp(musicLevel() * t / FADE_IN, 0, 1); return; }
    AU.music.volume = musicLevel();
    AU.fade = null;
  }
  const want = musicTheme(underRoof, override);
  if (!O.music || !O.sound) { if (AU.music) stopMusic(); return; }
  if (AU.musicTheme === null || (!AU.music && !AU.fade)) { startMusic(want, true); return; }
  if (want !== AU.musicTheme) {
    if (AU.want !== want) { AU.want = want; AU.wantAt = now; } else if (now - AU.wantAt >= (want === "Hearth" || AU.musicTheme === "Hearth" ? 300 : 2500)) {
      AU.want = null;
      if (AU.music) AU.resume[AU.musicTheme] = [AU.musicFile, AU.music.currentTime];
      AU.fade = { stage: "out", t0: now, next: want };
      if (!AU.music) startMusic(want, true);
    }
  } else AU.want = null;
}

// ----- the background sound for the place (data\Ambient.ini), indoors the hearth, outside the rain
export async function ambientTick(underRoof) {
  if (!AU.ctx) return;
  let want = "";
  if (O.sound && O.ambient) {
    want = trim(dictIni("ambient", "Maps", S.mapName, ""));
    if (underRoof && !["Cave", "Lair"].includes(want)) want = "Indoors";
    want = weatherAmbient(want, underRoof);
  }
  if (want === AU.ambientWant) return;
  AU.ambientWant = want;
  if (AU.ambient) {
    const old = AU.ambient;
    old.gain.gain.setTargetAtTime(0, AU.ctx.currentTime, 0.3);
    setTimeout(() => { try { old.src.stop(); } catch (e) { /* (already stopped) */ } }, 1500);
    AU.ambient = null;
  }
  if (!want) return;
  const f = file("Ambient_" + want);
  if (!f) return;
  const b = await buffer(f);
  if (!b || AU.ambientWant !== want) return;
  const src = AU.ctx.createBufferSource();
  src.buffer = b;
  src.loop = true;
  const gain = AU.ctx.createGain();
  gain.gain.value = 0;
  gain.gain.setTargetAtTime(ambientLevel(), AU.ctx.currentTime, 0.4);
  src.connect(gain);
  gain.connect(AU.master);
  src.start();
  AU.ambient = { src, gain, name: want };
}

function ambientLevel() { return O.volume / 100 * O.ambientVolume / 100 * 0.25; }

export function applyVolume() {
  if (AU.music && !AU.fade) AU.music.volume = musicLevel();
  if (AU.ambient && AU.ctx) AU.ambient.gain.gain.setTargetAtTime(ambientLevel(), AU.ctx.currentTime, 0.1);
  if (!O.music) stopMusic();
  if (!O.sound) { stopMusic(); AU.ambientWant = null; }
}
