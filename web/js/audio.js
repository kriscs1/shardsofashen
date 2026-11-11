// Sounds, music and the background sounds (the desktop game's save.py, its second half), in Web Audio. Browsers only
// let a page make sound after a click or a key, so it all starts then.
import { A, at, configRead, dictIni, entityIni } from "./assets.js";
import { S } from "./state.js";
import { val, trim, clamp } from "./util.js";
import { weatherAmbient } from "./sky.js";

export const O = {               // the options (kept in the browser)
  sound: true, volume: 100, music: true, musicVolume: 30, ambient: true, ambientVolume: 70, chatSound: true,
  voices: true,                  // (people murmur as their words appear: voice.js)
  musicChosen: false,            // (the player has moved the music slider: their level is kept)
};

export const AU = { ctx: null, buffers: new Map(), master: null, music: null, musicGain: null, musicTheme: null,
  musicFile: "", resume: {}, turns: {}, fade: null, want: null, wantAt: 0, ambient: null, ambientWant: "",
  ambientName: "", effect: false };

export function loadOptions() {
  try {
    const o = JSON.parse(localStorage.getItem("ds.audio") || "{}");
    if (!o.musicChosen) delete o.musicVolume;        // (the old default, 80, was too loud: the new one instead)
    Object.assign(O, o);
  } catch (e) { /* (private window) */ }
  let kept = null;
  try { kept = localStorage.getItem("ds.audio"); } catch (e) { /* (a friend's game: nothing kept) */ }
  if (kept === null) {
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
  // (a sound with takes - Fail, Fail_2, Fail_3: build_soundscape.py; Moo .. Moo_5: build_voices.py - one at random,
  // so a repeat doesn't grate)
  const takes = [];
  for (let k = 1; k <= 8 && s[(k > 1 ? `${name}_${k}` : name) + ".wav"]; k++) takes.push(k > 1 ? `${name}_${k}` : name);
  if (takes.length > 1) return s[takes[Math.floor(Math.random() * takes.length)] + ".wav"];
  return s[name + ".wav"] || s[name + ".mid"] || null;
}

async function buffer(f) {
  if (AU.buffers.has(f)) return AU.buffers.get(f);
  const p = fetch(at("assets/sounds/" + encodeURIComponent(f))).then((r) => r.arrayBuffer())
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

export async function playSound(name, at = null, loud = 1) {
  if (!O.sound || !AU.ctx || !trim(name)) return;
  let [g, pan] = place(at);
  g *= loud;                                     // (how loud this one is: a footstep's softer)
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

// (a speaker's greeting - Voice_Man, Voice_Man_2 ... _10: build_voices.py - never the one just said, at their own
// pitch)
let lastVoice = "";
export async function playVoice(kind, pitch = 1) {
  if (!O.sound || !O.voices || !AU.ctx || !kind) return;
  const s = A.m.sounds || {};
  const takes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => `Voice_${kind}${n > 1 ? "_" + n : ""}.wav`).filter((t) => s[t]);
  if (!takes.length) return;
  const others = takes.length > 1 ? takes.filter((t) => t !== lastVoice) : takes;
  const take = others[Math.floor(Math.random() * others.length)];
  lastVoice = take;
  const b = await buffer(s[take]);
  if (!b) return;
  const src = AU.ctx.createBufferSource();
  src.buffer = b;
  src.playbackRate.value = pitch;
  const gain = AU.ctx.createGain();
  gain.gain.value = 0.6 * O.volume / 100;
  src.connect(gain);
  gain.connect(AU.master);
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
  const el = new Audio(at("assets/sounds/" + encodeURIComponent(f)));
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
  const el = new Audio(at("assets/sounds/" + encodeURIComponent(f)));
  el.volume = O.volume / 100;
  AU.effect = el;
  const over = () => { if (AU.effect === el) { AU.effect = false; AU.musicTheme = null; } };   // (the music back)
  el.addEventListener("ended", over);
  el.addEventListener("error", over);
  el.addEventListener("loadedmetadata", () => setTimeout(over, (el.duration || 0) * 1000 + 3000));
  setTimeout(() => { if (!el.duration) over(); }, 15000);     // (never started: not held off for good)
  el.play().catch(over);
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

// ----- what's heard only near it (Entities.ini Sound.Loop, Sound.Reach in pixels: the Grand Fountain), over the place's
// own sound: louder as you come, nothing past its reach, nothing under a roof
const NEAR_GAIN = 2.0;
const nearKinds = new Map();
function nearKind(name) {
  if (!nearKinds.has(name)) {
    const sound = trim(entityIni(name, "Sound.Loop", ""));
    nearKinds.set(name, sound ? [sound, val(entityIni(name, "Sound.Reach", "320")) || 320] : null);
  }
  return nearKinds.get(name);
}

function nearestLoop(underRoof) {
  if (underRoof || !S.pos || !O.sound || !O.ambient) return null;
  const px = S.pos.dx + 16, py = S.pos.dy + 24;
  let best = null;
  for (const e of S.ents.values()) {
    const kind = nearKind(e.n);
    if (!kind) continue;
    const k = 1 - Math.hypot(e.dx + e.w / 2 - px, e.dy + e.h / 2 - py) / kind[1];
    if (k > 0 && (!best || k > best.k)) best = { sound: kind[0], k };
  }
  return best;
}

export async function nearLoopTick(underRoof) {
  if (!AU.ctx) return;
  const near = nearestLoop(underRoof);
  const want = near ? near.sound : "";
  AU.nearK = near ? near.k : 0;
  if (want !== AU.nearWant) {
    AU.nearWant = want;
    if (AU.near) {
      const old = AU.near;
      old.gain.gain.setTargetAtTime(0, AU.ctx.currentTime, 0.3);
      setTimeout(() => { try { old.src.stop(); } catch (e) { /* (already stopped) */ } }, 1500);
      AU.near = null;
    }
    if (want) {
      const f = file(want);
      const b = f ? await buffer(f) : null;
      if (b && AU.nearWant === want) {
        const src = AU.ctx.createBufferSource();
        src.buffer = b;
        src.loop = true;
        const gain = AU.ctx.createGain();
        gain.gain.value = 0;
        src.connect(gain);
        gain.connect(AU.master);
        src.start();
        AU.near = { src, gain, name: want };
      }
    }
  }
  if (AU.near) AU.near.gain.gain.setTargetAtTime(ambientLevel() * NEAR_GAIN * AU.nearK ** 1.5, AU.ctx.currentTime, 0.25);
}

export function applyVolume() {
  if (AU.music && !AU.fade) AU.music.volume = musicLevel();
  if (AU.ambient && AU.ctx) AU.ambient.gain.gain.setTargetAtTime(ambientLevel(), AU.ctx.currentTime, 0.1);
  if (!O.music) stopMusic();
  if (!O.sound) { stopMusic(); AU.ambientWant = null; }
}
