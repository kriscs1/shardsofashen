"""The game is Shards of Ashen everywhere, not only where players read it (rename_ashen.py did that):

  * the Python package dragonsword\\ is ashen\\ (every import), the editor is "Shards of Ashen Editor.py";
  * the database is ashen.db (server/store.py moves an old dragonsword.db over the first time it starts), its backups
    ashen-YYYYMMDD-HHMM.db;
  * the Docker image is ghcr.io/kriscs1/shards-of-ashen (the workflow pushes the old name too, for servers set up
    before), the compose project, the systemd unit and the Unraid template shards-of-ashen;
  * the Android app is io.github.kriscs1.shardsofashen (a new app: it doesn't update the old one), and the games on
    the network answer as "shardsofashen";
  * the GitHub repository is kriscs1/shards-of-ashen.

Not renamed: the weapon (the Dragon Sword, Dragon_Sword), the archive (dev\\Archive, dev\\Log.txt), the names of the
retired game's own files (Dragon Sword.py, Dragon Sword.bas, Dragon Sword Editor.bas), and the dsengine\\, dsedit\\
folders and DS_ settings (their "ds" is only a prefix now).

Once: a second run does nothing (the old names left after it, in the notes on moving over, are on purpose).

  python -I "dev\\migrate\\rename_shards_of_ashen.py"
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JAVA = "android/app/src/main/java/io/github/kriscs1/"
MOVES = [("dragonsword", "ashen"), ("Dragon Sword Editor.py", "Shards of Ashen Editor.py"),
         ("deploy/dragonsword.service", "deploy/shards-of-ashen.service"),
         ("deploy/unraid/dragonsword.xml", "deploy/unraid/shards-of-ashen.xml"),
         (JAVA + "dragonsword", JAVA + "shardsofashen")]
SKIP = ("dev/Archive/", "dev/Log.txt", "dev/migrate/generated.json", "dev/migrate/rename_shards_of_ashen.py",
        "maps/", "saves/", "web/assets/", "android/app/build/")
TEXT = (".py", ".md", ".txt", ".ini", ".js", ".html", ".css", ".yml", ".yaml", ".xml", ".java", ".gradle",
        ".properties", ".bat", ".service", ".env", ".json", ".toml", ".cfg")
SUBS = [   # (pattern, replacement), in order: the specific first
    (r"images: ghcr\.io/\$\{\{ github\.repository_owner \}\}/dragonsword\n",           # (the old name too, for now)
     "images: |\n            ghcr.io/${{ github.repository_owner }}/shards-of-ashen\n"
     "            ghcr.io/${{ github.repository_owner }}/dragonsword\n"),
    (r"kriscs1/dragonsword", "kriscs1/shards-of-ashen"),
    (r"(ghcr\.io/(?:kriscs1|<you>)/)dragonsword", r"\1shards-of-ashen"),
    (r"packages/container/dragonsword", "packages/container/shards-of-ashen"),
    (r"io\.github\.kriscs1\.dragonsword", "io.github.kriscs1.shardsofashen"),
    (r"dragonsword-android", "shards-of-ashen-android"),
    (r"dragonsword\.db", "ashen.db"),
    (r"dragonsword-(YYYYMMDD|%Y%m%d)", r"ashen-\1"),
    (r'startswith\("dragonsword-"\)', 'startswith(("ashen-", "dragonsword-"))'),
    (r"deploy/dragonsword\.service", "deploy/shards-of-ashen.service"),
    (r"deploy/unraid/dragonsword\.xml", "deploy/unraid/shards-of-ashen.xml"),
    (r"my-DragonSword\.xml", "my-ShardsOfAshen.xml"),
    (r"\bDragonSword\b", "ShardsOfAshen"),
    (r"dragonsword\.example\.com", "ashen.example.com"),
    (r'"game": "dragonsword"', '"game": "shardsofashen"'),
    (r'answer\.get\("game"\) == "dragonsword"', 'answer.get("game") == "shardsofashen"'),
    (r'answer\["game"\] == "dragonsword"', 'answer["game"] == "shardsofashen"'),
    (r'"dragonsword"\.equals', '"shardsofashen".equals'),
    (r"DRAGONSWORD\?", "SHARDSOFASHEN?"),
    (r'"dragonsword:', '"shardsofashen:'),
    (r'name="dragonsword"', 'name="shardsofashen"'),
    (r'getLogger\("dragonsword\.', 'getLogger("ashen.'),
    (r"\bfrom dragonsword\b", "from ashen"),
    (r"\bimport dragonsword\b", "import ashen"),
    (r'p\("dragonsword", ', 'p("ashen", '),
    (r'"dragonsword/\*\*"', '"ashen/**"'),
    (r"COPY dragonsword dragonsword", "COPY ashen ashen"),
    (r"(/srv/|~/|/opt/|/var/lib/|/mnt/user/appdata/)dragonsword", r"\1shards-of-ashen"),
    (r"(StateDirectory=|User=|--now |name: |-p |-t )dragonsword\b", r"\1shards-of-ashen"),
    (r"dragonsword-test", "shards-of-ashen-test"),
    (r"image: dragonsword:local", "image: shards-of-ashen:local"),
    (r"`dragonsword/`", "`ashen/`"),
    (r"\bdragonsword([\\/]{1,2})", r"ashen\1"),
    (r"\(e\.g\. dragonsword\)", "(e.g. shards-of-ashen)"),
    (r"yourname/dragonsword\.git", "yourname/shards-of-ashen.git"),
    (r"(?<![Tt]he )Dragon Sword v2\b", "Shards of Ashen"),
    (r"(?<![Tt]he )(?<!old )Dragon Sword(?!(?: Editor)?\.bas|\.py|,)(?= Editor|'s| server| game| for | is | on |: |\b)",
     "Shards of Ashen"),
]


def at(*p):
    return os.path.join(ROOT, *p)


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True)


def move():
    for old, new in MOVES:
        if os.path.exists(at(old)) and not os.path.exists(at(new)):
            r = git("mv", old, new)
            if r.returncode:
                raise SystemExit("git mv %s: %s" % (old, r.stderr))
            print("moved", old, "->", new)


def rename_text(t):
    for pat, rep in SUBS:
        t = re.sub(pat, rep, t)
    return t


def texts():
    files = git("ls-files").stdout.splitlines()
    for f in files:
        if f.startswith(SKIP) or not (f.endswith(TEXT) or os.path.basename(f) in ("Dockerfile", "VERSION")):
            continue
        path = at(f)
        if not os.path.isfile(path):
            continue
        raw = open(path, "rb").read()
        enc = "utf-8"
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            enc = "cp1252"
            t = raw.decode(enc)
        crlf = "\r\n" in t
        new = rename_text(t.replace("\r\n", "\n"))
        if crlf:
            new = new.replace("\n", "\r\n")
        if new != t:
            open(path, "wb").write(new.encode(enc))
            print("updated", f)


def main():
    if os.path.isdir(at("ashen")) and not os.path.isdir(at("dragonsword")):
        print("Shards of Ashen everywhere already: nothing to do (the old names left now are on purpose).")
        return
    move()
    texts()


if __name__ == "__main__":
    main()
