// A conversation's words appearing a few at a time, and the speaker's greeting as it opens ("Hello!", "Well met.",
// "How can I help?"): one of their kind's, at a pitch of their own. The server says whose voice (Entities.ini
// Voice=, npc_voice); build_voices.py cuts them from recordings of people. A notice, a sign or a letter has none,
// and is silent. Options can turn the greetings off; the words still come a few at a time (a click shows the rest).
import { playVoice } from "./audio.js";

const R = { key: "", n: 0, len: 0, next: 0 };
const greeted = new Map();                             // (who greeted you when: not again on every answer)

function pageKey(b) { return `${b.fresh || 0}|${b.tpage || 0}`; }

// a conversation opening (prev: the box before it): its speaker greets you, unless they did a moment ago
export function greet(prev, b) {
  if (b.mode !== "Conversation" || !b.voice) return;
  if (prev && prev.mode === "Conversation" && prev.title === b.title) return;
  const now = performance.now(), last = greeted.get(b.title);
  if (last !== undefined && now - last < 20000) return;
  greeted.set(b.title, now);
  playVoice(b.voice, (b.pitch || 100) / 100);
}

// how many of a page's characters show now (text: the page's lines, one "\n" between)
export function revealed(b, text, now) {
  const key = pageKey(b);
  if (key !== R.key) Object.assign(R, { key, n: 0, next: now });
  R.len = text.length;
  const cps = Math.max(55, text.length / 2);           // (a long page comes quicker: none takes more than a few seconds)
  if (now - R.next > 250) R.next = now;                // (back from another tab, or a slow frame: on from here)
  while (R.n < text.length && now >= R.next) {
    const c = text[R.n++];
    R.next += 1000 / cps + (".!?".includes(c) ? 200 : ",;:".includes(c) ? 80 : 0);
  }
  return R.n;
}

// still coming? (a click then shows the rest, rather than answering)
export function revealing(b) { return b.mode === "Conversation" && R.key === pageKey(b) && R.n < R.len; }

export function showAll() { R.n = R.len; }
