"""Scrolls made rare, chests made quiet and the healing draughts given tiers, once (the rules: CLAUDE.md, Magic and
Shards; Writing).
  * A scroll only teaches its spell: Learn, and it's used up (a spell is cast from Channeling, in the Stats box). A
    scroll comes one at a time (Stackable=1), and a new character starts with none.
  * Scrolls come from quests, from a few chests in places of their own (the standing stones' and the cinder cache's),
    from the bottom of the Shifting Deep, and from the wizards' shops - dearly (Value 100 + 40 a Channeling level the
    spell needs). Nothing a quest gives or a chest holds is ever for sale (Value=0, Droppable=0), no beast drops a
    scroll, no ordinary chest holds one, and Bert no longer writes them (CRAFT-Scrolls is gone from his words).
  * Opening a chest says nothing: what's in it shows in its box.
  * Healing draughts: a Minor (8-12), the Healing Draught (15-20, was 28-36) and a Major (26-32), brewed at the
    alchemy rack from more herbs as they get stronger.
Safe to run again (what's done already is left as it is).
Usage: python -I dev/migrate/rare_scrolls.py"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common import Ini, p, read_lines, write_lines  # noqa: E402
from dsedit.project import Project, ScriptDoc  # noqa: E402
from dsedit import scriptlang as SL  # noqa: E402

KEEP_CHEST_SCROLLS = {("0,0,0", "Lightning_Scroll"), ("25,11,0", "Fire_Storm_Scroll")}   # (the few, in places of their own)
CHESTS = ("Open Chest", "Open Chest 2", "Open Chest 3", "Open Hollow_Hill_Chest")
LEARN_INFO = "Learn it, and the spell is yours for good (the scroll is used up); cast it from Channeling."
OLD_INFO = ("Read it to learn the spell for good; casting it then costs Shards (the journal's Spells).",
            "Read it to learn the spell for good; casting it then costs Shards.")
DRAUGHTS = {    # name: (heal, value, its examine, its recipe at CRAFT-Potion_Making: ingredients, xp, Alchemy level)
    "Minor_Healing_Draught": ("8-12", 15, "A pale pink draught of marigold. Drink it to heal 8-12 hitpoints.",
                              "Marigold 1 Empty_Vial 1", "0.4", 1),
    "Healing_Draught": ("15-20", 35, "A rose-pink draught of sage and marigold. Drink it to heal 15-20 hitpoints.",
                        "Sage 1 Marigold 2 Empty_Vial 1", "0.8", 6),
    "Major_Healing_Draught": ("26-32", 80, "A deep crimson draught of sage, marigold and cave mushroom. Drink it to "
                                           "heal 26-32 hitpoints.", "Sage 2 Marigold 2 Cave_Mushroom 1 Empty_Vial 1",
                              "1.3", 13),
}
HUES = {"Minor_Healing_Draught": 0.95, "Major_Healing_Draught": 0.99}    # (Basic_Potion recoloured: build_herbs)


def renumber(doc, before):
    """After lines were removed: every goto points at the line it did (dsedit/pages/scripts.py renumber)."""
    old = [id(ln) for ln in before if not ln.is_comment]
    new = {lid: i + 1 for i, lid in enumerate(id(ln) for ln in doc.lines if not ln.is_comment)}
    for ln in doc.lines:
        if ln.is_comment:
            continue
        for k, t in enumerate(SL.COMMANDS.get(ln.command, [])):
            if k < len(ln.args) and SL.is_goto(t) and ln.args[k].strip().isdigit():
                n = int(ln.args[k])
                if 1 <= n <= len(old):
                    ln.args[k] = "%02d" % new.get(old[n - 1], min(n, len(new)))


def drop_lines(doc, gone):
    before = list(doc.lines)
    doc.lines = [ln for ln in doc.lines if not gone(ln)]
    if len(doc.lines) != len(before):
        renumber(doc, before)
        return True
    return False


def scroll_names(ents, spells):
    """Every item that teaches a spell (not a potion, not the Spellwright's page)."""
    out = []
    for name, items in ents.sections:
        sp = ents.get(name, "Spell")
        if sp and (spells.get(sp, "Kind") or "Scroll").lower() != "potion" and sp != "Own_Spell":
            out.append(name)
    return out


def chests(project, scrolls):
    done = 0
    for name in CHESTS:
        doc = ScriptDoc(project, name)
        if not doc.exists:
            continue
        where = None
        keep_ids = set()
        for ln in doc.lines:                                # (which map's chest each Give.Item is in)
            if ln.is_comment:
                continue
            if ln.command == ">On.Map" and ln.args:
                where = ln.args[0].strip()
            if ln.command == "Give.Item" and len(ln.args) > 1 and ln.args[0].strip() in scrolls:
                if (where, ln.args[0].strip()) in KEEP_CHEST_SCROLLS:
                    ln.args[1] = "1"
                    keep_ids.add(id(ln))
        changed = drop_lines(doc, lambda ln: not ln.is_comment and (
            (ln.command == "Give.Item" and ln.args and ln.args[0].strip() in scrolls and id(ln) not in keep_ids) or
            (ln.command == "Display.Message" and ln.args and ln.args[0].strip() in ("Yellow", "Green"))))
        if doc.save() or changed:
            done += 1
    print("Chests: quiet, and %d scripts without their scrolls" % done)


def bert(project):
    doc = ScriptDoc(project, "Talk to Bert")
    if not doc.exists:
        return
    target = None
    for i, ln in enumerate(doc.commands()):
        if ln.command == "Display.Item.Rack" and "CRAFT-Scrolls" in ln.args:
            target = i + 1
    if target is None:
        return
    for ln in doc.commands():                               # (his answer about writing scrolls: gone)
        if ln.command == "Display.Conversation":
            a = ln.args
            for k in range(2, len(a) - 1, 2):
                if a[k + 1].strip() == "%02d" % target or a[k + 1].strip() == str(target):
                    del a[k:k + 2]
                    a[1] = a[1].replace("I sell spell scrolls, and I can teach you to write your own.",
                                        "I sell spell scrolls, though they don't come cheap.")
                    break
    cmds = doc.commands()
    rack, end = cmds[target - 1], cmds[target] if target < len(cmds) else None
    drop_lines(doc, lambda ln: ln is rack or (ln is end and ln.command == "End"))
    doc.save()
    print("Bert: sells scrolls, writes none")


def main():
    project = Project(p())
    ents, spells = Ini(p("data", "Entities.ini")), Ini(p("data", "Spells.ini"))
    racks, quests, deep = Ini(p("data", "ItemRacks.ini")), Ini(p("data", "Quests.ini")), Ini(p("data", "Deep.ini"))
    scrolls = scroll_names(ents, spells)
    sset = set(scrolls)

    # ----- what a quest gives, a chest holds or lies on a map: never for sale
    chests(project, sset)
    bert(project)
    found = set()
    for sec, _ in quests.sections:
        found |= {w for w in (quests.get(sec, "Reward.Items") or "").split() if w in sset}
    folder = p("data", "Scripts")
    for f in os.listdir(folder):
        if f.endswith(".txt"):
            for ln in read_lines(os.path.join(folder, f)):
                c = ln.split("\t")
                if len(c) > 2 and c[1] == "Give.Item" and c[2].strip() in sset:
                    found.add(c[2].strip())
    for f in os.listdir(p("maps")):
        if f.endswith(".txt"):
            path = p("maps", f)
            lines = read_lines(path)
            hit = False
            for i, ln in enumerate(lines):
                c = ln.split("\t")
                if len(c) > 4 and c[0] == "MapItem" and c[1] in sset:
                    found.add(c[1])
                    if c[4].strip() not in ("", "1"):
                        c[4] = "1"
                        lines[i] = "\t".join(c)
                        hit = True
            if hit:
                write_lines(path, lines)
    for sec, _ in deep.sections:                            # (the Deep: only its Heart, at the bottom, keeps one)
        for key in ("Loot", "Secret.Loot", "Heart.Loot"):
            v = deep.get(sec, key)
            if not v:
                continue
            parts = v.split()
            if key == "Heart.Loot":
                found |= {x.split(",")[0] for x in parts if x.split(",")[0] in sset}
            else:
                keep = [x for x in parts if x.split(",")[0] not in sset]
                if keep != parts:
                    deep.set(sec, key, " ".join(keep))
    deep.save(p("data", "Deep.ini"))
    found |= {s for s in scrolls if re.search(r"_(II|III)$", s)}       # (an upgrade's scroll: quests only)

    # ----- the scrolls themselves
    for s in scrolls:
        ents.set(s, "Stackable", "1")
        words = ents.get(s, "Use.Words") or ""
        if "Cast" in [w.strip() for w in words.split(",")]:
            ents.set(s, "Use.Words", ",".join("Learn" if w.strip() == "Cast" else w for w in words.split(",")))
        info = ents.get(s, "Examine.Info") or ""
        for old in OLD_INFO:
            info = info.replace(old, LEARN_INFO)
        info = info.replace("Read it to learn", "Learn it to know")
        ents.set(s, "Examine.Info", info)
        sp = ents.get(s, "Spell")
        if s in found:
            ents.set(s, "Value", "0")
            ents.set(s, "Droppable", "0")
        else:
            level = int(float(spells.get(sp, "Level") or 1))
            ents.set(s, "Value", str(100 + 40 * level))
    for name, items in ents.sections:                       # (no beast drops a scroll)
        d = ents.get(name, "Drops")
        if d:
            keep = [x for x in d.split() if x.split(",")[0] not in sset]
            if len(keep) != len(d.split()):
                ents.set(name, "Drops", " ".join(keep))
    spells.remove("Grasp", "Keep")                           # (learnt, and the scroll's used up, like any other)

    # ----- the shops: a scroll only at the wizards' (one at a time), and never one a quest or a chest gives
    for sec, items in racks.sections:
        if not sec.upper().startswith("SHOP-"):
            continue
        out, n = [], 0
        for k, v in items:
            if k is None or not re.fullmatch(r"Item\d+", k):
                out.append((k, v))
                continue
            name = v.split(",")[0]
            if name == "Blank_Scroll" or (name in sset and (name in found or sec not in ("SHOP-Wizard",
                                                                                        "SHOP-Homestead"))):
                continue
            if name in sset:
                v = "%s,1" % name
            n += 1
            out.append(("Item%d" % n, v))
        for name in ("Blizzard_Scroll",) if sec == "SHOP-Wizard" else ():   # (once only written: now sold)
            if name in sset and name not in found and not any(v.split(",")[0] == name for k, v in out if k):
                n += 1
                out.append(("Item%d" % n, "%s,1" % name))
        items[:] = out
    racks.sections = [sc for sc in racks.sections if sc[0] != "CRAFT-Scrolls"]   # (nobody writes scrolls now)

    # ----- the healing draughts, in three strengths
    E = "Empty_Vial"
    rack = racks.section("CRAFT-Potion_Making")
    for name, (heal, value, info, recipe, xp, level) in DRAUGHTS.items():
        for k, v in (("Type", "MapItem"), ("Use.Words", "Drink"), ("Examine.Info", info), ("Stackable", "1"),
                     ("Value", str(value)), ("Spell", name)):
            ents.set(name, k, v, overwrite=k in ("Examine.Info", "Value"))
        for k, v in (("Scroll", name), ("Kind", "Potion"), ("Skill", "Alchemy"), ("Level", "1"), ("Leaves", E),
                     ("XP", "0"), ("Effect", "Heal"), ("Heal", heal), ("Impact", "Heal_Glow"), ("Sound", "SpellHeal")):
            spells.set(name, k, v, overwrite=k == "Heal")
        line = "%s,%s,%s,%d" % (name, recipe, xp, level)
        i = next((j for j, (k, v) in enumerate(rack[1]) if k and v.split(",")[0] == name), None)
        if i is None:
            rack[1].append(("Item0", line))
        else:
            rack[1][i] = (rack[1][i][0], line)
    recipes = [(k, v) for k, v in rack[1] if k and re.fullmatch(r"Item\d+", k)]
    others = [(k, v) for k, v in rack[1] if not (k and re.fullmatch(r"Item\d+", k))]
    recipes.sort(key=lambda kv: int(kv[1].split(",")[3]) if len(kv[1].split(",")) > 3 else 1)
    rack[1] = others + [("Item%d" % (i + 1), v) for i, (_, v) in enumerate(recipes)]

    ents.save(p("data", "Entities.ini"))
    spells.save(p("data", "Spells.ini"))
    racks.save(p("data", "ItemRacks.ini"))

    # ----- a new character: no scrolls
    tpl = p("saves", "TEMPLATE.ini")
    lines = read_lines(tpl)
    keep = [ln for ln in lines if not (re.match(r"Slot\d+=", ln) and ln.split("=", 1)[1].split(",")[0] in sset)]
    if keep != lines:
        n, out, inv = 0, [], False
        for ln in keep:                                     # (the pack's slots numbered again from 1)
            if ln.strip().startswith("["):
                inv, n = ln.strip() == "[Inventory]", 0
            if inv and re.match(r"Slot\d+=", ln):
                n += 1
                ln = "Slot%d=%s" % (n, ln.split("=", 1)[1])
            out.append(ln)
        write_lines(tpl, out)

    # ----- the new draughts' pictures (build_herbs.py draws the potions so: Basic_Potion recoloured)
    try:
        import build_herbs as H
        import sprite_kit as K
        for name, hue in HUES.items():
            K.save("Entities", name, H.potion_img(hue))
    except Exception as e:                                  # (pygame or PIL missing: draw them later)
        print("Pictures not drawn: %s" % e)
    print("Scrolls: %d (%d never sold); draughts in three strengths" % (len(scrolls), len(found)))


if __name__ == "__main__":
    main()
