// The journal (H, F1 or the ? Help button): what you can make, what you can gather, your quests, your spells (learnt
// from scrolls, cast from here or the hotbar for Shards), the controls.
// The server sends the lists when it opens; drawn as the desktop game's screens.py drew it, on a 1024 x 768 page.
import { S } from "./state.js";
import { sprite } from "./assets.js";
import { val, word, lbstr, pretty, drawText, drawTextMid, centreText, textWidth, fitText, wrapLines, roundBox } from "./util.js";
import { questLook, questRows, drawChecklist, badge, padlock, ROW_H } from "./ui.js";
import { skillLevel, held, knowsSpell, cooldownLeft } from "./verbs.js";
import { send } from "./net.js";

const INK = [243, 232, 136];
const PARCHMENT = [212, 191, 126];
const DIM = [190, 160, 110];

export const J = { open: false, tab: 1, page: 1, hover: 0, focus: "", x0: 0 };

const CONTROLS = [
  ["M", "Left-click ground", "Walk there."],
  ["M", "Left-click a thing", "Do its main action: Talk to a person, Pick up an item, Attack an enemy, Use an object..."],
  ["M", "Right-click", "A menu of everything you can do with it: Examine, Eat, Use, Drop All, Drop 1..."],
  ["M", "Use, then click", "Pick Use on an item you carry, then click what to use it with. Right-click to stop."],
  ["M", "Shops, bank, crafting", "Left-click buys, sells, banks or makes one. Right-click for more (Buy 5, Sell All, Value, Inspect...)."],
  ["M", "Box arrows, wheel", "Next or previous page of a shop, bank or crafting list (or turn the mouse wheel over it)."],
  ["M", "Skills (Stats)", "Point at a skill for its level. Right-click: progress to the next level. Left-click: the skill's guide, if it has one."],
  ["M", "Stats / Gear / Quests", "The tabs at the top of the Stats box: your skills, your 8 equipment slots, your quests."],
  ["M", "Wield, Wear", "Left-click a weapon, shield or armour in your inventory to put it on. Click it in the Gear tab to take it off."],
  ["M", "Hotbar", "The five slots at the bottom of the view. Right-click an item: Put it on the hotbar. Click a slot (or press 1-5) to use it; right-click a slot to take it off."],
  ["M", "Dying", "You lose a quarter of your gold, and press Respawn to wake at the start (or in your bed at home). You keep your 5 most valuable things (worn or carried) and anything you can't drop; the rest is in a grave where you fell, marked on the minimap: Search it within 2 minutes."],
  ["M", "Sun and moon", "Above the minimap: point at it for the time of day. Everyone shares the same sky."],
  ["M", "Sleep", "Click a bed: you wake healed. The night only passes when everyone playing is asleep."],
  ["M", "Wear and repair", "Weapons and armour wear as you fight; worn out they break. Right-click a blacksmith: Repair, or use the item on an anvil with a bar of its metal."],
  ["M", "Minimap - and +", "Zoom the minimap out and in."],
  ["M", "Mouse wheel", "Over the map: zoom in and out (75% to 300%)."],
  ["M", "Other players", "Up to five of you share this world: what you do (chopping, mining, fighting, picking things up) is seen by everyone; your quests are your own."],
  ["M", "The arena", "Talk to the Arena Master in Ashford. On the arena's sand you can fight other players (right-click: Attack); the paving round it is safe. Beaten, you lose nothing."],
  ["M", "Farming", "Buy seeds from the farmer by Ashford and use them on tilled soil: his furrows are free for anyone, or lay soil on your homestead. Crops grow by themselves (even while you're away); only whoever sowed them can harvest."],
  ["M", "The market", "At a market board (Ashford's market, and by every shardstone) you see everything everyone has for sale. With it open, right-click things in your pack: Sell on the market, at your own price. They sell while you're away; collect the gold at any board."],
  ["M", "Digging", "Use a spade anywhere on open ground: now and then you turn up gold or something useful, and sometimes Shards."],
  ["M", "Spells and Shards", "Read a spell's scroll to learn it for good. Casting it spends Shards (top left: how many you have); each spell has its own cooldown. Cast from the journal's Spells, or put the scroll on the hotbar. Shards don't come back by themselves: absorb the Shard Remnants beasts leave behind (Absorb, in your pack), and chests, digging and quests give them."],
  ["M", "Shardstones", "Wake a shardstone the first time with a few Shards; after that you can travel to it from any shardstone you've woken."],
  ["M", "The Green Dragon", "Ashford's beer garden, behind the houses. The innkeeper plays Three Cups and High or Low; at a dice table everyone puts in a stake and the highest roll takes the pot."],
  ["M", "Raids", "Now and then monsters attack a town in waves. Fight them off together: gold for each one you kill, and a reward for everyone who holds out."],
  ["M", "Shop signs", "Every shop has a sign by its door with a picture of what it sells."],
  ["M", "Dropping things", "Something you drop is yours alone to see for 10 seconds; then everyone can see it and pick it up."],
  ["M", "Your homestead", "The settler by Ashford's homestone gives you an Access Crystal for a little building work. Touch a homestone (by every shardstone) to go home, or to visit a friend's. At home its homestone says who may visit: only you, friends, or anyone."],
  ["M", "Building", "At home, press B (or the Build button): pick a piece, then click or drag on your land. Take down gives back half. Sleep in your own bed and you wake there if you fall; a chest there is your bank."],
  ["K", "Arrows or W A S D", "Walk (two at once walks diagonally)."],
  ["K", "Enter", "Talk to the other players (the chat)."],
  ["K", "H or F1", "Open or close this journal."],
  ["K", "B", "Build mode, on your own homestead (Esc or right-click to stop)."],
  ["K", "Esc", "Close a menu, box or this journal, or stop using an item. With nothing open: leave the game."],
  ["K", "1 - 5", "Use what's in that hotbar slot."],
  ["K", "1 - 5", "Journal: pick a tab (Left and Right also work)."],
  ["K", "Up / Down", "Journal: previous or next page (PgUp and PgDn too)."],
  ["K", "F11", "Full screen (or the button at the top left of the view)."],
  ["K", "+ / -", "Zoom the map in and out."],
  ["K", "Saving", "Automatic: the server keeps your game."],
];

export function pageSize() { return { 1: 14, 2: 7, 3: 7, 4: 8 }[J.tab] || 1; }

function count() {
  const d = S.journal || { crafts: [], gathers: [], quests: [], spells: [] };
  return { 1: d.crafts.length, 2: d.gathers.length, 3: d.quests.length, 4: (d.spells || []).length }[J.tab] || 1;
}

export function pages() { return Math.max(1, Math.ceil(count() / pageSize())); }

export function hit(x, y) {
  for (let t = 1; t <= 5; t++) {
    const tx = 40 + (t - 1) * 160;
    if (x >= tx && x <= tx + 152 && y >= 60 && y <= 92) return t;
  }
  if (x >= 942 && x <= 982 && y >= 20 && y <= 48) return 10;
  if (x >= 40 && x <= 160 && y >= 696 && y <= 724) return 11;
  if (x >= 864 && x <= 984 && y >= 696 && y <= 724) return 12;
  if (J.tab === 4) {                              // (a known spell's Cast and Hotbar buttons: 200 + slot x 2 (+1))
    for (let slot = 0; slot < 8; slot++) {
      const [cx, cy] = spellCardAt(slot);
      for (const [n, bx] of [[0, cx + SPELL_W - 196], [1, cx + SPELL_W - 100]]) {
        if (x >= bx && x <= bx + 88 && y >= cy + SPELL_H - 38 && y <= cy + SPELL_H - 10) return 200 + slot * 2 + n;
      }
    }
  }
  if (J.tab === 3 && x >= 48 && x <= 976) {
    const n = Math.floor((y - 108) / 82);
    if (n >= 0 && n < 7 && y - 108 - n * 82 <= 76 && (J.page - 1) * 7 + n < (S.journal?.quests.length || 0)) return 100 + n;
  }
  return 0;
}

function button(ctx, x, y, w, h, label, state) {
  const [fill, border, ink] = { 0: [[51, 34, 27], [77, 43, 33], [110, 90, 70]], 2: [[92, 60, 46], [160, 104, 80], INK],
    3: [[126, 77, 63], [190, 140, 100], [255, 255, 255]] }[state] || [[64, 42, 33], [126, 77, 63], PARCHMENT];
  roundBox(ctx, x, y, w, h, fill, border, 2, 10);
  const lb = fitText(ctx, label, w - 12, 10, true);
  drawTextMid(ctx, lb, x + Math.floor((w - textWidth(ctx, lb, 10, true)) / 2), y, h, 10, true, ink);
}

function card(ctx, x, y, w, h, border) {
  if (!border) roundBox(ctx, x, y, w, h, [61, 40, 31], [92, 60, 46], 1, 10);
  else roundBox(ctx, x, y, w, h, [61, 40, 31], border, 2, 10);
}

function iconWell(ctx, x, y, item) {
  roundBox(ctx, x + 10, y + 10, 36, 36, [40, 26, 20], [92, 60, 46], 1, 8);
  const im = sprite(item);
  if (im) {
    const s = Math.min(32 / im.width, 32 / im.height);
    ctx.drawImage(im, x + 12 + (32 - im.width * s) / 2, y + 12 + (32 - im.height * s) / 2, im.width * s, im.height * s);
  } else centreText(ctx, x + 28, y + 18, "?", 12, true, [110, 90, 70]);
}

// A line of text runs and icons, cut short at its right edge
class Run {
  constructor(ctx, x, edge) { this.ctx = ctx; this.x = x; this.edge = edge; this.full = false; }
  text(t, col, y, size = 9, bold = false) {
    if (this.full || !t) return;
    if (this.x + textWidth(this.ctx, t, size, bold) > this.edge) {
      t = fitText(this.ctx, t, this.edge - this.x, size, bold);
      this.full = true;
      if (!t) return;
    }
    this.x += drawText(this.ctx, t, this.x, y, size, bold, col);
  }
  icon(item, y, sz) {
    const im = sprite(item);
    if (this.full || !im) return;
    if (this.x + sz > this.edge) { this.full = true; return; }
    const s = Math.min(sz / im.width, sz / im.height);
    this.ctx.drawImage(im, this.x, y, im.width * s, im.height * s);
    this.x += sz + 3;
  }
}

function skillNeed(r, skill, level, xp, y) {
  r.text("Skill: ", DIM, y);
  if (!skill) r.text("none", PARCHMENT, y);
  else {
    if (level > 0) r.text(`${skill} level ${lbstr(level)}`, skillLevel(skill) < level ? [235, 105, 85] : [120, 210, 110], y);
    else r.text(skill + " (any level)", PARCHMENT, y);
    r.text(`  (yours: ${skillLevel(skill)})`, DIM, y);
  }
  if (val(xp) !== 0) r.text(`     +${xp} XP`, PARCHMENT, y);
}

function recipe(ctx, c, x, y, w) {
  const [border, label, bc] = c.status === 0 ? [[21, 171, 75], "Can make now", [120, 210, 110]] :
    c.status === 1 ? [null, "Missing items", [235, 160, 80]] : [null, "Need level " + lbstr(c.level), [235, 105, 85]];
  card(ctx, x, y, w, 76, border);
  iconWell(ctx, x, y, c.product);
  const bw = badge(ctx, x + w - 10, y + 8, label, bc);
  drawText(ctx, fitText(ctx, pretty(c.product), w - 76 - bw, 10, true), x + 56, y + 6, 10, true, INK);
  let r = new Run(ctx, x + 56, x + w - 10);
  r.text("Needs: ", DIM, y + 26);
  if (!word(c.ingredients, 1)) r.text("nothing", PARCHMENT, y + 26);
  for (let j = 1; word(c.ingredients, j); j += 2) {
    const nm = word(c.ingredients, j), need = Math.max(1, val(word(c.ingredients, j + 1))), have = held(nm);
    if (j > 1) r.text(",  ", DIM, y + 26);
    r.icon(nm, y + 25, 16);
    r.text(`${pretty(nm)} ${have}/${lbstr(need)}`, have >= need ? [120, 210, 110] : [235, 105, 85], y + 26);
  }
  r = new Run(ctx, x + 56, x + w - 10);
  skillNeed(r, c.skill, c.level, c.xp, y + 42);
  r = new Run(ctx, x + 56, x + w - 10);
  r.text("Made at: ", DIM, y + 58);
  r.text(c.rack + " (crafting list)", PARCHMENT, y + 58);
}

function gather(ctx, g, x, y, w) {
  const [border, label, bc] = g.status === 0 ? [[21, 171, 75], "Can gather now", [120, 210, 110]] :
    g.status === 1 ? [null, "Need " + pretty(g.missing), [235, 160, 80]] : [null, "Need level " + lbstr(g.level), [235, 105, 85]];
  card(ctx, x, y, w, 76, border);
  iconWell(ctx, x, y, word(g.gives, 1));
  const bw = badge(ctx, x + w - 10, y + 8, label, bc);
  drawText(ctx, fitText(ctx, g.title, w - 76 - bw, 10, true), x + 56, y + 6, 10, true, INK);
  let r = new Run(ctx, x + 56, x + w - 10);
  r.text("Gives: ", DIM, y + 26);
  if (!g.gives) r.text("-", PARCHMENT, y + 26);
  g.gives.split(/\s+/).filter(Boolean).forEach((it, k) => {
    if (k) r.text(",  ", DIM, y + 26);
    r.icon(it, y + 25, 16);
    r.text(pretty(it), [250, 240, 210], y + 26);
  });
  if (g.source || g.verb) {
    r.text("          " + (g.verb || "From") + ": ", DIM, y + 26);
    const names = [...new Set(g.source.split(/\s+/).filter(Boolean).map(pretty))].join(", ");
    r.text(names || "-", PARCHMENT, y + 26);
  }
  r = new Run(ctx, x + 56, x + w - 10);
  r.text("Tool: ", DIM, y + 42);
  if (!g.tool) r.text("none", PARCHMENT, y + 42);
  g.tool.split(/\s+/).filter(Boolean).forEach((alts, k) => {
    if (k) r.text(" and ", DIM, y + 42);
    const items = alts.split("/").filter(Boolean);
    const have = [...items].reverse().find((it) => held(it) > 0);
    if (have) { r.icon(have, y + 41, 16); r.text(pretty(have) + " (you have one)", [120, 210, 110], y + 42); } else {
      r.icon(items[0], y + 41, 16);
      r.text(pretty(items[0]) + (alts.includes("/") ? " or better" : "") + " (you need one)", [235, 105, 85], y + 42);
    }
  });
  r.text("          ", DIM, y + 42);
  skillNeed(r, g.skill, g.level, g.xp, y + 42);
  r = new Run(ctx, x + 56, x + w - 10);
  r.text("Where: ", DIM, y + 58);
  r.text(g.where || "-", PARCHMENT, y + 58);
}

function wrap(ctx, x, y, w, text, col, lineH, maxLines, size = 9, bold = false) {
  const lines = wrapLines(ctx, text, w, size, bold);
  const shown = lines.slice(0, maxLines);
  if (lines.length > maxLines && shown.length) shown[shown.length - 1] = fitText(ctx, lines.slice(maxLines - 1).join(" "), w, size, bold);
  shown.forEach((ln, i) => drawText(ctx, ln, x, y + i * lineH, size, bold, col));
  return shown.length;
}

function questCard(ctx, q, x, y, w) {
  const [sc, label] = questLook(q);
  const locked = q.status === 1 && q.needs && q.needs.length;
  const [border, tc] = q.status === 0 ? [[200, 150, 60], [250, 240, 210]] : locked ? [null, [150, 132, 114]] :
    q.status === 1 ? [sc, [220, 210, 180]] : [[21, 171, 75], [150, 140, 120]];
  if (q.title === J.focus) {
    roundBox(ctx, x - 4, y - 4, w + 8, 84, null, [255, 214, 90], 2, 13);
    roundBox(ctx, x, y, w, 76, [92, 66, 40], [255, 214, 90], 2, 10);
  } else card(ctx, x, y, w, 76, border);
  let bw = badge(ctx, x + w - 10, y + 8, label, sc, !!locked);
  if (q.main) bw += 8 + badge(ctx, x + w - 18 - bw, y + 8, "Main story" + (q.chapter ? " " + q.chapter : ""), [240, 200, 90]);
  const tw = drawText(ctx, fitText(ctx, q.title, w - 36 - bw, 10, true), x + 16, y + 6, 10, true, sc);
  if (q.status === 2) {
    ctx.strokeStyle = "rgb(90,150,80)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x + 15, y + 13.5); ctx.lineTo(x + 17 + tw, y + 13.5); ctx.stroke();
  }
  let ty = y + 26;
  if (q.giver) {
    const r = new Run(ctx, x + 16, x + w - 16);
    r.text("Given by: ", DIM, y + 26);
    r.text(pretty(q.giver), PARCHMENT, y + 26);
    ty = y + 42;
  }
  let text = q.text;
  if (locked) ty += 15 * wrap(ctx, x + 16, ty, w - 32, "Locked until you have: " + q.needs.join(", ") + ".", [225, 140, 115], 15, 1, 9, true);
  else if (q.status === 1) text = "You can start this now. " + text;
  if (y + 74 - ty >= 15) wrap(ctx, x + 16, ty, w - 32, text, tc, 15, Math.floor((y + 74 - ty) / 15));
  const todo = (q.notes || []).filter((n) => !n[1]).length;
  if (todo && q.status !== 2) bw += 8 + badge(ctx, x + w - 18 - bw, y + 8, `${todo} to do`, [255, 214, 90]);
  if (q.shards && q.status !== 2) bw += 8 + badge(ctx, x + w - 18 - bw, y + 8, `+${q.shards} Shards`, [190, 180, 255]);   // (its reward)
  if ((q.xp || []).length && q.status !== 2) badge(ctx, x + w - 18 - bw, y + 8, `+${q.xp.length > 2 ? "skills" : q.xp.map(pretty).join(", ")} xp`, [150, 225, 150]);
}

// ----- spells: every one a scroll teaches; the ones you know you can cast here (or put on the hotbar)
const SPELL_W = 462, SPELL_H = 136;

function spellCardAt(slot) { return [48 + (slot % 2) * 466, 108 + Math.floor(slot / 2) * 144]; }

export function spellClick(h) {
  // (a button on a spell card: its number from hit(); true if it was one)
  if (J.tab !== 4 || h < 200) return false;
  const d = S.journal?.spells || [];
  const sp = d[(J.page - 1) * 8 + Math.floor((h - 200) / 2)];
  if (!sp || !knowsSpell(sp.spell)) return true;
  if ((h - 200) % 2 === 0) send({ t: "cast", spell: sp.spell });
  else send({ t: "hotbar_spell", spell: sp.spell });
  return true;
}

function spellCard(ctx, sp, slot) {
  const [x, y] = spellCardAt(slot);
  const known = knowsSpell(sp.spell);
  const short = skillLevel(sp.skill) < sp.level;
  card(ctx, x, y, SPELL_W, SPELL_H, known ? [120, 110, 220] : null);
  iconWell(ctx, x, y, sp.scroll);
  const label = known ? "Known" : short ? `Needs ${sp.skill} ${sp.level}` : "Not learnt";
  const bw = badge(ctx, x + SPELL_W - 10, y + 8, label, known ? [150, 140, 255] : short ? [235, 105, 85] : [190, 160, 110]);
  drawText(ctx, fitText(ctx, sp.title || pretty(sp.spell), SPELL_W - 80 - bw, 11, true), x + 56, y + 8, 11, true, known ? INK : PARCHMENT);
  const r = new Run(ctx, x + 56, x + SPELL_W - 12);
  r.text(`${sp.skill} ${sp.level}`, short ? [235, 105, 85] : [120, 210, 110], y + 28, 9, true);
  r.text("   ·   ", DIM, y + 28);
  r.icon("Shard", y + 25, 14);
  r.text(`${sp.cost} Shards a cast`, (S.me.shards || 0) < sp.cost && known ? [235, 105, 85] : [214, 200, 255], y + 28, 9, true);
  if (sp.cooldown > 0) r.text(`   ·   ready again after ${lbstr(sp.cooldown)} s`, PARCHMENT, y + 28);
  wrap(ctx, x + 16, y + 50, SPELL_W - 32, sp.what.charAt(0).toUpperCase() + sp.what.slice(1) + ".", [250, 240, 210], 15, sp.next ? 1 : 2);
  if (sp.next) {                                  // (its next rank: what it'll be, and what it needs)
    const n = sp.next;
    wrap(ctx, x + 16, y + 68, SPELL_W - 32, `Upgrade: ${n.title} (${sp.skill} ${n.level}, ${n.cost} Shards): ${n.what}. Its scroll is rare: quests and treasure.`,
      skillLevel(sp.skill) >= n.level ? [190, 180, 255] : DIM, 15, 2);
  }
  if (known) {
    const left = cooldownLeft(sp.spell), poor = (S.me.shards || 0) < sp.cost;
    if (left > 0) drawText(ctx, `Ready in ${Math.ceil(left / 1000)} s`, x + 16, y + SPELL_H - 32, 9, true, [255, 214, 90]);
    else if (poor) drawText(ctx, "Not enough Shards", x + 16, y + SPELL_H - 32, 9, true, [235, 105, 85]);
    const h = J.hover - 200 - slot * 2;
    button(ctx, x + SPELL_W - 196, y + SPELL_H - 38, 88, 28, "Cast", left > 0 || poor ? 0 : h === 0 ? 2 : 1);
    const on = (S.me.hotbar || []).includes(sp.scroll);
    button(ctx, x + SPELL_W - 100, y + SPELL_H - 38, 88, 28, on ? "On hotbar" : "Hotbar", on ? 0 : h === 1 ? 2 : 1);
  } else {
    wrap(ctx, x + 16, y + SPELL_H - 30, SPELL_W - 32, "Read its scroll to learn it for good: scrolls turn up in chests, in shops and on foes.", DIM, 15, 1);
  }
}

function controls(ctx) {
  const heading = (x, y, t) => {
    drawText(ctx, t, x, y, 12, true, INK);
    ctx.fillStyle = "rgb(126,77,63)";
    ctx.fillRect(x, y + 24, 420, 1);
    return y + 32;
  };
  const row = (x, y, control, what) => {
    drawText(ctx, fitText(ctx, control, 140, 9, true), x, y, 9, true, INK);
    const n = wrap(ctx, x + 148, y, 272, what, [250, 240, 210], 15, 3);
    return y + Math.max(1, n) * 15 + 8;
  };
  const height = (what) => Math.min(3, wrapLines(ctx, what, 272, 9).length) * 15 + 8;
  const mouse = CONTROLS.filter((c) => c[0] === "M");
  let y = heading(60, 110, "Mouse");
  while (mouse.length && y + height(mouse[0][2]) <= 680) { const c = mouse.shift(); y = row(60, y, c[1], c[2]); }
  y = heading(528, 110, "Keyboard");
  for (const c of CONTROLS) if (c[0] === "K") y = row(528, y, c[1], c[2]);
  if (mouse.length) {
    y = heading(528, y + 10, "Mouse (more)");
    for (const c of mouse) if (y + height(c[2]) <= 680) y = row(528, y, c[1], c[2]);
  }
}

export function drawJournal(ctx) {
  const d = S.journal || { crafts: [], gathers: [], quests: [], spells: [], level: 1 };
  const spells = d.spells || [];
  J.page = Math.min(Math.max(1, J.page), pages());
  ctx.fillStyle = "rgb(24,14,10)";
  ctx.fillRect(-2000, 0, 6000, 768);
  roundBox(ctx, 20, 12, 984, 744, [51, 34, 27], [126, 77, 63], 3, 18);
  drawText(ctx, "Journal", 44, 18, 16, true, INK);
  const tw = textWidth(ctx, "Journal", 16, true);
  drawText(ctx, fitText(ctx, S.name + "  -  what you can make, gather and do", 860 - tw, 9), 58 + tw, 30, 9, false, PARCHMENT);
  button(ctx, 942, 20, 40, 28, "X", J.hover === 10 ? 2 : 1);
  for (let t = 1; t <= 5; t++) {
    const label = { 1: `Crafting (${d.crafts.length})`, 2: `Gathering (${d.gathers.length})`, 3: `Quests (${d.quests.length})`,
      4: `Spells (${spells.filter((s) => knowsSpell(s.spell)).length}/${spells.length})` }[t] || "Controls";
    button(ctx, 40 + (t - 1) * 160, 60, 152, 32, label, J.tab === t ? 3 : J.hover === t ? 2 : 1);
  }
  roundBox(ctx, 36, 98, 952, 590, [40, 26, 20], [126, 77, 63], 2, 12);
  if (!S.journal && J.tab !== 5) centreText(ctx, 512, 330, "Opening the journal...", 14, true, INK);
  else if (J.tab === 1) {
    if (!d.crafts.length) centreText(ctx, 512, 330, "Nothing to make yet.", 14, true, INK);
    const first = (J.page - 1) * 14;
    d.crafts.slice(first, first + 14).forEach((c, slot) => recipe(ctx, c, 48 + (slot % 2) * 466, 108 + Math.floor(slot / 2) * 82, 462));
  } else if (J.tab === 2) {
    if (!d.gathers.length) centreText(ctx, 512, 330, "Nothing to gather yet.", 14, true, INK);
    const first = (J.page - 1) * 7;
    d.gathers.slice(first, first + 7).forEach((g, n) => gather(ctx, g, 48, 108 + n * 82, 928));
  } else if (J.tab === 3) {
    if (!d.quests.length) centreText(ctx, 512, 330, "No quests yet.", 14, true, INK);
    const first = (J.page - 1) * 7;
    d.quests.slice(first, first + 7).forEach((q, n) => questCard(ctx, q, 48, 108 + n * 82, 928));
    const n = J.hover - 100;
    const q = d.quests[first + n];
    if (n >= 0 && n < 7 && q) {
      const rows = questRows(ctx, q, 380, "");
      const h = 16 + rows.reduce((a, r) => a + ROW_H[r[0]], 0);
      const top = 108 + n * 82;
      const y = top + 70 + h <= 740 ? top + 70 : Math.max(20, top + 6 - h);
      drawChecklist(ctx, q, rows, 976 - 380 - 16, y, 380, h);
    }
  } else if (J.tab === 4) {
    if (!spells.length) centreText(ctx, 512, 330, "No spells.", 14, true, INK);
    const first = (J.page - 1) * 8;
    spells.slice(first, first + 8).forEach((sp, slot) => spellCard(ctx, sp, slot));
  } else controls(ctx);
  button(ctx, 40, 696, 120, 28, "< Previous", J.page > 1 ? (J.hover === 11 ? 2 : 1) : 0);
  button(ctx, 864, 696, 120, 28, "Next >", J.page < pages() ? (J.hover === 12 ? 2 : 1) : 0);
  let info;
  if (J.tab === 1) info = `${d.crafts.filter((c) => c.status === 0).length} of ${d.crafts.length} recipes ready to make`;
  else if (J.tab === 2) info = `${d.gathers.filter((g) => g.status === 0).length} of ${d.gathers.length} you can gather now`;
  else if (J.tab === 3) info = `${d.quests.filter((q) => q.status === 2).length}/${d.quests.length} complete`;
  else if (J.tab === 4) info = `You carry ${S.me.shards || 0} Shards`;
  else info = "The world carries on while the journal is open";
  if (pages() > 1) info = `Page ${J.page} of ${pages()}     ${info}`;
  centreText(ctx, 512, 700, info, 10, true, INK);
  centreText(ctx, 512, 730, "H, F1 or Esc: close      1-5 or Left/Right: tabs      Up/Down or PgUp/PgDn: pages", 9, false, DIM);
}
