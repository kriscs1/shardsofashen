// The mouse and the keyboard (the desktop game's interact.py, its first half): what's under the mouse and what a click
// on it does; walking with the keys (or a phone's stick). Commands go to the server, which does them. A phone's taps
// come here as left clicks and its long presses as right clicks (main.js).
import { G, S, tileAt, cellOf } from "./state.js";
import { A, tileIni, entityIni, size } from "./assets.js";
import { send } from "./net.js";
import { V, screenToWorld, entityUnder, entitiesUnder, changeZoom, roofCovers, markClick } from "./render.js";
import { fogBlack } from "./sky.js";
import { L, U, stoneAt, openMenu, menuRowAt, hotbarAt, hotbarLabel, invItemAt, boxItemAt, boxRect, boxArrow, boxCloseAt,
  responseAt, responseBoxRect, clockRect, statTileAt, skillOfRow, skillInfo, equipX, equipY, EQUIP_BOX, equipSlotInfo,
  spellTileAt, spellHoverText, knownSpells, scrollChat, changeMinimapZoom, hoverText, chatTrack, toggleTracked, minimapHit,
  chatArrow, vitalsAt, stanceAt, nextStance, STANCE_WORDS, statsShown, touchButtonAt, bagRect, journalOrigin, joyCentre, JOY, wmZoomAt, wmButtonAt,
  wmInBox } from "./ui.js";
import { M } from "./mobile.js";
import { T, getVerbs, verbLabel, cursorOfVerb, displayName } from "./verbs.js";
import { J, hit as journalHit, pages as journalPages, spellClick, friendClick, journalQuests, TABS } from "./journal.js";
import { dayFraction, timeText } from "./sky.js";
import { unlock, playSound } from "./audio.js";
import { pretty, val } from "./util.js";

export const I = { mx: -1, my: -1, keys: new Set(), dir: 0, cursor: "pointer", clickAt: 0, clickKind: "", ui: null,
  hoverEnt: null, joyDir: 0 };

// ----- what's under the mouse
function tileEntity(wx, wy, worldOnly) {
  const t = tileAt(S.mapZ, wx, wy);
  if (!t || t.tx < 1 || t.ty < 1 || t.tx > G.xt || t.ty > G.yt) return null;
  if (roofCovers(wx, wy) || fogBlack(wx, wy)) return null;
  const [tile, decor] = cellOf(t.m, t.tx, t.ty);
  const name = decor || tile;
  if (!name || name === "Black001") return null;
  const lock = S.locks.get(t.m.name + "," + t.tx + "," + t.ty);
  const e = { k: T.TILE, n: name, x: t.m.ox + (t.tx - 1) * G.tw, y: t.m.oy + (t.ty - 1) * G.th, w: G.tw, h: G.th,
    misc: tileIni(name, "Show.Name", "0"), uw: tileIni(name, "Use.Words", ""), map: t.m.name, tx: t.tx, ty: t.ty,
    offMap: t.m.name !== S.mapName };
  if (lock !== undefined) e.lock = lock;
  return e;
}

function inPlayfield(x, y) { return x >= 0 && y >= 0 && x < L.VW && y < L.VH && !overTouchUI(x, y); }

function inRect(x, y, r) { return !!r && x >= r[0] && x < r[0] + r[2] && y >= r[1] && y < r[1] + r[3]; }

export function overTouchUI(x, y) {
  // (a phone's interface over the world: the bag, the chat log, the minimap, the buttons, the stick)
  if (!M.on) return false;
  if (M.bag && inRect(x, y, bagRect())) return true;
  if (M.chat && y >= L.chatY && x < L.chatW) return true;
  if (Math.hypot(x - L.mmX, y - L.mmY) <= L.mmSize / 2 + 4) return true;
  if (touchButtonAt(x, y)) return true;
  const [jx, jy] = joyCentre();
  return !S.box.mode && !M.chat && !M.bag && Math.hypot(x - jx, y - jy) <= JOY.r + 8;
}

function under(x, y) {
  // The front-most thing under the mouse: the interface first, then the world
  if (y < 0 || y >= L.VH || x < 0 || x > L.W) return null;
  if (S.box.mode) {
    const it = boxItemAt(x, y);
    if (it) return it;
  }
  const inv = invItemAt(x, y);
  if (inv) return inv;
  const br = boxRect(), rr = responseBoxRect();
  if (br && x >= br[0] && x < br[0] + br[2] && y >= br[1] && y < br[1] + br[3]) return null;
  if (rr && x >= rr[0] && x < rr[0] + rr[2] && y >= rr[1] && y < rr[1] + rr[3]) return null;
  if (x >= L.VW || S.box.mode || overTouchUI(x, y)) return null;
  const [wx, wy] = screenToWorld(x, y);
  const e = entityUnder(wx, wy);
  if (e) {
    if (e.self) return null;
    return e;
  }
  return tileEntity(wx, wy);
}

export function mouseMove(x, y) {
  I.mx = x; I.my = y;
  U.mx = x; U.my = y;                     // (the item boxes light up the slot under the mouse)
  if (J.open) {
    const [jx, jy] = journalOrigin();
    const h = journalHit(x - jx, y - jy);
    if (h !== J.hover) J.hover = h;
    I.cursor = "pointer";
    return;
  }
  if (U.worldMap && x < L.VW && y < L.VH) {        // (the world map over the view: nothing under it to walk to)
    I.cursor = "pointer";
    I.hoverEnt = null;
    U.stoneHover = U.worldMap === "stones" ? stoneAt(x, y) : "";
    return;
  }
  let msg = "", kind = "INTERFACE";
  I.cursor = "pointer";
  U.hover = null;
  const dx = L.DX, desk = !M.on;
  if (desk && x >= 1000 + dx && x <= 1020 + dx && y >= 5 && y <= 25) msg = "Leave the game";
  if (desk && x >= 872 + dx && x <= 888 + dx && y >= 147 && y <= 162) msg = "Zoom Out";
  if (desk && x >= 988 + dx && x <= 1000 + dx && y >= 147 && y <= 162) msg = "Zoom In";
  if (desk && x >= L.helpX && x <= L.helpX + 52 && y >= L.helpY && y <= L.helpY + 22) { msg = "Journal and help (H)"; U.hover = "help"; }
  if (desk && S.admin && x >= L.helpX && x <= L.helpX + 52 && y >= L.helpY + 26 && y <= L.helpY + 48) { msg = "Admin panel|give items, set skills"; U.hover = "admin"; }
  const tb = M.on ? touchButtonAt(x, y) : "";
  if (tb) {
    U.hover = "touch:" + tb;
    msg = { bag: "Bag|your stats, gear, quests and pack", chat: "Chat|the messages, and a line to say something",
      journal: "Journal and help", menu: "Menu|options, and leaving the game", admin: "Admin panel" }[tb];
  }
  if (!msg && stanceAt(x, y)) {
    U.hover = "stance";
    msg = `#${STANCE_WORDS[S.me.stance || ""]}|~${M.on ? "Tap" : "Click (or Q)"}: ${nextStance() || "stand easy"}`;
  }
  const vit = !msg ? vitalsAt(x, y) : "";
  if (vit === "level") msg = "Your level|the best of your fighting skills";
  if (vit === "hp") msg = `${S.me.hp} / ${S.me.max_hp} hitpoints`;
  if (vit === "shards") msg = `#${S.me.shards} Shards|Spent to cast spells and wake shardstones|~Absorbed from the Shard Remnants beasts leave, found in chests and the earth, and given for quests`;
  const [cx, cy, cw, ch] = clockRect();
  if (!msg && S.clock.on && x >= cx && x < cx + cw && y >= cy && y < cy + ch) msg = timeText(dayFraction(performance.now()));
  const fr = U.fullscreenRect;
  if (fr && x >= fr[0] && x < fr[0] + fr[2] && y >= fr[1] && y < fr[1] + fr[3]) { msg = "Full screen (F11)"; U.hover = "fullscreen"; }
  if (!msg && minimapHit(x, y)) msg = M.on ? "#World map|~Tap: the whole map, its places named" : "#World map|~Click (or M): the whole map, its places named";
  const arrow = desk || M.chat ? chatArrow(x, y) : 0;
  if (arrow === 1) msg = U.chatLine + 4 < S.messages.length ? "Scroll Up" : "<No More>";
  if (arrow === -1) msg = U.chatLine === 1 ? "<No More>" : "Scroll Down";
  // the Stats box
  const smx = statsShown() ? x - L.statX : -999, smy = y - L.statY;
  U.equipHover = 0; U.skillHover = 0; U.spellHover = 0;
  if (!msg && smx >= 31 && smx <= 194 && smy >= 15 && smy <= 36) {
    if (smx <= 81) msg = "Stats|your skills";
    else if (smx >= 84 && smx <= 135) msg = "Gear|what you are wearing";
    else if (smx >= 138) msg = "Channeling|the spells you know: cast them from here";
  }
  if (!msg && U.statsView === 2) {
    const i = spellTileAt(smx, smy);
    if (i) { U.spellHover = i; msg = spellHoverText(knownSpells()[i - 1]); }
  }
  if (!msg && U.statsView === 1) {
    for (let s = 1; s <= 8; s++) {
      if (smx >= equipX(s) && smx < equipX(s) + EQUIP_BOX && smy >= equipY(s) && smy < equipY(s) + EQUIP_BOX) {
        U.equipHover = s;
        msg = equipSlotInfo(s);
      }
    }
  }
  const k = !msg && U.statsView === 0 ? statTileAt(smx, smy) : -1;
  if (k >= 2) { U.skillHover = skillOfRow(k - 1); if (U.skillHover) msg = skillInfo(U.skillHover, false); }
  // the ActionBox
  U.rbHover = 0;
  if (S.box.mode) {
    if (boxCloseAt(x, y)) msg = "Close";
    if (boxArrow(x, y) === -1) msg = "Previous page";
    if (boxArrow(x, y) === 1) msg = "Next page";
    U.rbHover = responseAt(x, y);
    if (U.rbHover) msg = S.box.responses[U.rbHover - 1];
  }
  // the right-click menu
  if (U.rcm) {
    U.rcm.hi = menuRowAt(x, y);
    if (U.rcm.hi) {
      msg = U.rcm.labels[U.rcm.hi - 1];
      I.cursor = cursorOfVerb(U.rcm.verbs[U.rcm.hi - 1]);
    }
    setQuick(msg, "ENTITY");
    return;
  }
  U.hotHover = !msg ? hotbarAt(x, y) : -1;
  if (U.hotHover >= 0) { setQuick(hotbarLabel(U.hotHover), "INTERFACE"); I.hoverEnt = null; return; }
  const e = under(x, y);
  I.hoverEnt = e;
  if (!msg) {
    kind = "ENTITY";
    const world = inPlayfield(x, y) && !S.box.mode;
    I.cursor = world && S.me.input ? "walk" : "pointer";
    if (S.spellReady) {                          // (a spell held ready: who it's for)
      I.cursor = "target";
      msg = hoverText(e || { k: T.INVITEM });
    } else if (S.itemInUse) {
      I.cursor = "target";
      msg = hoverText(e || { k: T.INVITEM, u: S.itemInUse });
    } else if (e) {
      const first = getVerbs(e)[0] || "";
      if (first && first !== "Walk here") I.cursor = cursorOfVerb(first);
      msg = hoverText(e);
    }
  }
  setQuick(msg, kind);
}

function setQuick(msg, kind) { U.qm = msg; U.qmKind = kind; }

// ----- clicks
function targetOf(e) {
  if (!e) return null;
  if (e.k === T.TILE) return { k: "tile" };
  if (e.k === T.INFRONT) return { k: "infront" };
  if (e.k === T.INVITEM) return { k: "inv", uid: e.u };
  if (e.k === T.RACKITEM) return { k: "rack", i: e.i };
  if (e.k === T.PLAYER) return { k: "player", uid: e.u };
  return { k: "ent", uid: e.u };
}

export function chooseVerb(verb, e, wx, wy) {
  if (verb === "Cancel" || !verb) return;
  if (!e || (e.k !== T.INVITEM && e.k !== T.RACKITEM)) markClick(verb, e, wx, wy);   // (seen at once: render.js)
  if (verb === "Walk here") {
    if (e && e.lock !== undefined && e.k === T.TILE && !e.offMap) {
      send({ t: "verb", verb, x: wx, y: wy });
      return;
    }
    send({ t: "verb", verb, x: wx, y: wy });
    return;
  }
  if (verb === "Whisper" && e && e.k === T.PLAYER) { window.dsUI.openChat("/w " + e.n + " "); return; }
  if (verb === "Sell on the market" || verb === "Set price") {        // (the market: ask the price first)
    const target = targetOf(e);
    window.dsUI.askPrice(e, verb === "Sell on the market", (price, qty) => send({ t: "verb", verb, target, x: wx, y: wy, price, qty }));
    return;
  }
  const msg = { t: "verb", verb, target: targetOf(e), x: wx, y: wy };
  if (verb === "Use with") msg.item = S.itemInUse;
  if (verb === "Use with" || verb !== "Use") S.itemInUse = verb === "Use with" ? 0 : S.itemInUse;
  send(msg);
}

export function mouseDown(button, x, y) {
  unlock();
  mouseMove(x, y);
  I.clickAt = performance.now();
  I.clickKind = I.cursor;
  const left = button === 0, right = button === 2;
  if (!left && !right) return;
  if (J.open) {
    if (!left) return;
    const h = J.hover;
    if (h === 10) { closeJournal(); return; }
    if (h >= 1 && h <= TABS) { J.tab = h; J.page = 1; J.focus = ""; }
    if (spellClick(h)) return;
    if (friendClick(h)) return;
    if (h >= 100 && h < 107) {                     // (a quest: follow it, its place marked on the maps)
      const q = journalQuests()[(J.page - 1) * 7 + h - 100];
      if (q) toggleTracked(q.title);
      return;
    }
    if (h === 11) J.page = Math.max(1, J.page - 1);
    if (h === 12) J.page = Math.min(journalPages(), J.page + 1);
    return;
  }
  const dx = L.DX, desk = !M.on;
  if (U.worldMap) {                                // (the world map's open: a click puts it away)
    const zb = left ? wmButtonAt(x, y) : "";
    if (zb) { wmZoomAt(zb === "in" ? 1.5 : 1 / 1.5); return; }
    if (x < L.VW && y < L.VH) {
      const k = U.worldMap === "stones" ? stoneAt(x, y) : "";   // (the travel map: a stone picked, or a way home)
      if (k === "home") send({ t: "stone_home" });
      else if (k === "visit") send({ t: "stone_visit" });
      else if (k) send({ t: "stone_go", k });
      U.worldMap = false;
      return;
    }
  }
  if (left && !U.rcm && (desk || M.chat) && scrollBarClick(x, y)) return;
  if (left && !U.rcm && S.me && stanceAt(x, y)) { send({ t: "stance", stance: nextStance() }); return; }
  if (left && M.on && !U.rcm) {
    const tb = touchButtonAt(x, y);
    if (tb === "bag") { M.bag = !M.bag; M.chat = false; if (M.bag && S.box.mode === "Conversation") send({ t: "close" }); return; }
    if (tb === "chat") { M.chat = !M.chat; M.bag = false; return; }
    if (tb === "journal") { openJournal(); return; }
    if (tb === "menu") { window.dsUI.openQuit(); return; }
    if (tb === "admin") { window.dsUI.openAdmin(); return; }
    if (M.chat && y >= L.chatY && x < L.chatW && !chatArrow(x, y)) { window.dsUI.openChat(); return; }   // (the log: say something)
    if (M.bag && !inRect(x, y, bagRect()) && !minimapHit(x, y)) { M.bag = false; return; }   // (off the bag: it shuts)
  }
  if (left) {
    if (desk && x >= 1000 + dx && x <= 1020 + dx && y >= 5 && y <= 25) { window.dsUI.openQuit(); return; }
    if (desk && x >= 872 + dx && x <= 888 + dx && y >= 147 && y <= 162) { changeMinimapZoom(0.5); return; }
    if (desk && x >= 988 + dx && x <= 1000 + dx && y >= 147 && y <= 162) { changeMinimapZoom(2); return; }
    if (U.hover === "help") { openJournal(); return; }
    if (minimapHit(x, y)) { U.worldMap = !U.worldMap; return; }
    if (U.hover === "admin") { window.dsUI.openAdmin(); return; }
    if (U.hover === "fullscreen") { window.dsUI.toggleFullscreen(); return; }
    const arrow = desk || M.chat ? chatArrow(x, y) : 0;
    if (arrow) { scrollChat(arrow); return; }
    const smx = statsShown() ? x - L.statX : -999, smy = y - L.statY;
    if (smx >= 31 && smx <= 194 && smy >= 15 && smy <= 36) {
      U.statsView = smx <= 81 ? 0 : smx <= 135 ? 1 : 2;
      U.equipHover = U.spellHover = 0;
      return;
    }
  }
  if (U.hotHover >= 0 && !U.rcm) {
    if (left) send({ t: "hotbar", k: U.hotHover });
    else send({ t: "hotbar_remove", k: U.hotHover });
    return;
  }
  if (U.rcm) {
    const r = U.rcm;
    U.rcm = null;
    if (left && r.hi > 0) {
      const verb = r.verbs[r.hi - 1];
      const target = r.targets[r.hi - 1] || r.target;
      if (verb === "Use with") chooseVerb("Use with", target, r.worldXY[0], r.worldXY[1]);
      else if (verb !== "Cancel") {
        S.itemInUse = 0;
        chooseVerb(verb, target, r.worldXY[0], r.worldXY[1]);
      }
    }
    return;
  }
  if (S.box.mode && left) {
    if (boxCloseAt(x, y)) { send({ t: "close" }); return; }
    const arrow = boxArrow(x, y);
    if (arrow) { send({ t: "page", page: S.box.page + arrow }); return; }
    if (U.rbHover) {
      const b = S.box;
      if (b.mode === "Conversation" && (b.tpage || 0) < (b.tpages || 1) - 1) { b.tpage = (b.tpage || 0) + 1; return; }
      send({ t: "respond", n: U.rbHover });
      return;
    }
  }
  if (U.skillHover > 0) {
    if (left) send({ t: "skill", i: U.skillHover });
    else S.addLocal(skillInfo(U.skillHover, true), "black");
    return;
  }
  if (U.spellHover > 0) {                          // (Channeling: cast it, or on or off the hotbar)
    const spell = knownSpells()[U.spellHover - 1];
    if (!spell) return;
    if (left) {
      S.spellReady = "";
      send({ t: "cast", spell });
      if (M.on) M.bag = false;                     // (the phone: the bag out of the way, to see who it's at)
    } else send({ t: "hotbar_spell", spell });
    return;
  }
  if (U.equipHover > 0) {
    if (left) send({ t: "unequip", slot: U.equipHover });
    else S.addLocal(equipSlotInfo(U.equipHover), "black");
    return;
  }
  if (!S.me.input) return;
  let clicked = I.hoverEnt;
  if (clicked && clicked.k === T.TILE && clicked.offMap) clicked = null;
  const [wx, wy] = screenToWorld(x, y);
  if (right) {
    if (S.spellReady) { S.spellReady = ""; return; }
    if (S.itemInUse) { S.itemInUse = 0; send({ t: "use_cancel" }); return; }
    if (S.box.mode && !clicked) return;
    const behind = clicked && clicked.k !== T.INVITEM && clicked.k !== T.TILE ?
      entitiesUnder(wx, wy).filter((e) => e !== clicked && e.k !== T.INFRONT && e.k !== T.TILE && e.k !== T.PLAYER) : [];
    openMenu(clicked, x, y, [wx, wy], behind);
    return;
  }
  if (S.spellReady) {                              // (the spell held ready: cast at what's clicked, or let go)
    const spell = S.spellReady;
    S.spellReady = "";
    if (clicked && clicked.k !== T.INVITEM) send({ t: "cast", spell, target: targetOf(clicked), x: wx, y: wy });
    return;
  }
  if (S.itemInUse) {
    if (!clicked || (clicked.k === T.INVITEM && clicked.u === S.itemInUse)) { S.itemInUse = 0; send({ t: "use_cancel" }); }
    else chooseVerb("Use with", clicked, wx, wy);
    return;
  }
  if (!clicked) {
    if (inPlayfield(x, y) && !S.box.mode) chooseVerb("Walk here", null, wx, wy);
    return;
  }
  const verbs = getVerbs(clicked);
  if (verbs.length) chooseVerb(verbs[0], clicked, wx, wy);
}

let dragging = "";
function scrollBarClick(x, y) {
  const [tx, ty, tw, th] = chatTrack();
  if (x >= tx && x < tx + tw && y >= ty && y < ty + th) { dragging = "chat"; scrollTo(y); return true; }
  return false;
}

function scrollTo(y) {
  const [, ty, , th] = chatTrack();
  const most = Math.max(0, S.messages.length - 5);
  if (most <= 0) return;
  const frac = Math.min(1, Math.max(0, (y - ty) / th));
  U.chatLine = 1 + Math.round((1 - frac) * most);
}

export function mouseDrag(y, held) {
  if (!held) { dragging = ""; return; }
  if (dragging === "chat") scrollTo(y);
}

export function wheel(dy, x, y) {
  if (U.worldMap) {                                // (the world map: in or out, about the mouse)
    if (wmInBox(x, y)) wmZoomAt(dy < 0 ? 1.25 : 0.8, x, y);
    return;
  }
  if (J.open) {
    J.page = Math.min(journalPages(), Math.max(1, J.page + (dy > 0 ? 1 : -1)));
    return;
  }
  if ((M.on ? M.chat : true) && y >= L.chatY && x < L.chatR + 20) { scrollChat(dy < 0 ? 1 : -1); return; }
  const br = boxRect();
  if (br && S.box.mode !== "Conversation" && x >= br[0] && x < br[0] + br[2] && y >= br[1] && y < br[1] + br[3]) {
    const page = Math.min(S.box.pages, Math.max(1, S.box.page + (dy < 0 ? -1 : 1)));
    if (page !== S.box.page) send({ t: "page", page });
    return;
  }
  if (inPlayfield(x, y) && !S.box.mode) changeZoom(dy < 0 ? 1 : -1);
}

// ----- the keyboard
const DIRS = { ArrowUp: 1, KeyW: 1, ArrowRight: 2, KeyD: 2, ArrowDown: 4, KeyS: 4, ArrowLeft: 8, KeyA: 8 };

function sendDir() {
  let d = I.joyDir;
  for (const k of I.keys) d |= DIRS[k] || 0;
  if ((d & 5) === 5) d -= 5;
  if ((d & 10) === 10) d -= 10;
  if (d !== I.dir) {
    I.dir = d;
    send({ t: "move", dir: d });
  }
}

export function openJournal() {
  J.open = true;
  J.page = 1;
  M.panX = M.panY = 0;
  J.hover = 0;
  J.focus = "";
  U.rcm = null;
  S.journal = null;
  send({ t: "journal" });
}

export function closeJournal() { J.open = false; }

export function keyDown(ev) {
  unlock();
  const code = ev.code;
  if (code === "F11") { ev.preventDefault(); window.dsUI.toggleFullscreen(); return; }
  if (J.open) {
    if (code === "Escape" || code === "KeyH" || code === "F1") { ev.preventDefault(); closeJournal(); return; }
    const n = { Digit1: 1, Digit2: 2, Digit3: 3, Digit4: 4, Digit5: 5, Digit6: 6, Digit7: 7, Numpad1: 1, Numpad2: 2,
      Numpad3: 3, Numpad4: 4, Numpad5: 5, Numpad6: 6, Numpad7: 7 }[code];
    if (n) { J.tab = n; J.page = 1; J.focus = ""; }
    if (code === "ArrowLeft") { J.tab = J.tab === 1 ? TABS : J.tab - 1; J.page = 1; }
    if (code === "ArrowRight") { J.tab = J.tab === TABS ? 1 : J.tab + 1; J.page = 1; }
    if (code === "ArrowUp" || code === "PageUp") J.page = Math.max(1, J.page - 1);
    if (code === "ArrowDown" || code === "PageDown") J.page = Math.min(journalPages(), J.page + 1);
    ev.preventDefault();
    return;
  }
  if (code === "KeyM") { ev.preventDefault(); U.worldMap = !U.worldMap; return; }
  if (code === "Escape") {
    ev.preventDefault();
    if (U.worldMap) { U.worldMap = false; return; }
    if (U.rcm) { U.rcm = null; return; }
    if (S.spellReady) { S.spellReady = ""; return; }
    if (S.itemInUse) { S.itemInUse = 0; send({ t: "use_cancel" }); return; }
    if (S.box.mode) { send({ t: "close" }); return; }
    window.dsUI.openQuit();
    return;
  }
  if (code === "Enter" || code === "NumpadEnter") { ev.preventDefault(); window.dsUI.openChat(); return; }
  if (code === "KeyH" || code === "F1") { ev.preventDefault(); openJournal(); return; }
  if (code === "Equal" || code === "NumpadAdd") { if (!S.box.mode) changeZoom(1); return; }
  if (code === "Minus" || code === "NumpadSubtract") { if (!S.box.mode) changeZoom(-1); return; }
  if (!S.me || !S.me.input || S.box.mode) return;
  if (code === "KeyQ") { send({ t: "stance", stance: nextStance() }); return; }
  const hk = { Digit1: 0, Digit2: 1, Digit3: 2, Digit4: 3, Digit5: 4, Numpad1: 0, Numpad2: 1, Numpad3: 2, Numpad4: 3, Numpad5: 4 }[code];
  if (hk !== undefined) { send({ t: "hotbar", k: hk }); return; }
  if (code in DIRS) {
    ev.preventDefault();
    I.keys.add(code);
    sendDir();
  }
}

export function keyUp(ev) {
  if (ev.code in DIRS) {
    I.keys.delete(ev.code);
    sendDir();
  }
}

export function releaseKeys() {
  I.keys.clear();
  I.joyDir = 0;
  sendDir();
}

export function stick(dx, dy) {
  // A phone's stick pushed (dx, dy) from its middle: the way to walk, of eight (none near the middle)
  let d = 0;
  if (Math.hypot(dx, dy) > JOY.r * 0.3) {
    const a = Math.atan2(dy, dx), oct = Math.round(a / (Math.PI / 4));     // (-4..4: 0 is right, 2 down)
    d = { 0: 2, 1: 6, 2: 4, 3: 12, 4: 8, "-4": 8, "-3": 9, "-2": 1, "-1": 3 }[oct];
  }
  if (d && (!S.me || !S.me.input || S.box.mode)) d = 0;
  if (d !== I.joyDir) { I.joyDir = d; sendDir(); }
}

// ----- the mouse cursor (pictures made by the asset export: cursor.py's)
let shownCursor = "";
export function updateCursor(canvas, now) {
  const hot = A.m.cursors?.hot || {};
  let kind = I.cursor in hot && !U.worldMap ? I.cursor : "pointer";   // (the world map open: just the pointer)
  let step = 0;
  const cm = A.m.cursors?.click_ms || 220;
  const t = (now - I.clickAt) / cm;
  if (t >= 0 && t < 1) {
    kind = I.clickKind in hot ? I.clickKind : kind;
    step = 1 + Math.min(6, Math.floor(t * 7));
  }
  // (its size: Options > Mouse pointer size, in screen points; a picture twice that for sharp high-DPI screens)
  const sizes = A.m.cursors?.sizes || [22];
  const px = sizes.includes(U.cursorSize) ? U.cursorSize : (sizes.includes(22) ? 22 : sizes[0]);
  const key = kind + "_" + step + "@" + px;
  if (key === shownCursor) return;
  shownCursor = key;
  const unit = A.m.cursors?.unit || 32;
  const [hx, hy] = (hot[kind] || [2, 2]).map((v) => Math.round(v * px / unit));
  const v = A.m.cursors?.drawn ? `?v=${A.m.cursors.drawn}` : "";   // (redrawn cursors: fetched anew, not from a cache)
  const one = `url("/assets/cursors/${kind}_${step}@${px}.png${v}")`,
    two = `url("/assets/cursors/${kind}_${step}@${px * 2}.png${v}")`;
  canvas.style.cursor = `${one} ${hx} ${hy}, auto`;                        // (every browser)
  canvas.style.cursor = `-webkit-image-set(${one} 1x, ${two} 2x) ${hx} ${hy}, auto`;   // (sharper, where it's known)
  canvas.style.cursor = `image-set(${one} 1x, ${two} 2x) ${hx} ${hy}, auto`;
}
