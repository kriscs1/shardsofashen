"""What a potion is and what a spell is, put right, once (the rule: CLAUDE.md, Magic and Shards). A potion is herbs: it
works inside the one who drinks it (mends, strengthens, sharpens the senses, cures) and needs no Shards. A spell is
Shard magic: it reaches out of you into the world (strikes, freezes, moves things, moves you) or binds Shards round
you (a ward). Shards can't mend a body, and herbs can't make Shards.
  * Healing was a spell: it's the brewer's now. Its scroll is a Healing Draught, its rank II a Mega Potion (the
    Herbalist's reward: three); the scroll desk no longer writes it, and the shops sell draughts.
  * Farsight was a spell: sharper eyes are the Owl Potion's. Its scroll is an Owl Potion, and isn't written.
  * Stone Skin (a body turned to stone) is the Shard Ward: Shards bound round you as a shell, +5 Defence.
  * The violet Magic Potion no longer settles into Shards (herbs can't make them): it clears your head, so your
    spells strike harder.
Characters who knew Healing or Farsight get potions instead as they load (dsengine/session.py); their scrolls and
Stone Skin are renamed as they load (dsengine/renames.py).
It refuses to run again (Spells.ini has no [Healing]).
Usage: python -I dev/migrate/potions_and_spells.py"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

TOKENS = [("Healing_Scroll_II", "Mega_Potion"), ("Healing_Scroll", "Healing_Draught"), ("Farsight_Scroll", "Owl_Potion"),
          ("Stone_Skin_Scroll", "Shard_Ward_Scroll")]
GONE_RECIPES = ("Healing_Scroll", "Farsight_Scroll")
WARD_INFO = ("A scroll of Shard Ward: Shards bound round you as a shell of light, +5 Defence for a minute. Magic 7. "
             "Read it to learn the spell for good; casting it then costs Shards (the journal's Spells).")
MAGIC_INFO = "A violet potion: it clears your head, and your spells do 5 more damage for two minutes."


def tokens(s):
    for a, b in TOKENS:
        s = re.sub(r"\b%s\b" % a, b, s)
    return s


def entities():
    ini = Ini(p("data", "Entities.ini"))
    ini.sections = [s for s in ini.sections if s[0] not in ("Healing_Scroll", "Healing_Scroll_II", "Farsight_Scroll")]
    for s in ini.sections:
        if s[0] == "Stone_Skin_Scroll":
            s[0] = "Shard_Ward_Scroll"
        s[1] = [(k, tokens(v)) if k == "Drops" else (k, v) for k, v in s[1]]
    ini.set("Shard_Ward_Scroll", "Spell", "Shard_Ward")
    ini.set("Shard_Ward_Scroll", "Examine.Info", WARD_INFO)
    ini.set("Magic_Potion", "Examine.Info", MAGIC_INFO)
    ini.save(p("data", "Entities.ini"))


def spells():
    ini = Ini(p("data", "Spells.ini"))
    ini.sections = [s for s in ini.sections if s[0] not in ("Healing", "Farsight")]
    for s in ini.sections:
        if s[0] == "Stone_Skin":
            s[0] = "Shard_Ward"
            s[1] = [(k, "Shard_Ward_Scroll" if k == "Scroll" else v) for k, v in s[1]]
    ini.remove("Magic_Potion", "Shards")
    ini.save(p("data", "Spells.ini"))
    sh = Ini(p("data", "Shards.ini"))
    sh.sections = [s for s in sh.sections if s[0] != "Upgrade.Healing"]
    sh.save(p("data", "Shards.ini"))


def racks():
    ini = Ini(p("data", "ItemRacks.ini"))
    for s in ini.sections:
        items, other, seen = [], [], set()
        for k, v in s[1]:
            if k is not None and re.fullmatch(r"Item\d+", k):
                name = v.split(",")[0].strip()
                if s[0] == "CRAFT-Scrolls" and name in GONE_RECIPES:
                    continue                                     # (not written: they're potions, or gone)
                v = tokens(v)
                if v.split(",")[0].strip() in seen:
                    continue                                     # (a shop that sold both: once)
                seen.add(v.split(",")[0].strip())
                items.append(v)
            else:
                other.append((k, v))
        if items:
            s[1] = other + [("Item%d" % (i + 1), v) for i, v in enumerate(items)]
    ini.save(p("data", "ItemRacks.ini"))


def quests_and_scripts():
    q = Ini(p("data", "Quests.ini"))
    for s in q.sections:
        s[1] = [(k, "Mega_Potion 3" if (k == "Reward.Items" and v.strip() == "Healing_Scroll_II 1") else tokens(v))
                if k is not None else (k, v) for k, v in s[1]]
    q.save(p("data", "Quests.ini"))
    sd = p("data", "Scripts")
    for f in os.listdir(sd) + [os.path.join("..", "..", "saves", "TEMPLATE.ini")]:     # (and a new character's kit)
        path = os.path.join(sd, f)
        b = open(path, "rb").read().decode("cp1252")
        t = tokens(b)
        if t != b:
            open(path, "wb").write(t.encode("cp1252"))


def sprites():
    ed = p("sprites", "Entities")
    if os.path.exists(os.path.join(ed, "Stone_Skin_Scroll.png")):
        shutil.copyfile(os.path.join(ed, "Stone_Skin_Scroll.png"), os.path.join(ed, "Shard_Ward_Scroll.png"))
    for f in ("Healing_Scroll", "Healing_Scroll_II", "Farsight_Scroll", "Stone_Skin_Scroll"):
        if os.path.exists(os.path.join(ed, f + ".png")):
            os.remove(os.path.join(ed, f + ".png"))


def main():
    if Ini(p("data", "Spells.ini")).section("Healing") is None:
        sys.exit("Potions and spells are put right already: this has been run.")
    entities()
    spells()
    racks()
    quests_and_scripts()
    sprites()
    print("Potions and spells: Healing and Farsight are potions now, Stone Skin is the Shard Ward")


if __name__ == "__main__":
    main()
