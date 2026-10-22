"""
lblint.py - a static checker for Liberty BASIC 4 source files.

Liberty BASIC can't syntax-check from the command line, so this catches the
common mistakes before you open the IDE:

  * unbalanced blocks (if/end if, for/next, while/wend, do/loop,
    select/end select, sub/end sub, function/end function)
  * goto/gosub/event-handler targets that don't exist (labels are scoped:
    a sub can only jump to labels inside that same sub)
  * calls to subs that don't exist, or with the wrong number of arguments
  * duplicate sub/function/label definitions
  * exit sub inside a function (and vice-versa)
  * in files with '#TOOL-BEGIN XX sections (Dragon Sword Editor.bas): names a section
    defines (labels, subs, arrays, globals, handles, main-code variables) must start with XX
  * (--locals) variables read inside a sub/function that are never
    assigned there, aren't parameters and aren't declared global. In LB,
    sub/function variables are local, so these are usually bugs.

Usage:  python Dev/lblint.py "Dragon Sword Editor.bas" [more.bas ...] [--locals]
Exit code is 1 if any errors were found.
"""
import re
import sys

KEYWORDS = set("""
and or not xor mod if then else end for to step next while wend do loop until
select case sub function exit call gosub goto return global dim redim print
input line open close as append output binary random len let rem wait scan
nomainwin true false struct calldll ptr long ulong short ushort word char
boolean void double ulong dword handle for is
""".split())

BUILTINS = set("""
abs acs asc asn atn chr$ cos date$ dechex$ eof exp hbmp hexdec hwnd inp
input$ instr int left$ len lof log lower$ max mid$ min mkdir right$ rmdir rnd
sin space$ sqr str$ tab tan time$ trim$ txcount upper$ usingval using val
word$ midipos eval eval$ inkey$ lpt not
""".split())

SPECIAL_VARS = set("""
DefaultDir$ DisplayWidth DisplayHeight WindowWidth WindowHeight UpperLeftX
UpperLeftY BackgroundColor$ ForegroundColor$ TextboxColor$ ListboxColor$
ComboboxColor$ TexteditorColor$ Err Err$ MouseX MouseY Inkey$ Drives$
Platform$ Version$ Joy1x Joy1y Joy1z Joy1button1 Joy1button2 Joy2x Joy2y
Joy2z Joy2button1 Joy2button2 PrintCollate PrintCopies PrinterFont$
PrinterName$ CommandLine$ StartupDir$ ProgramName$ OSVersion$ ComError
ComErrorNumber CommandLine$ SystemFonts$ DialogColor$ WindowHandle
""".split())

# Statement words that can't be used as a variable name ("restore = 5" is a syntax error: RESTORE goes with READ/DATA)
RESERVED_VARS = set("""
restore read data kill files run stop beep cls confirm notice prompt dump timer trace sort seek resume locate out
redim exit unloadbmp loadbmp playwave playmidi stopmidi lprint error on wait end print input open close goto gosub
return call dim global let rem select case if then else for next while wend do loop until sub function scan
""".split())

BLOCK_OPEN = {"if": "end if", "for": "next", "while": "wend", "do": "loop",
              "select": "end select", "sub": "end sub", "function": "end function"}


def strip_comment_and_strings(line):
    """Return (code_without_strings_and_comments, list_of_string_literals)."""
    out, strings, i, n = [], [], 0, len(line)
    while i < n:
        c = line[i]
        if c == '"':
            j = line.find('"', i + 1)
            if j == -1:
                j = n
            strings.append(line[i + 1:j])
            out.append('""')
            i = j + 1
            continue
        if c == "'":
            break
        out.append(c)
        i += 1
    code = "".join(out)
    m = re.match(r"\s*rem\b", code, re.I)
    if m:
        code = ""
    return code, strings


def logical_lines(path):
    """Yield (line_no, code, strings) joining '_' continuations."""
    with open(path, encoding="latin-1") as f:
        raw = f.read().splitlines()
    buf, bufstr, start = "", [], None
    for no, line in enumerate(raw, 1):
        code, strings = strip_comment_and_strings(line)
        if start is None:
            start = no
        stripped = code.rstrip()
        if stripped.endswith(" _") or stripped == "_" or stripped.endswith(",_") or stripped.endswith(")_"):
            buf += stripped[:-1] + " "
            bufstr += strings
            continue
        buf += code
        bufstr += strings
        yield start, buf, bufstr
        buf, bufstr, start = "", [], None
    if buf:
        yield start, buf, bufstr


def split_statements(code):
    # strings were already replaced with "" so splitting on ':' is safe
    return [s.strip() for s in code.split(":")]


class Unit:
    def __init__(self, kind, name, params, line):
        self.kind, self.name, self.params, self.line = kind, name, params, line
        self.labels = {}
        self.jumps = []      # (target, line)
        self.assigned = set()
        self.used = {}       # name -> first line
        self.has_exit_sub = []
        self.has_exit_function = []


IDENT = r"[A-Za-z_][A-Za-z0-9_.]*\$?"


def lint(path, check_locals):
    errors, warnings = [], []
    main = Unit("main", "<main>", [], 1)
    units = [main]
    cur = main
    stack = []          # (block, line)
    subs, funcs = {}, {}
    globals_ = set()
    arrays = set()
    calls = []          # (name, nargs, line)
    handler_refs = []   # (target, line, unit)

    def add_jump(target, no):
        cur.jumps.append((target, no))

    for no, code, strings in logical_lines(path):
        # event handlers / labels inside strings, e.g. "trapclose [Quit]"
        for s in strings:
            if re.search(r"\b(trapclose|when)\b", s, re.I):
                for m in re.finditer(r"\[([^\]\s][^\]]*)\]", s):
                    handler_refs.append((m.group(1), no, cur))
            # graphics queries like "stringwidth? w" or "spritecollides x list$" assign a variable
            for q in re.findall(r"\?\s*(" + IDENT + r")", s):
                cur.assigned.add(q.lower())
            # "stringwidth? text$ widthVar": the second name receives the width
            for q in re.findall(r"stringwidth\?\s*" + IDENT + r"\s+(" + IDENT + r")", s, re.I):
                cur.assigned.add(q.lower())
            m = re.match(r"\s*(spritecollides|getbmp)\s+\S+\s+(" + IDENT + r")\s*$", s, re.I)
            if m and m.group(1).lower() == "spritecollides":
                cur.assigned.add(m.group(2).lower())
        for stmt in split_statements(code):
            if not stmt:
                continue
            low = stmt.lower()
            # label definition
            m = re.match(r"^\[([^\]]+)\]\s*(.*)$", stmt)
            if m:
                name = m.group(1)
                if name.lower() in cur.labels:
                    errors.append((no, "duplicate label [%s] (first at line %d)" % (name, cur.labels[name.lower()])))
                cur.labels[name.lower()] = no
                stmt = m.group(2).strip()
                low = stmt.lower()
                if not stmt:
                    continue
            # keyword must not be the start of a dotted name like next.Cell$
            first = re.match(r"^([A-Za-z]+)(?![\w.$])", low)
            kw = first.group(1) if first else ""

            # controls with [handler] e.g. button #w.b, "x", [Click], UL...
            if re.match(r"^(button|bmpbutton|checkbox|radiobutton|listbox|combobox|textbox|menu|popupmenu|timer|graphicbox|statictext|texteditor|groupbox)(?![\w.$])", low):
                for t in re.findall(r"\[([^\]]+)\]", stmt):
                    handler_refs.append((t, no, cur))
                continue

            if kw == "sub" or kw == "function":
                m = re.match(r"^(sub|function)\s+(" + IDENT + r")\s*(\(?)(.*?)\)?\s*$", stmt, re.I)
                if not m:
                    errors.append((no, "can't parse definition: " + stmt))
                    continue
                if cur is not main:
                    errors.append((no, "%s %s defined inside %s %s (missing end?)" % (kw, m.group(2), cur.kind, cur.name)))
                plist = [p.strip() for p in m.group(4).split(",") if p.strip()]
                plist = [p.split()[0] for p in plist]
                u = Unit(kw, m.group(2), plist, no)
                table = subs if kw == "sub" else funcs
                if m.group(2).lower() in table:
                    errors.append((no, "duplicate %s %s" % (kw, m.group(2))))
                table[m.group(2).lower()] = u
                units.append(u)
                cur = u
                stack.append((kw, no))
                for p in plist:
                    cur.assigned.add(p.lower())
                continue

            if re.match(r"^end\s+(sub|function)\b", low):
                low = re.sub(r"\s+", " ", low)
                want = low.split()[1]
                if not stack or stack[-1][0] != want:
                    errors.append((no, "'end %s' without matching '%s' (open: %s)" % (want, want, stack[-1] if stack else None)))
                    # recover: pop until we find it
                    while stack and stack[-1][0] not in ("sub", "function"):
                        errors.append((stack[-1][1], "unclosed '%s'" % stack[-1][0]))
                        stack.pop()
                if stack:
                    stack.pop()
                cur = main
                continue

            if kw == "global":
                for g in stmt[6:].split(","):
                    g = g.strip()
                    if g:
                        globals_.add(g.lower())
                continue
            if kw in ("dim", "redim"):
                for m in re.finditer(r"(" + IDENT + r")\s*\(", stmt[len(kw):]):
                    arrays.add(m.group(1).lower())
                continue

            if kw == "if":
                mm = re.match(r"^if\b(.*?)\bthen\b(.*)$", stmt, re.I)
                if not mm:
                    errors.append((no, "if without then: " + stmt))
                    continue
                rest = mm.group(2).strip()
                check_condition(mm.group(1), no, errors)
                scan_expr(mm.group(1), cur, no)
                if rest == "":
                    stack.append(("if", no))
                else:
                    # single-line if; handle then [label] / else [label] / nested stmts
                    parts = re.split(r"\belse\b", rest, flags=re.I)
                    for part in parts:
                        part = part.strip()
                        lm = re.match(r"^\[([^\]]+)\]$", part)
                        if lm:
                            add_jump(lm.group(1), no)
                        elif part:
                            handle_simple(part, cur, no, add_jump, calls, errors)
                continue
            if kw == "else":
                if not stack or stack[-1][0] not in ("if",):
                    errors.append((no, "else outside if block"))
                rest = stmt[4:].strip()
                if rest:
                    if rest.lower().startswith("if "):
                        errors.append((no, "'else if' is not supported in Liberty BASIC 4 (use nested if)"))
                    else:
                        handle_simple(rest, cur, no, add_jump, calls, errors)
                continue
            if re.match(r"^end\s+if\b", low):
                pop(stack, "if", no, errors)
                continue
            if re.match(r"^end\s+select\b", low):
                pop(stack, "select", no, errors)
                continue
            if kw == "select":
                stack.append(("select", no))
                scan_expr(stmt[6:], cur, no)
                continue
            if kw == "case":
                if not stack or stack[-1][0] != "select":
                    errors.append((no, "case outside select"))
                continue
            if kw == "for":
                stack.append(("for", no))
                mm = re.match(r"^for\s+(" + IDENT + r")\s*=(.*)$", stmt, re.I)
                if mm:
                    cur.assigned.add(mm.group(1).lower())
                    scan_expr(mm.group(2), cur, no)
                continue
            if kw == "next":
                pop(stack, "for", no, errors)
                continue
            if kw == "while":
                check_condition(stmt[5:], no, errors)
                stack.append(("while", no))
                scan_expr(stmt[5:], cur, no)
                continue
            if kw == "wend":
                pop(stack, "while", no, errors)
                continue
            if kw == "do":
                stack.append(("do", no))
                scan_expr(stmt[2:], cur, no)
                continue
            if kw == "loop":
                pop(stack, "do", no, errors)
                scan_expr(stmt[4:], cur, no)
                continue
            if low in ("end",):
                continue
            handle_simple(stmt, cur, no, add_jump, calls, errors)

    for blk, no in stack:
        errors.append((no, "unclosed '%s'" % blk))

    # jumps
    for u in units:
        for target, no in u.jumps:
            if target.lower() not in u.labels:
                where = "main program" if u is main else "%s %s" % (u.kind, u.name)
                if u is not main and target.lower() in main.labels:
                    errors.append((no, "goto/gosub [%s] from inside %s - labels outside a sub/function are not visible" % (target, where)))
                else:
                    errors.append((no, "goto/gosub target [%s] not found in %s" % (target, where)))
        if u.kind == "function":
            for no in u.has_exit_sub:
                errors.append((no, "'exit sub' inside function %s" % u.name))
        if u.kind == "sub":
            for no in u.has_exit_function:
                errors.append((no, "'exit function' inside sub %s" % u.name))
    for target, no, u in handler_refs:
        if target.lower() in u.labels or target.lower() in main.labels:
            continue
        if target.lower() in subs:
            continue
        errors.append((no, "event handler [%s] not found" % target))

    for name, nargs, no in calls:
        s = subs.get(name.lower())
        if s is None:
            errors.append((no, "call to undefined sub %s" % name))
        elif nargs != len(s.params):
            errors.append((no, "sub %s expects %d argument(s), got %d" % (name, len(s.params), nargs)))

    if check_locals:
        # STRUCTs are global in Liberty BASIC, wherever they are declared
        with open(path, encoding="latin-1") as f:
            globals_ |= set(n.lower() for n in re.findall(r"^\s*struct\s+(" + IDENT + r")", f.read(), re.I | re.M))
        for u in units:
            if u is main:
                continue
            for name, no in u.used.items():
                if name in u.assigned or name in globals_ or name in arrays:
                    continue
                if name == u.name.lower():
                    continue
                warnings.append((no, "%s %s reads '%s' which is never set there (not a param or global)" % (u.kind, u.name, name)))

    return errors, warnings


def pop(stack, want, no, errors):
    if stack and stack[-1][0] == want:
        stack.pop()
        return
    errors.append((no, "'%s' closer without matching open block (innermost open: %s)" % (
        BLOCK_OPEN[want], "%s@%d" % stack[-1] if stack else "none")))
    for i in range(len(stack) - 1, -1, -1):
        if stack[i][0] == want:
            del stack[i:]
            return


def check_condition(cond, no, errors):
    """';' joins strings in print/assignments/arguments, but not at the top level of a condition:
    if a$ = "[";b$;"]" then  -> runtime error. Use + instead."""
    depth = 0
    for c in cond:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == ";" and depth == 0:
            errors.append((no, "';' string join inside a condition - use + instead (LB errors at run time)"))
            return


def count_args(argstr):
    argstr = argstr.strip()
    if not argstr:
        return 0
    depth, n = 0, 1
    for c in argstr:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            n += 1
    return n


def scan_expr(expr, cur, no):
    for m in re.finditer(r"(#?)(" + IDENT + r")(\s*\(?)", expr):
        if m.group(1):
            continue
        name = m.group(2)
        low = name.lower()
        if m.group(3).strip() == "(":
            continue  # function call or array
        if low in KEYWORDS or low in BUILTINS or name in SPECIAL_VARS or low.startswith("_"):
            continue
        if re.match(r"^\d", name) or ".struct" in low:
            continue
        cur.used.setdefault(low, no)


def handle_simple(stmt, cur, no, add_jump, calls, errors):
    low = stmt.lower()
    m = re.match(r"^(goto|gosub)\s*\[([^\]]+)\]", stmt, re.I)
    if m:
        add_jump(m.group(2), no)
        return
    if re.match(r"^exit\s+sub\b", low):
        cur.has_exit_sub.append(no)
        return
    if re.match(r"^exit\s+function\b", low):
        cur.has_exit_function.append(no)
        return
    if low.startswith("exit"):
        return
    m = re.match(r"^call\s+(" + IDENT + r")\s*,?(.*)$", stmt, re.I)
    if m:
        calls.append((m.group(1), count_args(m.group(2)), no))
        scan_expr(m.group(2), cur, no)
        return
    m = re.match(r"^(?:let\s+)?(" + IDENT + r")\s*(\([^=]*\))?\s*=(.*)$", stmt, re.I)
    if m and m.group(1).lower() in RESERVED_VARS:
        errors.append((no, "'%s' is a Liberty BASIC statement word: it can't be a variable name (rename it)" % m.group(1)))
        return
    if m and m.group(1).lower() not in KEYWORDS:
        if not m.group(2):
            cur.assigned.add(m.group(1).lower())
        else:
            scan_expr(m.group(2), cur, no)
        scan_expr(m.group(3), cur, no)
        return
    m = re.match(r"^(input|line\s+input)\s+#?[\w.$]*\s*,?\s*(.*)$", stmt, re.I)
    if m:
        for v in m.group(2).split(","):
            v = v.strip().split("(")[0]
            if v:
                cur.assigned.add(v.lower())
        return
    # print #h, "...? var" style queries assign var
    for q in re.findall(r"\?\s*(" + IDENT + r")", stmt):
        cur.assigned.add(q.lower())
    m = re.match(r"^print\s+#[^,]*,\s*(.*)$", stmt, re.I)
    if m:
        scan_expr(m.group(1), cur, no)
        return
    if re.match(r"^(open|close|loadbmp|unloadbmp|bmpsave|kill|name|notice|playwave|playmidi|stopmidi|timer|files)\b", low):
        if low.startswith("open"):
            return
        scan_expr(re.sub(r"^\w+", "", re.sub(r"#[\w.]+", "", stmt)), cur, no)
        return
    m = re.match(r"^struct\s+(" + IDENT + r")", stmt, re.I)
    if m:
        cur.assigned.add(m.group(1).lower())
        return
    m = re.match(r"^(calldll)\b(.*)$", stmt, re.I)
    if m:
        # calldll #dll, "fn", a as long, ..., result as long  -> last is assigned
        parts = m.group(2).split(",")
        if parts and m.group(1).lower() == "calldll":
            last = parts[-1].strip().split()
            if last:
                cur.assigned.add(last[0].lower())
            for p in parts[2:-1]:
                p = p.strip().split()
                if p and not p[0].startswith('"') and p[0].lower() not in cur.assigned:
                    scan_expr(p[0], cur, no)
        return
    m = re.match(r"^(filedialog|prompt|confirm)\b.*?([A-Za-z_][\w.]*\$?)\s*$", stmt, re.I)
    if m:
        cur.assigned.add(m.group(2).lower())
        return
    m = re.match(r"^files\s+(.*)$", stmt, re.I)
    if m:
        return
    # the rest: open/close/notice/loadbmp/etc. Just collect variable reads.
    scan_expr(re.sub(r"^\w+", "", stmt), cur, no)


CONTROL_BANG = {"button", "bmpbutton", "textbox", "texteditor", "statictext", "groupbox"}
CONTROL_PLAIN = {"checkbox", "radiobutton", "combobox", "listbox"}


def check_enable_disable(path):
    """Buttons, textboxes, statictext... need "!enable"/"!disable" (plain text just becomes their caption);
    checkboxes, radiobuttons, comboboxes and listboxes take plain "enable"/"disable"."""
    errors = []
    with open(path, encoding="latin-1") as f:
        src = f.read()
    types = {}
    for m in re.finditer(r"^\s*(button|bmpbutton|textbox|texteditor|statictext|groupbox|checkbox|radiobutton|combobox|listbox)\s+(#[\w.]+)", src, re.I | re.M):
        types[m.group(2).lower()] = m.group(1).lower()
    for no, line in enumerate(src.splitlines(), 1):
        for m in re.finditer(r'print\s+(#[\w.]+)\s*,\s*"\s*(!?)(enable|disable)\s*"', line, re.I):
            t = types.get(m.group(1).lower())
            if t in CONTROL_BANG and m.group(2) == "":
                errors.append((no, '%s is a %s: use "!%s" (plain text only changes its caption)' % (m.group(1), t, m.group(3))))
            if t in CONTROL_PLAIN and m.group(2) == "!":
                errors.append((no, '%s is a %s: use plain "%s"' % (m.group(1), t, m.group(3))))
    return errors


LB_WINDOW_VARS = {"windowwidth", "windowheight", "upperleftx", "upperlefty", "backgroundcolor$", "foregroundcolor$",
                  "textboxcolor$", "comboboxcolor$", "listboxcolor$", "texteditorcolor$"}


def check_tool_sections(path):
    """Files with '#TOOL-BEGIN <prefix> <name> ... '#TOOL-END <prefix> sections (Dragon Sword Editor.bas): everything a
    section defines that is shared program-wide must start with its prefix, so tools can't clash: labels, subs,
    functions, arrays (dim), globals, structs, window/control handles, and variables set in its main code."""
    errors = []
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()
    if not any(l.startswith("'#TOOL-BEGIN ") for l in lines):
        return errors
    prefix_at, prefix = {}, None
    for no, raw in enumerate(lines, 1):
        if raw.startswith("'#TOOL-BEGIN "):
            prefix = raw.split()[1]
        elif raw.startswith("'#TOOL-END "):
            prefix = None
        prefix_at[no] = prefix
    in_sub = False
    for no, code, _ in logical_lines(path):
        prefix = prefix_at.get(no)
        if prefix is None:
            in_sub = False
            continue
        low = code.strip().lower()
        if re.match(r"(sub|function)\s", low):
            in_sub = True
        elif re.match(r"end\s+(sub|function)\b", low):
            in_sub = False

        def bad(kind, name):
            errors.append((no, "%s %s is in the %s section but doesn't start with %s." % (kind, name, prefix, prefix)))

        m = re.match(r"\s*\[([\w.]+)\]", code)
        if m and not m.group(1).startswith(prefix + "."):
            bad("label", "[%s]" % m.group(1))
        m = re.match(r"\s*(sub|function)\s+([\w.]+\$?)", code, re.I)
        if m and not m.group(2).startswith(prefix + "."):
            bad(m.group(1).lower(), m.group(2))
        m = re.match(r"\s*struct\s+(\w+)", code, re.I)
        if m and not m.group(1).startswith(prefix):
            bad("struct", m.group(1))
        for stmt in split_statements(code):
            st = stmt.strip()
            m = re.match(r"(dim|global)\s+(.*)", st, re.I)
            if m:
                for part in re.split(r",(?![^(]*\))", m.group(2)):
                    name = re.match(r"\s*([\w.]+\$?)", part)
                    if name and not name.group(1).startswith(prefix + "."):
                        bad("array" if m.group(1).lower() == "dim" else "global", name.group(1))
            for h in re.findall(r"(?:\bas\s+|^(?:button|bmpbutton|textbox|texteditor|statictext|groupbox|checkbox|"
                                r"radiobutton|combobox|listbox|graphicbox|menu)\s+)#(\w+)", st, re.I):
                if not h.startswith(prefix):
                    bad("handle", "#" + h)
            if not in_sub:
                m = re.match(r"(?:let\s+|for\s+)?([A-Za-z][\w.]*\$?)\s*=(?!=)", st, re.I)
                if m and m.group(1).lower() not in LB_WINDOW_VARS and m.group(1).lower() not in KEYWORDS \
                        and not m.group(1).startswith(prefix + ".") and not m.group(1).startswith("Bundle."):
                    bad("variable", m.group(1))
    return errors


def check_text_commands(path):
    """A graphics "\\text" command must be the start of its own print: "place 20 30; \\Hello" is a runtime error
    (Bad command), so the text goes in a second print."""
    errors = []
    with open(path, encoding="latin-1") as f:
        for no, line in enumerate(f.read().splitlines(), 1):
            code = line.split("'", 1)[0] if line.lstrip().startswith("'") else line
            if re.search(r'print\s+#[\w.$]+\s*,\s*"[^"]*;\s*\\', code, re.I):
                errors.append((no, 'a "\\text" command after ";" in the same print: put the text in its own print'))
    return errors


def check_sprite_boxes(path):
    """LB 4.04 lets only one window at a time use sprites (any number of its graphicboxes may: the game has them in
    #DS.main and #DS.responsebox). Sprites in a second window stop the program with "sprite DLL already in use", so
    all of a program's addsprite commands must go to one window. Handles held in variables (#handle$) are skipped."""
    errors, first = [], {}
    with open(path, encoding="latin-1") as f:
        for no, line in enumerate(f.read().splitlines(), 1):
            code = "" if line.lstrip().startswith("'") else line
            m = re.search(r'print\s+#([\w.$]+)\s*,\s*"addsprite\b', code, re.I)
            if m and "$" not in m.group(1):
                first.setdefault(m.group(1).split(".")[0].lower(), (no, m.group(1)))
    if len(first) > 1:
        boxes = sorted(first.values())
        for no, handle in boxes[1:]:
            errors.append((no, "sprites in #%s as well as #%s: LB lets only one window use sprites (\"sprite DLL already "
                               "in use\"); draw this one with drawbmp" % (handle, boxes[0][1])))
    return errors


def check_calldll_args(path):
    """calldll arguments must be plain variables, numbers or strings: an expression like 3*w or w-2 is a syntax error."""
    errors = []
    for no, code, _ in logical_lines(path):
        if not re.match(r"\s*calldll\b", code, re.I):
            continue
        for arg in code.split(",")[2:]:
            m = re.match(r"\s*(.+?)\s+as\s+\w+\s*$", arg, re.I)
            if m and not re.fullmatch(r'-?[\w.$]+|"[^"]*"', m.group(1)):
                errors.append((no, "calldll argument '%s' is an expression: put it in a variable first" % m.group(1)))
    return errors


def check_similar_strings(path):
    """LB 4.04 shows a "String variable warning" when one routine (or the main program) has two string variables whose
    names differ only by a trailing s (dir$ and dirs$), in case one is a typo. Rename one so the warning doesn't pop up."""
    errors, scopes, scope = [], [], ("main program", {})
    scopes.append(scope)
    for no, code, _ in logical_lines(path):
        m = re.match(r"\s*(sub|function)\s+([\w.$]+)", code, re.I)
        if m:
            scope = ("%s %s" % (m.group(1).lower(), m.group(2)), {})
            scopes.append(scope)
        for name in re.findall(r"(?<![\w.$])([A-Za-z][\w.]*\$)(?!\s*\()", code):
            scope[1].setdefault(name, no)
        if re.match(r"\s*end\s+(sub|function)\b", code, re.I):
            scope = scopes[0]
    for where, names in scopes:
        for name, no in names.items():
            plural = name[:-1] + "s$"
            if plural in names:
                errors.append((max(no, names[plural]), "%s: %s and %s differ only by an s (LB's String variable warning): rename one"
                               % (where, name, plural)))
    return errors


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_locals = "--locals" in sys.argv
    if not args:
        print(__doc__)
        return 2
    total = 0
    for path in args:
        errors, warnings = lint(path, check_locals)
        errors += check_enable_disable(path)
        errors += check_tool_sections(path)
        errors += check_text_commands(path)
        errors += check_similar_strings(path)
        errors += check_calldll_args(path)
        errors += check_sprite_boxes(path)
        for no, msg in sorted(errors):
            print("%s:%d: error: %s" % (path, no, msg))
        for no, msg in sorted(warnings):
            print("%s:%d: warning: %s" % (path, no, msg))
        print("%s: %d error(s), %d warning(s)" % (path, len(errors), len(warnings)))
        total += len(errors)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
