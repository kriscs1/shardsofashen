// The hover box's text for a thing: a few lines, each with its own look (ui.js drawQuick reads a line's first
// character): "#" the name (a heading), "~" a hint (small, dim), "!" a need not met (red), "+" a need met (green),
// "$" a price (gold); anything else is the plain text.
import { S } from "./state.js";
import { entityIni, spellIni } from "./assets.js";
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

export function itemLines(name) {
  // What an item is for, in a line or two, and what it needs
  const out = [];
  const spell = entityIni(name, "Spell", "").trim();
  const food = val(entityIni(name, "Food.Value", "0"));
  const slot = equipSlot(name);
  if (spell) {
    const eff = spellIni(spell, "Effect", "").toUpperCase();
    let what = spellSummary(spell, scrollRank(name));
    if (eff === "TELEPORT") what = spellIni(spell, "Map", "").trim() ? "Teleports you away" : "Teleports you home";
    if (eff === "HOME") what = "Takes you to your homestead";
    if (what) out.push(capital(what));
    if (spellIni(spell, "Kind", "Scroll").toUpperCase() !== "POTION") {
      // (one line: what it needs and what it costs)
      const rank = scrollRank(name), have = spellRank(spell);
      const level = val(spellAt(spell, "Level", "1", rank));
      const skill = spellIni(spell, "Skill", "Channeling");
      const cost = castCost(spell, rank);
      const cd = val(spellAt(spell, "Cooldown", "0", rank));
      out.push((skillLevel(skill) >= level ? "+" : "!") + `Needs ${pretty(skill)} ${lbstr(level)}` +
        (cost ? ` · ${lbstr(cost)} Shards a cast` : "") + (cd ? ` · ${lbstr(cd)} s` : ""));
      if (have >= rank) out.push(`+You know ${spellTitle(spell, have)}: the scroll isn't used up`);
      else if (have < rank - 1) out.push(`!Raises ${spellTitle(spell, rank - 1)} to ${spellTitle(spell, rank)}: learn that first`);
      else out.push(rank > 1 ? `~Read it: your ${spellTitle(spell, have)} becomes ${spellTitle(spell, rank)}` : "~Read it to learn the spell for good");
    }
  } else if (slot) {
    const bonus = ["Attack", "Defence", "Magic"].map((k) => [k, val(entityIni(name, k, "0"))])
      .filter(([, v]) => v).map(([k, v]) => `+${v} ${k}`);
    out.push(bonus.length ? bonus.join(", ") : capital(slot.toLowerCase()));
    const req = trim(entityIni(name, "Requires", "").replace(/,/g, " ")).split(/\s+/);
    for (let i = 0; i + 1 < req.length; i += 2) {
      const lv = val(req[i + 1]);
      if (lv > 0) out.push((skillLevel(req[i]) >= lv ? "+" : "!") + `Requirement: ${req[i]} ${lbstr(lv)}`);
    }
  } else if (food) {
    out.push(`Heals ${lbstr(food)} hitpoints`);
  } else if (entityIni(name, "Crop", "").trim()) {
    out.push("Seeds: sow them in tilled soil");
  } else {
    const info = firstSentence(entityIni(name, "Examine.Info", ""));
    if (info) out.push(info);
  }
  return out;
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
    const mode = S.box.mode;
    if (e.k === T.RACKITEM && mode === "Shop") lines.push(`$Price: ${itemPrice(e.n, S.box.buy_rate || 1.2)} gold`);
    if (e.k === T.RACKITEM && mode === "Market" && e.price) {
      lines.push(`$${e.price} gold each, from ${e.mine ? "you" : e.seller}`);
    }
    if (e.k === T.INVITEM && mode === "Shop") {
      lines.push(canSellHere(e.n) ? `$Sells for ${itemPrice(e.n, S.box.sell_rate || 0.2)} gold` : "!Can't be sold here");
    }
  } else if (e.k === T.NPC) {
    lines.push("#" + name);
    if (e.f) lines.push(`!Hostile  -  ${lbstr(e.hp)}/${lbstr(e.mh)} hitpoints`);
  } else if (e.k === T.PLAYER) {
    lines.push("#" + name, e.pvp ? "!In the arena: you can fight" : "Another adventurer", "~Right-click: Whisper");
    return lines.join("|");
  } else {
    if (first === "Walk here") return val(e.misc) === 1 ? "#" + name : "";
    lines.push("#" + name);
    const info = firstSentence(examineText(e), 48);
    if (info && e.k !== T.TILE) lines.push(info);
  }
  const h = hint(first);
  if (h) lines.push(h);
  return lines.join("|");
}
