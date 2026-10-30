// The verbs on things, as the desktop game's interact.py has them: the right-click menu (the first verb is the
// left-click), the label shown, how close you walk first. The server works them out again before it does one.
import { S } from "./state.js";
import { tileIni, entityIni, A, spellIni, configRead, shardsIni, OWN } from "./assets.js";
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
  return e.dn || pretty(e.n);           // (its own name, if the map gives it one)
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
    if (canSteal(e)) addVerb(v, "Steal");
    if ((S.me.traps || []).some((k) => k[0] === e.map && k[1] === e.tx && k[2] === e.ty && !k[3])) addVerb(v, "Disarm");
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
      const words = entityIni(e.n, "Use.Words", "");
      const sp = spellTaught(e.n);                // (a scroll that would teach you something: Learn, not Cast)
      addVerbs(v, sp && spellRank(sp) < scrollRank(e.n) ? words.split(",").map((w) => (w.trim() === "Cast" ? "Learn" : w)).join(",") : words);
      addVerb(v, equipVerb(e.n));
      addVerb(v, "Use");
      if (dismantleWorth(e.n)) addVerb(v, "Dismantle");
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
    if (e.lk) { addVerb(v, "Pick Lock"); if (!e.ib) addVerb(v, "Break Open"); }   // (a chest locked for you: locks.py)
    if (canSteal(e)) addVerb(v, "Steal");
    addVerb(v, "Examine");
  } else if (t === T.NPC && entityIni(e.n, "Vehicle", "0").trim() === "1") {
    // (a horse and cart, carts.py: hail it, get in; riding it, get out where it stops)
    if (S.me && S.me.ride === e.u) v = String(e.uw || "").includes("Get In") && !String(e.uw).includes("Hail") ?
      ["Get Out", "Examine"] : ["Examine"];
    else addVerbs(v, e.uw || "Examine");
  } else if (t === T.NPC && e.f) {
    addVerb(v, "Attack");
    addVerbs(v, e.uw);
    addVerb(v, "Examine");
  } else if (t === T.NPC) {
    for (const w of String(e.uw || "").split(",")) if (trim(w) && trim(w).toUpperCase() !== "ATTACK") addVerb(v, w);
    if (canPickpocket(e)) addVerb(v, "Pickpocket");             // (sneaking: thieving.py)
    addVerb(v, "Talk to");
    addVerb(v, "Examine");
  } else if (t === T.PLAYER) {
    // (a click on someone walks you there; Whisper is in the right-click menu. In the arena, a click attacks.)
    v = e.pvp ? ["Attack", "Whisper", "Examine"] : ["Walk here", "Whisper", "Examine"];
    const party = (S.me && S.me.party) || [];        // (together.py: a party of up to five)
    if (party.includes(e.n)) addVerb(v, "Leave party");
    else if (!party.length || party.length < 5) addVerb(v, "Invite to party");
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

// What a potion or spell scroll does, from data/Spells.ini: "+5 spell damage, 2 min" (shown on Drink / Cast)
export function spellSummary(spell, rank = 0) {
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
  } else if (eff === "HEAL") parts.push(`heals ${spellAt(spell, "Heal", "", rank)}`);
  else if (eff === "BOLT" || eff === "AREA") parts.push(`${spellAt(spell, "Damage", "", rank)} damage`);
  else if (eff === "TELEPORT" || eff === "HOME") parts.push("teleports you");
  else if (eff === "GRASP") parts.push("pulls a thing to you, from afar");
  if (n("Shards")) parts.push(`+${n("Shards")} Shards`);
  return parts.join(", ");
}

export function verbLabel(verb, e) {
  if (!e || verb === "Walk here" || verb === "Cancel") return verb;
  const name = displayName(e);
  if (verb === "Learn" && e.k === T.INVITEM) {
    const spell = spellTaught(e.n), rank = scrollRank(e.n);
    return `Learn ${spellTitle(spell, rank)} (for good: ${pretty(spellIni(spell, "Skill", "Channeling"))} ${lbstr(val(spellAt(spell, "Level", "1", rank)))})`;
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
  if (verb === "Make" && e.short) return `Make ${name} (needs ${pretty(S.box.skill)} level ${e.short})`;
  if (verb === "Make" && e.missing) return `Make ${name} (not enough ${e.missing})`;
  if (verb === "Pickup") return "Pick up " + name;
  if (verb === "Hotbar") return `Put ${name} on the hotbar`;
  if (verb === "Off hotbar") return `Take ${name} off the hotbar`;
  if (verb === "Use") return e.k === T.INVITEM ? `Use ${name}...` : "Use " + name;
  return verb + " " + name;
}

// ----- spells, learnt from their scrolls (S.me.spells), cast for Shards
export function spellTaught(name) {
  const spell = entityIni(name, "Spell", "").trim();
  return spell && spellIni(spell, "Kind", "Scroll").toUpperCase() !== "POTION" ? spell : "";
}

export function spellRank(spell) { return (S.me?.spells || {})[spell] || 0; }

export function knowsSpell(spell) { return spellRank(spell) > 0; }

export function scrollRank(name) { return Math.max(1, val(entityIni(name, "Rank", "1"))); }

export function spellTitle(spell, rank) {
  if (spell === OWN.spell && S.me?.own) return S.me.own.title;      // (the spell you wrote: ownspell.py)
  return pretty(spell) + ({ 2: " II", 3: " III", 4: " IV" }[rank || spellRank(spell)] || "");
}

// A spell's value at a rank (yours, if none's given): Shards.ini [Upgrade.<Spell>] Key.<rank>, the nearest lower
// rank's, else its Spells.ini Key
// A spell's Shards a cast as you are now: its Cost less what your Channeling saves (shards.py channeled_cost)
export function castCost(spell, rank = 0) {
  const cost = val(spellAt(spell, "Cost", "0", rank));
  if (cost <= 0) return 0;
  const num = (k, d) => { const v = shardsIni("Channeling", k, ""); return v.trim() !== "" ? val(v) : d; };
  const saving = Math.min(num("Saving.Max", 30), Math.max(0, skillLevel("Channeling") - 1) * num("Saving.Per.Level", 1.5)) / 100;
  return Math.max(Math.min(cost, num("Min.Cost", 1)), Math.round(cost * (1 - saving)));
}

export function spellAt(spell, key, dflt = "", rank = 0) {
  for (let r = rank || Math.max(1, spellRank(spell)); r > 1; r--) {
    const v = shardsIni(`Upgrade.${spell}`, `${key}.${r}`, "");     // (Shards.ini: a rank's values)
    if (v !== "") return v;
  }
  return spellIni(spell, key, dflt);
}

// What dismantling it gives (shards.py dismantle_worth): gear, or a scroll you know already; 0: it can't be
export function dismantleWorth(name) {
  if (name === "Shard" || entityIni(name, "Droppable", "1").trim() === "0") return 0;
  const value = val(entityIni(name, "Value", "0"));
  const sp = spellTaught(name);
  let per;
  if (sp) {
    if (spellRank(sp) < scrollRank(name)) return 0;
    per = val(shardsIni("Dismantle", "Scroll", "10"));
  } else if (equipVerb(name)) per = val(shardsIni("Dismantle", equipVerb(name) === "Wield" ? "Weapon" : "Armour", "25"));
  else return 0;
  return Math.max(1, Math.floor(value / Math.max(1, per)));
}

export function cooldownLeft(spell) {
  // (ms till it's ready: as the server last said, less the time since - "me" isn't sent while it counts down)
  const cd = (S.me?.cooldowns || {})[spell] || 0;
  return Math.max(0, cd - (performance.now() - (S.boostAt || 0)));
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
// (sneaking: a townsperson's pocket, a shop's shelves - as the server's thieving.py can_pickpocket, can_steal)
function sneaking() { return S.me && S.me.stance === "Sneaking"; }
function canPickpocket(e) {
  return sneaking() && !e.f && String(e.uw || "").includes("Talk to") && !entityIni(e.n, "Calls", "").trim() &&
    entityIni(e.n, "Vehicle", "0").trim() !== "1" && entityIni(e.n, "Flees", "0").trim() !== "1";
}
export function canSteal(e) {
  return sneaking() && ((e.k === T.TILE && /^Shelf_Goods/.test(e.n || "")) || (e.k === T.STATICOBJECT && /^Valuables/.test(e.n || "")));
}

export function cursorOfVerb(verb) {
  const verbs = A.m.cursors?.verbs || {};
  return verbs[String(verb).trim().toUpperCase()] || "hand";
}

// Skills renamed or made one (dsengine/renames.py SKILL_NAMES): an old name means the skill it's part of now
const SKILL_NAMES = { MAGIC: "Channeling", SMITHING: "Crafting", CONSTRUCTION: "Homesteading", FARMING: "Homesteading",
  POTION_MAKING: "Alchemy", HERBLORE: "Alchemy" };

export function skillLevel(skill) {
  const names = A.m.skills;
  const s = SKILL_NAMES[String(skill).toUpperCase()] || String(skill);
  const i = names.findIndex((n) => n.toUpperCase() === s.toUpperCase());
  if (String(skill).toUpperCase() === "HITPOINTS") return S.me.hp;
  if (i < 0) return 0;
  const now = (S.me.skill_now || [])[i];                  // (drained or boosted for a while: as it is now)
  return now ?? Math.min(+configMax(), Math.max(1, Math.floor(S.me.xp[i])));
}

function configMax() {
  return Math.max(2, Math.floor(val(configRead("Gameplay", "Skill.Max.Level", "25"))));
}
