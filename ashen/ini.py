"""INI files read and written the way Windows' GetPrivateProfileString / WritePrivateProfileString do it (the original
game used those): sections and keys match whatever their case, keys and values are trimmed, the first one wins, a value
in quotes loses them, and ";" only starts a comment at the beginning of a line. Parsed files are cached and read again
when they change on disk."""
import os
import time


def read_text(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


class _Parsed:
    def __init__(self, path):
        self.path = path
        self.sections = {}  # UPPER section -> {UPPER key: value}
        self.order = []  # (section name, [(key, value)...]) in file order
        self.mtime = None
        self.checked = 0.0
        self.load()

    def load(self):
        self.sections = {}
        self.order = []
        try:
            st = os.stat(self.path)
            self.mtime = (st.st_mtime_ns, st.st_size)
            text = read_text(self.path)
        except OSError:
            self.mtime = None
            return
        current = None
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("["):
                end = s.find("]")
                name = s[1:end].strip() if end > 0 else s[1:].strip()
                key = name.upper()
                if key in self.sections:
                    current = None  # Windows uses the first section of that name
                    continue
                current = {}
                self.sections[key] = current
                self.order.append((name, []))
                continue
            if current is None:
                continue
            eq = s.find("=")
            if eq < 1:
                continue
            k = s[:eq].strip()
            v = s[eq + 1:].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if k.upper() not in current:
                current[k.upper()] = v
            self.order[-1][1].append((k, v))

    def fresh(self):
        now = time.monotonic()
        if now - self.checked < 0.5:
            return
        self.checked = now
        try:
            st = os.stat(self.path)
            m = (st.st_mtime_ns, st.st_size)
        except OSError:
            m = None
        if m != self.mtime:
            self.load()


_cache = {}


def _parsed(path):
    p = _cache.get(path)
    if p is None:
        p = _Parsed(path)
        _cache[path] = p
    else:
        p.fresh()
    return p


def read(section, key, default, path):
    """Read.From.Ini$"""
    if not path:
        return default.strip() if isinstance(default, str) else default
    p = _parsed(path)
    sec = p.sections.get(section.upper())
    if sec is None:
        return default.strip()
    v = sec.get(key.upper())
    if v is None:
        return default.strip()
    return v


def section(section_name, path):
    """Every key=value of a section in file order: [(key, value)...] (Load.Ini.Section)."""
    if not path or not os.path.exists(path):
        return []
    p = _parsed(path)
    for name, items in p.order:
        if name.upper() == section_name.upper():
            return list(items)
    return []


def sections(path):
    """[(section name, [(key, value)...])...] for the whole file."""
    if not path or not os.path.exists(path):
        return []
    return list(_parsed(path).order)


def forget(path=None):
    if path is None:
        _cache.clear()
    else:
        _cache.pop(path, None)


def write(section_name, key, value, path):
    """Write.To.Ini: changes (or adds) one key, keeping the rest of the file as it is."""
    value = str(value)
    lines = []
    if os.path.exists(path):
        lines = read_text(path).splitlines()
    sec_start = -1
    sec_end = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("["):
            end = s.find("]")
            name = s[1:end].strip() if end > 0 else s[1:].strip()
            if sec_start >= 0:
                sec_end = i
                break
            if name.upper() == section_name.upper():
                sec_start = i
    if sec_start < 0:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append("[" + section_name + "]")
        lines.append(key + "=" + value)
    else:
        done = False
        last_key = sec_start
        for i in range(sec_start + 1, sec_end):
            s = lines[i].strip()
            eq = s.find("=")
            if eq >= 1 and not s.startswith(";"):
                last_key = i
                if s[:eq].strip().upper() == key.upper():
                    lines[i] = key + "=" + value
                    done = True
                    break
        if not done:
            lines.insert(last_key + 1, key + "=" + value)
    with open(path, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    forget(path)
