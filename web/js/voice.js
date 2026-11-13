// A conversation's words appearing a few at a time, and the speaker's greeting as it opens ("Hello!", "Well met.",
// "How can I help?"): one of their kind's, at a pitch of their own. The server says whose voice (Entities.ini
// Voice=, npc_voice), and only with the first page of a talk you started; build_voices.py cuts them from recordings. A notice, a sign or a letter has none,
// and is silent. As the talk closes (its last page, or a shop it opened), they say goodbye in the same voice, if
// their speaker recorded one (Bye_). Options can turn the voices off; the words still come a few at a time (a click
// shows the rest).
import { playVoice } from "./audio.js";

const R = { key: "", n: 0, len: 0, next: 0 };
const greeted = new Map();                             // (who greeted you when: not again on every answer)
let talk = null;                                       // (the talk you started, who's in it: their goodbye at its end)

function pageKey(b) { return `${b.fresh || 0}|${b.tpage || 0}`; }

// the box changing (prev: the one before it): a conversation opening, its speaker greets you, unless they did a
// moment ago; the box closing on a talk you started, they say goodbye
export function greet(prev, b) {
  const now = performance.now();
  if (!b.mode) {
    if (talk && now - talk.at > 1500) playVoice(talk.voice, talk.pitch, "Bye_");   // (not over a hello still going)
    talk = null;
    return;
  }
  if (b.mode !== "Conversation" || !b.voice) return;
  talk = { voice: b.voice, pitch: (b.pitch || 100) / 100, at: now };
  if (prev && prev.mode === "Conversation" && prev.title === b.title) return;
  const last = greeted.get(b.title);
  if (last !== undefined && now - last < 20000) return;
  greeted.set(b.title, now);
  playVoice(talk.voice, talk.pitch);
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
