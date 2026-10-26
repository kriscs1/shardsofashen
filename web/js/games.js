// The tavern's games at their own table (dsengine/tavern.py): Three Cups, High or Low, Dragon Dice. The server hides
// the coin and rolls the dice and says what's on the table ({t: "game"}); this draws the baize, the cups, the coin and
// the dice (sprites/Interface/Game_*), moves them (the shuffle, the dice tumbling, the cups lifted) and sends back the
// stake, the cup picked, the guess.
import { sprite } from "./assets.js";
import { send } from "./net.js";

const $ = (id) => document.getElementById(id);
const W = 200, H = 100;                 // (the table, drawn twice as big)
const SLOTS = [52, 100, 148];           // (where the three cups stand)
const SHUFFLE_MS = 1700, TUMBLE_MS = 900, LIFT_MS = 450;
const CUP_NAMES = ["left", "middle", "right"];
const T = { ev: null, at: 0, raf: 0, swaps: [] };

export function gameOpen() { return !$("tavern-game").hidden; }

export function onGame(m, now) {
  if (!m.game) { close(false); return; }
  const was = T.ev;
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
  if (!T.raf) T.raf = requestAnimationFrame(frame);
}

function close(tell) {
  if (tell && T.ev) send({ t: "game", do: "leave" });
  T.ev = null;
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
});
$("game-table").addEventListener("click", (ev) => {
  const m = T.ev;
  if (!m || m.game !== "cups" || m.phase !== "pick" || performance.now() - T.at < SHUFFLE_MS) return;
  const r = ev.target.getBoundingClientRect();
  const x = (ev.clientX - r.left) * W / r.width;
  const n = SLOTS.findIndex((s) => Math.abs(x - s) < 18);
  if (n >= 0) send({ t: "game", do: "pick", n: n + 1 });
});

// ----- what you can do now
function button(text, act, main) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = text;
  if (main) b.className = "main";
  b.onclick = act;
  $("game-buttons").append(b);
}

function stakeButtons(m, words) {
  for (const s of m.stakes) button(words.replace("%d", s), () => send({ t: "game", do: "stake", stake: s }), false);
}

function buttons(m) {
  $("game-buttons").innerHTML = "";
  const g = m.game, p = m.phase;
  if (g === "cups" && p === "pick") {
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
  if (m.game === "cups") drawCups(x, m, now);
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
