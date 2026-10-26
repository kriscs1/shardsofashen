// The game screen: the tavern's games at their own table (dsengine/tavern.py: Three Cups, High or Low, Dragon Dice),
// picking a lock and arm wrestling (dsengine/minigames.py). The server hides the coin, rolls the dice, keeps the pins'
// timing and the bout, and says what's on the table ({t: "game"}); this draws the baize, the cups, the coin, the dice,
// the lock and the arms (sprites/Interface/Game_*), moves them, and sends back the stake, the cup picked, the guess,
// the moment a pin was set, each push.
import { sprite } from "./assets.js";
import { send } from "./net.js";

const $ = (id) => document.getElementById(id);
const W = 200, H = 100;                 // (the table, drawn twice as big)
const SLOTS = [52, 100, 148];           // (where the three cups stand)
const SHUFFLE_MS = 1700, TUMBLE_MS = 900, LIFT_MS = 450;
const CUP_NAMES = ["left", "middle", "right"];
const T = { ev: null, at: 0, raf: 0, swaps: [], pinStart: 0, closing: 0, keys: "" };
const LEAN = 38;                        // (how far the arms lean over, pushed all the way)

function pinAt(pin, t) {
  // Where a pin is (0 down .. 1 up) t ms after it began (minigames.py pin_at)
  const p = ((t / pin.period + pin.phase) % 1 + 1) % 1;
  return p < 0.5 ? 2 * p : 2 - 2 * p;
}

export function gameOpen() { return !$("tavern-game").hidden; }

export function onGame(m, now) {
  if (T.closing) { clearTimeout(T.closing); T.closing = 0; }
  if (!m.game) {
    const last = T.ev;                     // (a lock opened, or the pick out of it: a moment to see it, then go)
    if (last && last.game === "lock") T.closing = setTimeout(() => close(false), 1300);
    else close(false);
    return;
  }
  const was = T.ev;
  if (m.game === "lock" && (!was || was.game !== "lock" || was.pin !== m.pin || m.slipped)) T.pinStart = now;
  if (m.game === "arm" && was && was.game === "arm" && m.bout && was.bout && !m.winner) {
    T.ev = m;                              // (the bout moving: no new buttons, no new start for the moving)
    return;
  }
  T.ev = m;
  T.at = now;
  if (m.game === "cups" && m.phase === "pick") T.swaps = shuffleSwaps();
  if (m.game === "dice" && m.round) T.roundAt = now;
  $("tavern-game").hidden = false;
  $("game-title").textContent = m.title;
  $("game-gold").textContent = `You have ${m.gold} gold.`;
  $("game-note").textContent = m.note || "";
  buttons(m);
  if (!was) $("game-leave").focus();
  else if (!$("tavern-game").contains(document.activeElement)) $("tavern-game").focus();   // (its buttons made again: keys still come here)
  if (!T.raf) T.raf = requestAnimationFrame(frame);
}

function close(tell) {
  if (tell && T.ev) send({ t: "game", do: "leave" });
  T.ev = null;
  T.keys = "";
  $("tavern-game").hidden = true;
  if (T.raf) cancelAnimationFrame(T.raf);
  T.raf = 0;
  const c = $("game");                     // (the world again)
  if (c) c.focus();
}

$("game-leave").onclick = () => close(true);
$("tavern-game").addEventListener("keydown", (ev) => {
  ev.stopPropagation();
  if (ev.key === "Escape") close(true);
  else if (ev.key === " " && T.ev && (T.ev.game === "lock" || T.ev.game === "arm")) {
    ev.preventDefault();
    act();
  }
});

function act() {
  // The one thing to do, as fast as you can: set the pin, push the arm
  const m = T.ev;
  if (!m) return;
  if (m.game === "lock" && m.phase === "pick") send({ t: "game", do: "set", t: Math.round(performance.now() - T.pinStart) });
  else if (m.game === "arm" && m.bout && !m.winner) send({ t: "game", do: "push" });
}

$("game-table").addEventListener("click", (ev) => {
  const m = T.ev;
  if (m && (m.game === "lock" || m.game === "arm")) { act(); return; }
  if (!m || m.game !== "cups" || m.phase !== "pick" || performance.now() - T.at < SHUFFLE_MS) return;
  const r = ev.target.getBoundingClientRect();
  const x = (ev.clientX - r.left) * W / r.width;
  const n = SLOTS.findIndex((s) => Math.abs(x - s) < 18);
  if (n >= 0) send({ t: "game", do: "pick", n: n + 1 });
});

// ----- what you can do now
let wanted = [];
function button(text, act, main) {
  wanted.push([text, act, main]);
}

function stakeButtons(m, words) {
  for (const s of m.stakes) button(words.replace("%d", s), () => send({ t: "game", do: "stake", stake: s }), false);
}

function buttons(m) {
  wanted = [];
  chooseButtons(m);
  const keys = wanted.map((w) => w[0]).join("|");
  if (keys === T.keys) return;             // (the same ones: leave them, a press in hand isn't lost)
  T.keys = keys;
  const box = $("game-buttons");
  box.innerHTML = "";
  for (const [text, act, main] of wanted) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    if (main) b.className = "main";
    b.onclick = act;
    box.append(b);
  }
  $("game-leave").textContent = m.game === "lock" ? "Give up" : "Leave the table";
}

function chooseButtons(m) {
  const g = m.game, p = m.phase;
  if (g === "lock") {
    if (p === "pick") button("Set the pin", act, true);
  } else if (g === "arm") {
    const b = m.bout;
    if (b && !m.winner) button("Push!", act, true);
    else if (!(m.waiting && m.waiting.who === m.me)) {
      if (m.waiting) button(`Take on ${m.waiting.who} (${m.waiting.stake} gold)`, () => send({ t: "game", do: "take" }), true);
      for (const s of m.stakes) button(`The innkeeper, for ${s} gold`, () => send({ t: "game", do: "house", stake: s }), false);
      if (!m.waiting) for (const s of m.stakes) button(`Wait for a challenger: ${s} gold`, () => send({ t: "game", do: "sit", stake: s }), false);
    }
  } else if (g === "cups" && p === "pick") {
    CUP_NAMES.forEach((w, i) => button(`The ${w} cup`, () => send({ t: "game", do: "pick", n: i + 1 }), true));
  } else if (g === "highlow" && p === "guess") {
    button("Higher!", () => send({ t: "game", do: "guess", higher: true }), true);
    button("Lower!", () => send({ t: "game", do: "guess", higher: false }), true);
  } else if (g === "dice") {
    const r = m.round;
    if (r && !r.players.includes(m.me)) button(`Join in (${r.stake} gold)`, () => send({ t: "game", do: "join" }), true);
    else if (!r) stakeButtons(m, "Start a round at %d gold");
  } else {
    stakeButtons(m, p === "done" ? "Again: %d gold" : "Stake %d gold");
  }
}

// ----- what's said over the table
function say(m, now) {
  const t = now - T.at;
  if (m.game === "lock") {
    if (m.phase === "done") return m.opened ? "The lock springs open!" : "The nail slips out of the lock.";
    const left = m.most - m.slips;
    if (m.slipped) return `The pick slips! ${left} more and it's out. Pin ${m.pin + 1} of ${m.pins.length}.`;
    if (m.set) return `Click! A pin sets. Pin ${m.pin + 1} of ${m.pins.length}.`;
    return `Set each pin as it crosses the line (tap, click or Space). Pin ${m.pin + 1} of ${m.pins.length}.`;
  }
  if (m.game === "arm") {
    const b = m.bout;
    if (b && m.winner) {
      return m.winner === m.me ? `You pin ${b.players[1 - b.me]}'s hand to the table! You take ${m.pot} gold.`
        : `${m.winner} pins your hand to the table.`;
    }
    if (b) return `Push! (Tap, click or Space, as fast as you can.) ${b.secs} seconds left.`;
    if (m.waiting && m.waiting.who === m.me) return "You sit, elbow on the table, and wait for a challenger. (Leave to take your stake back.)";
    if (m.waiting) return `${m.waiting.who} is sat at the table, waiting for a challenger, for ${m.waiting.stake} gold.`;
    return "Arm wrestling, for a stake: take on the innkeeper, or wait for another player to take you on. Push as fast as you can: the stronger you are, the more each push counts.";
  }
  if (m.game === "cups") {
    if (m.phase === "stake") return "A coin under one of three cups. Find it, and you get two and a half times your stake back.";
    if (m.phase === "pick") return t < SHUFFLE_MS ? "The innkeeper shuffles the cups round and round..." : "Which cup hides the coin?";
    if (t < LIFT_MS * 2) return "...";
    return m.won ? `There's the coin! You win ${m.won} gold.`
      : `Empty! The coin was under the ${CUP_NAMES[m.coin - 1]} cup.`;
  }
  if (m.game === "highlow") {
    if (m.phase === "stake") return "The innkeeper rolls a die. Will the next roll be higher, or lower? Right, and you get 1.4 times your stake back.";
    if (t < TUMBLE_MS) return "The innkeeper rolls...";
    if (m.phase === "guess") return `A ${m.first}. Higher, or lower? (The same again, and the house wins.)`;
    if (m.won) return `A ${m.second}! You called it, and win ${m.won} gold.`;
    return `A ${m.second}... ${m.second === m.first ? "the same again: the house wins" : "not this time"}.`;
  }
  const r = m.round;
  if (m.rolled && t < TUMBLE_MS + 200) return "The dice tumble across the baize...";
  if (r) {
    const secs = Math.max(0, r.secs - Math.floor((now - (T.roundAt || T.at)) / 1000));
    return `${r.players.join(", ")} ${r.players.length === 1 ? "is" : "are"} in, at ${r.stake} gold each. The dice roll in ${secs} seconds.`;
  }
  if (m.rolled) {
    const w = m.winners;
    return (w.length === 1 ? `${w[0]} wins the pot of ${m.pot} gold!` : `A tie! ${w.join(" and ")} share the pot of ${m.pot} gold.`)
      + (m.won ? ` You take ${m.won} gold.` : "");
  }
  return "Put a stake down and start a round: everyone at the tavern has 20 seconds to match it. The highest roll of three dice takes the pot.";
}

// ----- drawing the table
function frame() {
  T.raf = 0;
  const m = T.ev;
  if (!m) return;
  const now = performance.now();
  const c = $("game-table"), x = c.getContext("2d");
  x.imageSmoothingEnabled = false;
  x.setTransform(c.width / W, 0, 0, c.height / H, 0, 0);
  x.clearRect(0, 0, W, H);
  const table = sprite("Game_Table");
  if (table) x.drawImage(table, 0, 0);
  else { x.fillStyle = "#26683a"; x.fillRect(0, 0, W, H); }
  if (m.game === "lock") drawLock(x, m, now);
  else if (m.game === "arm") drawArms(x, m, now);
  else if (m.game === "cups") drawCups(x, m, now);
  else if (m.game === "highlow") drawHighLow(x, m, now);
  else drawDragonDice(x, m, now);
  $("game-say").textContent = say(m, now);
  T.raf = requestAnimationFrame(frame);
}

function shuffleSwaps() {
  // Five swaps of two cups each, the browser's own: only the server knows where the coin is
  const out = [];
  for (let i = 0; i < 5; i++) {
    const a = Math.floor(Math.random() * 3);
    out.push([a, (a + 1 + Math.floor(Math.random() * 2)) % 3]);
  }
  return out;
}

function drawCup(x, cx, lift, z = 0) {
  const im = sprite("Game_Cup");
  if (!im) return;
  x.globalAlpha = 0.25;                     // (its shadow on the baize)
  x.fillStyle = "#000";
  x.beginPath(); x.ellipse(cx, 68, 12, 3, 0, 0, 6.283); x.fill();
  x.globalAlpha = 1;
  x.drawImage(im, Math.round(cx - 12), Math.round(42 - lift + z));
}

function drawCoin(x, cx) {
  const im = sprite("Game_Coin");
  if (im) x.drawImage(im, Math.round(cx - 5), 60);
}

function drawCups(x, m, now) {
  const t = now - T.at;
  if (m.phase === "stake") {
    drawCoin(x, SLOTS[1]);
    SLOTS.forEach((s, i) => drawCup(x, s, i === 1 ? 16 : 0));
    return;
  }
  if (m.phase === "pick" && t < SHUFFLE_MS) {
    const per = SHUFFLE_MS / T.swaps.length, k = Math.min(T.swaps.length - 1, Math.floor(t / per));
    const f = (t - k * per) / per, e = f * f * (3 - 2 * f);
    const [a, b] = T.swaps[k];
    SLOTS.forEach((s, i) => {
      if (i === a) drawCup(x, s + (SLOTS[b] - s) * e, 0, -Math.sin(f * Math.PI) * 6);
      else if (i === b) drawCup(x, s + (SLOTS[a] - s) * e, 0, Math.sin(f * Math.PI) * 4);
      else drawCup(x, s, 0);
    });
    return;
  }
  if (m.phase === "pick") { SLOTS.forEach((s) => drawCup(x, s, 0)); return; }
  const up = (start) => 16 * Math.min(1, Math.max(0, (t - start) / LIFT_MS));
  drawCoin(x, SLOTS[m.coin - 1]);
  SLOTS.forEach((s, i) => {
    const n = i + 1;
    drawCup(x, s, n === m.pick ? up(0) : n === m.coin ? up(LIFT_MS) : 0);
  });
}

function drawDie(x, face, cx, cy, size, tumble, seed) {
  // A die, size pixels across; tumbling (0..1 of the throw: it bounces, spins and changes face till it lands)
  let f = face, dy = 0, turn = 0;
  if (tumble < 1) {
    f = 1 + Math.floor((Math.sin(seed * 12.9 + tumble * 40) * 0.5 + 0.5) * 5.99);
    dy = -Math.abs(Math.sin(tumble * Math.PI * 3)) * 10 * (1 - tumble);
    turn = (1 - tumble) * 6 * (seed % 2 ? 1 : -1);
  }
  const im = sprite("Game_Die" + f);
  if (!im) return;
  x.save();
  x.translate(cx, cy + dy);
  x.rotate(turn);
  x.drawImage(im, -size / 2, -size / 2, size, size);
  x.restore();
}

function drawHighLow(x, m, now) {
  const t = now - T.at, roll = Math.min(1, t / TUMBLE_MS);
  if (m.phase === "stake") {
    x.globalAlpha = 0.35;
    drawDie(x, 1, 76, 50, 24, 1, 1);
    drawDie(x, 6, 124, 50, 24, 1, 2);
    x.globalAlpha = 1;
    return;
  }
  drawDie(x, m.first, 76, 50, 24, m.phase === "guess" ? roll : 1, 3);
  if (m.phase === "done") drawDie(x, m.second, 124, 50, 24, roll, 4);
  label(x, "first", 76, 74);
  if (m.phase === "done") label(x, "next", 124, 74);
}

function label(x, text, cx, y, colour = "#f3e888") {
  x.font = "7px Georgia, serif";
  x.textAlign = "center";
  x.textBaseline = "top";
  x.fillStyle = colour;
  x.fillText(text, cx, y);
}

function drawDragonDice(x, m, now) {
  const t = now - T.at;
  const rows = m.rolled && !(m.round && m.round.players.length) ? Object.keys(m.rolled)
    : (m.round ? m.round.players : []);
  if (!rows.length) {
    [1, 3, 5].forEach((f, i) => { x.globalAlpha = 0.35; drawDie(x, f, 76 + i * 24, 50, 18, 1, i); });
    x.globalAlpha = 1;
    return;
  }
  const step = Math.min(14, 84 / rows.length), top = 50 - (rows.length - 1) * step / 2;
  rows.forEach((who, i) => {
    const y = top + i * step;
    const win = m.rolled && m.winners && m.winners.includes(who) && t > TUMBLE_MS;
    label(x, who === m.me ? `${who} (you)` : who, 52, y - 4, win ? "#ffd84a" : "#efe6c8");
    const dice = m.rolled && m.rolled[who];
    for (let k = 0; k < 3; k++) {
      if (dice) drawDie(x, dice[k], 104 + k * 15, y, Math.min(12, step - 1), Math.min(1, (t - i * 80) / TUMBLE_MS), i * 3 + k + 1);
      else { x.globalAlpha = 0.3; drawDie(x, 1 + ((i + k) % 6), 104 + k * 15, y, Math.min(12, step - 1), 1, k); x.globalAlpha = 1; }
    }
    if (dice && t > TUMBLE_MS) label(x, String(dice[0] + dice[1] + dice[2]), 160, y - 4, win ? "#ffd84a" : "#efe6c8");
  });
}

// ----- picking a lock: the lock's face, a slot for each pin, the line it must cross (green), the slips left
function drawLock(x, m, now) {
  x.fillStyle = "#3e2a1c";
  x.fillRect(0, 0, W, H);
  const face = sprite("Game_Lock");
  if (face) x.drawImage(face, 16, 16);
  const n = m.pins.length, gap = Math.min(20, 90 / n), x0 = 100;
  const top = (pos) => 84 - pos * 64 - 10;
  m.pins.forEach((pin, i) => {
    const cx = Math.round(x0 + i * gap + 6);
    x.fillStyle = "#1a110b";
    x.fillRect(cx - 5, 8, 10, 82);
    if (i === m.pin && m.phase === "pick") {
      x.fillStyle = "rgba(90, 220, 120, 0.45)";      // (where it has to be set)
      const y1 = top(pin.band + pin.width), y2 = top(pin.band - pin.width);
      x.fillRect(cx - 7, y1, 14, y2 - y1);
    }
    const pos = i < m.pin ? pin.band : (i === m.pin && m.phase === "pick" ? pinAt(pin, now - T.pinStart) : 0);
    const y = Math.round(top(pos));
    x.fillStyle = "#7c7c84";                         // (its spring)
    for (let k = y + 10; k < 88; k += 3) x.fillRect(cx - 2, k, 4, 1);
    x.fillStyle = i < m.pin || m.opened ? "#e2b04a" : "#c8c8d0";
    x.fillRect(cx - 3, y, 6, 10);
  });
  for (let k = 0; k < m.most; k++) {                   // (the slips: nails, the used ones crossed out)
    const nx = 27 + k * 14, ny = 94;
    x.fillStyle = "#a0a0a8";
    x.fillRect(nx, ny - 1, 10, 2);
    if (k < m.slips) {
      x.strokeStyle = "#e04040";
      x.lineWidth = 1.2;
      x.beginPath(); x.moveTo(nx, ny - 4); x.lineTo(nx + 10, ny + 4); x.moveTo(nx + 10, ny - 4); x.lineTo(nx, ny + 4); x.stroke();
    }
  }
}

// ----- arm wrestling: two forearms on their elbows, their fists locked, leaning the way the bout's going
function drawForearm(x, im, ex, ey, gx, gy, flip) {
  const len = Math.hypot(gx - ex, gy - ey);
  x.save();
  x.translate(ex, ey);
  x.rotate(Math.atan2(gy - ey, gx - ex) + Math.PI / 2);
  if (flip) x.scale(-1, 1);
  x.drawImage(im, -7, -len, 14, len);
  x.restore();
}

function drawArms(x, m, now) {
  const b = m.bout;
  const lean = b ? -b.at / 100 : 0;                    // (the first player winning: their fist over to the right)
  const gx = 100 + lean * LEAN, gy = 42 + Math.abs(lean) * 26;
  const im = sprite("Game_Arm");
  if (!b) x.globalAlpha = 0.45;
  if (im) {
    drawForearm(x, im, 72, 92, gx - 3, gy, false);
    drawForearm(x, im, 128, 92, gx + 3, gy, true);
  }
  x.globalAlpha = 1;
  if (!b) return;
  b.players.forEach((who, i) => label(x, who === m.me ? `${who} (you)` : who, i ? 160 : 40, 86,
    m.winner === who ? "#ffd84a" : "#efe6c8"));
  x.fillStyle = "rgba(0,0,0,0.45)";                    // (the bout so far: a bar, the middle marked)
  x.fillRect(30, 6, 140, 6);
  x.fillStyle = "#e2b04a";
  x.fillRect(Math.round(100 + lean * 70) - 2, 4, 4, 10);
  x.fillStyle = "#efe6c8";
  x.fillRect(99, 6, 2, 6);
  label(x, `${b.secs}s`, 100, 15);
}
