"""Small helpers that behave like the Liberty BASIC built-ins and utility functions the original game used
(val, word$, Field$, str$, Replace.Text$, Strip.Digits$, Wildcard.Match ...), plus the game clocks."""
import datetime
import math
import random
import re
import time

_NUM = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")


def val(text):
    """LB val(): the number at the start of text (0 if there is none)."""
    if isinstance(text, (int, float)):
        return text
    if text is None:
        return 0
    m = _NUM.match(str(text))
    if not m:
        return 0
    s = m.group(1)
    try:
        if "." in s or "e" in s or "E" in s:
            f = float(s)
            return int(f) if f.is_integer() and abs(f) < 1e15 else f
        return int(s)
    except ValueError:
        return 0


def lbstr(x):
    """LB str$(): whole numbers without a decimal point, others without trailing zeros."""
    if isinstance(x, str):
        return x
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, int):
        return str(x)
    if x != x or x in (float("inf"), float("-inf")):
        return "0"
    if float(x).is_integer() and abs(x) < 1e15:
        return str(int(x))
    s = ("%.9f" % x).rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


def word(text, n, delim=" "):
    """LB word$(): the nth item of text split on delim, empty items skipped ("" if there is none)."""
    if text is None or n < 1:
        return ""
    parts = [p for p in str(text).split(delim) if p != ""]
    if n <= len(parts):
        return parts[n - 1]
    return ""


def field(text, n, delim):
    """Field$(): like word$ but empty fields are kept (a<TAB><TAB>b has an empty field 2)."""
    if text is None:
        return ""
    parts = str(text).split(delim)
    if 1 <= n <= len(parts):
        return parts[n - 1]
    return ""


def word_count(text):
    return len([p for p in str(text).split(" ") if p != ""])


def trim(text):
    return str(text).strip(" ")


def strip_digits(name):
    """Tree001 -> Tree"""
    if len(name) > 3 and name[-3:].isdigit():
        return name[:-3]
    return name


def is_number(text):
    text = trim(text)
    if text == "":
        return False
    digits = 0
    for i, c in enumerate(text):
        if c in "0123456789":
            digits += 1
        elif c == "." or (i == 0 and c in "+-"):
            continue
        else:
            return False
    return digits > 0


def random_number(a, b):
    """A random whole number between a and b inclusive."""
    a = int(a)
    b = int(b)
    if b < a:
        a, b = b, a
    return int(random.random() * (b - a + 1)) + a


def rnd():
    return random.random()


def parse_quantity(quantity):
    """A number, or a range "min-max" for a random quantity."""
    quantity = trim(quantity)
    if quantity.find("-") > 0:
        return random_number(val(word(quantity, 1, "-")), val(word(quantity, 2, "-")))
    return val(quantity)


def apply_change(current, change):
    """change is =Q, +Q, -Q or Q"""
    change = trim(str(change))
    if change[:1] == "=":
        return val(change[1:])
    if change[:1] == "+":
        return current + val(change[1:])
    if change[:1] == "-":
        return current - val(change[1:])
    return val(change)


def wildcard_match(text, pattern):
    """pattern may start and/or end with *"""
    start = end = False
    if pattern[:1] == "*":
        pattern = pattern[1:]
        start = True
    if pattern[-1:] == "*":
        pattern = pattern[:-1]
        end = True
    if start and end:
        return pattern in text or pattern == ""
    if start:
        return text.endswith(pattern)
    if end:
        return text.startswith(pattern)
    return text == pattern


DISPLAY_NAMES = {}      # name (upper) -> what the player sees it called: Entities.ini / Tiles.ini Display.Name=


def pretty(name):
    """Pine_Tree001 -> Pine Tree; or its Display.Name, if it has one (its own name stays what scripts and saves use)"""
    if DISPLAY_NAMES:
        shown = DISPLAY_NAMES.get(str(name).upper()) or DISPLAY_NAMES.get(strip_digits(name).upper())
        if shown:
            return shown
    return strip_digits(name).replace("_", " ")


def wrap_text(text, width):
    """Inserts | line breaks so lines are at most width characters."""
    text = text.replace("\\", "|")
    out = []
    length = 0
    for c in text:
        if c == "|":
            length = 0
        if c == " " and length >= width:
            c = "|"
            length = 0
        elif c != "|":
            length += 1
        out.append(c)
    return "".join(out)


def distance(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)


# ----- Clocks. Clock.MS/Clock.Seconds count from 1 Jan 1901 like LB's date$("days"), in UTC: the clocks going back
# an hour in autumn never makes a wait an hour longer. (Saves from before were in local time: local_offset() is how
# far they're out.)
_EPOCH = datetime.date(1901, 1, 1)
_UTC_1901 = (datetime.date(1970, 1, 1) - _EPOCH).days * 86400


def clock_seconds():
    return int(time.time()) + _UTC_1901


def clock_ms():
    return int(time.time() * 1000) + _UTC_1901 * 1000


def local_offset():
    """Seconds local time is ahead of UTC here, now."""
    return int(datetime.datetime.now().astimezone().utcoffset().total_seconds())


def frame_ms():
    return int(time.perf_counter() * 1000)


def seconds_today():
    now = datetime.datetime.now()
    return now.hour * 3600 + now.minute * 60 + now.second


# ----- Arithmetic for Get.Value CALCULATION and conditions (LB eval of + - * / ^ and brackets)
class _Calc:
    def __init__(self, text):
        self.tokens = re.findall(r"\d+\.?\d*|\.\d+|[-+*/^()]", text)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self):
        t = self.peek()
        self.pos += 1
        return t

    def expr(self):
        v = self.term()
        while self.peek() in ("+", "-"):
            if self.take() == "+":
                v += self.term()
            else:
                v -= self.term()
        return v

    def term(self):
        v = self.power()
        while self.peek() in ("*", "/"):
            if self.take() == "*":
                v *= self.power()
            else:
                d = self.power()
                v = v / d if d != 0 else 0
        return v

    def power(self):
        v = self.unary()
        if self.peek() == "^":
            self.take()
            v = v ** self.power()
        return v

    def unary(self):
        if self.peek() == "-":
            self.take()
            return -self.unary()
        if self.peek() == "+":
            self.take()
            return self.unary()
        return self.atom()

    def atom(self):
        t = self.take()
        if t == "(":
            v = self.expr()
            self.take()
            return v
        if t is None:
            raise ValueError("end")
        return float(t)


def safe_eval(expression):
    """Evaluates arithmetic; anything else is returned as text (so bad input can't crash)."""
    expression = trim(expression)
    if expression == "" or is_number(expression):
        return expression
    digits = 0
    for i, c in enumerate(expression):
        if c not in "0123456789.+-*/()^ ":
            return expression
        if c in "0123456789":
            digits += 1
        if c == "/" and val(trim(expression[i + 1:])) == 0:
            return expression
    if digits == 0:
        return expression
    depth = 0
    prev = "("
    dots = 0
    for i, c in enumerate(expression):
        if c == " ":
            continue
        if c in "0123456789.":
            if prev in "0123456789." and expression[i - 1] == " ":
                return expression
            if prev == ")":
                return expression
            if prev not in "0123456789.":
                dots = 0
            if c == ".":
                dots += 1
            if dots > 1:
                return expression
        else:
            if c == "(":
                if prev in "0123456789.)":
                    return expression
                depth += 1
            if c == ")":
                if prev in "(+-*/^":
                    return expression
                depth -= 1
                if depth < 0:
                    return expression
            if c in "*/^" and prev in "(+-*/^":
                return expression
            if c in "+-" and prev in "+-":
                return expression
        prev = c
    if depth != 0 or prev in "+-*/^(":
        return expression
    try:
        result = _Calc(expression).expr()
    except Exception:
        return expression
    return lbstr(result)
