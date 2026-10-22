"""Reading a MIDI file well enough to start it part-way through: pygame can't seek in MIDI, so to carry on with a
piece where it left off (back outside after a house) the game plays a copy that starts there: the instruments,
controllers and tempo as they were at that moment, then the rest of the piece."""
import struct

_cache = {}


def _vlq(data, i):
    n = 0
    while True:
        b = data[i]
        i += 1
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            return n, i


def _put_vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


class Midi:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        if data[:4] != b"MThd":
            raise ValueError("not a MIDI file")
        hlen = struct.unpack(">I", data[4:8])[0]
        self.format, ntracks, self.division = struct.unpack(">HHH", data[8:14])
        if self.division & 0x8000:
            raise ValueError("SMPTE timing isn't supported")
        i = 8 + hlen
        self.tracks = []                                   # [(tick, message bytes)] each, ticks absolute
        for _ in range(ntracks):
            if data[i:i + 4] != b"MTrk":
                break
            tlen = struct.unpack(">I", data[i + 4:i + 8])[0]
            self.tracks.append(self._track(data[i + 8:i + 8 + tlen]))
            i += 8 + tlen
        tempos = sorted((t, struct.unpack(">I", b"\0" + m[3:6])[0]) for tr in self.tracks for t, m in tr
                        if m[0] == 0xFF and m[1] == 0x51)
        if not tempos or tempos[0][0] > 0:
            tempos = [(0, 500000)] + tempos                 # (the default tempo until the first one)
        self.tempos = tempos
        self.last_tick = max((tr[-1][0] for tr in self.tracks if tr), default=0)
        self.length_ms = self.ms_at(self.last_tick)

    @staticmethod
    def _track(d):
        out, i, tick, status = [], 0, 0, 0
        while i < len(d):
            delta, i = _vlq(d, i)
            tick += delta
            b = d[i]
            if b == 0xFF:                                   # meta
                n, j = _vlq(d, i + 2)
                out.append((tick, bytes(d[i:j + n])))
                i = j + n
            elif b in (0xF0, 0xF7):                         # sysex
                n, j = _vlq(d, i + 1)
                out.append((tick, bytes(d[i:j + n])))
                i = j + n
            else:
                if b & 0x80:
                    status = b
                    i += 1
                size = 1 if status & 0xF0 in (0xC0, 0xD0) else 2
                out.append((tick, bytes([status]) + bytes(d[i:i + size])))
                i += size
        return out

    def ms_at(self, tick):
        ms, last_t, tempo = 0.0, 0, 500000
        for t, tp in self.tempos:
            if t >= tick:
                break
            ms += (t - last_t) * tempo / 1000.0 / self.division
            last_t, tempo = t, tp
        return ms + (tick - last_t) * tempo / 1000.0 / self.division

    def tick_at(self, ms):
        done, last_t, tempo = 0.0, 0, 500000
        for t, tp in self.tempos:
            step = (t - last_t) * tempo / 1000.0 / self.division
            if done + step > ms:
                break
            done += step
            last_t, tempo = t, tp
        return int(last_t + (ms - done) * 1000.0 * self.division / tempo)

    def from_ms(self, ms):
        """The piece's bytes as a MIDI file starting ms into it."""
        start = self.tick_at(ms)
        out = [b"MThd", struct.pack(">IHHH", 6, self.format, len(self.tracks), self.division)]
        for tr in self.tracks:
            state = {}                                      # what's set before the start: kept, in order
            for t, m in tr:
                if t >= start:
                    break
                s = m[0]
                if s == 0xFF and m[1] in (0x51, 0x58, 0x59, 0x03):
                    state[("meta", m[1])] = m
                elif s & 0xF0 == 0xC0:
                    state[("prog", s & 0x0F)] = m
                elif s & 0xF0 == 0xB0:
                    state[("cc", s & 0x0F, m[1])] = m
                elif s & 0xF0 == 0xE0:
                    state[("bend", s & 0x0F)] = m
            body = b"".join(b"\0" + m for m in state.values())
            prev, ended = start, False
            for t, m in tr:
                if t < start:
                    continue
                body += _put_vlq(t - prev) + m
                prev = t
                ended = ended or (m[0] == 0xFF and m[1] == 0x2F)
            if not ended:
                body += b"\0\xFF\x2F\0"
            out += [b"MTrk", struct.pack(">I", len(body)), body]
        return b"".join(out)


def load(path):
    if path not in _cache:
        try:
            _cache[path] = Midi(path)
        except (OSError, ValueError, IndexError, struct.error):
            _cache[path] = None
    return _cache[path]
