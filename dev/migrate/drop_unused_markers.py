"""Takes away the place Ids build_estforlan.py once put by every townsperson it moved (Highwatch_Guard,
Fenwick_Trader...) that nothing names: no quest's marker, no script, the world map, the engine or the page. They only
cluttered the editor's places (and the Settler or Trader walks off from it anyway). Places named for buildings and
squares stay. The builder now marks a person only when something points at them (estforlan/places.py wanted).

Safe to run again (a second run finds nothing to take).

  python -I "dev\\migrate\\drop_unused_markers.py"
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def at(*p):
    return os.path.join(ROOT, *p)


def unused():
    """The <Place>_<Kind> Ids, Kind an Entities.ini thing, that nothing in the data or the code names."""
    ids = set()
    for f in glob.glob(at("maps", "*.txt")):
        with open(f, "rb") as fh:
            for ln in fh.read().decode("cp1252").splitlines():
                p = ln.split("\t")
                if p[0] == "Id" and len(p) > 1:
                    ids.add(p[1])
    text = " ".join(os.listdir(at("data", "Scripts")))
    for pat in ("data/*.ini", "data/Scripts/*.txt", "dsengine/*.py", "server/*.py", "web/js/*.js"):
        for f in glob.glob(at(*pat.split("/"))):
            with open(f, "rb") as fh:
                text += "\n" + fh.read().decode("latin-1")
    words = set(re.findall(r"[A-Za-z0-9_']+", text))
    with open(at("data", "Entities.ini"), "rb") as fh:
        kinds = set(re.findall(r"(?m)^\[([^\]]+)\]", fh.read().decode("cp1252")))
    return {i for i in ids if i not in words and "_" in i and i.split("_", 1)[1] in kinds}


def drop(text, gone):
    """A map's text without the Id lines for gone."""
    nl = "\r\n" if "\r\n" in text else "\n"
    keep = [ln for ln in text.split(nl) if not (ln.split("\t")[0] == "Id" and len(ln.split("\t")) > 1 and
                                                ln.split("\t")[1] in gone)]
    return nl.join(keep)


def main():
    gone = unused()
    for f in sorted(glob.glob(at("maps", "*.txt"))):
        with open(f, "rb") as fh:
            raw = fh.read()
        new = drop(raw.decode("cp1252"), gone).encode("cp1252")
        if new != raw:
            with open(f, "wb") as fh:
                fh.write(new)
            print("%s: %d gone" % (os.path.basename(f), raw.count(b"\r\nId\t") - new.count(b"\r\nId\t")))
    print("%d unused markers taken away" % len(gone))


if __name__ == "__main__":
    main()
