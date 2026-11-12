# Shards of Ashen: the story and its quests

A summary of the quests in the game as it stands, for planning the story and making changes. The main quest line
comes first, step by step; then the side quests, by region. The last section says where each quest lives in the
game's files.

## The secret of the Shards (the Cutting)

The heir's story stays; under it is what Shards are. (This replaced the earlier "Heart of Ashen" idea, the owner's
choice: the dragon should be a real villain, so killing it feels right.)

- **The dragon was a devourer**: a vast, hungry thing that swallowed the world's magic and wanted all of it. The first
  king found a way to **cut it down** (the **Cutting**): almost all of it he pushed out of the world into a hollow, the
  **Shardrealm**; what was left was small enough to bind. That's the dragon the heir meets.
- **Shards are scraps of it**, thrown off by the Cutting: its power and its hunger in small pieces, tamed enough to
  use, and still growing, and good at telling you what you want to hear. A dead beast's **remnants** go for whoever
  killed it because a scrap wants a body to grow in. Broken magic sinks into the Shardrealm, the rest of the dragon,
  asleep: its rim is the cooled edge, its core a storm where it dreams. The dragon could anchor its barrier there
  because it's its own place.
- **The Pact** is extortion: a royal firstborn each generation is what the dragon feeds on so it doesn't tear its
  barrier open, and the blood also keeps the Cutting's wound apart. The King's Shard Seam is where the first cut was made.
- **The dragon is a villain and killing it is right.** But the rest of it is still asleep in the Shardrealm, a shadow
  that stays after the dragon dies.
- **Mary** found the Pact's price while she studied at the Wizards' Court, and ran to learn how it was made. Her notes
  are found as you go.
- **Through the chapters**: Aldous's lesson on the Shards a dead beast leaves (take it in before it takes root in you); the Sunken Grimoire
  and the Ember Ring (the king's side: the Cutting told as a triumph; the Pact's seal); the Shardrealm's core (the
  dragon's sleeping body); the dragon, dying (what it carried); a stealthy part in The Royal Guard (Mary's notes in the
  Archive's sealed vault, past its watchmen at night); the **Glass Wardens** (below) for the rest; the King's Seam
  (the choice: the Binding, the Crown, or, with the Wardens' truth, Unmake).
- Before leaving the Isle you must know where Shards come from: Wim won't take you till you've picked some up off
  the ground (`RemnantsAbsorbed`: Aldous leaves three on the cave floor by the niche, and beasts drop them) and are level 3; he sends you to Brother Aldous. The ferries run for everyone else all along:
  it's only you, without papers, they won't carry.

## The world in brief

- **Ashen** is the kingdom. Its capital, **Galaith**, in a gap in the mountains at the far east of the mainland,
  holds the only land route across the world and the gold and Shard mines behind it. A dragon has kept it shut behind
  a magical barrier for eighteen years: every generation it was owed the king's firstborn heir, and Queen **Mary** ran
  from Galaith with her baby, you, to break the bargain. King **Rupert**, your father, is shut in the city.
- **The Isle**: a small island off the south coast, where you grew up poor and where every new character begins, at
  their mother's funeral. It has a village with a lawyer's and doctor's house, a farm and a smithy, a chapel with caves under it, a hermit
  and a ferry.
- **The mainland**: **Northport** (a large city, where the ferry lands; Ashen's Parliament sits in its City Hall
  while Galaith is lost), **Ashford**, **King Rupert's Keep** (the old Tyron's Keep, held by the King's Steward), the
  **Wizards' Court** on the Royal Isle, Fenwick, Ravensgate, Highwatch, Frosthold, Oakhollow, Thornwick, Emberwatch,
  Greyford, Dunerest, Wildwood and Saltmarsh, each the size the owner set (see `CLAUDE.md`).
- **The Cinderlands**: north of the Elderwood. Emberwatch, the Ashwold and the Cinder Peaks, where the Ashen Priest
  holds the Cinder Fort.
- **Dragon Island**: south of Ravensgate, by Captain Rook's ship. Drakes, and the Temple of Valour.
- **Galaith**: east over the causeway from the Elderwood, through the mountain pass and its barrier. The scorched
  field where the dragon waits, the city's white walls burnt black, the mountains meeting behind it, and a mine mouth
  behind the city.

---

## The main quest line

Twenty-four chapters, each unlocked by the one before it. Chapters 1 to 4 are the Isle (`build_heir_isle.py`); 5 to
24 the mainland and Galaith (`build_heir_mainland.py`, with `build_galaith.py` for the city and its pass). The middle
(12, 13 and 18 to 21: `build_middle_quests.py`) leads you round the world a zone at a time, a piece of gear at each,
and each place's keeper names the next: never a letter or a sign.

### On the Isle (the tutorial)

| Ch. | Quest | What you do |
|---|---|---|
| 1 | **The Last Will** | You stand at your mother's fresh grave by the chapel. The mourners go; **Edwin** the lawyer walks you home and leaves her letter on the table. The cottage door stays locked until you've **read the letter** (three pages, in the owner's words): you are the heir of Ashen. Jimmy sleeps on her empty bed. |
| 2 | **Dinner at Edwin's** | Edwin the lawyer asks you to dinner. **Maren**, his wife, is the Isle's doctor (their house is two storeys of brick by the chapel, her surgery and his desk downstairs; it was the bank. They live upstairs, and go up at night). **Chop 3 logs** for her range (she lends an axe), **take an egg** from Bess's coop and **fry it** on her range, give it to Edwin. Reward: the key to the chapel's trapdoor, and a promise not to go down without a sword and shield. |
| 3 | **The Amulet of Succession** | **Bess** the milkmaid tells you Wim needs papers, and that her father wrote them. Her husband **Frank** the blacksmith (smoke from his chimney by day) helps you **make a wooden sword and shield**. **Brother Aldous** lets you down once you wield both and Attack and Defence are level 2. The amulet lies **behind bars** at the back of the caves: Aldous brings a **Grasp** scroll. Reward: the amulet and the key of the hobgoblins' lair. |
| 4 | **Passage to the Mainland** | Bess's father **Tobias** is missing and his house (Maren & Bess's Father's Home) is locked. The **hobgoblins' lair**: four hobgoblins (no new ones until you leave), the house key in the corner barrel, Tobias in a cage you **pick the lock** of (the lock minigame: set each pin as it crosses the line; three slips and you start again). He gives you his house and moves in with Maren at the bank. A hidden ladder climbs into a tent in their camp on the surface (only a tent until it's been climbed from below). In the house a **floorboard squeaks**: under it, the **papers** Mary left with him for you, under a crowned seal (what the hobgoblins were after). **Wim** reads them and lets you aboard, for a coin; at Northport the **port guard** reads them too and sends you to the Speaker. In the demo, the ferry goes no further: with the papers, the demo's end card shows what the Isle gave you and what's left to ask (the order in ash, the miniature, if found), and the full game goes on from there. |

### The road to the Wizards' Court

| Ch. | Quest | What you do |
|---|---|---|
| 5 | **The Temporary Capital** | The guard at Northport's port says Northport is the temporary capital. The **Speaker**, in the City Hall (the Parliament), says only **Bert**, the great wizard of the Wizards' Court, can break the barrier, and gives you a letter for the Mayor of Ashford. |
| 6 | **The Ashford Road** | The **Mayor of Ashford** (the Town Hall) wants the goblins raiding the farms east of town driven off (a wave at the farm crossroads). Reward: the Mayor's pass. |
| 7 | **The Steward's Hunt** | The **King's Steward** at King Rupert's Keep wants **five hobgoblins** slain in the old iron mine. Reward: 100 gold, a ruby, and the causeway to the Royal Isle. |

### Bert's three treasures

| Ch. | Quest | What you do |
|---|---|---|
| 8 | **Bert's Three Treasures** | **Bert**, at the top of the Wizards' Court's tower, needs three things to break the barrier: |
| 9 | **The Staff of Ashen** | The Steward's key opens the stair to the **King's solar**, at the top of the keep. Its old skeleton guard; the staff on its rack. |
| 10 | **The Sunken Grimoire** | The scholar **Yusra** in Dunerest: the Grimoire of Unbinding is in the sun priests' **buried library**, under a sand mound in the desert north of town (dig it out with a spade). A tomb guardian. |
| 11 | **The Ember Ring** | The **Warden** in Emberwatch: the **Ashen Priest** wears the ring, in the Cinder Fort. Take it from him. |

Bert only wanted the ring (it goes with his new robe, and he can't stand the Ashen Priest): chapter 8 ends with his
confession. He teaches you the spell of Unbinding, gives you the staff, and warns that only the **Sword of Valour**,
driven into its heart, kills the dragon.

### Orrin's chart and the Lodestar

| Ch. | Quest | What you do |
|---|---|---|
| 12 | **Orrin's Chart** | (level 10) **Captain Rook**, on the shore below King Rupert's Keep, would sail to Dragon Island, but its reefs move and he won't try them without the chart of **Orrin**, a navigator who climbed the **Sundered Tower** in the Shattered Reach and never came down. Orrin's ghost is at the top: his **Shadow**, below, has the chart; kill it and he gives it you. Reward: a mithril helm, 40 Shards. |
| 13 | **The Frozen Lodestar** | (level 12) The chart wants the **Lodestar** to read it by, and its shrine went under the ice in the Rime. **Nils** the surveyor at Frostwatch Lodge knows where: the **Drowned Shrine**. The **Rime Warden** stands over its altar; past it, Reach In for the Lodestar and take it to Rook. Reward: a mithril shield, 40 Shards. |

### The Sword of Valour

| Ch. | Quest | What you do |
|---|---|---|
| 14 | **A Ship for Dragon Island** | (level 13) With the chart and the Lodestar, Rook will sail if you bring 10 planks and 20 nails for his hull. |
| 15 | **The Island of Dragons** | Sail to **Dragon Island**. Three **Valour Seals** from its drakes open the Temple of Valour. |
| 16 | **The Sword of Valour** | Defeat the temple's **Guardian of Valour** and draw the sword from its stone. |

### Galaith

| Ch. | Quest | What you do |
|---|---|---|
| 17 | **The Shardgate** | Raise the staff at the barrier and it **holds**: something beyond the world feeds it. **Bert**: the dragon anchored it in the **Shardrealm**, where all broken magic goes. Shardstones reach only the realm's calm **rim** (where your homestead's pocket is, he says); the anchor is in its **core**, a storm, and only a great anchor can pierce it. He gives you his plans: build a **Shardgate** in the old ring of standing stones on the hill north of the Wizards' Court (4 silver bars, 2 sapphires, a Remnant's core, 30 Shards, Shardcraft 5, and at least **8 shardstones active** to steady it). It shows on your world map once it's built. Through it, the realm's core: get past its **Warden** and shatter the barrier's **anchor** with the staff, then tell Bert. Reward: 30 Shards, Channeling and Shardcraft experience. The gate stays: go back for the realm's Shard Remnants and its clusters (a few Shards every 8 hours). (A character who broke the barrier before this chapter was written gets it from Bert.) |
| 18 | **The Sleeping Sword** | (level 14) With the anchor gone the staff only **thins** the barrier. Beyond it the dragon wears a hide of **Shards** (the Ashen Hand has fed it through the wall) and laughs at the Sword of Valour: it's asleep. **Bert**: it was made in three fires, and must be woken in them again. The first was the Ashen Foundry; ask the Warden at Ashfall Outpost. |
| 19 | **The Ashen Foundry** | (level 15) **Warden Oska** at Ashfall Outpost: the **Forgemother** holds the Foundry. Break it, then work the **bellows** till the fire is hot enough (three pulls: a fourth and it chokes, and you start again) and Temper the sword at the **hearth**. Oska names the second fire: the Sun-Forge, and the nomad who knows it. Reward: a mithril platebody, 60 Shards. |
| 20 | **The Sun-Forge** | (level 17) **Nomad Tarek** at the Sun-Forge's temple (south of the well): the **Sun Keeper** still holds it. Break it, then turn the three **mirrors** to his grandmother's song (dawn to the east, noon to the south, dusk to the west) and Temper the sword at the forge. Tarek names the third: the Deep Anvil, and the delver who keeps the old hall. Reward: a dragonscale helm, 70 Shards. |
| 21 | **The Deep Anvil** | (level 19) **Delver Maud**: the **Stone King** sits the old dwarf hall's throne. Break it, strike the four **rune stones** in the work-song's order (Root, Rock, Hammer, Crown: a wrong one and they go quiet), and Temper the sword on the anvil: in your hand it's the **Woken Sword of Valour**, its wear kept. Reward: a dragonscale platebody, 90 Shards. |
| 22 | **The Dragon of Galaith** | (level 20) West to the pass in the West Range. **Use the staff on the barrier** (with Bert's spell learnt) and, with the sword awake, it shatters. The dragon speaks (the bargain, your mother's flight) and the boss fight begins: nothing but the **Sword of Valour** (woken or not), **wielded**, gives it its death blow. The city's gate onto the field opens. |
| 23 | **The Royal Guard** | Explore the city to win the guard over: the **captain** at the palace door sends you to the **Lord Chancellor** (the Parliament), who sends you to the **Royal Archivist** (the City Hall) with your mother's amulet; her word to the Chancellor; his warrant to the captain. |
| 24 | **The True Heir** | **King Rupert**, on his throne: show him the amulet, tell him the will. He holds you and weeps, and gives you the crown. From then the world is open play; **Jimmy** curls up on the throne, and in your house on the Isle. |

**Unlocks:** the mine behind Galaith (once you're king); the Wyrmsmith's Dragonforge in Wardhaven (The Dragonforge).

---

## Side quests

### On the Isle

**The Hermit's Fire**: *Woodcutting 5*
The hermit in the Isle's western woods wants 5 oak logs. Reward: 25 gold, an oak staff, Woodcutting experience.

**What Jimmy Kept**: *after The Amulet of Succession* (`build_isle_secrets.py`)
Brother Aldous kept one more thing of Mary's: a charm, a scrap of verse ("Velvet paw and whisker-wise, see the house
with Jimmy's eyes") and "Jimmy knows where." Read it aloud and you're a cat for two minutes (`Turn.Into`, the Isle's
body swap). As a cat, Jimmy talks to you: there's a gap behind the cottage, too small for anyone with hands.
Squeeze through it: a miniature of a crowned man, a baby in his arms. Reward: 10 Shards, Channeling experience.

**Tobias's Tin**: *after Passage to the Mainland's lair* (`build_isle_secrets.py`)
Tobias, safe at the bank, asks you to fetch his savings tin from the hobgoblins' chest in their camp, and teaches you
to sneak: two lookouts at the camp (2,2,0) stand facing the gate and turn now and then; walk in and the whole camp
comes for you, sneak round the east side behind them and they never know. Show him the order from the lair and he
tells you what it means. Reward: 25 gold, 5 Shards, Stealth experience.

### Ashford and King Rupert's Keep

**A Place of Your Own**: *after chapter 4*
The settler by Ashford's shardstone wants 10 planks and 4 stone blocks, made at her carpenter's bench (planks from
logs, blocks from stone mined with a pickaxe). Reward: the **Hearth Anchor**, which holds a pocket of the
**Stillwater** for you (any shardstone you've activated takes you there), and Homesteading experience. The pocket
starts as raw rim, glass in mist: you terraform it with Shards and Shardcraft, and grow Shard Blooms in it. In
chapter 15 Bert says what the Stillwater is: the calm rim of the Shardrealm.

**Granny Wren's Walk**: *after chapter 4*
An old woman off the ferry at Northport's landing, Granny Wren, can't see well enough to find her way to her
daughter Percy's in Ashford. **Lead her there**: she follows you, a step or two behind and slower than you walk
(Follow.Player), and waits if you go far ahead. At Percy's door talk to either of them. Lose her (log out) and she's
back at the landing, waiting. Reward: 30 gold and a berry pie; she lives at Percy's after.

**A Portrait of Mo**: *after chapter 4*
Ottilie paints at her easel in Ashford's market square, and the painting wants a cat: Mo, who never keeps still.
**Stroke Mo while Mo is sitting** and Mo settles for her; at any other moment it comes to nothing, each its own way
(mid-stretch; showing you its back end, to Ottilie's delight; or trotting off). Tell Ottilie: she paints. Reward: the
painting (Portrait of Mo) and 25 gold. (The scripts check what Mo is doing: >Entity.State, Set.NPC.State.)

**The Herbalist's Remedy**: *level 2, after chapter 4*
The Herbalist in her cottage on the Ashford farmlands wants 3 cave mushrooms (the old iron mine) and 2 spider silk
(giant spiders in the mine depths). Reward: 60 gold, 2 super potions, Alchemy experience.

**The Smugglers' Run**: *after chapter 4*
Sergeant Holt at the castle's south gate wants to know how smuggled goods reach the market. The fishermen mention
an old barrel on the lake path that nobody moves. **Search it**: it hides a tunnel to a smugglers' camp on the
cove. **Sneak to their leader, Red Meg, unseen.** The smugglers only see ahead of them, never through cargo,
tents or walls. Meg offers a deal (her trade stays off Holt's streets if his men stay off her cove). It ends one
of three ways (`SmugglerSide`, the journal says which):
* **The truce** (0): carry her deal to Holt. 60 gold; the smugglers are friendly and Meg's shop is open to you.
* **Meg's way** (1): tell her you'll send Holt to the wrong cove, and do. 60 gold, but the Court thinks less of you
  (-15). The smugglers are your side; her camp has a cot and a stash (your bank) for you, and a trapdoor to her tunnel,
  which comes up in a field outside Ashford.
* **Holt's way** (2): take her truce, then tell Holt where the camp is. His men wait in the camp; four smugglers must
  fall (your men's kills count: `SmugglerRaid`). Meg gets away by sea. 60 gold, the Court thinks more of you (+20), and
  the watch's quartermaster outside the Court's gate sells to you.

**The Tide Turns**: *Holt's way only*
Holt has word of Meg on a sandbar off the coast. Row the watch's boat out from the cove's shore, beat her two lads
(`TideGuards`), and she gives herself up. Reward: 80 gold. (`TideQuest`.)

**Under the Tide**: *Meg's way only*
Meg's job for a friend: a cask of brandy for Pell, the cellarer in the Wizards' Court's courtyard. Two watchmen walk
the courtyard while you carry it; if one sees you, the cask's taken and you're put out of the gate (Meg gives you
another). Reward: 90 gold and Stealth experience. (`UnderTideQuest`.)

**The Wardhaven Bridge**: *after chapter 6*
Mayor Hollis in Ashford's Town Hall: goblins have taken the bridge to Wardhaven, the walled town on its island north
of the farms, and the bridge guards fled. **Clear the four goblins off the bridge** (they're there for you while the
quest is on, as many as you've left), and tell the Mayor. Reward: 80 gold; Wardhaven's gates open to you, and the
guards are back at the bridge whenever you come by again. (`WardhavenQuest`, `BridgeGoblins`; the gate map's entry
script puts the goblins and the guards there.)

**The Dragonforge**: *after chapter 15*
The Wyrmsmith of Wardhaven keeps the only forge hot enough for dragon scale. Once Galaith's dragon is dead, bring her
**three of its scales**: she makes you a **dragonscale helm** and teaches you the forge (dragonscale armour from scales
and mithril bars, with Smithing). (`DragonforgeQuest`.)

**The Dwarf's Grudge**: *level 4, after chapter 7*
Brokk the dwarf, in the Deep Hollow (through the hatch in the hobgoblin warren), wants 4 skeletons smashed and the
cave troll slain. Reward: 150 gold, 2 sapphires, a steel sword, Mining experience.

### The Wildwood and Oakhollow

**The Wildwood Watch**: *level 3, after chapter 7*
Ranger Ash in Oakhollow sends you to visit the three old watch stones (the north road, the western woods, the
river), then to clear the spider nest west of Oakhollow (5 giant spiders). Reward: 120 gold, a yew staff,
Attack and Woodcutting experience.

**The Old Grove**: *after The Wildwood Watch*
Master Bramble, a timber merchant in Oakhollow, wants the old oaks south-east of the village felled; Ranger Ash wants
them kept. Side with one (`GroveQuest`, `GroveWay`):
* **Felled** (1): cut Bramble's mark into the great oak in the grove. 150 gold. The oaks are stumps for you, and
  Bramble's sawyer Tom sells cheap planks and logs there.
* **Kept** (2): drive off Bramble's two woodcutters in the grove (`GroveCutters`). 80 gold and Woodcutting experience.
  The rangers keep a lodge there: Warden Ivy sells rare herbs, arrows and an oak bow, and there's a cot to sleep on.
Either way: 10 Shards and Oakhollow +5. The village is split, and says so.

**Old Hob**: *after Bog Lights*
Old Hob of Oakhollow is missing and his house is boarded up, but a shutter hangs loose. His diary says a giant
spider bit him and he feels himself going wild. Ask Morwen for a cure, find the wild man in the Wildwood's western
woods, and use her calming draught on him. **A choice** about his chest (150 gold, which you may have already
emptied):
- He offers his savings to you; or
- if you took them, **give them back** (he rewards you 40 gold, keeps you as a friend) **or keep them** (the
  madness takes him again and he attacks, for good).
Oakhollow hears which (`HobAngry`): +10 for the first two, -15 for keeping them.

### the Greyflats, the Saltmarsh and the Redrock road

**Wolves of the Greyflats**: *level 3, after chapter 4*
The shepherd in Greyford: slay 6 moor wolves, then find the wolf den out east on the flats and kill the Alpha Wolf.
Reward: 150 gold, a steel shield, Defence experience.

**Bog Lights**: *level 3, Potion Making 3, after chapter 4*
Old Morwen the witch in Fenwick wants 4 bog myrtle. She brews something for Elder Pike; take it to him, then tell
her he drank it. Reward: 80 gold, 2 mega potions, Alchemy experience. (Morwen returns in *Old Hob*.)

**Bandits on the Road**: *level 5, after chapter 4*
Captain Hale in Highwatch: slay 5 bandits, then find their camp in the eastern hills and take the stolen goods
from their strongbox. Reward: 200 gold, a steel platebody, Attack experience, and Frosthold +10. Or, if you
sided with Red Meg in The Smugglers' Run, she'll buy the goods: 300 gold, and Frosthold -10 (`BanditWay`: 1 Hale's,
2 Meg's).

**The Redrock Signet**: *level 6, after chapter 4*
Ambrose, the last steward of Redrock Manor, thrown out by the bandits who hold it, waits on the road by its gate. The
old lord built the house so no thief could find his way about it (rooms with no doors, stairs to nowhere), and the
bandits have never found the vault. Bring him the family's signet from it. Beside the signet lies the old lord's scroll
of Dread (a spell that sends a foe running), yours with his blessing. Reward: 120 gold, Shards, Stealth and Attack
experience. Once you've taken the quest, Spleen, the bandits' chief, waits outside the manor's door to buy the signet
(`RedrockWay`):
* **Sold** (1): 130 gold more. Ambrose is gone from the road, and the bandits at Redrock are your friends.
* **Given back** (2): the bandits are thrown out, and Ambrose is home: a chair by his fire to rest in.

### The desert, the north and the downs

**The Lost Caravan**: *level 6, after Bandits on the Road*
Qadir the merchant in Dunerest: find his caravan wreck in the desert west of town, slay the scorpions there and
bring back its ledger. Reward: 180 gold, 2 rubies, Crafting experience.

**The Frozen Forge**: *level 7, after chapter 4*
Brann the forgemaster in Frosthold: bring 5 coal to light his forge, slay the Frost Troll that smashed his
waterwheel (on the frozen lake), then bring 2 mithril bars. Reward: 250 gold, a
mithril sword, Smithing experience.

**The Withering Wood**: *level 6, after Wolves of the Greyflats*
The Druid in Thornwick: touch the Heartwood, the Elderwood's old heart stone, then slay 4 blight-maddened bears.
Reward: 150 gold, an emerald ring, Alchemy and Woodcutting experience.

**The Barrow King**: *level 8, after The Withering Wood*
The Gravekeeper in Ravensgate: find the old king's barrow on the downs and lay the Barrow King to rest. Reward:
250 gold, a mithril helm, Defence experience.

### Galaith

**The Chancellor's Grain**: *Galaith, after The True Heir*
The Royal Archivist believes the Chancellor hoarded the city's grain in the hungry years. His ledger is in the
locked, iron-bound strongbox by his desk in the City Hall (pick it). Then (`GrainQuest`, `GrainWay`):
* **His bribe** (1): give him the ledger back. 250 gold, the run of his stores (a shop), and the key to the City
  Hall's treasury (300 gold and a sapphire, once). The Archivist never speaks to you again.
* **The captain** (2): give it to Captain Hart at the palace door. 100 gold; the Chancellor is taken below and the
  Archivist is Chancellor in his place; Galaith +20, and Galaith's bread is cheaper for you (Towns.ini
  `Cheaper.If`).
Either way: 15 Shards.

### The Cinderlands

**The Lost Patrol**: *level 7, after chapter 4*
The Scout in Emberwatch: her patrol never came back from the Ashwold. Recover 3 Scout's Tags from the ember hounds.
Reward: 200 gold, a yew bow and 100 arrows.

### The Wizards' Court

**The Shard Scholar**: *after chapter 4*
Magister Quill, in the great hall of the Wizards' Court, has spent forty years on the Shards. Bring him fifteen (you
hand them over only when you say so). He tells you what they are: the Old Ones bound the land's magic into the
shardstones; the dragon drank Galaith's mountain's down and shattered what it couldn't hold. That's why shardstones
must be fed, why beasts that swallow Shards carry them, and why the mountain behind Galaith was the richest seam of
all. Reward: a scroll of Frost Nova and Channeling experience. His answers about the Shards are there to ask any time,
and why a potion isn't a spell: Shards reach out of you, herbs work within; Shards can't mend a body.

**The Invisible Apprentice**: *after chapter 4*
Pip, apprentice to the Wizards' Court, drank his own invisibility potion three days ago and keeps getting sat on.
Bring him an egg, a feather and two cave mushrooms for the cure. It cures everything but his spectacles. Reward: two
Invisibility Potions (and the recipe, at the alchemy table), a scroll of **Swap** ("I spent last Tuesday as a cat"),
10 Shards.

**Pip's Spectacles**: *after The Invisible Apprentice*
Pip squints through the Magister's spare spectacles: his good ones went missing the afternoon a cat had his body. Only
the animals know, and they talk only to another animal. He gives you another Swap scroll.
1. In an animal's body, ask **Inkwell**, the Court's cat (in the courtyard): she remembers better with a fish inside
   her.
2. As yourself (no hands as an animal), feed her a fish (poultry won't do), then ask her again as an animal: she took
   the spectacles off because they made everything wobbly and dropped them; **Biscuit**, the dog outside the gate, ran
   off with them.
3. As an animal, ask Biscuit: he gave the "shiny stick" to his friend **Henrietta**, a hen by the pond.
4. As an animal, ask Henrietta: she's been sitting on them, hoping they'd hatch. They haven't.
5. Rummage in her nest (as yourself) for **Pip's Spectacles**, and take them back to Pip. Reward: 40 gold, 15 Shards,
   Channeling experience. Pip can see faces again.

**Lady Pettigrew's Hat**: *after The Invisible Apprentice*
On Goose Green, east of Northport, the geese have Lady Pettigrew's hat on their nest, and they are not reasonable
geese. Go unseen (an Invisibility Potion), or swap bodies with her goose Gerald and walk in as one of them. Reward: 60
gold, 12 Shards. Gerald does not apologise.

**Granny Bramble's Practice Hex**: *after The Invisible Apprentice*
A hedge witch at Fenwick's market practises a hex on you: your Attack drains to nothing for ten minutes. Then she
wants the four market rats seen to. Your sword arm's no use: a spell, a potion, or someone else's body. Reward:
Antidotes, 15 Shards, Channeling experience.

**The Shifting Deep**: an old Shard mine by the road south of Greyford, its tunnels never where they were. Three
floors of rooms and tunnels, monsters stronger the deeper you go, chests (once each, a shift; sometimes one bites),
traps hidden underfoot (darts, gas, a weakness rune, a bell that brings remnants, a pit that drops you a floor), a
secret room behind a cracked wall on each floor (Search it), and at the bottom, past its Warden, the Deep's Heart:
Shards. Every hour, once nobody's down there, it shifts, and it's all new.

**Bert's tower's secrets**: a cat flap low in the wall (only a cat fits: Bert's biscuit tin, 25 Shards and his pie)
and a big red button that shouldn't be pressed (a chicken, a bucket of water, confetti, or a goose).

**The Hollow Hill** (`dev/migrate/build_hollow_hill.py`): where Northport's west road runs into the range (2,4,0),
a cave mouth; Enter it. The cave below (2,4,-1) winds back under the mountain: bats and rats near the way in, coal,
copper and ore to mine, a pool, cave mushrooms, and at the back a spiders' chamber with an old cache in a chest
(each player's own, once). Steps lead back up to the daylight.

**Secrets in every settlement** (`dev/migrate/build_whimsy.py`): by each town's square stands something to Search (a
hollow stump, a loose cobble, an odd barrel, an old statue, a well), each with its own find and its own line: Shards,
gold, potions, a rubber duck, a lucky sock, a key that winks. Once each; five, ten and all seventeen found are noticed
(the attribute SecretsFound) with more Shards.

**Traps in the old dungeons**: the barrow, the desert library, the iron mine and the bandits' caves have plates
underfoot (Trigger `Trap_<Kind>`): darts, gas, a weakness rune, a shallow pit, an alarm that wakes a remnant, a bucket
of icy water, a custard pie. Each rests ten minutes after it springs.

**The Scarecrow's Hat**: *after chapter 4*
A scarecrow in the fields outside Oakhollow has been thinking for twenty years, out loud, and his head's cold. Bring
him a hat, any hat (a chef's hat makes him want to cook). Reward: 8 Shards, Homesteading experience, and a thought.

**Duchess Has Opinions**: *after chapter 4*
A cow outside Ashford can talk, and nobody's noticed. The grass is terrible: bring her three bunches of herbs. Reward:
a bucket of milk, 8 Shards, Homesteading experience.

**The Mayor's Missing Trousers**: *after The Ashford Road*
Constable Dobbs, in Ashford's square, needs it kept quiet: the Mayor's trousers went off the washing line. Search the
square for three clues (webbed footprints, a snapped line, a big white feather) and tell him who did it. It was a
goose. Reward: 50 gold, 10 Shards, Defence experience.

In an animal's body (Swap, or the red button), animals talk to you: cows, sheep, hens, ducks, geese, rabbits, cats,
dogs, frogs and seals each have something to say. Ordinary townsfolk have more to say, too.

**The Spellwright**: *after The Shard Scholar*
How does a Shard know what shape a spell is? Bring Quill the core of a risen Shard Remnant, then pick up twenty more
Shards where beasts fall and tell him how it felt. He teaches you to write a spell of your own at the **Spellwright's Lectern** by the
throne in the great hall: choose its effect (a bolt, a burst round you, a frost that holds foes, a ward), its power
(as far as your Channeling goes) and its reach; its Shards and rest are worked out to balance. Write it again whenever you
like, for a few Shards. Reward: 20 Shards, Channeling experience.

### The zones' points of interest (`build_middle_quests.py`)

Bosses of their own, each with a trophy, and side quests, games and odd folk round the main quest's places:

- **Bosses**: the **Scavenger King** on Bonebreak Mesa, **Old Whitefang** by Yeti Hollow, the **Slag Wyrm** in the Lava
  Fields, the **Sand-Mother** at the Drakes' Bones.
- **The Brother in the Ash** (`CaelQuest`, level 14, after The Shardgate): **Cael**, a penitent of the Ashen Hand at the
  Cinder Chapel, prays with his back to the others. He asks you to take his letter to his sister, **Warden Oska** of
  Ashfall Outpost; her answer back to him; his confession (Read it). Reward: a Ward Shard, 30 Shards.
- **The Wandering Echo** (`EchoQuest`, level 10): a voice on **Shardglass Field** asks three riddles nobody has stayed
  to answer (a Shard; the Shardrealm; under the world). A wrong answer and it starts again; each one right rings out 10 Shards, the last the quest's 45.
- **Old Skadi's Tall Tales** (`SkadiQuest`, level 12): at Frostwatch Lodge, three tales; say which are true and which
  lies. Reward: wool mittens.
- **Games and odd folk**: **Lucky Lem**'s rat races at Rustwater Halt (Bet on the track), **Vesna**'s fortunes at Ashfall
  Outpost, the **Mirage Trader** (the desert's odd goods; every time you look away he's a little further off), the **Echo Pool** in the Fungus Grotto
  (Listen, then sing its tune back), **Fenn**'s mushrooms at the Delvers' Camp.

### The wild places (`build_wilds.py`)

Something in each of the mainland's empty corners and dead ends, none of it needed by the story:

- **The Ringing Rocks** (1,7: a hollow in the mountains west of Northport): **Tamsin** and five veined stones, each a
  note. She rings a tune, you ring it back (the CHIMES minigame), a note more each round: three tunes, longer each time
  (`RingingRocks`: gold, then an emerald, then 8 Shards), then as many as you like for fun.
- **Abel's Lambs** (`LambQuest`, 5,9): **Abel**'s three lambs got over the river. Catch them (two on the far bank, one
  up by the bend). Reward: gold, wool, 4 Shards.
- **The Collier's Clamp** (`CollierQuest`, 6,14): **Hode** wants 5 logs for his charcoal clamp. Coal and gold; after,
  3 logs for a coal whenever you like.
- **The Toll-Keeper's Riddles** (`TollRiddles`, 2,14: where the road stops in the woods): the toll-keeper's ghost
  asks three riddles (a shirt; footsteps; himself). A wrong answer and he sulks a minute. Reward: gold, 6 Shards.
- **Merrin's Mead** (`BeeQuest`, -9,10): bring **Merrin** 3 honeycombs. Smoke a skep (a tinderbox), then Take Honey
  within half a minute, or the bees say so. Reward: mead, 4 Shards; honey whenever you like.
- **The Fen Horn** (-7,8): Blow it, and a coffer comes up out of the black pool for a minute, for everyone (its loot
  and 5 Shards once each).
- **The Frog King's Pearl** (`FrogQuest`, -11,4): **Mother Natter** makes you a frog to talk to the Frog King; the heron
  has his pearl, and a frog can't climb her nest; then a frog again to give it back. Reward: gold, 6 Shards, the
  fish bite a while.
- **Pell's Pick** (`DelverQuest`, level 14, -5,8): **Pell**'s ghost in the Stoneways; the wraith in its east tunnel
  (`Kill Stoneways_Wraith`) has his pick. Reward: a steel pickaxe, gold, 6 Shards.
- **The Castaway's Letters** (`CastawayQuest`, 0,22 and 1,23): **Salt Agnes** has seen three bottles; Tobin's letters
  lead to his cairn on the grass by the shore (Dig, a spade). Reward: a ruby, gold, 8 Shards.
- **The Smugglers' Signal** (27,12): Light the pyre (a tinderbox and 3 logs) and **Marro** rows in and trades for five
  minutes, for everyone, then rows off.
- **The Ward-Circle** (21,9): Wake the plinth and hold the circle against wisps and golems (the wave
  `Ward_Circle_Trial`, once each half hour); 8 Shards the first time it holds.
- **The Ice-Fishers' Camp** (18,23): **Ulla** and a salmon hole; Chip At the man frozen in the ice (a pickaxe, three
  goes) for what he held: a sapphire ring, gold, 6 Shards.
- **Three fairy rings** (19,10, 10,1 and -11,19; not on the world map): Step In one and out of the next; all three
  and 10 Shards.

### The Shardfall Deep (level 20 and up)

Under the sea north of Ashford, a great cave where a great Shard fell long ago, and the hold the first
king's Glass Wardens built beside it (`dev/migrate/build_shardfall.py`).

**Glass in the Nets** (`ShardfallGate`, the way in). Nell Tarrow, a fisherwoman at Gull Point (the tip of Ashford's
peninsula), pulls glowing glass out of the sea. The sea cave in the point's rocks goes down to a door of black glass,
the Wardens' Seal; Nell sends you to her grandmother Bryony, who gives you her late husband's Warden's Signet. Pour
100 Shards into it at the Seal, with Shardcraft 15, and it opens (for you). Reward: 40 Shards, Shardcraft.

**Charting the Deep** (`DeepChartQuest`). Pell Varrow, a cartographer camped in the Lantern Wood, wants five places
on her chart: stand in the Brinewater, Leviathan's Rest, by the Singing Geode, in the Wardens' Hold and in the
Shardfall. Reward: 600 gold, 40 Shards.

**The Brine Mother** (`BrineQuest`). Morrow the angler (the same camp) wants the Brine Mother dead, on the
Brinewater's north shore. Reward: the Brine Pearl Ring, 500 gold, 30 Shards.

**The Last Watch** (`WardenQuest`). Ysolde, the last Glass Warden's ghost, keeps the Hold's gate: end Marshal Corvane,
the Hollow Marshal, in the Great Hall, and bring her his seal. The Reliquary's iron door opens to you (its chest: the
Wardens' Aegis, a Lightning scroll II). Reward: 60 Shards.

**The Fallen Shard** (`FallenShardQuest`, after The Last Watch). Break the Shardborn in the Shardfall, then lay your
hand on the Fallen Shard and hear what the Wardens heard. Reward: the Shardglass Blade, 80 Shards. After it
the Fallen Shard gives Shards once a (real) day (Draw From).

#### The Glass Wardens (a secondary storyline in the Deep)

*Built by `dev/migrate/build_glass_wardens.py` (the hooks in the old Deep scripts by `build_shardfall.py`; Unmake at
the Seam by `build_kings_seam.py`). Written to be read by a twelve-year-old and still be worth an adult's time: plain
words, one big idea, and the frightening parts kept gentle. It builds on the Deep as it stands (Ysolde, Corvane, Hale,
the Brine Mother, Nell and Bryony, the five quests above) and changes none of their stages, rewards or attributes.*

**Where it differs from the first plan.** Mary's page in the Listening Room is gone: she couldn't have got past the
sealed door, so the Voice says she asked its sparks instead (what she learnt, she learnt from the Shards outside). The
Quiet Draught is glowfin and a **cave mushroom** (there's no shore salt in the game). Unmake gives the hammer-head and
no statue or title yet.

**The idea in one line.** The Shards are scraps of the dragon, and they're still a little bit of it: hungry, growing,
and very good at telling you what you want to hear.

**The truth under the whole game (replacing the Heart of Ashen).** The dragon was a **devourer**, a vast, hungry thing
that swallowed the world's magic and wanted all of it. The first king found a way to **cut it down**: almost all of it
he pushed out of the world into a hollow (the **Shardrealm**), and what was left was small enough to bind. That is the
dragon the heir meets. The cutting threw off scraps: those are **Shards**. They are not a crystal, not a treasure and
not gentle. They are its power and its hunger in small pieces, tamed enough to use.

- **Remnants hunt their killer** because a scrap wants a body to grow in.
- **The Shardrealm** is the rest of the dragon, asleep. Its rim is the cooled edge; its core is a storm where it
  dreams. It's why broken magic sinks there, and why the dragon could anchor its barrier there: it's its own place.
- **The Pact** is extortion, not a bargain. A royal firstborn each generation is what the dragon feeds on to keep
  from tearing its barrier open. The King's Shard Seam is where the first cut was made.
- **Killing the dragon is right.** It's a villain, and nobody should feel bad about it. But the rest of it is still
  asleep in the Shardrealm: a **shadow** that stays after the dragon dies.
- **Shardcraft** is learning to use its power without being used by it.

**What the Wardens learned, one piece at a time** (each found, none told; a journal, a vision or a person gives one
piece, and the last quest puts them together):

1. **The Shard grows.** Hale measured it for years: a hair a year, always. A scrap of the dragon that is growing back.
2. **It sings, and the song is a voice.** It tells you what you want, and offers it. If you answer, you're lost.
   Corvane answered. (Mary's note: *listen, but never answer it.*)
3. **It is calling something.** The Wardens heard something very large answer, a long way down.
4. **The first king's orders were fear.** He told them to keep it asleep. If the scraps were ever joined to the rest,
   the cut would heal and the dragon would come back whole.
5. **The Seam is a wound the Pact keeps open.** The firstborn's blood holds the cut apart: the dragon's price is also
   its prison. Break the Seam itself and the shadow fades. The Order died knowing this and could not get to it.

**Why this fits the rest of the story.** Aldous's remnants lesson now means *take it in before it takes root in you*.
The Sunken Grimoire and the Ember Ring are the king's side, the cutting told as a triumph. The Shardrealm chapter's
core is the dragon's sleeping body. Mary's notes stop at the Pact's price; the Voice tells you the rest of her: she
asked its sparks, outside, and they told her more than she wanted.

**Tone rules for every line in this chain.** Short sentences. Say it with an image, not a lecture (a plant growing
in the dark; a song you can't stop humming; a voice that knows your name). Nothing gory. Ghosts are sad and kind,
never scary for its own sake; the dragon's voice is the only thing that is truly sinister, and it is charming. A sign
still never hints, and nothing is laid out: the finale puts the pieces together, it doesn't announce them.

**How it starts: above ground.** The chain begins where Glass in the Nets does: Nell Tarrow at Gull Point. Two
more doors lead in without anyone being told: Ashford's rumours (the glowing nets; the woman who asked questions in
every library) and one of Mary's notes naming the Order. A player who ignores it loses nothing.

**Shape.** A gate, a wide middle you can do in any order, one finale.

```
Glass in the Nets (the gate: the Seal)                         [exists]
├── Charting the Deep (Pell)                                   [exists]
├── The Brine Mother (Morrow)  + Odile's Log (new, one line)   [exists, one addition]
├── The Last Watch (Ysolde) ── The Fallen Shard                [exist, one addition: the vision]
├── The Wardens' Words (Pell): six lost journals, nine in all  [built]
└── The Four Notes (found by listening at the Singing Geode)   [built]
        ↓  The Fallen Shard done, and the Four Notes (the hatch opens to them)
What the Wardens Heard (Ysolde): the Listening Room            [built: the finale]
```

All `Type=Side`, `Requires.Level=20`; the new ones are named so they read as a set in the journal ("The Glass
Wardens: The Four Notes"). The new quests only read the old ones' attributes (`ShardfallGate`, `DeepChartQuest`,
`BrineQuest`, `WardenQuest`, `FallenShardQuest`); they never change them.

**The quests**

- **The Wardens' Words** (`WardensWords`, Pell Varrow). Pell wants the Order's own writing for her book. Nine
  journals lie about the Deep, three already in the Hold's library; six more are new (the camp's old cairn,
  Leviathan's Rest, the Chapel, the cistern, the Shardfall's rim, and the Brinewater's shore). They run in the order
  the Order fell, whichever order you find them: Ysolde (the watch is quiet), Hale (it grows), Corvane (it asks to be
  listened to), Odile (the water hums back), Hale (the growth is quicker: something answers), Corvane (I asked it a
  question and it answered: it knows my name), Ysolde (the Order splits), Odile (I am going into the water, to get
  away from it), Ysolde (the last: *don't answer it*). A count in an attribute, like Charting the Deep. Reward: gold,
  Shards, and Pell's finished book as an item to read.
- **The Four Notes** (`FourNotes`, begun by listening at the Singing Geode). The Geode sings four notes in an order.
  Four **Warden's Chimes** (water at the Brinewater, bone at Leviathan's Rest, flame in the Chapel of the Flame, glass
  at the Shardfall's rim) are the Order's wards, each ringing one note to drown the voice out. Strike them in the
  Geode's order and the Hold's inner seal answers: the Listening Room is safe to hear in. *Sound-based, not worded*:
  the Geode plays its four sounds and each chime plays its own, so the puzzle is heard. **Seasons**: the order shifts
  with the season, so it's a puzzle to listen to afresh, and the Geode always sings today's. Reward: Shardcraft, and
  the way to the Listening Room.
- **Odile's Log** (no quest; an addition to the Brine Mother). Killing the Brine Mother, as now, finishes Morrow's
  quest. She also drops *Odile's Log*: a Warden's cook who went into the water to get away from the song, and was
  changed by it. She dragged sailors under because she knew it calls to them and couldn't stop. The kill stays a
  kill, and a mercy; the log makes it a sad one. Morrow gets one more line when you show it: it doesn't undo Davey,
  it explains.
- **The Last Watch / The Fallen Shard** (existing). The Hollow Marshal's honour guard can be passed by Sneaking (or
  fought). The Shardborn's Singing Remnant, absorbed, plays **the vision**: a short flashback of the cutting as the
  dragon felt it, huge, furious, and then small. It sets `SawCutting`.
- **What the Wardens Heard** (`WardensHeard`, Ysolde; the finale). When the four are done she asks you to the
  **Listening Room**, a small chamber behind the Reliquary where the Order did their listening. You stand there
  in the **Channelling stance** and hold it while the voice speaks. It's charming, it knows your name, and it offers you
  things; it tells the truth because it believes you'll help it. Hold the stance and don't answer: the voice boasts of
  the cutting, of what the Pact feeds, and of the one thing it fears, the Seam being broken. (A player who doesn't use
  stances is told, by Ysolde, to.) Answer it, or let the stance drop, and it's over till you try again. Ysolde rests
  (she fades, with the Shard's chime). The room is `12,-17,-2`, down the `Listening_Hatch` in the Reliquary (it opens
  only once the Four Notes are rung); the horn is `Listen Listening_Horn`. Reward: the **Wardens' Lantern** (carried,
  it lights you further: Entities.ini `Carried.Light`, `sky.js`), 100 Shards, Shardcraft XP, and `WardensTruth`.
- **What changes above ground afterwards.** Nell's nets come up with ordinary fish again, and the glass stops
  glowing; Bryony says her mother was right; Pell redraws her chart; Ashford's rumours change. Quiet things.

**The Shardsong** (an affliction, `data/Diseases.ini`; optional; the Malaria rules apply). The longer you stand near
the Geode or the Fallen Shard, the more a faint voice gets into your head. It stays through death and logging off,
comes as a short *listening* bout now and again (you sway and stop; afterwards your eyes are sharper for a moment, so
you see traps and secrets), and goes only for what says `Cures=Shardsong`: the **Quiet Draught**, brewed in Alchemy
from glowfin and a cave mushroom. Morrow knows it, and gives the first draught. A cost with a bonus, never a death.

**At the King's Seam: the third answer, Unmake.** Needs `WardensTruth`, so it's found through this chain, never
offered cold. The two old answers stand: the **Binding** (your blood the lock, the Seam gives the Crown Shards each day
as now) and the **Crown** (the dragon's piece in the crown: stronger, and it sings faintly in your head). **Unmake**
breaks the Seam itself. It costs the daily Crown Shards and the crown, and it gives:
- **Calmer storms.** Shard storms are rarer, shorter and softer for you.
- **Passive remnants.** The remnants of what you kill no longer hunt you; they lie where they fall to be absorbed.
- the Shardrealm still there, thinner and quieter: a shadow that stays after the dragon is gone, going slowly dark.
- a trophy, the Seam's **hammer-head** (`Seam_Hammerhead`). No extra power.
Shards still exist and still work. The dragon's *hold* is what's gone. *(Personal to you, like every ending's
epilogue: the world round you keeps its storms and remnants for everyone else.)*

**With company.** A story moment is yours; nothing needs a second player. A party near you at the same stage
reaches it too. The Shardborn and the Hollow Marshal get more health for each fighter, as every boss does.

**Rumours and banter** (data only): Ashford's gossip about the glowing nets and the fisherwoman; Nell and Bryony's
lines to each other; Pell talking to the mushrooms. No hints in any of it.

**What it added.** Items: Odile's Log, six journals, Pell's book, the Warden's Chimes (four), the Quiet Draught, the
Wardens' Lantern, the Singing Remnant, the Seam's hammer-head. A small Listening Room map (a free map, laid out by the
new builder alone, never over the owner's edits). The Shardsong disease. Engine: a personal "Unmade" attribute that
quiets storms (`wonders.py`) and makes the player's remnants passive (`remnants.py`). A chain name in the journal (or a
naming prefix). Sounds: four chime notes, the Voice, the vision's sound, Ysolde's rest. Everything in a new builder,
`dev/migrate/build_glass_wardens.py`, with the small additions to the Shardfall scripts made in `build_shardfall.py`.

#### The Mending (a secondary storyline, level 12 to 20)

*Built by `dev/migrate/build_mending.py` (it takes over the Ashen Shrine scripts), its people and things drawn by
`dev/migrate/build_mending_art.py`, every Shard number in `data/Shards.ini` `[Mending]`. Written like the Glass
Wardens: for a twelve-year-old, and still worth an adult's time. Nobody of the Mending is cruel. They're sad people
being kind to each other, and wrong. Nothing in the main quest needs it.*

**The idea in one line.** Shards tell you what you want to hear, and the Mending are the people who believed them.

**Who they are.** A widow hears her husband in a Shard; a sick man hears he'll be well; a lonely boy hears he's
wanted. They found one another, and they say the same thing: the Cutting was a wound, the scraps want to be whole, and
when they're whole the world will be mended. They don't know (or won't say) that "whole" is the dragon. The Glass
Wardens listened to the Shards for a hundred years and never answered; the Mending answered.

**What they've done.** The Mending paid the **Ashen Hand** in Shards to carry Shards up the pass and push them through
the barrier, "for the one beyond the wall". The Hand thought it kept a fire for the dragon; the Mending was feeding
it, a scrap at a time, so it would grow whole again (that's the hide of Shards on the dragon in The Sleeping Sword).
Cael's "they said it would make the world warm again": *they* were the strangers in grey. With the dragon dead, their
aim is the **first cut**: open the King's Shard Seam and let the rest of the dragon back into the world.

**What they're called.** The Mending; its people are "of the Mending" (an Acolyte of the Mending, Sister Linnet of the
Mending), never a one-word name. Townsfolk say "the Mending folk" or "them in grey". The Hand (fire, ash, the dragon)
is their hired help; the Mending is the Shards' own (grey robes, glass growing through them, cold blue fire).

**Its people.** **Acolytes** of the Mending (they fight with their hands and staves), **Cantors** (they sing, and
fight in the Channelling stance), the **Glassbound** (more glass than cloth: slow, strong, and full of remnants) and
the **Eldest of the Mending** (a boss, more glass than man, who heals by the remnants of his own). **Sister Linnet**
keeps their house in Ashford. **Annis**, mother of **Tam** the cooper of Ashford, went to them to hear her husband.
And now and then on the road, **one of the Mending** offers you a few Shards "for nothing, friend".

**Where.** Their **house in Ashford** (a quiet door, a kind welcome, and a shop of Shard goods for those in the
robe). Their **hall under Shardglass Field** (its way in hidden, lookouts above, the sermon hall, the **Shard Font**,
and the locked **sanctum** with the **great Shard**). The **Ashwold's** three shrines, cold now, and the **Hand's
camp** where the Mending pays it. **Wardhaven**, open once the dragon is dead and empty till now: the Mending takes
it quietly, and the Eldest's sanctum is there at the end.

**No joining.** You never become one of them. You can only look like one: the **robe of the Mending**, worn, and
they take you for one of their own (`Friend.If.Wearing=Mending_Robe`, each player's own gear). A blow, or a spell in
sight of one of them, ends it for that map, and those near come for you. The temptation is the Tithe.

**Mary's voice.** In the sanctum the great Shard speaks to you as your mother: she's proud of you, her
`$Player.Son`; she was wrong to run; come home and be whole with her. It's a lie, and by then the player knows it
(the Shards tell you what you want to hear: Cael's confession, the Glass Wardens), which is what makes it sad rather
than frightening. It never says anything Mary's letter didn't.

**The quests** (attribute in brackets; the way one ended in its `Ending=` attribute):
1. **Cold Fire** (`ColdFireQuest`, level 12, after The Ember Ring; the Warden in Emberwatch, `Talk to Warden`).
   - 0 → 1: the Warden has had word: the Hand's burnt shrines on the Ashwold are lit again, and the fire's blue.
   - 1 → 2: Listen at each of the three cold shrines (`Ashen Shrine 1-3`; `ColdShrine1-3`, counted in `ColdShrines`;
     the third sends you on). Footprints lead to the Hand's camp (`Hand Camp`, a trigger).
   - 2 → 3: come to the camp's fire Sneaking and hear two strangers in grey pay the Hand in Shards "for the one
     beyond the wall". Come any other way and the voices are too low to make out (said once: `ColdCampNear`).
   - 3 → 4: tell the Warden. 12 Shards, Stealth XP.
2. **The Kind Stranger** (`StrangerQuest`, 13, after Cold Fire; Tam the cooper in Ashford).
   - 0 → 1: Tam's mother Annis goes every day to the quiet house behind Rufus's yard.
   - 1 → 2: Annis (`Talk to House_Annis`) won't hear a word against the Shard; it talks to her in Oswin's voice.
   - 2 → 3: Cael at the Cinder Chapel writes her a few lines (`Caels_Lines`: what he told Oska).
   - 3 → 4, **the choice** (`StrangerEnd`): read them to her and walk her home (1: `AnnisHome`, `AnnisAway`;
     Ashford's standing +15; she's at Tam's after, `Talk to Home_Annis`), or leave her with her Shard (2:
     `AnnisAway`; she's in the hall, `Talk to Hall_Annis`, and in the Eldest's sanctum at the end). If In Grey's
     told before it's done, the watch takes her home (3).
3. **In Grey** (`GreyQuest`, 15, after The Shardgate and Cold Fire; Sister Linnet at the Mending's house).
   - 0 → 1: Linnet won't tell an outsider where they gather.
   - 1 → 2: a robe of the Mending (`Mending_Robe`): picked from an Acolyte's pocket, or off the washing line behind
     the house (`RobeTaken`). In it, Linnet takes you for one of them and tells you of the slab at Shardglass Field's
     east end (`Climb Down Mending_Slab`; The Hall Under the Glass is on the world map from here).
   - 2 → 3: the sermon (`Mending Sermon`, for one in the robe): Cantor Ivo names and thanks one who took the road's
     gift (`MendingGift`), and The Tithe starts.
   - 3 → 4: Listen to the great Shard in the sanctum (`Listen Hall_Great_Shard`): Mary's voice, her letter's words
     given back out of order. Their aim: the King's Seam.
   - 4 → 5, **the choice** (`GreyEnd`): tell Sheriff Flo (1: `MendingShut`; Ashford's and Galaith's standing +15;
     Linnet, the house's Shard and its shop gone; Annis brought home if she was left), or tell Linnet you'll keep
     their secret (2: the house and its shop stay open to you in the robe, and she teaches the Channelling form
     Drinking).
4. **The Tithe** (`TitheQuest`, started by the sermon). An iron gate shuts the sanctum (a `Lock`: `TitheOpen`).
   - 1 → 2, three ways (`TitheWay`): pour $Shards.Mending.Tithe Shards into the Font (`Pour Shards Hall_Font`, 1),
     pick the gate's lock (Stealth, 2), or kill the Font's keeper, a Glassbound, for its key (`Kill Font_Keeper`, 3:
     a blow ends the disguise). Done just inside the gate (`Mending Sanctum`). Channelling XP.
5. **The Eldest of the Mending** (`EldestQuest`, 20, after The Dragon of Galaith and In Grey; Amos, the priest of
   Wardhaven). The two Sisters in grey in his chapel are there since the dragon died (`GalaithQuest>=2`).
   - 0 → 1: Amos: singing under his chapel floor at night, and a stair he never knew of (`Climb Down
     Wardhaven_Undercroft_Stair`). The hall's great Shard is gone from under the field: it's here now.
   - 1 → 2: the Eldest (`Boss=1`, `Absorbs.Remnants=1`) and his choir of four Cantors. How he greets you
     (`Eldest Sanctum`, once: `EldestMet`) is how you came to the Font: one who tithed is one of the faithful, and
     he opens his arms (`Edit.Entity ATTITUDE Good`: your first blow is a sneak attack); one who picked the lock is a
     stranger; one who broke the keeper is the one who'll not listen. Killed (`Kill The_Eldest`).
   - 2 → 3, **the choice** (`EldestEnd`, `Listen Eldest_Great_Shard`): break the great Shard (1: the Mending
     scatters; Annis comes home if she'd been left; Sister Hesper and Brother Odo, penitents, in Wardhaven's chapel)
     or keep a splinter, **Mary's Whisper** (2: $Shards.Mending.Whisper Shards every Whisper.Hours real hours in her
     voice, `WhisperAt`; while you carry it, choosing Unmake at the Seam fails: the Whisper cries out, and your hand
     won't do it).
   30 Shards, Channelling and Defence XP.

**The world round it.**
- **On the road** (`Encounters.ini` `[Mending_Wayfarer]`, out of doors, level 12 up, after Cold Fire's told you of
  them, till the Seam's unmade or the great Shard's broken): a few Shards "for nothing, friend", once
  (`MendingGift`); the sermon remembers it.
- **The townsfolk's talk** (`build_banter.py`, `Grey_*`): soup, an aunt who hears her dead husband, "too kind";
  the robe worn in town; the house shut (Ashford's guards); gone quiet after Unmake; a cousin home after the great
  Shard's broken. No notice, sign or map text points to them.
- **The mine** (`Waves.ini` `[Mending_Raid]`): after The True Heir and till the Seam's unmade, now and then, the
  Mending comes down the tunnels behind Galaith for the King's Seam, only while someone there has got that far
  (`Requires=`).
- **After Unmake** (`HeartChoice=3`): Ivo's sermon says the Seam's closed for good, two of the hall's Sisters have
  gone home, and the great Shard has nothing left to say.

**With company.** All of it is each player's own: the disguise, the choices, Annis, the Whisper. A party at the same
stage reaches a story moment together, and the Eldest gets more health for each fighter, as every boss does.

### The towns' own choices (`build_town_choices.py`)

Each is after Passage to the Mainland, gives 8 Shards, and has two ways, each moving its town's standing (`Ending=`).

**The Deserter** (King Rupert's Keep): Sergeant Brask, outside the Keep, wants Pip, a farm boy run from the levy.
Pip hides in the woods south of the Keep (`Here.After=DeserterQuest:1`). `DeserterWay`:
* **Told** (1): back to Brask, 60 gold; Keep +15.
* **Let go** (2): give Pip 40 gold for a carter's cart south; Keep -10. He turns up in Saltmarsh, and gives you two
  fish pies once.

**The Dry Spring** (Dunerest): Elder Sabra's well has run low. North of the village, Corvin the water seller has dammed
its spring (`Dunerest_Dam`, Break). `WellWay`:
* **Bribed** (1): Corvin pays 100 gold to leave it; the dam stays; Dunerest -10.
* **Broken** (2): pull the dam down (`WellDamDown`), back to Sabra, 50 gold; Dunerest +15.

**The Eel Traps** (Saltmarsh): someone's been cutting Wenna the eel catcher's traps. It's Tobin, the boy next door,
whose family's going hungry (`Saltmarsh_Tobin`). `EelWay`:
* **Blamed** (1): tell Wenna, 60 gold; Tobin is sent inland; Saltmarsh +5.
* **Mended** (2): bring Wenna 3 planks for the traps and ask her to share her catch; Saltmarsh +15.

**Marsh Fever** (Mirefold): Bryony the healer asks what Doctor Pallister's cure is. Buy one from him (20 gold) and
bring it her: coloured water. `FeverWay`:
* **Paid off** (1): Pallister pays 80 gold for your silence and keeps selling it; Mirefold -15.
* **Run out** (2): he's gone, and Bryony sells a real fever tonic (`SHOP-Mirefold_Healer`); Mirefold +15.

---

## Stance forms: who teaches them

A form is shown you when you next talk to its teacher once you've earned it (`Stances.ini` `Taught.By`, `Taught.If`;
`build_forms.py`). None is needed by the story.

| Stance | Form | Taught by | Once |
|---|---|---|---|
| Fighting | Shieldwall | Sergeant Holt | you led his men into Red Meg's camp (`SmugglerSide=2`) |
| | Reckless | the Arena Master | three arena wins, or 300 creatures slain |
| | Duellist | Captain Hart, at the palace door | The Royal Guard is done (`GuardQuest>=5`) |
| | Dirty Fighting | Spleen, outside Redrock Manor | you sell him the signet (his script: `Learn.Stance`) |
| Channelling | Stormcaller | Bert | The Shardgate is done (`ShardgateQuest>=5`) |
| | Wardkeeper | Warden Ysolde | The Last Watch (`WardenQuest>=3`) |
| | Listening | Warden Ysolde | the Listening Room heard out (`WardensHeard>=2`) |
| | Drinking | Sister Linnet, in Ashford | In Grey's secret kept (`GreyEnd=2`) |
| Sneaking | Cutpurse | Red Meg | you took her side (`SmugglerSide=1`) |
| | Shadow | Ambrose, at home | the signet given back (`RedrockWay=2`) |
| | Ranger's Tread | Ranger Ash | the Old Grove kept (`GroveWay=2`) |

## How the quests lead into one another

```
The Last Will (1) ── Dinner at Edwin's (2) ── The Amulet of Succession (3) ── Passage to the Mainland (4)
Passage to the Mainland: every mainland quest needs it
├── The Temporary Capital (5) ── The Ashford Road (6) ── The Steward's Hunt (7)
│   ├── Bert's Three Treasures (8): The Staff of Ashen (9), The Sunken Grimoire (10), The Ember Ring (11)
│   │   └── Orrin's Chart (12) ── The Frozen Lodestar (13) ── A Ship for Dragon Island (14)
│   │       └── The Island of Dragons (15) ── The Sword of Valour (16) ── The Shardgate (17)
│   │           └── The Sleeping Sword (18) ── The Ashen Foundry (19) ── The Sun-Forge (20) ── The Deep Anvil (21)
│   │               └── The Dragon of Galaith (22) ── The Royal Guard (23) ── The True Heir (24)
│                   └── The Chancellor's Grain
│   │   The Shardgate: The Brother in the Ash
│   ├── The Dwarf's Grudge
│   └── The Wildwood Watch ── The Old Grove
├── A Place of Your Own, The Herbalist's Remedy, The Smugglers' Run, The Frozen Forge, The Lost Patrol,
│   Granny Wren's Walk, A Portrait of Mo
├── Wolves of the Greyflats ── The Withering Wood ── The Barrow King
├── Bandits on the Road ── The Lost Caravan
├── The Wandering Echo, Old Skadi's Tall Tales
└── Bog Lights ── Old Hob
On the Isle, any time: The Hermit's Fire; after the amulet, What Jimmy Kept; after the lair, Tobias's Tin
```

Recurring characters worth keeping consistent: **Jimmy** the cat (the cottage, your house on the Isle, the throne),
**Maren and Edwin** (their house by the chapel; Tobias lives with them after the lair), **Bert** (chapters 8 to 22), **the Steward**
(chapters 7 and 9), **Morwen** the witch (Bog Lights, Old Hob), **the Ashen Priest** (chapter 11; his cult's
shrines in the Ashwold, relit blue by the Mending), and **Cael** (The Brother in the Ash, The Kind Stranger).

## Loose threads and hooks

- **Who turns up on the road**: a travelling salesman, a jester and now and then a Shard Abomination
  (`data/Encounters.ini`). They aren't quests, and they don't say where anything is.
- **The stones in Galaith's graveyard**: the royal firstborn have stones with nobody under them, and the last is small,
  new and blank (the King had it cut the year the city shut). The sexton won't say more; nothing needs it to.
- **Wardhaven** opens once the dragon is dead: the Mending takes it quietly, and the Eldest of the Mending waits in
  its sanctum (The Mending, above).
- **The mine behind Galaith** opens to the King: the gold and Shard mines the bargain was made for. At its far
  wall the **King's Shard Seam** gives the Crown 12 Shards once every 20 hours (Shards.ini `Galaith.Seam`), with a
  pickaxe and some Mining.
- A villager in the Isle village says her granny warned never to dig in the **stone circle** on the north-west
  headland. Nothing is buried there yet (its hidden chest is opened, not dug up).
- **The order in ash** (`build_isle_secrets.py`): the lair's corner barrel holds, beside the key, an order to the
  hobgoblins: bring the papers of the woman from Galaith and her child's name, for Shards; no name under it, only a
  hand pressed in ash. Tobias (who writes the Isle's papers, why they took him) names the Ashen Hand. The demo ends
  with that question; chapter 11 answers it: the Ashen Priest drops his **ledger**, which paid for the raid, says
  the child has crossed the strait, and "the one beyond the wall is waiting" (the dragon, through the Mending).
- The **Ashen Hand's** shrines and acolytes in the Cinderlands: the Hand is the Mending's hired help, paid in Shards
  to feed the dragon through the wall; Cold Fire (after the Ember Ring) finds them at it (The Mending, above).

## For editors: where each quest lives

Every quest is a section of `data/Quests.ini`: its giver, its stages (the journal text for each), its markers on the
map, its type and chapter, what it requires, and the Shards it gives (`Reward.Shards`, paid once when it's done). Its progress is a number kept per player (the `Attribute`), set
by the scripts in `data/Scripts/` (named for what you do: `Talk to Milkmaid.txt`, `Kill Hobgoblin.txt`,
`Search Cellar_Crate.txt`...).

| Quest | Attribute | Main scripts |
|---|---|---|
| The Last Will | LastWill | The Funeral, 4,0,0, Read Last_Will |
| The Shard Scholar | ShardQuest | Talk to Court_Magister |
| The Spellwright | SpellwrightQuest | Quill the Spellwright (the lectern: dsengine/ownspell.py) |
| The Shardgate | ShardgateQuest | Use Staff_of_Ashen With Barrier, Bert and the Shardgate, Build Shardgate_Ring, Step Through Shardgate, Shatter Barrier_Anchor |
| Dinner at Edwin's | DinnerQuest | Talk to Edwin / Maren, Use Fried_Egg With Edwin, Marens_Range |
| The Amulet of Succession | AmuletQuest | Talk to Milkmaid, Talk to Frank, Talk to Chapel_Verger, Reach In / Grasp Barred_Niche |
| Passage to the Mainland | Passage | Pick Lock Caged_Tobias, Squeaky Floorboard, Talk to Milkmaid, Talk to Ferryman |
| The Temporary Capital, The Ashford Road | ParliamentQuest, AshfordQuest | Talk to Northport_Port_Guard, Talk to Northport_Speaker_*, Talk to the Mayor, Farm Raid Won |
| The Steward's Hunt, The Staff of Ashen | HobgoblinQuest, StaffQuest | Talk to Keep_Steward, Kill Hobgoblin, 22,11,1, Pickup Staff_of_Ashen |
| Bert's Three Treasures | BertQuest | Talk to Bert, Bert's Confession |
| The Redrock Signet | RedrockSignetQuest | Talk to Redrock_Steward, Open Redrock_Manor_Vault (build_hush_and_dread.py) |
| The Sunken Grimoire, The Ember Ring | GrimoireQuest, RingQuest | Talk to Dunerest_Scholar, 3,16,0, 3,16,-1, Talk to Warden, Kill Ashen_Priest |
| Orrin's Chart, The Frozen Lodestar | OrrinQuest, LodestarQuest | Talk to Captain_Rook, Talk to Orrin_Ghost, Kill Orrins_Shadow, Talk to Surveyor_Nils, Reach In Lodestar_Altar, Kill Rime_Warden (build_middle_quests.py) |
| The Sleeping Sword, The Ashen Foundry, The Sun-Forge, The Deep Anvil | WakeQuest, FoundryQuest, SunforgeQuest, AnvilQuest | Use Staff_of_Ashen With Barrier, Bert's Errands, Talk to Warden_Oska / Nomad_Tarek / Delver_Maud (their kill quests are Odd Jobs for <who>), Work Foundry_Bellows, Temper Foundry_Hearth / Sun_Forge / Deep_Anvil, Turn *_Mirror, Strike Rune_Stone_*, Kill Forgemother / Sun_Keeper / Stone_King |
| The Brother in the Ash, The Wandering Echo, Old Skadi's Tall Tales | CaelQuest, EchoQuest, SkadiQuest | Talk to Cael, Read Cael_Confession, Talk to Wandering_Echo, Talk to Old_Skadi (build_middle_quests.py) |
| A Ship for Dragon Island, The Island of Dragons, The Sword of Valour | ShipQuest, DragonIsleQuest, ValourQuest | Talk to Captain_Rook*, 22,20,0, Temple Door, Talk to Valour_Guardian_Knight |
| The Dragon of Galaith | GalaithQuest | 9,12,0, Use Staff_of_Ashen With Barrier, The Dragon Speaks, Kill Galaith_Dragon |
| The Chancellor's Grain | GrainQuest, GrainWay, GalaithTreasury | Talk to Galaith_Clerk_73, Open Chancellors_Strongbox, Talk to Galaith_Speaker_70, Talk to Palace_Captain, Talk to Chancellor_Sefton, Open Galaith_Treasury (`build_choices.py`) |
| The Royal Guard, The True Heir | GuardQuest, KingQuest | Talk to Palace_Captain, the Chancellor and the Archivist, Talk to Rupert_On_Throne, -9,14,0 |
| The Hermit's Fire | HermitQuest | Talk to Hermit |
| What Jimmy Kept | JimmyQuest | Talk to Chapel_Verger, Read Marys_Charm, Talk to Jimmy, Squeeze Through Cat_Gap (`build_isle_secrets.py`) |
| Tobias's Tin (and the order in ash) | TobiasTin, AshenOrder | Talk to Tobias, Open Hob_Camp_Chest, Search Lair_Corner_Barrel, Kill Ashen_Priest (`build_isle_secrets.py`) |
| A Place of Your Own | HomeQuest | Talk to Homestead_Settler |
| The Herbalist's Remedy | RemedyQuest | Talk to Herbalist |
| A Portrait of Mo | PortraitQuest | Talk to Ashford_Painter, Stroke Mo |
| The Wardhaven Bridge, The Dragonforge | WardhavenQuest, DragonforgeQuest | Talk to Ashford_Clerk_13, Kill Goblin, the gate's map's entry script, Talk to Wyrmsmith, Forge Wyrmsmith (all `build_estforlan.py`: estforlan/quests.py) |
| Granny Wren's Walk | EscortQuest | Talk to Granny_Wren, Granny Wren Home, Talk to Ashford_Resident_34, 4,4,0, 11,4,0 |
| The Smugglers' Run, The Tide Turns, Under the Tide | SmugglerQuest, SmugglerSide, SmugglerRaid, TideQuest, TideGuards, UnderTideQuest | Talk to Smuggler_Sergeant, Search Suspicious_Barrel, Talk to Red_Meg, Kill Smuggler, 17,4,0, 18,3,0, 21,5,0, Watch_Search, Talk to Castle_Cellarer, Talk to Meg_On_The_Sandbar (`build_smugglers_run.py`) |
| The Dwarf's Grudge | DwarfQuest | Talk to Dwarf, Kill Skeleton, Kill Cave_Troll |
| The Wildwood Watch | RangerQuest | Talk to Ranger, Watch Stone 1-3, Kill Giant_Spider |
| The Old Grove | GroveQuest, GroveWay, GroveCutters | Talk to Ranger, Talk to Timber_Merchant, Blaze Old_Grove_Oak, 9,12,0, Kill Woodcutter, Talk to Grove_Sawyer, Talk to Grove_Warden (`build_choices.py`) |
| Old Hob | HobQuest | Read Hobs_Diary, Talk to Witch, Use Calming_Draught With Hob, Talk to Hob |
| Wolves of the Greyflats | WolfQuest | Talk to Shepherd, Kill Wolf, Wolf Den, Kill Alpha_Wolf |
| Bog Lights | BogQuest | Talk to Witch, Talk to Elder |
| Bandits on the Road | BanditQuest | Talk to Captain, Kill Bandit, Open Strongbox |
| The Lost Caravan | CaravanQuest | Talk to Merchant, Caravan Wreck, Kill Scorpion |
| The Frozen Forge | ForgeQuest | Talk to Forgemaster, Kill Frost_Troll |
| The Withering Wood | DruidQuest | Talk to Druid, Heartwood, Kill Bear |
| The Barrow King | BarrowQuest | Talk to Gravekeeper, Barrow Door, Kill Barrow_King |
| The Lost Patrol | PatrolQuest | Talk to Scout |
| Glass in the Nets | ShardfallGate | Talk to Nell_Tarrow, Talk to Bryony_Tarrow, Touch Shardfall_Seal |
| Charting the Deep | DeepChartQuest | Talk to Pell_Varrow, Chart_Brinewater, Chart_Rest, Chart_Geode, Chart_Hold, Chart_Fall |
| The Brine Mother | BrineQuest | Talk to Morrow_Angler, Kill Brine_Mother |
| The Last Watch | WardenQuest | Talk to Warden_Ysolde, Kill Hollow_Marshal |
| The Fallen Shard | FallenShardQuest | Talk to Warden_Ysolde, Kill Shardborn, Touch Fallen_Shard |
| The Deserter, The Dry Spring, The Eel Traps, Marsh Fever | DeserterQuest, WellQuest, EelQuest, FeverQuest | Talk to Keep_Sergeant_Brask / Deserter_Pip, Talk to Dunerest_Elder_Sabra / Water_Seller_Corvin, Break Dunerest_Dam, Talk to Eel_Catcher_Wenna / Saltmarsh_Tobin, Talk to Mirefold_Healer_Bryony / Doctor_Pallister (build_town_choices.py) |

House rules for new writing (from `CLAUDE.md`): notices and signs never give hints; a conversation answer that
belongs to one stage of a quest shows only at that stage; each player's chest loot and quest progress are their
own.
