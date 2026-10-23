// The mouse and the keyboard (the desktop game's interact.py, its first half): what's under the mouse and what a click
// on it does; walking with the keys. Commands go to the server, which does them.
import { G, S, tileAt, cellOf } from "./state.js";
import { A, tileIni, entityIni, size } from "./assets.js";
import { send } from "./net.js";
import { V, screenToWorld, entityUnder, changeZoom, roofCovers } from "./render.js";
import { fogBlack } from "./sky.js";
import { L, U, openMenu, menuRowAt, hotbarAt, hotbarLabel, invItemAt, boxItemAt, boxRect, boxArrow, boxCloseAt,
  responseAt, responseBoxRect, clockRect, statTileAt, skillOfRow, skillInfo, equipX, equipY, EQUIP_BOX, equipSlotInfo,
  QUESTS_PER_PAGE, QUEST_ROW_TOP, QUEST_ROW_H, questPages, scrollChat, changeMinimapZoom, hoverText, chatTrack } from "./ui.js";
import { T, getVerbs, verbLabel, cursorOfVerb, displayName, spellStatus } from "./verbs.js";
import { J, hit as journalHit, pages as journalPages } from "./journal.js";
import { dayFraction, timeText } from "./sky.js";
import { unlock, playSound } from "./audio.js";
import { pretty, val } from "./util.js";

export const I = { mx: -1, my: -1, keys: new Set(), dir: 0, cursor: "pointer", clickAt: 0, clickKind: "", ui: null,
  hoverEnt: null };

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

function inPlayfield(x, y) { return x >= 0 && y >= 0 && x < L.VW && y < L.VH; }

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
  if (x >= L.VW || S.box.mode) return null;
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
  if (J.open) {
    const h = journalHit(x - (L.W - 1024) / 2, y);
    if (h !== J.hover) J.hover = h;
    I.cursor = "pointer";
    return;
  }
  let msg = "", kind = "INTERFACE";
  I.cursor = "pointer";
  U.hover = null;
  const dx = L.DX;
  if (x >= 1000 + dx && x <= 1020 + dx && y >= 5 && y <= 25) msg = "Leave the game";
  if (x >= 872 + dx && x <= 888 + dx && y >= 147 && y <= 162) msg = "Zoom Out";
  if (x >= 988 + dx && x <= 1000 + dx && y >= 147 && y <= 162) msg = "Zoom In";
  if (x >= L.helpX && x <= L.helpX + 52 && y >= L.helpY && y <= L.helpY + 22) { msg = "Journal and help (H)"; U.hover = "help"; }
  if (S.admin && x >= L.helpX && x <= L.helpX + 52 && y >= L.helpY + 26 && y <= L.helpY + 48) { msg = "Admin panel|give items, set skills"; U.hover = "admin"; }
  const [cx, cy, cw, ch] = clockRect();
  if (!msg && S.clock.on && x >= cx && x < cx + cw && y >= cy && y < cy + ch) msg = timeText(dayFraction(performance.now()));
  const fr = U.fullscreenRect;
  if (fr && x >= fr[0] && x < fr[0] + fr[2] && y >= fr[1] && y < fr[1] + fr[3]) { msg = "Full screen (F11)"; U.hover = "fullscreen"; }
  if (x >= 780 + dx && x <= 794 + dx && y >= 676 && y <= 690) msg = U.chatLine + 4 < S.messages.length ? "Scroll Up" : "<No More>";
  if (x >= 780 + dx && x <= 794 + dx && y >= 750 && y <= 764) msg = U.chatLine === 1 ? "<No More>" : "Scroll Down";
  // the Stats box
  const smx = x - L.VW, smy = y - L.statY;
  U.equipHover = 0; U.skillHover = 0;
  let questHover = 0;
  if (!msg && smx >= 31 && smx <= 194 && smy >= 15 && smy <= 36) {
    if (smx <= 81) msg = "Stats|your skills";
    else if (smx >= 84 && smx <= 135) msg = "Gear|what you are wearing";
    else if (smx >= 138) msg = "Quest log|quests in progress, to start and done";
  }
  if (!msg && U.statsView === 2 && smx >= 30 && smx <= 194 && smy >= QUEST_ROW_TOP && smy < QUEST_ROW_TOP + QUESTS_PER_PAGE * QUEST_ROW_H) {
    const row = Math.floor((smy - QUEST_ROW_TOP) / QUEST_ROW_H) + 1;
    if ((U.questsPage - 1) * QUESTS_PER_PAGE + row <= S.quests.length) { questHover = row; msg = "Click to see it in the journal"; }
  }
  U.questArrow = 0;
  if (U.statsView === 2 && questPages() > 1 && smy >= 41 && smy <= 55) {
    if (smx >= 146 && smx <= 160 && U.questsPage > 1) { msg = "Previous page"; U.questArrow = -1; }
    if (smx >= 182 && smx <= 196 && U.questsPage < questPages()) { msg = "Next page"; U.questArrow = 1; }
  }
  U.questHover = questHover;
  if (!msg && U.statsView === 1) {
    for (let s = 1; s <= 8; s++) {
      if (smx >= equipX(s) && smx < equipX(s) + EQUIP_BOX && smy >= equipY(s) && smy < equipY(s) + EQUIP_BOX) {
        U.equipHover = s;
        msg = equipSlotInfo(s);
      }
    }
  }
  const k = !msg && U.statsView === 0 ? statTileAt(smx, smy) : -1;
  if (k === 0) msg = `${S.me.hp} / ${S.me.max_hp} hitpoints`;
  if (k === 1) msg = `${Math.floor(S.me.mana)} / ${S.me.max_mana} mana`;
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
    if (S.itemInUse) {
      I.cursor = "target";
      msg = hoverText(e || { k: T.INVITEM, u: S.itemInUse });
    } else if (e) {
      const first = getVerbs(e)[0] || "";
      if (first && first !== "Walk here") I.cursor = cursorOfVerb(first);
      msg = hoverText(e);
      if (e.k === T.INVITEM) {
        const st = spellStatus(e.n);
        if (st) msg += "|" + st;
      }
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
    if (h >= 1 && h <= 4) { J.tab = h; J.page = 1; J.focus = ""; }
    if (h === 11) J.page = Math.max(1, J.page - 1);
    if (h === 12) J.page = Math.min(journalPages(), J.page + 1);
    return;
  }
  const dx = L.DX;
  if (left && !U.rcm && scrollBarClick(x, y)) return;
  if (left) {
    if (x >= 1000 + dx && x <= 1020 + dx && y >= 5 && y <= 25) { window.dsUI.openQuit(); return; }
    if (x >= 872 + dx && x <= 888 + dx && y >= 147 && y <= 162) { changeMinimapZoom(0.5); return; }
    if (x >= 988 + dx && x <= 1000 + dx && y >= 147 && y <= 162) { changeMinimapZoom(2); return; }
    if (U.hover === "help") { openJournal(); return; }
    if (U.hover === "admin") { window.dsUI.openAdmin(); return; }
    if (U.hover === "fullscreen") { window.dsUI.toggleFullscreen(); return; }
    if (x >= 780 + dx && x <= 794 + dx && y >= 676 && y <= 690) { scrollChat(1); return; }
    if (x >= 780 + dx && x <= 794 + dx && y >= 750 && y <= 764) { scrollChat(-1); return; }
    const smx = x - L.VW, smy = y - L.statY;
    if (smx >= 31 && smx <= 194 && smy >= 15 && smy <= 36) {
      U.statsView = smx <= 81 ? 0 : smx <= 135 ? 1 : 2;
      U.equipHover = U.questHover = 0;
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
      if (verb === "Use with") chooseVerb("Use with", r.target, r.worldXY[0], r.worldXY[1]);
      else if (verb !== "Cancel") {
        S.itemInUse = 0;
        chooseVerb(verb, r.target, r.worldXY[0], r.worldXY[1]);
      }
    }
    return;
  }
  if (S.box.mode && left) {
    if (boxCloseAt(x, y)) { send({ t: "close" }); return; }
    const arrow = boxArrow(x, y);
    if (arrow) { send({ t: "page", page: S.box.page + arrow }); return; }
    if (U.rbHover) { send({ t: "respond", n: U.rbHover }); return; }
  }
  if (U.skillHover > 0) {
    if (left) send({ t: "skill", i: U.skillHover });
    else S.addLocal(skillInfo(U.skillHover, true), "black");
    return;
  }
  if (U.questArrow) { U.questsPage += U.questArrow; U.questHover = 0; return; }
  if (U.questHover > 0) {
    const q = S.quests[(U.questsPage - 1) * QUESTS_PER_PAGE + U.questHover - 1];
    if (!q) return;
    if (left) {
      J.tab = 3;
      openJournal();
      J.focus = q.title;
      J.page = Math.floor(((U.questsPage - 1) * QUESTS_PER_PAGE + U.questHover - 1) / 7) + 1;
    } else S.addLocal(`${q.title}: ${q.text}`, "black");
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
    if (S.itemInUse) { S.itemInUse = 0; send({ t: "use_cancel" }); return; }
    if (S.box.mode && !clicked) return;
    openMenu(clicked, x, y, [wx, wy]);
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
  if (J.open) {
    J.page = Math.min(journalPages(), Math.max(1, J.page + (dy > 0 ? 1 : -1)));
    return;
  }
  if (y >= L.VH && x < L.VW + 4) { scrollChat(dy < 0 ? 1 : -1); return; }
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
  let d = 0;
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
    const n = { Digit1: 1, Digit2: 2, Digit3: 3, Digit4: 4, Numpad1: 1, Numpad2: 2, Numpad3: 3, Numpad4: 4 }[code];
    if (n) { J.tab = n; J.page = 1; J.focus = ""; }
    if (code === "ArrowLeft") { J.tab = J.tab === 1 ? 4 : J.tab - 1; J.page = 1; }
    if (code === "ArrowRight") { J.tab = J.tab === 4 ? 1 : J.tab + 1; J.page = 1; }
    if (code === "ArrowUp" || code === "PageUp") J.page = Math.max(1, J.page - 1);
    if (code === "ArrowDown" || code === "PageDown") J.page = Math.min(journalPages(), J.page + 1);
    ev.preventDefault();
    return;
  }
  if (code === "Escape") {
    ev.preventDefault();
    if (U.rcm) { U.rcm = null; return; }
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
  sendDir();
}

// ----- the mouse cursor (pictures made by the asset export: cursor.py's)
let shownCursor = "";
export function updateCursor(canvas, now) {
  const hot = A.m.cursors?.hot || {};
  let kind = I.cursor in hot ? I.cursor : "pointer";
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
  const one = `url("/assets/cursors/${kind}_${step}@${px}.png")`, two = `url("/assets/cursors/${kind}_${step}@${px * 2}.png")`;
  canvas.style.cursor = `${one} ${hx} ${hy}, auto`;                        // (every browser)
  canvas.style.cursor = `-webkit-image-set(${one} 1x, ${two} 2x) ${hx} ${hy}, auto`;   // (sharper, where it's known)
  canvas.style.cursor = `image-set(${one} 1x, ${two} 2x) ${hx} ${hy}, auto`;
}
