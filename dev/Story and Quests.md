# Dragon Sword: the story and its quests

A summary of the quests in the game as it stands, for planning the story and making changes. The main quest line
comes first, step by step; then the side quests, by region. The last section says where each quest lives in the
game's files.

## The world in brief

- **Estforlan** is the kingdom. Its capital, **Galaith**, in a gap in the mountains at the far east of the mainland,
  holds the only land route across the world and the gold and mana mines behind it. A dragon has kept it shut behind
  a magical barrier for eighteen years: every generation it was owed the king's firstborn heir, and Queen **Mary** ran
  from Galaith with her baby, you, to break the bargain. King **Rupert**, your father, is shut in the city.
- **The Isle**: a small island off the south coast, where you grew up poor and where every new character begins, at
  their mother's funeral. It has a village with a bank, a farm and a smithy, a chapel with caves under it, a hermit
  and a ferry.
- **The mainland**: **Southport** (a large city, where the ferry lands; Estforlan's Parliament sits in its City Hall
  while Galaith is lost), **Ashford**, **King Rupert's Keep** (the old Tyron's Keep, held by the King's Steward), the
  **Wizards' Court** on the Royal Isle, Fenwick, Ravensgate, Highwatch, Frosthold, Oakhollow, Thornwick, Emberwatch,
  Moorcross, Dunerest, Wildwood and Saltmarsh, each the size the owner set (see `CLAUDE.md`).
- **The Cinderlands**: north of the Elderwood. Emberwatch, the Ashwold and the Cinder Peaks, where the Ashen Priest
  holds the Cinder Fort.
- **Dragon Island**: south of Ravensgate, by Captain Rook's ship. Drakes, and the Temple of Valour.
- **Galaith**: east over the causeway from the Elderwood, through the mountain pass and its barrier. The scorched
  field where the dragon waits, the city's white walls burnt black, the mountains meeting behind it, and a mine mouth
  behind the city.

---

## The main quest line

Seventeen chapters, each unlocked by the one before it. Chapters 1 to 4 are the Isle (`build_heir_isle.py`); 5 to
17 the mainland and Galaith (`build_heir_mainland.py`, with `build_galaith.py` for the city and its pass).

### On the Isle (the tutorial)

| Ch. | Quest | What you do |
|---|---|---|
| 1 | **The Last Will** | You stand at your mother's fresh grave by the chapel. The mourners go; **Edwin** the lawyer walks you home and leaves her letter on the table. The cottage door stays locked until you've **read the letter** (three pages, in the owner's words): you are the heir of Estforlan. Jimmy sleeps on her empty bed. |
| 2 | **Dinner at the Bank** | Edwin asks you to dinner. **Maren**, his wife, keeps the bank (two storeys of brick; they live upstairs, and go up at night). **Chop 3 logs** for her range (she lends an axe), **take an egg** from Bess's coop and **fry it** on her range, give it to Edwin. Reward: the key to the chapel's trapdoor, and a promise not to go down without a sword and shield. |
| 3 | **The Amulet of Succession** | **Bess** the milkmaid has the only boat, but won't sail without her father's compass. Her husband **Frank** the blacksmith (smoke from his chimney by day) helps you **make a wooden sword and shield**. **Brother Aldous** lets you down once you wield both and Strength and Defence are level 2. The amulet lies **behind bars** at the back of the caves: Aldous brings a **Grasp** scroll. Reward: the amulet and the key of the hobgoblins' lair. |
| 4 | **Passage to the Mainland** | Bess's father **Tobias** is missing and his house (Maren & Bess's Father's Home) is locked. The **hobgoblins' lair**: four hobgoblins (no new ones until you leave), the house key in the corner barrel, Tobias in a cage you **pick the lock** of (the lock minigame: set each pin as it crosses the line; three slips and you start again). He gives you his house and moves in with Maren at the bank. A hidden ladder climbs into a tent in their camp on the surface (only a tent until it's been climbed from below). In the house a **floorboard squeaks**: the compass is under it. Bess sails you to Southport; after that **Wim** the ferryman crosses for a coin. |

### The road to the Wizards' Court

| Ch. | Quest | What you do |
|---|---|---|
| 5 | **The Temporary Capital** | The guard at Southport's port says Southport is the temporary capital. The **Speaker**, in the City Hall (the Parliament), says only **Bert**, the great wizard of the Wizards' Court, can break the barrier, and gives you a letter for the Mayor of Ashford. |
| 6 | **The Ashford Road** | The **Mayor of Ashford** (the Town Hall) wants the goblins raiding the farms east of town driven off (a wave at the farm crossroads). Reward: the Mayor's pass. |
| 7 | **The Steward's Hunt** | The **King's Steward** at King Rupert's Keep wants **five hobgoblins** slain in the old iron mine. Reward: 100 gold, a ruby, and the causeway to the Royal Isle. |

### Bert's three treasures

| Ch. | Quest | What you do |
|---|---|---|
| 8 | **Bert's Three Treasures** | **Bert**, at the top of the Wizards' Court's tower, needs three things to break the barrier: |
| 9 | **The Staff of Estforlan** | The Steward's key opens the stair to the **King's solar**, at the top of the keep. Its old skeleton guard; the staff on its rack. |
| 10 | **The Sunken Grimoire** | The scholar **Yusra** in Dunerest: the Grimoire of Unbinding is in the sun priests' **buried library**, under a sand mound in the desert north of town (dig it out with a spade). A tomb guardian. |
| 11 | **The Ember Ring** | The **Warden** in Emberwatch: the **Ashen Priest** wears the ring, in the Cinder Fort. Take it from him. |

Bert only wanted the ring (it goes with his new robe, and he can't stand the Ashen Priest): chapter 8 ends with his
confession. He teaches you the spell of Unbinding, gives you the staff, and warns that only the **Sword of Valour**,
driven into its heart, kills the dragon.

### The Sword of Valour

| Ch. | Quest | What you do |
|---|---|---|
| 12 | **A Ship for Dragon Island** | (level 12) **Captain Rook**, on the shore east of Ravensgate, will sail if you bring 10 planks and 20 nails for his hull. |
| 13 | **The Island of Dragons** | Sail to **Dragon Island**. Three **Valour Seals** from its drakes open the Temple of Valour. |
| 14 | **The Sword of Valour** | Defeat the temple's **Guardian of Valour** and draw the sword from its stone. |

### Galaith

| Ch. | Quest | What you do |
|---|---|---|
| 15 | **The Dragon of Galaith** | (level 16) East over the causeway to the pass. **Use the staff on the barrier** (with Bert's spell learnt) and it shatters. The dragon speaks (the bargain, your mother's flight) and the boss fight begins: nothing but the **Sword of Valour, wielded**, gives it its death blow. The city's west gate opens. |
| 16 | **The Royal Guard** | Explore the city to win the guard over: the **captain** at the palace door sends you to the **Lord Chancellor** (the Parliament), who sends you to the **Royal Archivist** (the City Hall) with your mother's amulet; her word to the Chancellor; his warrant to the captain. |
| 17 | **The True Heir** | **King Rupert**, on his throne: show him the amulet, tell him the will. He holds you and weeps, and gives you the crown. From then the world is open play; **Jimmy** curls up on the throne, and in your house on the Isle. |

**Unlocks:** the gates of **Wardhaven**, over the bridge east of Ashford's farms (once the dragon is dead), and the
mine behind Galaith (once you're king).

---

## Side quests

### On the Isle

**The Hermit's Fire**: *Woodcutting 10*
The hermit in the Isle's western woods wants 5 oak logs. Reward: 25 gold, an oak staff, Woodcutting experience.

### Ashford and King Rupert's Keep

**A Place of Your Own**: *after chapter 4*
The settler by Ashford's homestone wants 10 planks and 4 stone blocks, made at her carpenter's bench (planks from
logs, blocks from stone mined with a pickaxe). Reward: the **Access Crystal**, your own homestead to build on, and
Construction experience.

**Granny Wren's Walk**: *after chapter 4*
An old woman off the ferry at Southport's landing, Granny Wren, can't see well enough to find her way to her
daughter Percy's in Ashford. **Lead her there**: she follows you, a step or two behind and slower than you walk
(Follow.Player), and waits if you go far ahead. At Percy's door talk to either of them. Lose her (log out) and she's
back at the landing, waiting. Reward: 30 gold and a berry pie; she lives at Percy's after.

**A Portrait of Mo**: *after chapter 4*
Ottilie paints at her easel in Ashford's market square, and the painting wants a cat: Mo, who never keeps still.
**Stroke Mo while Mo is sitting** and Mo settles for her; at any other moment it comes to nothing, each its own way
(mid-stretch; showing you its back end, to Ottilie's delight; or trotting off). Tell Ottilie: she paints. Reward: the
painting (Portrait of Mo) and 25 gold. (The scripts check what Mo is doing: >Entity.State, Set.NPC.State.)

**The Herbalist's Remedy**: *level 3, after chapter 4*
The Herbalist in her cottage on the Ashford farmlands wants 3 cave mushrooms (the old iron mine) and 2 spider silk
(giant spiders in the mine depths). Reward: 60 gold, 2 super potions, Herblore experience.

**The Smugglers' Run**: *after chapter 4*
Sergeant Holt at the castle's south gate wants to know how smuggled goods reach the market. The fishermen mention
an old barrel on the lake path that nobody moves. **Search it**: it hides a tunnel to a smugglers' camp on the
cove. **Sneak to their leader, Red Meg, unseen.** The smugglers only see ahead of them, never through cargo,
tents or walls. Meg offers a deal (her trade stays off Holt's streets if his men stay off her cove). Tell Holt.
Reward: 60 gold; the smugglers become friendly, and Meg's shop is open to you.

**The Dwarf's Grudge**: *level 8, after chapter 7*
Brokk the dwarf, in the Deep Hollow (through the hatch in the hobgoblin warren), wants 4 skeletons smashed and the
cave troll slain. Reward: 150 gold, 2 sapphires, a steel sword, Mining experience.

### The Wildwood and Oakhollow

**The Wildwood Watch**: *level 5, after chapter 7*
Ranger Ash in Oakhollow sends you to visit the three old watch stones (the north road, the western woods, the
river), then to clear the spider nest west of Oakhollow (5 giant spiders). Reward: 120 gold, a yew staff,
Strength and Woodcutting experience.

**Old Hob**: *after Bog Lights*
Old Hob of Oakhollow is missing and his house is boarded up, but a shutter hangs loose. His diary says a giant
spider bit him and he feels himself going wild. Ask Morwen for a cure, find the wild man in the Wildwood's western
woods, and use her calming draught on him. **A choice** about his chest (150 gold, which you may have already
emptied):
- He offers his savings to you; or
- if you took them, **give them back** (he rewards you 40 gold, keeps you as a friend) **or keep them** (the
  madness takes him again and he attacks, for good).

### Greymoor, the Saltmarsh and the Redrock road

**Wolves of the Moor**: *level 6, after chapter 4*
The shepherd in Moorcross: slay 6 moor wolves, then find the wolf den on the eastern moor and kill the Alpha Wolf.
Reward: 150 gold, a steel shield, Defence experience.

**Bog Lights**: *level 6, Herblore 5, after chapter 4*
Old Morwen the witch in Fenwick wants 4 bog myrtle. She brews something for Elder Pike; take it to him, then tell
her he drank it. Reward: 80 gold, 2 mega potions, Herblore experience. (Morwen returns in *Old Hob*.)

**Bandits on the Road**: *level 9, after chapter 4*
Captain Hale in Highwatch: slay 5 bandits, then find their camp in the eastern hills and take the stolen goods
from their strongbox. Reward: 200 gold, a steel platebody, Strength experience.

### The desert, the north and the downs

**The Lost Caravan**: *level 11, after Bandits on the Road*
Qadir the merchant in Dunerest: find his caravan wreck in the desert west of town, slay the scorpions there and
bring back its ledger. Reward: 180 gold, 2 rubies, Crafting experience.

**The Frozen Forge**: *level 13, after chapter 4*
Brann the forgemaster in Frosthold: bring 5 coal to light his forge, slay the Frost Troll that smashed his
waterwheel (on the frozen lake), then bring 2 mithril bars. Reward: 250 gold, a
mithril sword, Smithing experience.

**The Withering Wood**: *level 12, after Wolves of the Moor*
The Druid in Thornwick: touch the Heartwood, the Elderwood's old heart stone, then slay 4 blight-maddened bears.
Reward: 150 gold, an emerald ring, Herblore and Woodcutting experience.

**The Barrow King**: *level 15, after The Withering Wood*
The Gravekeeper in Ravensgate: find the old king's barrow on the downs and lay the Barrow King to rest. Reward:
250 gold, a mithril helm, Defence experience.

### The Cinderlands

**The Lost Patrol**: *level 14, after chapter 4*
The Scout in Emberwatch: her patrol never came back from the Ashwold. Recover 3 Scout's Tags from the ember hounds.
Reward: 200 gold, a yew bow and 100 arrows.

---

## How the quests lead into one another

```
The Last Will (1) ── Dinner at the Bank (2) ── The Amulet of Succession (3) ── Passage to the Mainland (4)
Passage to the Mainland: every mainland quest needs it
├── The Temporary Capital (5) ── The Ashford Road (6) ── The Steward's Hunt (7)
│   ├── Bert's Three Treasures (8): The Staff of Estforlan (9), The Sunken Grimoire (10), The Ember Ring (11)
│   │   └── A Ship for Dragon Island (12) ── The Island of Dragons (13) ── The Sword of Valour (14)
│   │       └── The Dragon of Galaith (15) ── The Royal Guard (16) ── The True Heir (17)
│   ├── The Dwarf's Grudge
│   └── The Wildwood Watch
├── A Place of Your Own, The Herbalist's Remedy, The Smugglers' Run, The Frozen Forge, The Lost Patrol,
│   Granny Wren's Walk, A Portrait of Mo
├── Wolves of the Moor ── The Withering Wood ── The Barrow King
├── Bandits on the Road ── The Lost Caravan
└── Bog Lights ── Old Hob
On the Isle, any time: The Hermit's Fire
```

Recurring characters worth keeping consistent: **Jimmy** the cat (the cottage, your house on the Isle, the throne),
**Maren and Edwin** (the bank; Tobias lives with them after the lair), **Bert** (chapters 8 to 15), **the Steward**
(chapters 7 and 9), **Morwen** the witch (Bog Lights, Old Hob), and **the Ashen Priest** (chapter 11; his cult's
shrines stand quiet in the Ashwold).

## Loose threads and hooks

- **Wardhaven** opens once the dragon is dead, but nothing happens there yet.
- **The mine behind Galaith** opens to the King: the gold and mana mines the bargain was made for.
- A villager in the Isle village says her granny warned never to dig in the **stone circle** on the north-west
  headland. Nothing is buried there yet (its hidden chest is opened, not dug up).
- The **Ashen Hand's** shrines and acolytes are still in the Cinderlands with nothing to do since the old chapters
  went: room for a quest after the Ember Ring.

## For editors: where each quest lives

Every quest is a section of `data/Quests.ini`: its giver, its stages (the journal text for each), its markers on the
map, its type and chapter, and what it requires. Its progress is a number kept per player (the `Attribute`), set
by the scripts in `data/Scripts/` (named for what you do: `Talk to Milkmaid.txt`, `Kill Hobgoblin.txt`,
`Search Cellar_Crate.txt`...).

| Quest | Attribute | Main scripts |
|---|---|---|
| The Last Will | LastWill | The Funeral, 4,0,0, Read Last_Will |
| Dinner at the Bank | DinnerQuest | Talk to Edwin / Maren, Use Fried_Egg With Edwin, Marens_Range |
| The Amulet of Succession | AmuletQuest | Talk to Milkmaid, Talk to Frank, Talk to Chapel_Verger, Reach In / Grasp Barred_Niche |
| Passage to the Mainland | Passage | Pick Lock Caged_Tobias, Squeaky Floorboard, Talk to Milkmaid, Talk to Ferryman |
| The Temporary Capital, The Ashford Road | ParliamentQuest, AshfordQuest | Talk to Southport_Port_Guard, Talk to Southport_Speaker_*, Talk to the Mayor, Farm Raid Won |
| The Steward's Hunt, The Staff of Estforlan | HobgoblinQuest, StaffQuest | Talk to Keep_Steward, Kill Hobgoblin, 2,4,1, Pickup Staff_of_Estforlan |
| Bert's Three Treasures | BertQuest | Talk to Bert, Bert's Confession |
| The Sunken Grimoire, The Ember Ring | GrimoireQuest, RingQuest | Talk to Dunerest_Scholar, 1,9,0, 1,9,-1, Talk to Warden, Kill Ashen_Priest |
| A Ship for Dragon Island, The Island of Dragons, The Sword of Valour | ShipQuest, DragonIsleQuest, ValourQuest | Talk to Captain_Rook*, 8,10,0, Temple Door, Talk to Valour_Guardian_Knight |
| The Dragon of Galaith | GalaithQuest | 10,6,0, Use Staff_of_Estforlan With Barrier, The Dragon Speaks, Kill Galaith_Dragon |
| The Royal Guard, The True Heir | GuardQuest, KingQuest | Talk to Palace_Captain, the Chancellor and the Archivist, Talk to Rupert_On_Throne, 12,5,0 |
| The Hermit's Fire | HermitQuest | Talk to Hermit |
| A Place of Your Own | HomeQuest | Talk to Homestead_Settler |
| The Herbalist's Remedy | RemedyQuest | Talk to Herbalist |
| A Portrait of Mo | PortraitQuest | Talk to Ashford_Painter, Stroke Mo |
| Granny Wren's Walk | EscortQuest | Talk to Granny_Wren, Granny Wren Home, Talk to Ashford_Resident_34, 1,3,0, 2,3,0 |
| The Smugglers' Run | SmugglerQuest | Talk to Smuggler_Sergeant, Search Suspicious_Barrel, Talk to Red_Meg |
| The Dwarf's Grudge | DwarfQuest | Talk to Dwarf, Kill Skeleton, Kill Cave_Troll |
| The Wildwood Watch | RangerQuest | Talk to Ranger, Watch Stone 1-3, Kill Giant_Spider |
| Old Hob | HobQuest | Read Hobs_Diary, Talk to Witch, Use Calming_Draught With Hob, Talk to Hob |
| Wolves of the Moor | WolfQuest | Talk to Shepherd, Kill Wolf, Wolf Den, Kill Alpha_Wolf |
| Bog Lights | BogQuest | Talk to Witch, Talk to Elder |
| Bandits on the Road | BanditQuest | Talk to Captain, Kill Bandit, Open Strongbox |
| The Lost Caravan | CaravanQuest | Talk to Merchant, Caravan Wreck, Kill Scorpion |
| The Frozen Forge | ForgeQuest | Talk to Forgemaster, Kill Frost_Troll |
| The Withering Wood | DruidQuest | Talk to Druid, Heartwood, Kill Bear |
| The Barrow King | BarrowQuest | Talk to Gravekeeper, Barrow Door, Kill Barrow_King |
| The Lost Patrol | PatrolQuest | Talk to Scout |

House rules for new writing (from `CLAUDE.md`): notices and signs never give hints; a conversation answer that
belongs to one stage of a quest shows only at that stage; each player's chest loot and quest progress are their
own.
