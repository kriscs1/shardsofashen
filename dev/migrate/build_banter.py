"""Banter's words (dsengine/banter.py, data\\Banter.ini): what the world's people and animals say to each other as you
pass, and to you when you've given them cause; and a dog's bark and a cat's hiss. Never a hint: nobody here knows
anything about a quest, and nobody says where a thing is (but a thief hears where the fences are: When=Thief).

A scene already in Banter.ini is left as it is: edit them there, and add more there.

Safe to run again.

  python -I "dev\\migrate\\build_banter.py"     (then export_web_assets.py, validate.py)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import Ini, p                               # noqa: E402
from build_sounds import n, mix, shaped, delay, voice, noise, lowpass    # noqa: E402
from build_soundscape import breath, wav_bytes          # noqa: E402

HEADER = """; Banter (dsengine/banter.py): who says what to whom, over their heads, where a player can see it.
; [Banter]: Every.Seconds, about how long between a player's scenes; Sight.Tiles, how near that player; Near.Tiles, how near
;   each other two must be; Beat.Seconds between lines; Scene.Rest.Minutes, Speaker.Rest.Minutes before they go again.
; [Groups]: names for kinds of people (Entities.ini names, commas between).
; A scene: A, B (a group or kinds), Line1.. (A: or B: and the words, short: they're one line over a head), Sound1.. (played
;   with that line), After=Scatter (B runs off). B=Player: said about the player, When= Form (any other shape), a form's
;   name (Chicken), Sneaking, Hurt, or their rank in the town they're in (Outlaw, Distrusted, Welcome, Trusted, Honoured);
;   Thief (they've stolen something: any scene). Town= (a Towns.ini town): only there.
; Never a hint, never a quest: these people don't know anything (save where a thief might sell what they took).
"""
SETTINGS = [("On", "1"), ("Every.Seconds", "40"), ("Sight.Tiles", "6"), ("Near.Tiles", "5"), ("Beat.Seconds", "2.6"),
            ("Scene.Rest.Minutes", "10"), ("Speaker.Rest.Minutes", "5"), ("Most.At.Once", "3"), ("Scatter.Tiles", "4")]
GROUPS = [("Townsfolk", "Villager,Man,Woman,Settler,Farmer,Fisherman,Shepherd,Old_Woman,Miner"),
          ("Trades", "Baker,Butcher,Fishmonger,Greengrocer,Merchant,Trader,Tailor,Cobbler,Blacksmith,Armourer"),
          ("Guards", "Guard,Constable,Sheriff,Royal_Guard"),
          ("Tavern", "Barkeep,Barmaid"),
          ("Healers", "Doctor,Nurse"),
          ("Clerks", "Banker,Clerk"),
          ("Cats", "Cat,Black_Cat,Ginger_Cat")]


def scene(a, b, *lines, after="", when="", sounds=None, town=""):
    """(A, B, lines): each line "A:words" or "B:words"."""
    return a, b, lines, after, when, sounds or {}, town


SCENES = {
    # ----- neighbours
    "Goat": scene("Townsfolk", "Townsfolk", "A:Morning. Seen my goat?", "B:What goat?", "A:Exactly."),
    "Rain": scene("Townsfolk", "Townsfolk", "A:They say it'll rain.", "B:They said that yesterday.", "A:It rained yesterday."),
    "Miller": scene("Townsfolk", "Townsfolk", "A:Did you hear about the miller?", "B:No?", "A:Nor me. Nobody tells me anything."),
    "Chicken_Debt": scene("Townsfolk", "Townsfolk", "A:You owe me a chicken.", "B:It came back.", "A:It came back different."),
    "Knee": scene("Townsfolk", "Townsfolk", "A:My knee says there's a storm coming.", "B:It said that at my wedding.", "A:And was it wrong?"),
    "Wife": scene("Townsfolk", "Townsfolk", "A:How's the family?", "B:Still related to me.", "A:Poor things."),
    "Ladder": scene("Townsfolk", "Townsfolk", "A:Is that my ladder?", "B:It's a ladder.", "A:...Fair."),
    "Soup": scene("Townsfolk", "Townsfolk", "A:What's in the soup tonight?", "B:Don't ask.", "A:I asked last night.", "B:And?", "A:Don't ask."),
    # ----- the law
    "Along": scene("Guards", "Townsfolk", "A:Move along.", "B:Along where?", "A:Just along."),
    "Report": scene("Guards", "Townsfolk", "A:Anything to report?", "B:My neighbour sings.", "A:That's no crime.", "B:You've not heard him."),
    "Quiet_Shift": scene("Guards", "Guards", "A:Quiet shift.", "B:Don't say that.", "A:Say what?", "B:...Nothing. Quiet shift."),
    "Why_Guard": scene("Guards", "Guards", "A:Why do we guard this bit?", "B:Because it's here.", "A:Good point."),
    # ----- trade
    "Fresh": scene("Trades", "Townsfolk", "A:Fresh today!", "B:You said that on Tuesday.", "A:It was fresh on Tuesday."),
    "How_Much": scene("Trades", "Townsfolk", "B:How much?", "A:Ten.", "B:Ten?! For that?", "A:Twelve, now."),
    "Slow_Trade": scene("Trades", "Trades", "A:Trade's slow.", "B:Yours is. Mine's terrible."),
    "Tab": scene("Tavern", "Townsfolk", "A:About your tab, friend.", "B:What tab?", "A:The long one."),
    "Stew": scene("Tavern", "Tavern", "A:Who ordered the stew?", "B:Nobody. Ever."),
    "Greens": scene("Healers", "Townsfolk", "A:You should eat more greens.", "B:I eat fish.", "A:Fish aren't greens.", "B:Some of them are."),
    "Cough": scene("Healers", "Townsfolk", "A:How's the cough?", "B:Much better!", "A:Then stop doing it at me."),
    "Overdrawn": scene("Clerks", "Townsfolk", "A:Your account's overdrawn.", "B:By how much?", "A:You'll want to sit down."),
    # ----- animals
    "Dog_Cat": scene("Dog", "Cats", "A:Woof! Woof! Woof!", "B:Hssss!", after="Scatter",
                     sounds={1: "Dog_Bark", 2: "Cat_Hiss"}),
    "Dog_Hen": scene("Dog", "Chicken", "A:Woof!", "B:BOK BOK BOK!", after="Scatter", sounds={1: "Dog_Bark"}),
    "Cat_Hen": scene("Cats", "Chicken", "A:...", "B:Bok?", "A:......", "B:BOK!", after="Scatter"),
    "Good_Dog": scene("Townsfolk", "Dog", "A:Who's a good dog?", "B:Woof!", "A:That's not an answer.", sounds={2: "Dog_Bark"}),
    "Puss": scene("Townsfolk", "Cats", "A:Puss puss puss...", "B:...", "A:Fine. Be like that.", sounds={2: "Meow"}),
    "Sheep": scene("Townsfolk", "Sheep", "A:Evening.", "B:Baa.", "A:That's what I said to her."),
    # ----- the jester
    "Jester_Guard": scene("Guards", "Jester", "A:Halt! What are you wearing?", "B:Ambition.", "A:...Move along."),
    "Jester_Crime": scene("Jester", "Guards", "A:Arrest me! My jokes are a crime!", "B:We know.", "A:Everyone's a critic."),
    "Jester_Knock": scene("Jester", "Townsfolk", "A:Knock knock!", "B:Who's there?", "A:Not me. I'm leaving."),
    "Jester_Fish": scene("Jester", "Trades", "A:Is that fresh?", "B:Caught today!", "A:By what, old age?"),
    "Jester_Dog": scene("Jester", "Dog", "A:Sit!", "B:Woof!", "A:Good. Now the one about the bishop.", sounds={2: "Dog_Bark"}),
    "Jester_Cat": scene("Jester", "Cats", "A:Bow before your jester!", "B:...", "A:Tough crowd."),
    # ----- the salesman
    "Sales_Trade": scene("Travelling_Salesman", "Trades", "A:Those prices! You're robbing them.", "B:And you?", "A:Politely."),
    "Sales_Bucket": scene("Travelling_Salesman", "Townsfolk", "A:Lovely day for a bucket.", "B:I've got a bucket.", "A:A second bucket!"),
    "Sales_Guard": scene("Guards", "Travelling_Salesman", "A:Got a licence for that?", "B:Got a discount for you.", "A:...Go on."),
    "Sales_Jester": scene("Travelling_Salesman", "Jester", "A:You again.", "B:Me again.", "A:Buy something.", "B:Laugh at something."),
    # ----- to you, when you've given them cause
    "You_Chicken": scene("Townsfolk", "Player", "A:Is that chicken wearing boots?", when="Chicken"),
    "You_Chicken_Guard": scene("Guards", "Player", "A:You. Bird. Move along.", when="Chicken"),
    "You_Form": scene("Townsfolk", "Player", "A:You look different today. Have you done something?", when="Form"),
    "You_Sneak": scene("Townsfolk", "Player", "A:Why are you walking like that?", when="Sneaking"),
    "You_Sneak_Guard": scene("Guards", "Player", "A:I can see you, you know.", when="Sneaking"),
    "You_Sneak_Trade": scene("Trades", "Player", "A:I'm watching those fingers.", when="Sneaking"),
    "You_Hurt": scene("Townsfolk", "Player", "A:You look dreadful. No offence.", when="Hurt"),
    "You_Hurt_Doctor": scene("Healers", "Player", "A:You want to see someone about that. Me, for instance.", when="Hurt"),
    # ----- to you, as the town thinks of you (standing.py)
    "You_Outlaw": scene("Townsfolk", "Player", "A:That's the one the guards want. Don't look!", when="Outlaw"),
    "You_Outlaw_Trade": scene("Trades", "Player", "A:We're closed. To you, we're closed.", when="Outlaw"),
    "You_Distrusted": scene("Townsfolk", "Player", "A:Keep your hands where I can see them.", when="Distrusted"),
    "You_Distrusted_Guard": scene("Guards", "Player", "A:I've got my eye on you.", when="Distrusted"),
    "You_Distrusted_Trade": scene("Trades", "Player", "A:Coin first, with you.", when="Distrusted"),
    "You_Welcome": scene("Townsfolk", "Player", "A:Oh, it's you! Good day to you.", when="Welcome"),
    "You_Trusted": scene("Townsfolk", "Player", "A:Good to have you back.", when="Trusted"),
    "You_Trusted_Guard": scene("Guards", "Player", "A:All quiet, friend. Mind how you go.", when="Trusted"),
    "You_Honoured": scene("Townsfolk", "Player", "A:Look who it is! Make way, make way.", when="Honoured"),
    "You_Honoured_Guard": scene("Guards", "Player", "A:An honour. Go on through.", when="Honoured"),
    "You_Honoured_Trade": scene("Trades", "Player", "A:For you? A little off, as ever.", when="Honoured"),
    # ----- where a thief sells (thieving.py: only to those who've stolen, only in the fence's own town)
    "Fence_Northport": scene("Townsfolk", "Player", "A:Got things you can't sell? The docks, after dark.",
                             "A:Ask for Wick. You didn't hear it from me.", when="Thief", town="Northport"),
    "Fence_Northport_Talk": scene("Townsfolk", "Townsfolk", "A:Wick bought my cousin's \"found\" silver.",
                                  "B:Didn't ask where from?", "A:Wick never asks.", when="Thief", town="Northport"),
    "Fence_Galaith": scene("Townsfolk", "Player", "A:Looking to sell what isn't yours?",
                           "A:Old Sully. The tavern's corner. Quietly.", when="Thief", town="Galaith"),
    "Fence_Galaith_Talk": scene("Townsfolk", "Townsfolk", "A:Old Sully had a duke's spoons last week.",
                                "B:Sully buys anything.", "A:Anything stolen, anyhow.", when="Thief", town="Galaith"),
    # ----- the Court's watch, after the Smugglers' Run (build_smugglers_run.py: which way you went)
    "Cove_Taken": scene("Guards", "Player", "A:You're the one who cleared the cove.", "A:Drinks are on the watch.",
                        when="$Attr.SmugglerSide=2", town="Court"),
    "Cove_Taken_Talk": scene("Guards", "Guards", "A:Red Meg's camp. Gone, in one night.", "B:And Meg?",
                             "A:Out to sea. She'll be back.", when="$Attr.SmugglerSide=2", town="Court"),
    "Wrong_Beach": scene("Guards", "Player", "A:A cold night on an empty beach.", "A:Funny, that. Wasn't it?",
                         when="$Attr.SmugglerSide=1", town="Court"),
    "Wrong_Beach_Talk": scene("Guards", "Guards", "A:Holt's still fuming about that beach.",
                              "B:Somebody had a word in Meg's ear.", when="$Attr.SmugglerSide=1", town="Court"),
    "Quiet_Market": scene("Guards", "Guards", "A:Not a smuggled keg in the market all week.", "B:Holt's happy.",
                          "A:Holt's never happy.", when="$Attr.SmugglerQuest>=4 and $Attr.SmugglerSide=0",
                          town="Court"),
    # ----- the other choices (build_choices.py: which way the old grove, the grain and Hob went, for you)
    "Grove_Felled": scene("Townsfolk", "Townsfolk", "A:My lad's at Bramble's mill now.", "B:Steady work?",
                          "A:Steadier than mine.", when="$Attr.GroveWay=1", town="Oakhollow"),
    "Grove_Felled_Sore": scene("Townsfolk", "Townsfolk", "A:Three hundred years, those oaks.", "B:And now planks.",
                               "A:Good planks, mind.", when="$Attr.GroveWay=1", town="Oakhollow"),
    "Grove_Kept": scene("Townsfolk", "Townsfolk", "A:Walked through the old grove today.", "B:Still there, then?",
                        "A:Rangers everywhere.", when="$Attr.GroveWay=2", town="Oakhollow"),
    "Grove_Kept_Sore": scene("Townsfolk", "Townsfolk", "A:Bramble was going to hire half the village.",
                             "B:Was.", "A:Was.", when="$Attr.GroveWay=2", town="Oakhollow"),
    "Hob_Wild": scene("Townsfolk", "Townsfolk", "A:Don't go near old Hob's.", "B:Still mad?", "A:Madder.",
                      when="$Attr.HobAngry=1", town="Oakhollow"),
    "Bread_Cheap": scene("Townsfolk", "Townsfolk", "A:Bread's cheaper this week.", "B:And last week.",
                         "A:Funny what a new Chancellor does.", when="$Attr.GrainWay=2", town="Galaith"),
    "Bread_Dear": scene("Townsfolk", "Townsfolk", "A:The Chancellor's cellars are full, they say.",
                        "B:And the bakers' bins are empty.", when="$Attr.GrainWay=1", town="Galaith"),
}


# ================================================================== the animals' sounds
def dog_bark():
    """Two barks: a rough voice, up and off, in a chest."""
    one = voice(290, 0.13, glide=-0.45, rough=0.6, seed=2)
    return mix((shaped(one, 0.003, 11), 1.0), (delay(shaped(voice(320, 0.12, glide=-0.5, rough=0.6, seed=3), 0.003, 12), 0.2), 0.9),
               (lowpass(shaped(noise(4, n(0.34), 0.2), 0.002, 18), 0.25), 0.25))


def cat_hiss():
    """Breath through teeth, rising and then cut off."""
    return shaped(breath(5, 0.6, 0.45, 0.25), 0.02, 2)


def main():
    conf = Ini(p("data", "Banter.ini"))
    conf.header = HEADER.rstrip().split("\n")
    for k, v in SETTINGS:
        conf.set("Banter", k, v, overwrite=False)
    for k, v in GROUPS:
        conf.set("Groups", k, v, overwrite=False)
    for key, (a, b, lines, after, when, sounds, town) in SCENES.items():
        sec = "Scene." + key
        if conf.section(sec) is not None:
            continue
        items = [("A", a), ("B", b)]
        for k, line in enumerate(lines, 1):
            items.append(("Line%d" % k, line))
            if k in sounds:
                items.append(("Sound%d" % k, sounds[k]))
        if after:
            items.append(("After", after))
        if when:
            items.append(("When", when))
        if town:
            items.append(("Town", town))
        for k, v in items:
            conf.set(sec, k, v)
    conf.save(p("data", "Banter.ini"))
    for name, sig, level in (("Dog_Bark", dog_bark(), 0.55), ("Cat_Hiss", cat_hiss(), 0.45)):
        path = p("sounds", name + ".wav")
        blob = wav_bytes(sig, level)
        if not os.path.exists(path) or open(path, "rb").read() != blob:
            with open(path, "wb") as f:
                f.write(blob)
    print("Banter: %d scenes" % len(SCENES))


if __name__ == "__main__":
    main()
