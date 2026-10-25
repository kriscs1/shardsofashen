"""The quests' notes in the journal: lines the scripts write with Quest.Note (and cross out with Quest.Note.Done), shown
in the checklist you get by pointing at a quest (the sidebar's Quests tab, the journal's quest cards) under the steps
the game makes from data\\Quests.ini's stages.

Not run on its own: build_content.extend() calls apply() at the very end, when every script is in build_world.S, so
`python -I "dev\\migrate\\build_world.py"` builds it. The notes go into the scripts right after the step they belong to:
  * STAGES: after `Update.Attribute <quest attribute> =<stage>` in any script (where the quest moves on);
  * EVENTS: after a given step in a given script (a watch stone touched, the last of a kill count, a troll killed);
  * and when a quest is done (its Done value) every note of it is crossed out first.
A note is "+text" (write it) or "-text" (cross it out); -* crosses out all of the quest's notes. The notes say what the
stage text doesn't: where things are, who said what, what to bring, and the parts of a stage, ticked off one by one.
"""

STAGES = {
    "FerryQuest": {
        1: ["+The milkmaid keeps the ferry's ticket book: her farm is in the north of the Isle."],
        2: ["-The milkmaid keeps the ferry's ticket book: her farm is in the north of the Isle.",
            "+Collect 3 eggs from the hens' nests round the milkmaid's farm (Collect on a nest)."],
        3: ["-Collect 3 eggs from the hens' nests round the milkmaid's farm (Collect on a nest)."],
    },
    "RemedyQuest": {
        1: ["+Pick 3 Cave Mushrooms in the old iron mine.",
            "+Get 2 Spider Silk from the giant spiders in the mine depths.",
            "+Bring them all to the Herbalist's cottage on the Ashford farmlands."],
    },
    "DwarfQuest": {
        1: ["+Smash four skeletons in the Deep Hollow.",
            "+Slay the cave troll in the Deep Hollow.",
            "+Then go back to Brokk."],
    },
    "RangerQuest": {
        1: ["+Watch stone by the north road, between King Rupert's Keep and Oakhollow.",
            "+Watch stone in the western woods.",
            "+Watch stone east of the river."],
        3: ["+The spider nest is in the deep woods west of Oakhollow.",
            "+Slay five giant spiders there."],
    },
    "WolfQuest": {
        1: ["+Slay six wolves on Greymoor."],
        2: ["-Tell the shepherd in Moorcross.",
            "+The wolf den is on the eastern moor.",
            "+Slay the Alpha Wolf, the great black brute leading the pack."],
        3: ["-Slay the Alpha Wolf, the great black brute leading the pack."],
    },
    "BogQuest": {
        1: ["+Bog myrtle grows in the Saltmarsh round Fenwick (Herblore 5 to pick it).",
            "+Bring Morwen 4 bog myrtle."],
        2: ["-Bring Morwen 4 bog myrtle."],
    },
    "BanditQuest": {
        1: ["+Bandits rob travellers on the Redrock road and in the hills: slay five."],
        2: ["-Report to Captain Hale in Highwatch.",
            "+The bandits' camp is somewhere in the eastern hills.",
            "+Break open their strongbox and take back the stolen goods."],
        3: ["-Break open their strongbox and take back the stolen goods."],
    },
    "CaravanQuest": {
        1: ["+Qadir's caravan was lost in the Sunscar Desert, west of Dunerest.",
            "+Scorpions roam the desert: bring food."],
        2: ["-Qadir's caravan was lost in the Sunscar Desert, west of Dunerest.",
            "+Slay the scorpions at the wreck.",
            "+Find the caravan's ledger and bring it to Qadir."],
    },
    "ForgeQuest": {
        1: ["+Bring Brann 5 coal (mine coal rocks, Mining 5, or buy some)."],
        2: ["-Bring Brann 5 coal (mine coal rocks, Mining 5, or buy some).",
            "+The Frost Troll is on the frozen lake east of Frosthold."],
        3: ["-The Frost Troll is on the frozen lake east of Frosthold.",
            "+Mithril ore needs Mining 25 and a steel pickaxe or better; smelt it at a furnace."],
    },
    "HermitQuest": {
        1: ["+His camp is in the Isle's western woods. Oak trees grow all over the Isle."],
    },
    "DruidQuest": {
        1: ["+The Heartwood is north-east of Thornwick, where the yews are oldest.",
            "+Touch the heart stone, then tell the Druid what you feel."],
        2: ["-The Heartwood is north-east of Thornwick, where the yews are oldest.",
            "-Touch the heart stone, then tell the Druid what you feel.",
            "+Slay four maddened bears in the Elderwood."],
        3: ["-Slay four maddened bears in the Elderwood."],
    },
    "HobQuest": {
        1: ["+Morwen the witch lives in Fenwick, in the Saltmarsh south of Oakhollow."],
        2: ["-Morwen the witch lives in Fenwick, in the Saltmarsh south of Oakhollow.",
            "+The wild man roams the western woods, near the old watch stone. He attacks on sight.",
            "+Use the calming draught on him (Use, then click him)."],
        3: ["-The wild man roams the western woods, near the old watch stone. He attacks on sight.",
            "-Use the calming draught on him (Use, then click him)."],
    },
    "BarrowQuest": {
        1: ["+The barrow is out on the downs east of Ravensgate: look for the broken walls."],
        2: ["-The barrow is out on the downs east of Ravensgate: look for the broken walls.",
            "+The Barrow King has two skeleton guards. Bring food."],
    },
}

EVENTS = [   # (script, the step the notes follow, quest attribute, notes)
    ("Kill Cave_Troll", ("Update.Attribute", "TrollSlain", "=1"), "DwarfQuest", ["-Slay the cave troll in the Deep Hollow."]),
    ("Watch Stone 1", ("Update.Attribute", "Watch1", "=1"), "RangerQuest",
     ["-Watch stone by the north road, between King Rupert's Keep and Oakhollow."]),
    ("Watch Stone 2", ("Update.Attribute", "Watch2", "=1"), "RangerQuest", ["-Watch stone in the western woods."]),
    ("Watch Stone 3", ("Update.Attribute", "Watch3", "=1"), "RangerQuest", ["-Watch stone east of the river."]),
    ("Kill Giant_Spider", "enough:", "RangerQuest",
     ["-Slay five giant spiders there.", "+Return to Ranger Ash in Oakhollow."]),
    ("Kill Wolf", "enough:", "WolfQuest", ["-Slay six wolves on Greymoor.", "+Tell the shepherd in Moorcross."]),
    ("Kill Bandit", "enough:", "BanditQuest",
     ["-Bandits rob travellers on the Redrock road and in the hills: slay five.", "+Report to Captain Hale in Highwatch."]),
    ("Kill Scorpion", "enough:", "CaravanQuest", ["-Slay the scorpions at the wreck."]),
]


def steps_for(quest, notes):
    return [("Quest.Note.Done", quest, n[1:]) if n[0] == "-" else ("Quest.Note", quest, n[1:]) for n in notes]


def insert_after(steps, match, new):
    """Puts new after every step of steps that is match (a label, or a step starting with match). Returns how many."""
    hits = 0
    i = 0
    while i < len(steps):
        s = steps[i]
        if (isinstance(match, str) and s == match) or (isinstance(match, tuple) and isinstance(s, tuple)
                                                        and s[:len(match)] == match):
            steps[i + 1:i + 1] = new
            hits += 1
            i += len(new)
        i += 1
    return hits


def apply(S, quests):
    """S: build_world.S (script name -> steps); quests: build_content.QUESTS [(title, [(key, value)])]. Returns the
    rules that matched nothing (a script changed under them), for the build's problem list."""
    done_at = {}
    for title, keys in quests:
        k = dict(keys)
        if k.get("Attribute") and k.get("Done"):
            done_at[k["Attribute"]] = int(k["Done"])
    unused = []
    for quest in sorted(set(STAGES) | set(done_at)):
        stages = dict(STAGES.get(quest, {}))
        if quest in done_at:                              # done: every note crossed out, then any last word
            stages[done_at[quest]] = ["-*"] + stages.get(done_at[quest], [])
        for stage, notes in sorted(stages.items()):
            match = ("Update.Attribute", quest, "=%d" % stage)
            hits = sum(insert_after(steps, match, steps_for(quest, notes)) for steps in S.values())
            if not hits:
                unused.append("quest_notes.py: no script sets %s to %d" % (quest, stage))
    for script, match, quest, notes in EVENTS:
        if notes and (script not in S or not insert_after(S[script], match, steps_for(quest, notes))):
            unused.append("quest_notes.py: %r has no step %r" % (script, match))
    return unused
