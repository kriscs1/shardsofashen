"""Stance forms (dsengine/forms.py): each stance's forms (Cautious too), taught by people round the world.
  * data\\Stances.ini: a section for each form ([Fighting.Shieldwall]...): its title, what it does, its colour round
    the stance's ring, who teaches it and when (Taught.By= an NPC's Id, or its kind; Taught.If= a condition;
    Taught.Words= what they say), and its numbers, times the stance's own. [Limits]: every number's least and most.
  * data\\Shards.ini [Forms]: six bound at most, a form's binding in Shards, its Shardcraft xp, how often the Shards
    whisper to one who drinks them.
Only the keys missing are added: edit the numbers there. Safe to run again.
  python -I "dev\\migrate\\build_forms.py"
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402

FORMS = [   # (section, [(key, value)])
    ("Cautious.Shield_Wall", [
        ("Title", "Shield Wall"),
        ("What", "A firmer guard still; slower on foot."),
        ("Colour", "120,150,190"),
        ("Taught.By", "Palace_Captain"), ("Taught.If", "$Skill.Defence>=10"),
        ("Taught.Words", "Captain Hart watches you square up, and nods. \"Good: you don't charge in. Now hold it "
                         "properly. Shield high, chin down, and let them break on you.\""),
        ("Defence", "1.3"), ("Walk", "0.85")]),
    ("Cautious.Sure_Step", [
        ("Title", "Sure Step"),
        ("What", "Quicker on foot, and out of a fight sooner (you start to heal sooner after one)."),
        ("Colour", "190,200,120"),
        ("Taught.By", "Captain_Rook"), ("Taught.If", "$Skill.Defence>=5"),
        ("Taught.Words", "\"You walk like a landsman, matey,\" Rook says. \"Light on the feet: a deck pitches, and so "
                         "does a fight. Step back, breathe, and it's behind you.\""),
        ("Walk", "1.12"), ("Calm", "0.5")]),
    ("Cautious.Riposte", [
        ("Title", "Riposte"),
        ("What", "A blow you block is sometimes answered with one of yours; a weaker guard."),
        ("Colour", "220,150,110"),
        ("Taught.By", "Captain"), ("Taught.If", "$Attr.BanditWay=1"),
        ("Taught.Words", "\"You held off those bandits better than my own lads,\" Hale says. \"Here's one more "
                         "thing: when you turn a blow, don't wait. Answer it, while they're still open.\""),
        ("Riposte", "15"), ("Defence", "0.9")]),
    ("Fighting.Shieldwall", [
        ("Title", "Hold the Line"),
        ("What", "A much firmer guard, slower on foot; monsters near come for you before your friends."),
        ("Colour", "170,180,200"),
        ("Taught.By", "Smuggler_Sergeant"), ("Taught.If", "$Attr.SmugglerSide=2"),
        ("Taught.Words", "\"You held the line in Meg's camp like one of mine,\" Holt says. \"Here: the way the watch "
                         "holds a door. Feet set, shield up, and let them come to you, not to the lad beside you.\""),
        ("Defence", "1.4"), ("Walk", "0.8"), ("Draw", "160")]),
    ("Fighting.Reckless", [
        ("Title", "Reckless"),
        ("What", "Harder blows, a weaker guard; a kill gives you a moment's rush (quicker, and harder still)."),
        ("Colour", "240,120,40"),
        ("Taught.By", "Arena_Master"), ("Taught.If", "$Attr.ArenaWins>=3 or $Attr.Kills>=300"),
        ("Taught.Words", "The Arena Master looks you up and down. \"I've watched you. You fight like you've nothing to "
                         "lose, so lose the rest of it: forget your guard and finish them. One down, and on to the "
                         "next before they know it.\""),
        ("Damage", "1.25"), ("Defence", "0.8"), ("Rush.Seconds", "4"), ("Rush.Damage", "1.2"), ("Rush.Walk", "1.3")]),
    ("Fighting.Duellist", [
        ("Title", "Duellist"),
        ("What", "More of your blows land, and now and then you turn one of theirs aside."),
        ("Colour", "235,215,120"),
        ("Taught.By", "Palace_Captain"), ("Taught.If", "$Attr.GuardQuest>=5"),
        ("Taught.Words", "\"A guard of the palace fights with a point, not a club,\" Captain Hart says, and shows you: "
                         "the blade always between you and them, a flick of the wrist to turn a blow."),
        ("Attack", "1.3"), ("Parry", "12")]),
    ("Fighting.Dirty_Fighting", [
        ("Title", "Dirty Fighting"),
        ("What", "Your blows can daze for a moment; a weaker guard."),
        ("Colour", "130,160,60"),
        ("Daze", "12"), ("Daze.Seconds", "1.5"), ("Defence", "0.85")]),
    ("Channelling.Stormcaller", [
        ("Title", "Stormcaller"),
        ("What", "Your spells much stronger, and dearer in Shards."),
        ("Colour", "250,240,130"),
        ("Taught.By", "Bert"), ("Taught.If", "$Attr.ShardgateQuest>=5"),
        ("Taught.Words", "\"The gate taught me something,\" Bert says. \"Don't sip the Shards. Pull. Pull everything "
                         "you've got through at once. It costs, oh, it costs, but you should have seen the cat's "
                         "face.\""),
        ("Spell.Power", "1.3"), ("Spell.Cost", "1.5")]),
    ("Channelling.Wardkeeper", [
        ("Title", "Wardkeeper"),
        ("What", "Your wards last twice as long, and drains and poisons hardly touch you."),
        ("Colour", "120,230,220"),
        ("Taught.By", "Warden_Ysolde"), ("Taught.If", "$Attr.WardenQuest>=3"),
        ("Taught.Words", "\"The Wardens kept the watch for a hundred years,\" Ysolde says. \"This is how we kept "
                         "ourselves: the Shards held close, like a cloak against the cold.\""),
        ("Spell.Duration", "2"), ("Resist.Status", "1.6")]),
    ("Channelling.Listening", [
        ("Title", "Listening"),
        ("What", "You hear Shards: remnants, clusters and Shard secrets near you show."),
        ("Colour", "150,120,255"),
        ("Taught.By", "Warden_Ysolde"), ("Taught.If", "$Attr.WardensHeard>=2"),
        ("Taught.Words", "\"You heard it, down there, and didn't answer,\" Ysolde says. \"Then you can learn what we "
                         "learnt: to hear the Shards without them hearing you.\""),
        ("Hear.Shards", "320")]),
    ("Channelling.Drinking", [
        ("Title", "Drinking"),
        ("What", "Remnants on the ground near you are drunk straight off, and heal you; a very weak guard; the Shards "
                 "whisper to you."),
        ("Colour", "200,60,90"),
        ("Taught.By", "Sister_Linnet"), ("Taught.If", "$Attr.GreyEnd=2"),       # (In Grey: their secret kept)
        ("Taught.Words", "Sister Linnet takes your hands and closes them round a Shard. \"Don't fight it, "
                         "$Player.Brother. Let it in. It only ever wanted to be part of you.\" It goes into your "
                         "palms, warm, and something in you is thirstier than it was."),
        ("Drink.Reach", "96"), ("Drink.Heal", "2"), ("Defence", "0.6"),
        ("Whisper.1", "Something in the Shards says your name, very softly."),
        ("Whisper.2", "The Shards in you are warm. They like it here."),
        ("Whisper.3", "More, says something at the edge of hearing. There's always more."),
        ("Whisper.4", "For a moment you remember a place you've never been: a hall of glass, and singing.")]),
    ("Sneaking.Cutpurse", [
        ("Title", "Cutpurse"),
        ("What", "Better hands for pockets and shelves, and those watching look the other way more."),
        ("Colour", "200,170,60"),
        ("Taught.By", "Red_Meg"), ("Taught.If", "$Attr.SmugglerSide=1"),
        ("Taught.Words", "Meg grins and lifts your purse, and gives it back, all in one move. \"Watch the eyes, not "
                         "the pocket. When they look away, you're already done.\""),
        ("Thieving", "15"), ("Watched", "0.5")]),
    ("Sneaking.Shadow", [
        ("Title", "Shadow"),
        ("What", "Harder to see and to hear, and a harder blow from where they never saw you."),
        ("Colour", "90,70,140"),
        ("Taught.By", "Ambrose_At_Home"), ("Taught.If", "$Attr.RedrockWay=2"),
        ("Taught.Words", "\"Forty years I caught thieves,\" Ambrose says, \"and I know how they're seen: by moving "
                         "when you're looked at. Be still when eyes are on you, and you're a shadow.\""),
        ("Sight", "0.75"), ("Noise", "0.85"), ("Sneak.Attack", "1.5")]),
    ("Sneaking.Rangers_Tread", [
        ("Title", "Ranger's Tread"),
        ("What", "Quicker than sneaking is; quieter still on grass and in the woods; animals don't run from you."),
        ("Colour", "80,170,80"),
        ("Taught.By", "Ranger"), ("Taught.If", "$Attr.GroveWay=2"),
        ("Taught.Words", "\"You kept the grove, so I'll keep nothing from you,\" Ash says. \"Walk on the edges of your "
                         "feet, where the moss is, and the deer won't even look up.\""),
        ("Walk", "1.5"), ("Woods.Noise", "0.5"), ("Woods.Grounds", "Grass,Forest,Moss,Leaves,Meadow,Wood"),
        ("Calm.Animals", "1")]),
]

LIMITS = [  # (key, least,most): every stance number, however the forms stack
    ("Attack", "0.5,2"), ("Damage", "0.5,2"), ("Defence", "0.4,2"), ("Walk", "0.35,1.25"), ("Spell.Power", "0.5,2"),
    ("Spell.Duration", "0.5,3"), ("Spell.Cost", "0.5,2.5"), ("Resist.Status", "0,90"), ("Spell.Hurt", "0.5,2"),
    ("Status.Hurt", "0.5,2"), ("Noise", "0.2,2"), ("Sight", "0.2,1.5"), ("Sneak.Attack", "1,4"), ("Parry", "0,40"),
    ("Daze", "0,40"), ("Thieving", "0,40"), ("Watched", "0.2,1"), ("Draw", "0,320"), ("Hear.Shards", "0,480"),
    ("Drink.Reach", "0,160"), ("Riposte", "0,40"), ("Calm", "0.25,1")]

SHARDS = [  # Shards.ini [Forms]
    ("Most", "6", "Most: forms bound at once. Bind: Shards to bind one (Bind.<Form>: one that costs more or less);"),
    ("Bind", "8", "Bind.XP: its Shardcraft. Whisper.Least, .Most: seconds between the Shards' whispers (Drinking)."),
    ("Bind.XP", "0.4", None),
    ("Whisper.Least", "90", None),
    ("Whisper.Most", "240", None),
]


def stances():
    path = p("data", "Stances.ini")
    ini = Ini(path)
    for sec, rows in FORMS:
        if ini.section(sec) is None:
            s = ini.section(sec, create=True)
            s[1].append((None, "; A form of %s (forms.py): its numbers times the stance's" % sec.split(".")[0]))
        s = ini.section(sec)
        for k, v in rows:
            if ini.get(sec, k) is None:
                s[1].append((k, v))
    if ini.section("Limits") is None:
        s = ini.section("Limits", create=True)
        s[1].append((None, "; Every number of a stance and its forms, held within least,most however they stack"))
    s = ini.section("Limits")
    for k, v in LIMITS:
        if ini.get("Limits", k) is None:
            s[1].append((k, v))
    ini.save(path)


def shards():
    path = p("data", "Shards.ini")
    ini = Ini(path)
    if ini.section("Forms") is None:
        ini.section("Forms", create=True)
    s = ini.section("Forms")
    for k, v, note in SHARDS:
        if ini.get("Forms", k) is None:
            if note:
                s[1].append((None, "; " + note))
            s[1].append((k, v))
    ini.save(path)


def main():
    stances()
    shards()
    print("Stance forms: %d in Stances.ini" % len(FORMS))


if __name__ == "__main__":
    main()
