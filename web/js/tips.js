// The hover box's text for a thing: a few lines, each with its own look (ui.js drawQuick reads a line's first
// character): "#" the name (a heading), "~" a hint (small, dim), "!" a need not met (red), "+" a need met (green),
// "$" a price (gold); anything else is the plain text.
import { S } from "./state.js";
import { entityIni, spellIni, locksIni } from "./assets.js";
import { val, trim, lbstr, pretty } from "./util.js";
import { T, getVerbs, displayName, examineText, equipSlot, spellSummary, skillLevel, itemPrice,
  canSellHere, knowsSpell, spellRank, scrollRank, spellAt, spellTitle, castCost } from "./verbs.js";

function firstSentence(text, most = 64) {
  const t = String(text || "").trim();
  if (!t) return "";
  const end = t.search(/[.!?](\s|$)/);
  let s = end >= 0 ? t.slice(0, end + 1) : t;
  if (s.length > most) s = s.slice(0, s.lastIndexOf(" ", most)) + "...";
  return s;
}

const capital = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
// (a thing's own line is marked "=", plain, so "+3 Attack" isn't read as a need met: ui.js drawHoverTop)
const SLOT_WORDS = ["", "Weapon", "Shield", "Head", "Body", "Legs", "Feet", "Hands", "Ring"];   // (verbs.js equipSlot)

export function itemLines(name) {
  // What an item is for, in a line or two, and what it needs: its own hover line (Hover.Info) if it has one, else
  // worked out from its numbers (a scroll's spell, gear's bonuses, food's healing)
  const out = [];
  const own = trim(entityIni(name, "Hover.Info", ""));
  const spell = entityIni(name, "Spell", "").trim();
  const food = val(entityIni(name, "Food.Value", "0"));
  const slot = equipSlot(name);
  if (spell) {
    const eff = spellIni(spell, "Effect", "").toUpperCase();
    let what = spellSummary(spell, scrollRank(name));
    if (eff === "TELEPORT") what = spellIni(spell, "Map", "").trim() ? "Teleports you away" : "Teleports you home";
    if (eff === "HOME") what = "Takes you to your homestead";
    if (own || what) out.push("=" + (own || capital(what)));
    if (spellIni(spell, "Kind", "Scroll").toUpperCase() !== "POTION") {
      // (one line: what it needs and what it costs)
      const rank = scrollRank(name), have = spellRank(spell);
      const level = val(spellAt(spell, "Level", "1", rank));
      const skill = spellIni(spell, "Skill", "Channeling");
      const cost = castCost(spell, rank);
      const cd = val(spellAt(spell, "Cooldown", "0", rank));
      out.push((skillLevel(skill) >= level ? "+" : "!") + `Needs ${pretty(skill)} ${lbstr(level)}` +
        (cost ? ` · ${lbstr(cost)} Shards a cast` : "") + (cd ? ` · ${lbstr(cd)} s` : ""));
      if (have >= rank) out.push("+You already know this");
      else if (have < rank - 1) out.push(`!Raises ${spellTitle(spell, rank - 1)} to ${spellTitle(spell, rank)}: learn that first`);
      else out.push(rank > 1 ? `~Read it: your ${spellTitle(spell, have)} becomes ${spellTitle(spell, rank)}` : "~Read it to learn the spell for good");
    }
  } else if (slot) {
    const bonus = ["Attack", "Defence", "Magic"].map((k) => [k, val(entityIni(name, k, "0"))])
      .filter(([, v]) => v).map(([k, v]) => `+${lbstr(v)} ${k}`);
    // (and what it wards off, whether it's warm: "+5 Attack | +2 Defence"; with none, the slot it goes in)
    if (entityIni(name, "Ammo", "").trim()) bonus.push("Shoots " + pretty(entityIni(name, "Ammo", "")));
    const wards = trim(entityIni(name, "Resists", "")).split(/\s+/).filter(Boolean);
    if (wards.length) bonus.push("Wards off " + wards.map((w) => w.toLowerCase()).join(", "));
    if (trim(entityIni(name, "Warm", "0")) === "1") bonus.push("Keeps out the cold");
    out.push("=" + (own || (bonus.length ? bonus.join(" | ") : SLOT_WORDS[slot])));
    const req = trim(entityIni(name, "Requires", "").replace(/,/g, " ")).split(/\s+/);
    for (let i = 0; i + 1 < req.length; i += 2) {
      const lv = val(req[i + 1]);
      if (lv > 0) out.push((skillLevel(req[i]) >= lv ? "+" : "!") + `Requirement: ${req[i]} ${lbstr(lv)}`);
    }
  } else if (own) {
    out.push("=" + own);
  } else if (food) {
    out.push(`Heals ${lbstr(food)}`);
  } else if (entityIni(name, "Crop", "").trim()) {
    out.push("Seeds | Sow them in tilled soil");
  } else {
    const info = hoverLine(name);
    if (info) out.push("=" + info);
  }
  return out;
}

function lockWord(lv) {
  // (how hard a lock is, Locks.ini Easy and Medium: its level is said only when you try one beyond your picks)
  return lv <= val(locksIni("Easy", "4")) ? "Easy" : lv <= val(locksIni("Medium", "9")) ? "Medium" : "Hard";
}

export function hoverLine(name) {
  // (a thing's own hover line, Entities.ini Hover.Info: build_hover.py; one without, its examine text's first sentence)
  return trim(entityIni(name, "Hover.Info", "")) || firstSentence(entityIni(name, "Examine.Info", ""));
}

// How a creature's level stands to yours: 0 far below (grey), 1 below (green), 2 about yours (yellow), 3 above (orange),
// 4 far above (red)
export function difficulty(lv) {
  const d = lv - ((S.me && S.me.level) || S.level || 1);
  return d <= -6 ? 0 : d <= -2 ? 1 : d <= 1 ? 2 : d <= 4 ? 3 : 4;
}

export function entityTip(e) {
  // The lines the hover box shows for e ("" = nothing to say)
  if (!e) return "";
  const verbs = getVerbs(e);
  const first = verbs[0] || "";
  const name = displayName(e);
  const hint = (v) => (v && v !== "Walk here" && v !== "Examine" ? `~Left-click: ${v}` : "");
  const lines = [];
  if (e.k === T.INVITEM || e.k === T.RACKITEM || e.k === T.MAPITEM) {
    const q = val(e.q || 1);
    lines.push("#" + name + (q > 1 ? `  (${lbstr(q)})` : ""));
    lines.push(...itemLines(e.n));
    if (e.stolen) lines.push("!Stolen: only a fence buys it");
    const mode = S.box.mode;
    if (e.k === T.RACKITEM && mode === "Shop") lines.push(`$Price: ${itemPrice(e.n, S.box.buy_rate || 1.2)} gold`);
    if (e.k === T.RACKITEM && mode === "Market" && e.price) {
      lines.push(`$${e.price} gold each, from ${e.mine ? "you" : e.seller}`);
    }
    if (e.k === T.INVITEM && mode === "Shop") {
      const rate = (S.box.sell_rate || 0.2) * (e.stolen ? S.box.fence : 1);   // (a fence pays less for it)
      if (canSellHere(e.n, e.stolen)) lines.push(`$Sells for ${itemPrice(e.n, rate)} gold`);
      else if (!e.stolen) lines.push("!Can't be sold here");
    }
  } else if (e.k === T.NPC) {
    // (one you can fight: its name coloured by how it stands to you - %0 far below to %4 far above: ui.js DIFFICULTY)
    // (a level only on one you can fight: the ferry, a shopkeeper, have none to show)
    const odds = e.f && e.lv ? "%" + difficulty(e.lv) : "#";
    lines.push(odds + name + (e.f && e.lv ? `  (level ${e.lv})` : ""));
    const info = hoverLine(e.n);
    if (info) lines.push("=" + info);
    if (e.f === 2) lines.push(`Passive | ${lbstr(e.hp)}/${lbstr(e.mh)} hitpoints`);
    else if (e.f) lines.push(`!Hostile | ${lbstr(e.hp)}/${lbstr(e.mh)} hitpoints`);
  } else if (e.k === T.STATICOBJECT && e.lc) {
    lines.push("#" + name, `!${e.ib ? "Iron-bound" : "Locked"} | ${lockWord(e.lc)}`);
  } else if (e.k === T.TILE && e.lockPick) {
    lines.push("#" + name, `!Locked | ${lockWord(e.lockPick)}`);               // (a door that can be picked)
  } else if (e.k === T.PLAYER) {
    lines.push("#" + name, e.pvp ? (S.me?.arena ? "!In the arena: you can fight" : "!You can fight them here")
      : "Another adventurer");
    if (e.mk) lines.push("!Marked: struck another player first");
    lines.push("~Right-click: Whisper");
    return lines.join("|");
  } else {
    if (first === "Walk here") return val(e.misc) === 1 ? "#" + name : "";
    lines.push("#" + name);
    const info = trim(entityIni(e.n, "Hover.Info", "")) || firstSentence(examineText(e), 48);
    if (info && e.k !== T.TILE) lines.push("=" + info);
  }
  const h = hint(first);
  if (h) lines.push(h);
  return lines.join("|");
}
