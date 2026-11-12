// The connection to the server: JSON messages over a WebSocket (each server message is one message or a list of them).
import { note } from "./clientlog.js";

export const N = { ws: null, open: false, onMessage: null, onClose: null, onOpen: null };

export function connect() {
  // (beside the page: the game's own at /ws, or a friend's game through the central server at /play/<game>/ws)
  const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host +
    location.pathname.replace(/[^/]*$/, "") + "ws";
  const ws = new WebSocket(url);
  N.ws = ws;
  ws.addEventListener("open", () => {             // (only the current socket counts: not one that's been replaced)
    if (N.ws !== ws) return;
    N.open = true;
    note("Connected");
    if (N.onOpen) N.onOpen();
  });
  ws.addEventListener("message", (ev) => {
    let data;
    try { data = JSON.parse(ev.data); } catch (e) { return; }
    const list = Array.isArray(data) ? data : [data];
    for (const m of list) if (N.onMessage) N.onMessage(m);
  });
  ws.addEventListener("close", (ev) => {
    if (N.ws !== ws) return;
    note(`The connection closed (${ev.code}${ev.reason ? ": " + ev.reason : ""}${N.open ? "" : ", before it opened"})`);
    N.open = false;
    if (N.onClose) N.onClose();
  });
  return ws;
}

export function send(msg) {
  if (N.ws && N.open) N.ws.send(JSON.stringify(msg));
}
