// The journal (H, F1 or the ? Help button): what you can make, what you can gather, your quests, your spells (learnt
// from scrolls, cast from here or the hotbar for Shards), your skills (how each is levelled, what it opens), the controls.
// The server sends the lists when it opens; drawn as the desktop game's screens.py drew it, on a 1024 x 768 page.
import { S } from "./state.js";
import { sprite } from "./assets.js";
import { val, word, lbstr, pretty, drawText, drawTextMid, centreText, textWidth, fitText, wrapLines, roundBox } from "./util.js";
import { questLook, questRows, drawChecklist, badge, padlock, ROW_H, trackedQuest, skillShown, levelOfXp, levelProgress } from "./ui.js";
import { A, configRead } from "./assets.js";
import { skillLevel, held, knowsSpell, cooldownLeft } from "./verbs.js";
import { send } from "./net.js";

const INK = [243, 232, 136];
const PARCHMENT = [212, 191, 126];
const DIM = [190, 160, 110];

export const J = { open: false, tab: 1, page: 1, hover: 0, focus: "", x0: 0, done: false, standing: false, skill: "" };
// (done: Quests' Done tab; standing: its Standing tab, what each town thinks of you)

const CONTROLS = [
  ["M", "Left-click ground", "Walk there."],
  ["M", "Left-click a thing", "Do its main action: Talk to a person, Pick up an item, Attack an enemy, Use an object..."],
  ["M", "Right-click", "A menu of everything you can do with it: Examine, Eat, Use, Drop All, Drop 1..."],
  ["M", "Use, then click", "Pick Use on an item you carry, then click what to use it with. Right-click to stop."],
  ["M", "Shops, bank, crafting", "Left-click buys, sells, banks or makes one. Right-click for more (Buy 5, Sell All, Value, Inspect...)."],
  ["M", "Box arrows, wheel", "Next or previous page of a shop, bank or crafting list (or turn the mouse wheel over it)."],
  ["M", "Skills (Stats)", "Point at one: its level. Right-click: progress to the next. Left-click: its guide. How to level each, and what it opens: the journal's Skills tab."],
  ["M", "Stats / Gear / Spells", "The tabs at the top of the Stats box: your skills, your 8 equipment slots, and the spells you know (click one to cast it; right-click: on or off the hotbar). Your quests are here in the journal: click one to follow it on the map."],
  ["M", "Wield, Wear", "Left-click a weapon, shield or armour in your inventory to put it on. Click it in the Gear tab to take it off."],
  ["M", "Hotbar", "The slots at the bottom of the view (five, or as many as ten: Options). Right-click an item: Put it on the hotbar. Click a slot (or press its number; 0 is the tenth) to use it; right-click a slot to take it off."],
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
  ["M", "Spells and Shards", "Learn a spell from its scroll, once, for good (the scroll is used up). Casting it spends Shards (top left: how many you have); each spell has its own cooldown. Cast from Spells in the Stats box, or put it on the hotbar. Shards don't come back by themselves: absorb the Shard Remnants beasts leave behind (Absorb, in your pack), and chests, digging and quests give them. Spells reach out of you; to mend or strengthen yourself, drink a potion (herbs, not Shards). Magister Quill can teach you to write a spell of your own. The better your Channeling, the fewer Shards each cast drinks."],
  ["M", "Shardstones", "A shardstone stands dormant till you activate it, once, with a few Shards. Travel from an active one and the world map opens with every stone you've activated on it: pick one to go there."],
  ["M", "Shardcraft", "The working of Shard magic: activating shardstones, dismantling gear (now and then a rare shard is left in the dust), writing a spell of your own, and enchanting. Use a rare shard on a weapon or armour in your pack (Enchant) to bind it in for good."],
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
  ["K", "1 - 9, 0", "Use what's in that hotbar slot."],
  ["K", "1 - 8", "Journal: pick a tab (Left and Right also work)."],
  ["K", "Up / Down", "Journal: previous or next page (PgUp and PgDn too)."],
  ["K", "F11", "Full screen (or the button at the top left of the view)."],
  ["K", "+ / -", "Zoom the map in and out."],
  ["K", "Saving", "Automatic: the server keeps your game."],
];

// (the tabs: 1 Crafting, 2 Gathering, 3 Quests, 4 Spells, 5 Records, 6 Friends, 7 Skills, 8 Controls)
export const TABS = 8;
const TAB_W = 114, TAB_STEP = 119;
const FRIENDS_SHOWN = 8;
export const QUESTS_SHOWN = 6, QUEST_TOP = 146;          // (Quests: In hand and Done tabs over the cards)
export function pageSize() { return { 1: 14, 2: 7, 3: QUESTS_SHOWN, 4: 8, 6: FRIENDS_SHOWN }[J.tab] || 1; }

function count() {
  const d = S.journal || { crafts: [], gathers: [], quests: [], spells: [] };
  return { 1: d.crafts.length, 2: d.gathers.length, 3: J.standing ? 1 : journalQuests().length, 4: (d.spells || []).length,
    6: (d.friends || []).length }[J.tab] || 1;
}

// ----- friends (together.py): each a row - about or not, where, their level - with Whisper, Invite and Remove; a
// Hallisium account's friends by account ("Character (account)" here, or where they're playing), asks to Accept or Decline
const FRIEND_BUTTONS = ["Whisper", "Invite", "Remove"];
function friendButtons(f) { return !f.asks && !f.asked && !f.on ? ["Letter", "Invite", "Remove"] : f.asks ? ["Accept", "", "Decline"] : f.asked ? ["", "", "Cancel"] : FRIEND_BUTTONS; }
function friendRowY(n) { return 108 + n * 70; }

// ----- each button's [x, y, w, h], said once: drawn by it and clicked by it (hit), so the two can't drift apart
const BUTTON_RECTS = { 10: [942, 20, 40, 28], 11: [40, 696, 120, 28], 12: [864, 696, 120, 28],   // (close; the pages)
  400: [48, 106, 180, 30], 401: [236, 106, 180, 30], 402: [424, 106, 180, 30] };             // (Quests: In hand, Done, Standing)
const tabRect = (t) => [40 + (t - 1) * TAB_STEP, 60, TAB_W, 32];
const friendButtonRect = (n, k) => [976 - 316 + k * 104, friendRowY(n) + 15, 96, 32];
function spellButtonRect(slot, k) {                 // (k 0: Cast, 1: Hotbar)
  const [x, y] = spellCardAt(slot);
  return [x + SPELL_W - (k ? 100 : 196), y + SPELL_H - 38, 88, 28];
}
const within = (x, y, [bx, by, w, h]) => x >= bx && x <= bx + w && y >= by && y <= by + h;    // (its edges count too)

export function friendClick(h) {
  // (300 + row x 3 + button: whisper them, ask them into your party, take them off the list)
  if (h < 300 || h >= 300 + FRIENDS_SHOWN * 3) return false;
  const rows = (S.journal && S.journal.friends) || [];
  const f = rows[(J.page - 1) * FRIENDS_SHOWN + Math.floor((h - 300) / 3)];
  if (!f) return true;
  const k = (h - 300) % 3, who = f.char || f.name, acct = f.account ? 1 : 0;
  if (f.asks && k === 0) send({ t: "friend", name: f.account, account: 1 });
  else if (f.asks || f.asked) { if (k === 2) send({ t: "friend", name: f.account, account: 1, remove: 1 }); }
  else if (k === 0) window.dsUI.openChat((f.on ? "/w " : "/letter ") + who + " ");
  else if (k === 1 && f.on) send({ t: "party_invite", name: who });
  else if (k === 2) send({ t: "friend", name: f.account || f.name, account: acct, remove: 1 });
  else return true;
  setTimeout(() => send({ t: "journal" }), 600);
  return true;
}

function friendRow(ctx, f, n) {
  const y = friendRowY(n);
  card(ctx, 48, y, 928, 62, f.on ? [126, 77, 63] : [77, 43, 33]);
  ctx.fillStyle = f.on ? "rgb(110,210,110)" : "rgb(110,100,90)";
  ctx.beginPath(); ctx.arc(70, y + 31, 6, 0, 6.283); ctx.fill();
  drawText(ctx, f.name + (f.party ? "  (in your party)" : ""), 88, y + 10, 12, true, f.on || f.asks ? INK : DIM);
  const where = f.asks ? "Asks to be your friend" : f.asked ? "You've asked them to be your friend" :
    f.on ? `About, ${f.where || "in Ashen"}` + (f.level ? `  ·  level ${f.level}` : "") :
    (f.where || "Away") + (f.level ? `  ·  level ${f.level}` : "");
  drawText(ctx, where, 88, y + 34, 9, false, f.on || f.asks ? PARCHMENT : DIM);
  friendButtons(f).forEach((label, k) => {
    if (!label) return;
    const off = !f.asks && !f.asked && ((k === 1 && !f.on) || (k === 1 && f.party));
    button(ctx, ...friendButtonRect(n, k), label, off ? 0 : J.hover === 300 + n * 3 + k ? 2 : 1);
  });
}

function friendsPage(ctx, d) {
  const rows = d.friends || [];
  if (!rows.length) {
    centreText(ctx, 512, 300, "No friends on your list yet.", 14, true, INK);
    centreText(ctx, 512, 330, "Right-click a player and choose Add friend, or type /friend and their name (or their Hallisium account's) in the chat.", 10, false, PARCHMENT);
    return;
  }
  const first = (J.page - 1) * FRIENDS_SHOWN;
  rows.slice(first, first + FRIENDS_SHOWN).forEach((f, n) => friendRow(ctx, f, n));
}

// ----- records (together.py): each record's top three across the world, and yours
function recordsPage(ctx, d) {
  const recs = d.records || [];
  if (!recs.length) { centreText(ctx, 512, 330, "No records yet.", 14, true, INK); return; }
  recs.forEach((r, i) => {
    const x = 48 + (i % 2) * 466, y = 108 + Math.floor(i / 2) * 290;
    card(ctx, x, y, 462, 280, [126, 77, 63]);
    drawText(ctx, "Most " + r.words, x + 18, y + 14, 13, true, INK);
    if (!r.top.length) drawText(ctx, "Nobody yet. It could be you.", x + 18, y + 54, 10, false, DIM);
    r.top.forEach(([name, v], k) => {
      const col = [[250, 215, 110], [220, 220, 230], [210, 160, 110]][k];
      drawText(ctx, `${k + 1}.  ${name}`, x + 18, y + 54 + k * 40, 12, true, col);
      const vt = String(v);
      drawText(ctx, vt, x + 444 - textWidth(ctx, vt, 12, true), y + 54 + k * 40, 12, true, col);
    });
    ctx.fillStyle = "rgb(126,77,63)";
    ctx.fillRect(x + 18, y + 226, 426, 1);
    drawText(ctx, `Yours: ${r.mine}`, x + 18, y + 240, 11, true, PARCHMENT);
  });
}

export function pages() { return J.tab === 7 ? skillPageN : Math.max(1, Math.ceil(count() / pageSize())); }

export function hit(x, y) {
  for (let t = 1; t <= TABS; t++) if (within(x, y, tabRect(t))) return t;
  if (J.tab === 6) {
    for (let n = 0; n < FRIENDS_SHOWN; n++) {
      for (let k = 0; k < 3; k++) if (within(x, y, friendButtonRect(n, k))) return 300 + n * 3 + k;
    }
  }
  for (const b of [10, 11, 12]) if (within(x, y, BUTTON_RECTS[b])) return b;
  if (J.tab === 4) {                              // (a known spell's Cast and Hotbar buttons: 200 + slot x 2 (+1))
    for (let slot = 0; slot < 8; slot++) {
      for (const k of [0, 1]) if (within(x, y, spellButtonRect(slot, k))) return 200 + slot * 2 + k;
    }
  }
  if (J.tab === 7) {                              // (a skill in the list down the left: 500 + its row)
    for (let n = 0; n < skillRows(); n++) if (within(x, y, skillRowRect(n))) return 500 + n;
  }
  if (J.tab === 3) for (const b of [400, 401, 402]) if (within(x, y, BUTTON_RECTS[b])) return b;
  if (J.tab === 3 && !J.standing && x >= 48 && x <= 976) {
    const n = Math.floor((y - QUEST_TOP) / 82);
    if (n >= 0 && n < QUESTS_SHOWN && y - QUEST_TOP - n * 82 <= 76 &&
        (J.page - 1) * QUESTS_SHOWN + n < journalQuests().length) return 100 + n;
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

// ----- standing (standing.py): each town that knows you, its rank, and where you are between Outlaw and Honoured
const RANK_COLOUR = { Outlaw: [235, 90, 70], Distrusted: [230, 150, 80], Stranger: DIM, Welcome: PARCHMENT,
  Trusted: [140, 215, 120], Honoured: [250, 215, 110] };

function standingPage(ctx, d) {
  const rows = d.standing || [];
  if (!rows.length) { centreText(ctx, 512, 330, "No town knows you yet. You're a stranger everywhere.", 14, true, INK); return; }
  rows.slice(0, 16).forEach(([town, n, rank], i) => {
    const x = 48 + (i % 2) * 466, y = 146 + Math.floor(i / 2) * 66;
    const col = RANK_COLOUR[rank] || PARCHMENT;
    card(ctx, x, y, 462, 60);
    drawText(ctx, fitText(ctx, town, 250, 12), x + 16, y + 10, 12, true, INK);
    drawText(ctx, rank, x + 446 - textWidth(ctx, rank, 12, true), y + 10, 12, true, col);
    const bx = x + 16, bw = 430, by = y + 38, mid = bx + bw / 2;     // (a bar: Outlaw at the left, Honoured at the right)
    roundBox(ctx, bx, by, bw, 8, [40, 26, 20], [92, 60, 46], 1, 4);
    const end = mid + (Math.max(-100, Math.min(100, n)) / 100) * (bw / 2 - 2);
    ctx.fillStyle = `rgb(${col.join(",")})`;
    ctx.fillRect(Math.min(mid, end), by + 2, Math.max(2, Math.abs(end - mid)), 4);
    ctx.fillStyle = "rgb(126,77,63)";
    ctx.fillRect(mid, by - 2, 1, 12);
  });
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
    if (level > 0) r.text(`${pretty(skill)} level ${lbstr(level)}`, skillLevel(skill) < level ? [235, 105, 85] : [120, 210, 110], y);
    else r.text(pretty(skill) + " (any level)", PARCHMENT, y);
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

// (the quests in the journal: in hand, done, and those you can start now - not the ones still locked to you)
function allQuests() {
  return (S.journal?.quests || []).filter((q) => !(q.status === 1 && q.needs && q.needs.length));
}
export function journalQuests() {
  // (the tab shown: In hand - begun, or yours to start - or Done)
  return allQuests().filter((q) => (q.status === 2) === J.done);
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
  if (q.title === trackedQuest() && q.status !== 2) bw += 8 + badge(ctx, x + w - 18 - bw, y + 8, "Following", [255, 214, 90]);
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
  if (todo && q.status !== 2) badge(ctx, x + w - 18 - bw, y + 8, `${todo} to do`, [255, 214, 90]);
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
  const label = known ? "Known" : short ? `Needs ${pretty(sp.skill)} ${sp.level}` : "Not learnt";
  const bw = badge(ctx, x + SPELL_W - 10, y + 8, label, known ? [150, 140, 255] : short ? [235, 105, 85] : [190, 160, 110]);
  drawText(ctx, fitText(ctx, sp.title || pretty(sp.spell), SPELL_W - 80 - bw, 11, true), x + 56, y + 8, 11, true, known ? INK : PARCHMENT);
  const r = new Run(ctx, x + 56, x + SPELL_W - 12);
  r.text(`${pretty(sp.skill)} ${sp.level}`, short ? [235, 105, 85] : [120, 210, 110], y + 28, 9, true);
  r.text("   ·   ", DIM, y + 28);
  r.icon("Shard", y + 25, 14);
  r.text(`${sp.cost} Shards a cast`, (S.me.shards || 0) < sp.cost && known ? [235, 105, 85] : [214, 200, 255], y + 28, 9, true);
  if (sp.cooldown > 0) r.text(`   ·   ready again after ${lbstr(sp.cooldown)} s`, PARCHMENT, y + 28);
  wrap(ctx, x + 16, y + 50, SPELL_W - 32, sp.what.charAt(0).toUpperCase() + sp.what.slice(1) + ".", [250, 240, 210], 15, sp.next ? 1 : 2);
  if (sp.next) {                                  // (its next rank: what it'll be, and what it needs)
    const n = sp.next;
    wrap(ctx, x + 16, y + 68, SPELL_W - 32, `Upgrade: ${n.title} (${pretty(sp.skill)} ${n.level}, ${n.cost} Shards): ${n.what}. Its scroll comes from quests.`,
      skillLevel(sp.skill) >= n.level ? [190, 180, 255] : DIM, 15, 2);
  }
  if (known) {
    const left = cooldownLeft(sp.spell), poor = (S.me.shards || 0) < sp.cost;
    if (left > 0) drawText(ctx, `Ready in ${Math.ceil(left / 1000)} s`, x + 16, y + SPELL_H - 32, 9, true, [255, 214, 90]);
    else if (poor) drawText(ctx, "Not enough Shards", x + 16, y + SPELL_H - 32, 9, true, [235, 105, 85]);
    const h = J.hover - 200 - slot * 2;
    button(ctx, ...spellButtonRect(slot, 0), "Cast", left > 0 || poor ? 0 : h === 0 ? 2 : 1);
    const on = (S.me.hotbar || []).includes(sp.scroll);
    button(ctx, ...spellButtonRect(slot, 1), on ? "On hotbar" : "Hotbar", on ? 0 : h === 1 ? 2 : 1);
  } else {
    wrap(ctx, x + 16, y + SPELL_H - 30, SPELL_W - 32, "Learn it from its scroll: they're rare (quests, and the wizards, who charge dearly).", DIM, 15, 1);
  }
}

// ----- skills: the list down the left (your level, how far to the next); the one picked, how it's levelled
// (Skills.ini) and what each level opens up (worked out from the data by the server), paged if it runs long
let skillPageN = 1;
const FORMS_ROW = "~forms";                       // (the row under the skills: your stance forms - forms.py)
const skillRows = () => skillList().length + (S.me?.forms?.length ? 1 : 0);
const skillRowRect = (n) => {
  const step = Math.min(47, Math.floor(576 / Math.max(1, skillRows())));     // (all of them fit down the page)
  return [48, 108 + n * step, 292, step - 5];
};
const maxSkill = () => Math.max(2, Math.floor(val(configRead("Gameplay", "Skill.Max.Level", "25"))));

function skillList() {
  // (the skills you see in Stats, in their order: each with its page from the server)
  const pages = S.journal?.skills || [];
  return A.m.skills.map((name, i) => ({ name, i, page: pages.find((p) => p.skill === name) }))
    .filter((s) => skillShown(s.i + 1) && s.page);
}

export function skillClick(h) {
  if (J.tab !== 7 || h < 500 || h >= 600) return false;
  const s = skillList()[h - 500];
  if (s) { J.skill = s.name; J.page = 1; }
  else if (h - 500 === skillList().length && S.me?.forms?.length) { J.skill = FORMS_ROW; J.page = 1; }
  return true;
}

function skillsPage(ctx) {
  const list = skillList();
  if (!list.length) { skillPageN = 1; centreText(ctx, 512, 330, "No skills.", 14, true, INK); return; }
  const forms = S.me.forms || [];
  const sel = J.skill === FORMS_ROW && forms.length ? null : list.find((s) => s.name === J.skill) || list[0];
  J.skill = sel ? sel.name : FORMS_ROW;
  if (forms.length) formsRow(ctx, list.length, !sel);
  list.forEach((s, n) => {
    const [x, y, w, h] = skillRowRect(n), xp = S.me.xp?.[s.i] || 0, lv = levelOfXp(xp);
    const picked = s === sel;
    roundBox(ctx, x, y, w, h, picked ? [92, 60, 46] : J.hover === 500 + n ? [72, 47, 37] : [61, 40, 31],
      picked ? [190, 140, 100] : [92, 60, 46], picked ? 2 : 1, 10);
    const ic = sprite(configRead("Skills", "Icon." + s.name, "").trim());
    if (ic) {
      const k = Math.min(28 / ic.width, 28 / ic.height);
      ctx.drawImage(ic, x + 8 + (28 - ic.width * k) / 2, y + 7 + (28 - ic.height * k) / 2, ic.width * k, ic.height * k);
    }
    drawText(ctx, pretty(s.name), x + 44, y + 5, 11, true, picked ? INK : PARCHMENT);
    const lt = `${lv}/${maxSkill()}`;
    drawText(ctx, lt, x + w - 10 - textWidth(ctx, lt, 10, true), y + 6, 10, true, lv >= maxSkill() ? [255, 215, 60] : INK);
    ctx.fillStyle = "rgb(40,26,20)";
    ctx.fillRect(x + 44, y + 28, w - 54, 6);
    ctx.fillStyle = "rgb(120,210,110)";
    ctx.fillRect(x + 44, y + 28, Math.round((w - 54) * levelProgress(xp) / 100), 6);
  });
  if (!sel) { formsPage(ctx, forms); return; }
  // (the one picked: how it's levelled, then what each level opens up, the levels you have green, the next one lit)
  const x = 364, w = 612, xp = S.me.xp?.[sel.i] || 0, lv = levelOfXp(xp), p = sel.page;
  drawText(ctx, pretty(sel.name), x, 108, 15, true, INK);
  const tw = textWidth(ctx, pretty(sel.name), 15, true);
  const where = lv >= maxSkill() ? `Level ${lv}: mastered` : `Level ${lv}   ·   ${levelProgress(xp)}% of the way to ${lv + 1}`;
  drawText(ctx, where, x + tw + 16, 113, 10, true, lv >= maxSkill() ? [255, 215, 60] : PARCHMENT);
  let y = 140;
  drawText(ctx, "How to level it", x, y, 11, true, INK);
  y += 20 + 16 * wrap(ctx, x, y + 20, w, p.trains || "-", [250, 240, 210], 16, 4, 10);
  drawText(ctx, "What opens up", x, y + 10, 11, true, INK);
  ctx.fillStyle = "rgb(126,77,63)";
  ctx.fillRect(x, y + 32, w, 1);
  const top = y + 42, bottom = 684;
  // (each level a row of up to four lines; as many rows to a page as fit, the rest on the next)
  const rows = (p.opens || []).map(([level, what]) => ({ level, what, lines: Math.max(1, Math.min(4, wrapLines(ctx, what, w - 64, 9).length)) }));
  const pg = [[]];
  let room = bottom - top;
  for (const r of rows) {
    const h = r.lines * 15 + 9;
    if (h > room && pg[pg.length - 1].length) { pg.push([]); room = bottom - top; }
    pg[pg.length - 1].push(r);
    room -= h;
  }
  skillPageN = pg.length;
  J.page = Math.min(J.page, skillPageN);
  if (!rows.length) drawText(ctx, "Nothing more than getting better at it.", x, top, 10, false, DIM);
  const next = rows.find((r) => r.level > lv);
  y = top;
  for (const r of pg[J.page - 1] || []) {
    const got = r.level <= lv, soon = r === next;
    const [fill, border, ink] = got ? [[30, 70, 35], [80, 160, 80], [150, 230, 140]] :
      soon ? [[92, 60, 46], [190, 140, 100], INK] : [[51, 34, 27], [92, 60, 46], DIM];
    roundBox(ctx, x, y - 2, 52, 20, fill, border, 1, 8);
    centreText(ctx, x + 26, y + 1, "Lv " + r.level, 9, true, ink);
    wrap(ctx, x + 64, y, w - 64, r.what, got ? [250, 240, 210] : soon ? PARCHMENT : DIM, 15, 4);
    y += r.lines * 15 + 9;
  }
}

function formsRow(ctx, n, picked) {
  // (the row under the skills: how many forms you hold, a dot of each one's colour)
  const [x, y, w, h] = skillRowRect(n), forms = S.me.forms;
  roundBox(ctx, x, y, w, h, picked ? [92, 60, 46] : J.hover === 500 + n ? [72, 47, 37] : [61, 40, 31],
    picked ? [190, 140, 100] : [92, 60, 46], picked ? 2 : 1, 10);
  drawText(ctx, "Stance forms", x + 44, y + 5, 11, true, picked ? INK : PARCHMENT);
  const bound = forms.filter((f) => f[2]).length, lt = `${bound}/${S.me.forms_most || 6}`;
  drawText(ctx, lt, x + w - 10 - textWidth(ctx, lt, 10, true), y + 6, 10, true, INK);
  ringIcon(ctx, x + 22, y + 21, forms.filter((f) => f[2]).map((f) => f[4]));
  forms.forEach((f, k) => {
    ctx.fillStyle = f[2] ? `rgb(${f[4].join(",")})` : "rgb(92,60,46)";
    ctx.fillRect(x + 44 + k * 12, y + 27, 8, 8);
  });
}

function ringIcon(ctx, cx, cy, cols) {
  // (a little stance ring, with a mark of each bound form's colour round it)
  ctx.strokeStyle = "rgb(212,191,126)";
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.ellipse(cx, cy, 11, 5, 0, 0, Math.PI * 2); ctx.stroke();
  cols.forEach((c, k) => {
    const a = k * 6.283 / Math.max(1, cols.length) - 1.571;
    ctx.fillStyle = `rgb(${c.join(",")})`;
    ctx.fillRect(Math.round(cx + Math.cos(a) * 11) - 2, Math.round(cy + Math.sin(a) * 5) - 2, 4, 4);
  });
}

function formsPage(ctx, forms) {
  // (every form you know, each stance's together: bound or not, and what it does)
  skillPageN = 1;
  J.page = 1;
  const x = 364, w = 612, bound = forms.filter((f) => f[2]).length;
  drawText(ctx, "Stance forms", x, 108, 15, true, INK);
  const tw = textWidth(ctx, "Stance forms", 15, true);
  drawText(ctx, `${bound} of ${S.me.forms_most || 6} bound`, x + tw + 16, 113, 10, true, PARCHMENT);
  let y = 140;
  y += 16 * wrap(ctx, x, y, w, "A form is a way of holding the Shards in you, taught by people round the world. A bound " +
    "form counts while you're in its stance. Bind or let go of them at any shardstone you've woken: Bind forms, on its " +
    "travel map.", [250, 240, 210], 16, 4, 10) + 8;
  for (const st of ["Fighting", "Channelling", "Sneaking"]) {
    const mine = forms.filter((f) => f[0] === st);
    if (!mine.length) continue;
    drawText(ctx, st, x, y, 11, true, INK);
    ctx.fillStyle = "rgb(126,77,63)";
    ctx.fillRect(x, y + 20, w, 1);
    y += 28;
    for (const f of mine) {
      ctx.fillStyle = `rgb(${f[4].join(",")})`;
      ctx.globalAlpha = f[2] ? 1 : 0.35;
      ctx.beginPath(); ctx.arc(x + 7, y + 7, 6, 0, 6.283); ctx.fill();
      ctx.globalAlpha = 1;
      drawText(ctx, f[1], x + 20, y, 10, true, f[2] ? [150, 230, 140] : PARCHMENT);
      const lw = textWidth(ctx, f[1], 10, true);
      drawText(ctx, f[2] ? "bound" : "not bound", x + 28 + lw, y + 1, 9, false, f[2] ? [120, 210, 110] : DIM);
      y += 16 + 15 * wrap(ctx, x + 20, y + 16, w - 20, f[3], f[2] ? [250, 240, 210] : DIM, 15, 2) + 6;
    }
    y += 6;
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
  button(ctx, ...BUTTON_RECTS[10], "X", J.hover === 10 ? 2 : 1);
  for (let t = 1; t <= TABS; t++) {
    const mine = (d.friends || []).filter((f) => !f.asks && !f.asked), on = mine.filter((f) => f.on).length;
    const label = { 1: `Crafting (${d.crafts.length})`, 2: `Gathering (${d.gathers.length})`, 3: `Quests (${allQuests().length})`,
      4: `Spells (${spells.filter((s) => knowsSpell(s.spell)).length}/${spells.length})`, 5: "Records",
      6: `Friends (${on}/${mine.length})`, 7: "Skills" }[t] || "Controls";
    button(ctx, ...tabRect(t), label, J.tab === t ? 3 : J.hover === t ? 2 : 1);
  }
  roundBox(ctx, 36, 98, 952, 590, [40, 26, 20], [126, 77, 63], 2, 12);
  if (!S.journal && J.tab !== TABS) centreText(ctx, 512, 330, "Opening the journal...", 14, true, INK);
  else if (J.tab === 1) {
    if (!d.crafts.length) centreText(ctx, 512, 330, "Nothing to make yet.", 14, true, INK);
    const first = (J.page - 1) * 14;
    d.crafts.slice(first, first + 14).forEach((c, slot) => recipe(ctx, c, 48 + (slot % 2) * 466, 108 + Math.floor(slot / 2) * 82, 462));
  } else if (J.tab === 2) {
    if (!d.gathers.length) centreText(ctx, 512, 330, "Nothing to gather yet.", 14, true, INK);
    const first = (J.page - 1) * 7;
    d.gathers.slice(first, first + 7).forEach((g, n) => gather(ctx, g, 48, 108 + n * 82, 928));
  } else if (J.tab === 3) {
    const quests = journalQuests(), all = allQuests(), done = all.filter((q) => q.status === 2).length;
    button(ctx, ...BUTTON_RECTS[400], `In hand (${all.length - done})`, !J.done && !J.standing ? 3 : J.hover === 400 ? 2 : 1);
    button(ctx, ...BUTTON_RECTS[401], `Done (${done})`, J.done && !J.standing ? 3 : J.hover === 401 ? 2 : 1);
    button(ctx, ...BUTTON_RECTS[402], "Standing", J.standing ? 3 : J.hover === 402 ? 2 : 1);
    if (J.standing) standingPage(ctx, d);
    else if (!quests.length) centreText(ctx, 512, 330, J.done ? "No quests done yet." : "No quests in hand.", 14, true, INK);
    const first = (J.page - 1) * QUESTS_SHOWN;
    if (!J.standing) quests.slice(first, first + QUESTS_SHOWN).forEach((q, n) => questCard(ctx, q, 48, QUEST_TOP + n * 82, 928));
    const n = J.hover - 100;
    const q = J.standing ? null : quests[first + n];
    if (n >= 0 && n < QUESTS_SHOWN && q) {
      const rows = questRows(ctx, q, 380, "");
      const h = 16 + rows.reduce((a, r) => a + ROW_H[r[0]], 0);
      const top = QUEST_TOP + n * 82;
      const y = top + 70 + h <= 740 ? top + 70 : Math.max(20, top + 6 - h);
      drawChecklist(ctx, q, rows, 976 - 380 - 16, y, 380, h);
    }
  } else if (J.tab === 4) {
    if (!spells.length) centreText(ctx, 512, 330, "No spells.", 14, true, INK);
    const first = (J.page - 1) * 8;
    spells.slice(first, first + 8).forEach((sp, slot) => spellCard(ctx, sp, slot));
  } else if (J.tab === 5) recordsPage(ctx, d);
  else if (J.tab === 6) friendsPage(ctx, d);
  else if (J.tab === 7) skillsPage(ctx);
  else controls(ctx);
  button(ctx, ...BUTTON_RECTS[11], "< Previous", J.page > 1 ? (J.hover === 11 ? 2 : 1) : 0);
  button(ctx, ...BUTTON_RECTS[12], "Next >", J.page < pages() ? (J.hover === 12 ? 2 : 1) : 0);
  let info;
  if (J.tab === 1) info = `${d.crafts.filter((c) => c.status === 0).length} of ${d.crafts.length} recipes ready to make`;
  else if (J.tab === 2) info = `${d.gathers.filter((g) => g.status === 0).length} of ${d.gathers.length} you can gather now`;
  else if (J.tab === 3) info = J.standing ? "What each town thinks of you: its prices, its guards and its doors" :
    J.done ? "The quests you've seen through" : "Click a quest to follow it on the map";
  else if (J.tab === 4) info = `You carry ${S.me.shards || 0} Shards`;
  else if (J.tab === 5) info = "Kept for everyone who's played here";
  else if (J.tab === 6) info = "Right-click a player, or /friend Name, to add a friend";
  else if (J.tab === 7) info = "Click a skill: how to level it, and what each level opens up";
  else info = "The world carries on while the journal is open";
  if (pages() > 1) info = `Page ${J.page} of ${pages()}     ${info}`;
  centreText(ctx, 512, 700, info, 10, true, INK);
  centreText(ctx, 512, 730, "H, F1 or Esc: close      1-8 or Left/Right: tabs      Up/Down or PgUp/PgDn: pages", 9, false, DIM);
}
