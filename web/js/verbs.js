// The verbs on things, as the desktop game's interact.py has them: the right-click menu (the first verb is the
// left-click), the label shown, how close you walk first. The server works them out again before it does one.
import { S } from "./state.js";
import { tileIni, entityIni, A, spellIni, configRead } from "./assets.js";
import { val, word, trim, pretty, stripDigits, lbstr } from "./util.js";

export const T = { PLAYER: 1, TILE: 2, MAPITEM: 3, STATICOBJECT: 4, NPC: 5, MISSILE: 7, TEMPORARY: 8, INFRONT: 10,
  RACKITEM: 13, INVITEM: 14 };

const WALK_FIRST = ["Wall", "Forest", "Hedge", "Pond", "Pool", "_Window", "Water", "Timber0", "Plaster0", "Sandstone0",
  "Brick0"];

function addVerb(lst, verb) {
  verb = trim(verb);
  if (!verb) return lst;
  if (lst.some((v) => v.toUpperCase() === verb.toUpperCase())) return lst;
  lst.push(verb);
  return lst;
}

function addVerbs(lst, verbs) {
  for (const v of String(verbs || "").split(",")) addVerb(lst, v);
  return lst;
}

export function displayName(e) {
  if (!e) return "";
  if (e.k === T.PLAYER) return e.n;
  return pretty(e.n);
}

export function examineText(e) {
  if (e.k === T.TILE || e.k === T.INFRONT) {
    return tileIni(e.n, "Examine.Info", "") || tileIni(stripDigits(e.n), "Examine.Info", "");
  }
  return entityIni(e.n, "Examine.Info", "");
}

function examineFirst(e) {
  if (val(e.misc) !== 1 || examineText(e) === "" || WALK_FIRST.some((w) => e.n.includes(w))) return false;
  const all = "1".repeat((A.m.geometry.walk_res || 7) ** 2);
  return tileIni(e.n, "Walkable.Data", all).includes("0");
}

export function equipSlot(item) {
  const s = entityIni(item, "Slot", "").trim().toUpperCase();
  const names = ["", "WEAPON", "SHIELD", "HEAD", "BODY", "LEGS", "FEET", "HANDS", "RING"];
  const i = names.indexOf(s);
  return i > 0 ? i : 0;
}

export function equipVerb(item) {
  const s = equipSlot(item);
  if (!s) return "";
  return s <= 2 ? "Wield" : "Wear";
}

export function canSellHere(name) {
  if (name === "Gold_Coin(s)" || val(entityIni(name, "Value", "0")) <= 0) return false;
  const b = S.box;
  return !(b.specific === 1 && !(b.stock || []).includes(name));
}

export function getVerbs(e) {
  if (!e) return [];
  const t = e.k;
  let v = [];
  const mode = S.box.mode;
  if (t === T.TILE || t === T.INFRONT) {
    addVerbs(v, e.uw);
    if (e.lock !== undefined) { addVerb(v, "Open"); addVerb(v, "Unlock"); }
    if (!v.length && examineFirst(e)) v = ["Examine"];
    addVerb(v, "Walk here");
    if (val(e.misc) === 1 || e.uw || examineText(e)) addVerb(v, "Examine");
  } else if (t === T.MAPITEM) {
    v = ["Pickup", "Examine"];
  } else if (mode === "Chest" && (t === T.INVITEM || t === T.RACKITEM)) {
    v = t === T.RACKITEM ? ["Take 1", "Take all", "Examine"] : ["Examine"];
  } else if (t === T.INVITEM && mode === "Market") {
    const sellable = e.n !== "Gold_Coin(s)" && entityIni(e.n, "Droppable", "1").trim() !== "0";
    v = sellable ? ["Sell on the market", "Examine"] : ["Examine"];
  } else if (t === T.RACKITEM && mode === "Market") {
    v = e.mine ? ["Take back 1", "Take back all", "Set price", "Examine"] : ["Buy 1", "Buy 5", "Value", "Examine"];
  } else if (t === T.INVITEM) {
    if (mode === "Shop") v = canSellHere(e.n) ? ["Sell 1", "Sell All", "Value", "Examine"] : ["Examine"];
    else if (mode === "Bank") v = ["Deposit 1", "Deposit All", "Examine"];
    else {
      addVerbs(v, entityIni(e.n, "Use.Words", ""));
      addVerb(v, equipVerb(e.n));
      addVerb(v, "Use");
      if (entityIni(e.n, "Droppable", "1").trim() === "0") { /* (kept: quest things, the Access Crystal) */ }
      else if (e.q > 1) { addVerb(v, "Drop All"); addVerb(v, "Drop 1"); } else addVerb(v, "Drop");
      addVerb(v, "Examine");
      addVerb(v, (S.me.hotbar || []).includes(e.n) ? "Off hotbar" : "Hotbar");
    }
  } else if (t === T.RACKITEM) {
    if (mode === "Shop") v = ["Buy 1", "Buy 5", "Value", "Examine"];
    else if (mode === "Bank") v = ["Withdraw 1", "Withdraw All", "Examine"];
    else if (mode === "Craft") v = ["Make", "Inspect", "Examine"];
    else v = ["Examine"];
  } else if (t === T.STATICOBJECT || t === T.TEMPORARY || t === T.MISSILE) {
    addVerbs(v, e.uw);
    if (!v.length) v = ["Use"];
    addVerb(v, "Examine");
  } else if (t === T.NPC && e.f) {
    addVerb(v, "Attack");
    addVerbs(v, e.uw);
    addVerb(v, "Examine");
  } else if (t === T.NPC) {
    for (const w of String(e.uw || "").split(",")) if (trim(w) && trim(w).toUpperCase() !== "ATTACK") addVerb(v, w);
    addVerb(v, "Talk to");
    addVerb(v, "Examine");
  } else if (t === T.PLAYER) {
    v = e.pvp ? ["Attack", "Whisper", "Examine"] : ["Whisper", "Examine"];   // (the server says when you may fight: the arena)
  }
  if (S.itemInUse && !(e.k === T.INVITEM && e.u === S.itemInUse) && !mode) v = ["Use with", ...v];
  return v;
}

export function itemPrice(name, rate) {
  return Math.max(1, Math.floor(val(entityIni(name, "Value", "0")) * rate + 0.5));
}

export function itemInUseName() {
  const it = (S.me.inv || []).find((i) => i[0] === S.itemInUse);
  return it ? it[1] : "";
}

// What a potion or spell scroll does, from Data/Spells.ini: "+5 spell damage, 2 min" (shown on Drink / Cast)
export function spellSummary(spell) {
  const eff = spellIni(spell, "Effect", "").toUpperCase();
  const n = (k) => val(spellIni(spell, k, "0"));
  const parts = [];
  if (eff === "BOOST" || eff === "SHIELD") {
    if (n("Attack")) parts.push(`+${n("Attack")} Attack`);
    if (n("Defence")) parts.push(`+${n("Defence")} Defence`);
    if (n("Magic")) parts.push(`+${n("Magic")} spell damage`);
    if (n("Sight")) parts.push("far sight");
    const s = n("Duration") || 60;
    parts.push(s % 60 === 0 ? `${s / 60} min` : `${s} s`);
  } else if (eff === "HEAL") parts.push(`heals ${spellIni(spell, "Heal", "")}`);
  else if (eff === "BOLT" || eff === "AREA") parts.push(`${spellIni(spell, "Damage", "")} damage`);
  else if (eff === "TELEPORT" || eff === "HOME") parts.push("teleports you");
  if (n("Mana")) parts.push(`+${n("Mana")} mana`);
  return parts.join(", ");
}

export function verbLabel(verb, e) {
  if (!e || verb === "Walk here" || verb === "Cancel") return verb;
  const name = displayName(e);
  if ((verb === "Drink" || verb === "Cast") && e.k === T.INVITEM) {
    const spell = entityIni(e.n, "Spell", "").trim();
    const what = spell ? spellSummary(spell) : "";
    if (what) return `${verb} ${name} (${what})`;
  }
  if (verb === "Use with") return `Use ${pretty(itemInUseName())} with ${name}`;
  if (verb === "Attack") return `Attack ${name} (${lbstr(e.hp)}/${lbstr(e.mh)})`;
  if ((verb === "Buy 1" || verb === "Buy 5") && S.box.mode === "Market") return `${verb} ${name} (${e.price} gold each, from ${e.seller})`;
  if (verb === "Buy 1" || verb === "Buy 5") return `${verb} ${name} (${itemPrice(e.n, S.box.buy_rate || 1.2)} gold)`;
  if (verb === "Sell on the market") return `Sell ${name} on the market...`;
  if (verb === "Set price") return `Set the price of ${name} (now ${e.price} gold)...`;
  if (verb === "Sell 1" || verb === "Sell All") {
    const n = verb === "Sell 1" ? 1 : Math.max(1, held(e.n));
    return `${verb} ${name} (${itemPrice(e.n, S.box.sell_rate || 0.2) * n} gold)`;
  }
  if (verb === "Make" && e.short) return `Make ${name} (needs ${S.box.skill} level ${e.short})`;
  if (verb === "Make" && e.missing) return `Make ${name} (not enough ${e.missing})`;
  if (verb === "Pickup") return "Pick up " + name;
  if (verb === "Hotbar") return `Put ${name} on the hotbar`;
  if (verb === "Off hotbar") return `Take ${name} off the hotbar`;
  if (verb === "Use") return e.k === T.INVITEM ? `Use ${name}...` : "Use " + name;
  return verb + " " + name;
}

export function held(name) {
  return (S.me?.inv || []).filter((i) => i[1] === name).reduce((a, i) => a + i[2], 0);
}

export function verbRange(verb, e) {
  if (!e || [T.INVITEM, T.RACKITEM, T.PLAYER].includes(e.k)) return 0;
  if (["Examine", "Value", "Inspect", "Walk here", "Cancel"].includes(verb)) return 0;
  if (verb === "Pickup") return 28;
  if (verb === "Talk to") return 48;
  if (verb === "Attack") return 36 + (e.wr || 0);
  if (verb === "Use with") return 36;
  return e.k === T.TILE || e.k === T.INFRONT ? 26 : 36;
}

// The mouse cursor for a verb (cursor.py)
export function cursorOfVerb(verb) {
  const verbs = A.m.cursors?.verbs || {};
  return verbs[String(verb).trim().toUpperCase()] || "hand";
}

export function spellStatus(name) {
  const spell = entityIni(name, "Spell", "");
  if (!spell) return "";
  if (spellIni(spell, "Kind", "Scroll").toUpperCase() === "POTION") return "";
  const level = val(spellIni(spell, "Level", "1"));
  const skill = spellIni(spell, "Skill", "Magic");
  const have = skillLevel(skill);
  if (have < level) return `Needs ${skill} ${lbstr(level)}`;
  const cost = val(spellIni(spell, "Cost", "0"));
  let s = `${lbstr(cost)} mana`;
  const cd = (S.me.cooldowns || {})[spell];
  s += cd > 0 ? `|Ready in ${Math.ceil(cd / 1000)} s` : "|Ready";
  if (S.me.mana < cost) s += " (not enough mana)";
  return s;
}

export function skillLevel(skill) {
  const names = A.m.skills;
  const i = names.findIndex((n) => n.toUpperCase() === String(skill).toUpperCase());
  if (String(skill).toUpperCase() === "HITPOINTS") return S.me.hp;
  if (i < 0) return 0;
  return Math.min(+configMax(), Math.max(1, Math.floor(S.me.xp[i])));
}

function configMax() {
  return Math.max(2, Math.floor(val(configRead("Gameplay", "Skill.Max.Level", "50"))));
}
