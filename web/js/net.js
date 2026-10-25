// The connection to the server: JSON messages over a WebSocket (each server message is one message or a list of them).

export const N = { ws: null, open: false, onMessage: null, onClose: null, onOpen: null };

export function connect() {
  const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
  const ws = new WebSocket(url);
  N.ws = ws;
  ws.addEventListener("open", () => {             // (only the current socket counts: not one that's been replaced)
    if (N.ws !== ws) return;
    N.open = true;
    if (N.onOpen) N.onOpen();
  });
  ws.addEventListener("message", (ev) => {
    let data;
    try { data = JSON.parse(ev.data); } catch (e) { return; }
    const list = Array.isArray(data) ? data : [data];
    for (const m of list) if (N.onMessage) N.onMessage(m);
  });
  ws.addEventListener("close", () => {
    if (N.ws !== ws) return;
    N.open = false;
    if (N.onClose) N.onClose();
  });
  return ws;
}

export function send(msg) {
  if (N.ws && N.open) N.ws.send(JSON.stringify(msg));
}
