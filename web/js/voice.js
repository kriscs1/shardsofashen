// A conversation's words appearing a few at a time, murmured in the speaker's voice. The server says whose voice
// (Entities.ini Voice=, and a pitch of their own: npc_voice); build_voices.py makes them. A notice, a sign or a
// letter has none, and its words appear just the same, silently. With voices off (Options) it's all at once, as ever.
import { O, playVoice } from "./audio.js";

const GAP = { Ghost: 210, Beast: 260, Croak: 190 };    // (the slower voices: the least between two syllables, ms)
const R = { key: "", n: 0, len: 0, next: 0, said: 0, run: 0 };
const letter = (c) => /[\p{L}\p{N}]/u.test(c);

function pageKey(b) { return `${b.fresh || 0}|${b.tpage || 0}`; }

// how many of a page's characters show now (text: the page's lines, one "\n" between), murmuring as they come
export function revealed(b, text, now) {
  const key = pageKey(b);
  if (key !== R.key) Object.assign(R, { key, n: 0, next: now, said: 0, run: 0 });
  R.len = text.length;
  if (!O.voices) R.n = text.length;
  const cps = Math.max(45, text.length / 2.2);         // (a long page comes quicker: none takes more than a few seconds)
  if (now - R.next > 250) R.next = now;                // (back from another tab, or a slow frame: on from here)
  while (R.n < text.length && now >= R.next) {
    const c = text[R.n++];
    R.next += 1000 / cps + (".!?".includes(c) ? 240 : ",;:".includes(c) ? 100 : 0);
    if (!letter(c)) { R.run = 0; continue; }
    // (a syllable as a word starts, and another every few letters of a long one)
    if (R.run++ % 4 === 0 && b.voice && now - R.said >= (GAP[b.voice] || 110)) {
      R.said = now;
      playVoice(b.voice, (b.pitch || 100) / 100);
    }
  }
  return R.n;
}

// still coming? (a click then shows the rest, rather than answering)
export function revealing(b) { return b.mode === "Conversation" && R.key === pageKey(b) && R.n < R.len; }

export function showAll() { R.n = R.len; }
