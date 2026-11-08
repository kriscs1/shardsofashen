# Shards of Ashen: the rules in full

The owner's rules for the story, the game, its look and sound, and how code and data are written: everything that
must stay consistent. `CLAUDE.md` holds what applies to every change and says which section here to read for a
task (`grep -n '^##' "dev/Rules.md"` lists them). When the owner gives a rule that should last ("always",
"never", "from now on", or a correction of something done wrong), add it to the right section here, in the same
commit (to `CLAUDE.md` only if it applies to every change).

## The story

**You are the true heir of Ashen.** Every generation the dragon takes the king's firstborn heir, or it keeps
Galaith, the capital, shut behind a magical barrier: the city that holds the only land route across the world, with
the gold and Shard mines in the mountains behind it. Your mother, **Queen Mary**, ran from Galaith with you as a baby
to save you and to break the curse. The city has been sealed since your birth; King **Rupert**, your father, is shut
in it. You grew up poor on the Isle, in the **cottage on its east** (map 4,0,0), with **Jimmy**, a deep orange
ginger tabby with a creamy chin (Noops, by Edwin and Maren's house, is a big grey tabby: both drawn from the
owner's own cats' photos). New characters start with no sword.

The main quest line (`Type=Main` in `data/Quests.ini`, in chapters; the Isle's are built by
`dev/migrate/build_heir_isle.py`):

1. **The Last Will** (`LastWill`). A new character stands at Mary's fresh grave at the chapel graveyard's east end, by the
   sea (4,1,0's entry script runs `The Funeral`). The mourners go; **Edwin** the lawyer walks you home and leaves her letter on the
   table. The cottage door stays locked (a Lock) until you've read it: the letter (`Last_Will`, Read) tells you who
   you are, and little else: that she hid something, that the Isle kept her secrets, that your father waits in
   Galaith. **The main quest is discovered, not laid out**: no letter or stage text says where a thing is hidden or
   who has a boat; people and places reveal it as you go (the Amulet of Succession's stages say "something of your
   mother's", not "the amulet at the back of the caves").
2. **Dinner at Edwin's** (`DinnerQuest`). Edwin the lawyer and **Maren**, the Isle's doctor, live in the brick house
   in the Isle's north-west corner, by the sea (0,-2,0, two storeys; it was the bank, by the chapel, and its place Id
   is still `Isle_Bank`): her surgery and his desk downstairs by day, their rooms upstairs (0,-2,1), going up at
   night. There's no bank on the Isle. Three logs for her range (with the axe she
   lends you), an egg from Bess's coop fried on her range, the egg to Edwin. Maren gives the chapel trapdoor's key
   and makes you promise not to go down without a sword and shield.
3. **The Amulet of Succession** (`AmuletQuest`). **Bess** the milkmaid sends you to Frank before the hobgoblins; her
   husband **Frank** the blacksmith (his smithy by the dairy, smoke from its chimney by day) helps you make a wooden
   sword and shield. **Brother Aldous** opens the trapdoor to you once you wield both and Strength and Defence are
   level 2. The amulet lies behind bars at the back of the caves (1,1,-2); Aldous follows you down with a scroll of
   Grasp, and gives you the key of the hobgoblins' lair door.
4. **Passage to the Mainland** (`Passage`, done at 5). The ferries run from the start, for everyone, but **Wim**
   won't carry you without papers: since the raids, Northport turns back anyone off the Isle without them, and Bess's
   father **Tobias**, who kept the Isle's roll and wrote its papers, is missing; his house (the old brick
   house, 1,1,0, "Maren & Bess's Father's Home") is locked. The hobgoblins' lair (2,2,-2) is behind an iron door in the
   caves: four hobgoblins (killed ones come back when someone next comes in), the house key in the corner barrel,
   Tobias in a cage you pick the lock of (he gives you his house and moves in with Maren). A hidden ladder climbs into
   a tent in their palisaded camp (2,2,0): only a tent until you've climbed it from below. In his house a floorboard
   squeaks: stand on it, then Search it: the papers Mary left with him for you, under a crowned seal (what the
   hobgoblins were after; `Marys_Papers`, `PapersFound`). Wim reads them (and tells you of Northport's shardstone),
   and **the ferries** carry you (`dev/migrate/build_ferry.py`, the owner's wish): two boats, one from each pier, casting off together on the
   bell and passing halfway, turning to the way they go (`Ferry_Boat`, sixteen headings: a route in Carts.ini with its
   own vehicle, `carts.py`), both tying up at Northport's berth by the harbour pier; you step aboard, pay a coin,
   and ride it across. Northport's port guard reads your papers and sends you to the Speaker (The Temporary Capital).

**The Isle** is maps 0..4 by -3..2: `dev/migrate/grow_isle.py` grew it north to twice its size (its old north coast's
shape three maps further north, new land between), with Hollow Wood, Mirror Tarn, the Tin Braes and the Old Beacon in
the new land, and the ring of standing stones by its south-east shore. `move_lawyers_house.py` then put the
hobgoblins' camp back over their lair and moved Edwin and Maren's house to the north-west corner by whole maps (2,1 to
0,-2: every tile of it, upstairs and down, where it was on its map). `cut_isle_corner.py` cut away the Isle's
north-east corner: the coast comes down on the slant from the bay on the north coast to above the cottage, so the Isle
isn't a box, and the tin that was out there lies nearer the Tin Braes.

**The Isle teaches the game through play**, in what people say and give you, never in signs: Edwin hands over Mary's
jar of Shards (the bar under your health), Maren gives healing draughts (herbs mend you; Shards can't), Frank gives his
old dagger to break down for a Shard (Dismantle) and tells how to pick or force a lock (the Isle's chests have the
easiest), Brother Aldous shows you a dead beast's Shard Remnants (Absorb) and the Grasp scroll (learnt for good, cast
for Shards), and Wim points out Northport's shardstone. Anything new a player
must learn early is taught the same way, on the Isle.

On the mainland (built by `dev/migrate/build_estforlan.py`; the quests' scripts by `build_heir_mainland.py`):
5. **The Temporary Capital** (`ParliamentQuest`): the guard at Northport's port; the **Speaker** in Northport's City
   Hall, which is Ashen's Parliament while Galaith is lost. Only **Bert**, the great wizard of the **Wizards'
   Court** (the old King's Castle, 21,5,0; Bert at the top of its tower, 21,5,1), can break the barrier.
   **Northport is shut** (`dev/migrate/build_northport_blockade.py`, the owner's wish, to keep the start directed): it has only
   two roads out, the river bridge east (8,6,0) and the forest road south (2,10,0), each shut by oak gates (`City_Gate001`, a
   `Lock` on each gate tile, open once `ParliamentQuest>=2`) with a gate guard who says why (`Talk to Northport_<Way>_Gate_Guard`).
   Visible gates only, never invisible locks. Leaving only: nothing inside changes.
6. **The Ashford Road** (`AshfordQuest`): the **Mayor** in Ashford's Town Hall; the goblins' raid on the farms.
7. **The Steward's Hunt** (`HobgoblinQuest`): the **King's Steward** at **King Rupert's Keep** (the old Tyron's Keep;
   King Tyron is gone from the game), five hobgoblins in the old iron mine.
8. **Bert's Three Treasures** (`BertQuest`): 9. **The Staff of Ashen** (the King's solar, 26,18,1, up a locked
   stair in the keep); 10. **The Sunken Grimoire** (the scholar in Dunerest; a buried library under a mound in the
   desert, 3,18,-1); 11. **The Ember Ring** (the Warden in Emberwatch; the Ashen Priest wears it). Bert only wanted
   the ring: he teaches the spell (`BarrierSpell`), gives you the staff and warns of the **Sword of Valour**.
   **The middle leads you round the world** (`dev/migrate/build_middle_quests.py`: a zone at a time, a piece of gear at
   each; each place's keeper names the next, never a letter): 12. **Orrin's Chart** (`OrrinQuest`, level 10): Captain
   Rook (the shore below King Rupert's Keep, 27,20,0) won't sail the moving reefs without it; Orrin's ghost in the
   Sundered Tower (the Shattered Reach, 22,8,0), his Shadow below. 13. **The Frozen Lodestar** (`LodestarQuest`, 12):
   Nils at Frostwatch Lodge; the Drowned Shrine (20,25,0), the Rime Warden over its altar.
14. **A Ship for Dragon Island** (Rook's hull), 15. **The Island of
   Dragons** (26,23,0: drakes, three Valour Seals), 16. **The Sword of Valour** (the Temple of Valour's guardian).
17. **The Shardgate** (`ShardgateQuest`, `dev/migrate/build_shardgate.py`): with the sword, the staff at the barrier
   fails, because the dragon anchored it in the **Shardrealm**, where all broken magic goes. Bert gives the plans; you
   build a Shardgate in the old ring of stones on the hill north of the Wizards' Court (21,4,0: silver, sapphires, a
   Remnant's core, Shards, Shardcraft 5, and at least 8 shardstones active to steady it: Shards.ini `Shardgate.Stones`).
   Shardstones reach only the realm's calm **rim**; the anchor is in its **core**, a storm where broken magic pools,
   and only a great anchor like the ring can pierce it. It's on the world map once you've built yours. Through it, the
   realm's core (21,4,-10): past its Warden, the staff shatters the anchor. The gate stays, and you can go back (remnants roam the realm; its clusters
   give Shards).
18. **The Sleeping Sword** (`WakeQuest`, 14): with the anchor gone the barrier only thins; beyond it the dragon is
   plated in Shards (the Ashen Hand has fed it through the wall: `build_shard_dragon.py` draws it) and laughs at a sword
   that's asleep. Bert: it was made in three fires. 19. **The Ashen Foundry** (`FoundryQuest`, 15): Warden Oska at
   Ashfall Outpost, the Forgemother, the bellows (`FoundryHeat` 3; past it the fire chokes), the hearth. 20. **The
   Sun-Forge** (`SunforgeQuest`, 17): Nomad Tarek, the Sun Keeper (0,20,0), three mirrors turned to his grandmother's
   song (`Mirror.Dawn` east, `Mirror.Noon` south, `Mirror.Dusk` west). 21. **The Deep Anvil** (`AnvilQuest`, 19):
   Delver Maud, the Stone King (-7,10,0), four rune stones struck in the work-song's order (`AnvilRunes`); the anvil
   makes it the **Woken Sword of Valour** (`Replace.Item`: in your hand, its wear kept). The four givers' own kill
   quests (`build_zones.py`) are their "Odd Jobs for <who>" now, reached from their talk. Mithril helm, shield and
   platebody, the Dragonscale helm and platebody on the way.
22. **The Dragon of Galaith** (`GalaithQuest`, 20): the staff used on the barrier (in the pass, 0,14,0) breaks it once
   the sword's awake; the dragon speaks;
   it has `Slain.By=Woken_Sword_of_Valour,Sword_of_Valour` (a list: any other weapon leaves it at 1 hp). Its death opens Galaith's gate (its east gate,
   onto the field; its Id is still `Galaith_West_Gate`).
23. **The Royal Guard** (`GuardQuest`): the captain at the palace door (-10,14,0), the Lord Chancellor (Galaith's
   Parliament), the Royal Archivist (its City Hall) with the amulet, back to the Chancellor, the warrant to the
   captain.
24. **The True Heir** (`KingQuest`): King Rupert on his throne; the amulet, the will, the crown. Open play after;
   **Jimmy** sleeps on the throne and in your house on the Isle, and the mine behind Galaith opens: at its far wall
   the **King's Shard Seam** gives the Crown Shards once a (real) day (`dev/migrate/build_kings_seam.py`).

**The secret under it all: the Cutting** (the owner's choice; replaces the Heart of Ashen; `dev/Story and Quests.md`
"The secret of the Shards"). The dragon was a **devourer**, a vast hungry thing that swallowed the world's magic. The
first king **cut it down**: almost all of it was pushed out of the world into the Shardrealm, and what was left was
small enough to bind. **Shards are scraps of it**, thrown off by the Cutting: its power and hunger in small pieces,
tamed enough to use and still growing, and good at telling you what you want to hear. That's why a dead beast's
remnants go for its killer (a scrap wants a body to grow in), and why broken magic sinks into the Shardrealm, the rest
of the dragon, asleep (its rim the cooled edge, its core a storm where it dreams). The Pact is extortion: a royal
firstborn each generation is what the dragon feeds on, and the King's Shard Seam is where the first cut was made. **The
dragon is a villain and killing it is right**; the rest of it stays asleep in the Shardrealm as a shadow after. Mary
found the Pact's price at the Wizards' Court and ran to learn how it was made; her notes are found as you go. Each
chapter gives a piece (Aldous: take it in before it takes root in you; the Sunken Grimoire and the Ember Ring: the
king's side; the Shardrealm's core: the dragon's sleeping body; the dragon, dying: what it carried), still discovered,
never laid out. The Glass Wardens' chain in the Shardfall Deep (a side storyline, level 20+,
`dev/migrate/build_glass_wardens.py`: nine journals, four chimes rung in the season's order, the Shardsong and its
Quiet Draught, the Listening Room heard out in the Channelling stance, never answered) puts the rest together. At
the Seam you choose: the Binding, the Crown, or, only with the Wardens' truth, **Unmake** (break the Seam: storms calmer
and remnants passive for you, no more Crown Shards); the game plays the same after any. You don't leave the
Isle till you know what Shard Remnants are (Wim won't take you till you've absorbed some, and are level 3).

The old chapters (The Ashen Hand, The Ashen Omens, The Dragon of Ashpeak and its lair 0,0,-9) and the side quest
The Beggar's Lost Key are gone; their places stay, quiet. `dev/Story and Quests.md` has every quest, step by step.

Side quests hang off these by `Requires.Quests` and `Requires.Level`. A new quest must fit this world: its places
named in `WorldMap.ini`, its giver a placed NPC, its stages written in `Quests.ini` with `Marker<N>` place Ids.

## Game rules to keep

### Shared vs personal
- Shared, seen by everyone: chopped trees, mined rocks, fires, dropped items, NPC deaths and kill loot (the
  killer's for 10 s), shop stock, unlocked doors, the time and the weather, the horses and carts going round.
- Personal: quest attributes, quest doors and `Lock` lines, `Once=` items, NPC attitudes set by quests, fog of war.
- **Chests are per player**: everyone finds a chest's loot, once each. A chest script tracks its loot with an
  attribute, never with shared state.
- The world keeps running while everyone is logged out.

### Playing together (`dsengine/together.py`, `dev/migrate/build_together.py`; the plan: `dev/Roadmap.md` group 15)
- **Every story moment is yours; the world round it is everyone's.** Nothing in the story ever needs a second player;
  company makes it quicker and safer, never required. A scene's actors are added for the one player (`Add.Entity`
  after `$Attr`); a line about the other heirs is said only when one is near (`$Players.Near`).
- **A kill counts for everyone who fought it** in the last minute (a blow either way) and for the killer's party near:
  its Kill script runs for each, each gets their own loot roll. A boss (`Boss=1`) has more health for each fighter
  (`[Together] Boss.Per.Player`); a raid sends more for each player there. One alone still wins at the base numbers.
  **Every town has a surprise raid** (`data/Waves.ini`, `dev/migrate/build_town_raids.py`: raiders to suit its land),
  and it comes only while someone's there to meet it (`waves.py` random_attacks).
- **Parties** (right-click a player: Invite to party; `/p` talks to it, `/leave`): a quest stage one member reaches,
  the members near at that same stage reach too, with the quest's own things.
- **Friends** (right-click a player, or `/friend Name`): two Hallisium accounts are friends **by account, on the
  central server** (asking is a request till they ask back; any character of theirs, in every game; the journal shows
  "Character (account)", where friends are playing, and asks to Accept or Decline; the start screen's Friends too). A
  game server acts for a player only with the key their ticket brought (`/api/game/friends`). A device's characters
  keep the world's own list. The journal's Friends page (who's about,
  where; Whisper, Invite, Remove); told when one comes or goes; your homestead's friends are yours. **Trading**
  (right-click a player: Trade): a window with both offers, gold too; both accept and it changes hands at once, any
  change undoing both accepts. The journal's tabs: Crafting, Gathering, Quests, Spells, Records, Friends, Skills, Controls.
- **Gifts**: use an item on a player; they take it or not. **Town projects** (`data/Projects.ini`): anyone gives to
  the foreman; finished, what has `Project=<Key>` on its map line appears and the perk holds, for everyone. The town
  crier tells the news, the bounty clerk sets a hunt a day, the record keeper keeps the records (`/records`), the
  Pocket Anchor has a guestbook and a gift box, and a day away ends with what happened while you were gone.
- **Companions**: Jimmy follows the crowned heir (he finds secrets), a sellsword can be hired; they step aside when a
  real player in your party is near. Townsfolk greet the crowned heir (a speech bubble, now and then: never the
  chat log). The arena: talk to the Arena Master (in Ashford) once and the arena's shardstone knows you.

### Writing
- **Notices and signs never give hints or instructions.** They name or describe a place (and a signpost says which
  way places lie), nothing about quests, keys, secrets, who sells what or what you need to get in.
- **No hint text on the world map.**
- **Conversation answers that belong to a quest stage show only at that stage**: append `[if CONDITION]` to the
  answer, e.g. `About a ferry ticket... [if $Attr.Passage>=1 and $Attr.Passage<=10]`.
- Refusals are plain: "The chest is empty." (with the `Empty` sound), not hints.
- **Opening a chest says nothing**: what's in it shows in its box (no "Grave goods: ..." line).
- NPCs can have their own names through the map option `Name=` (underscores become spaces).
- **One of a kind gets its own script**: a thing's `Id=`, or a tile's place ID (an `Id` line; in the editor,
  right-click a tile, "Name this tile"), makes `<Verb> <Id>` run before `<Verb> <Kind>` (every grave has its own
  `Examine Grave_...`). Don't give many tiles one text when each could say its own.
- **The chat log isn't spammed**: no line per blow in a fight (the numbers over heads show hits and misses).
  Log what matters: kills, loot, level-ups, warnings, quest news.
- **Bad news is heard as well as read.** In scripts it's written there: `Display.Message COLOUR MESSAGE [SOUND]`
  (or a `Play.Sound` beside it). Every red script message (DarkRed, Red) says its sound: **`Denied`** (a low knock on a
  shut shutter) when you can't (too far, no axe, level too low); **`Fail`** (a lute's "oh well") when an attempt comes
  to nothing in the world ("..but fail to get any logs!"); **`-`** for none on purpose (arriving somewhere, a story's
  moment). The engine's own messages (not from a script) that say no get the Denied tell from `Session.take_out`.
- **Good news is heard too**: a gathering or cooking script's success line says its sound (`Gather_Wood`, `Gather_Ore`,
  `Gather_Fish`, `Harvest`, `Cooked`, `Crafted`: `dev/migrate/success_sounds.py`); unlocking, learning, levelling and
  quests have theirs. Only on the event, never on every swing. Other script messages are silent.

### Creatures
- `Attitude=Good` NPCs are friendly and can't be attacked. Only NPCs that would attack you keep you from sleeping.
- **Mosquitoes over the marsh** (`dev/migrate/build_mosquito.py`): tiny, and they swarm: one on the map is a cloud, the
  page drawing `Swarm=` of them (Entities.ini) buzzing about its spot, never still, fewer as it's hurt (`render.js`
  drawSwarm); weak, quick, flying; one for every so many marsh tiles out in the wild (never a settlement's map), and the
  Marsh and Bog terrains scatter them.
- **Malaria** (`dsengine/disease.py`, `data/Diseases.ini`, `dev/migrate/build_malaria.py`): a mosquito's bite may give it
  (`On.Hit=Malaria 5`; armour's no help). A disease has no end of its own: it stays through death and logging off, comes
  on as a bout of Fever now and again (Strength down, health down, the player shaking; a fever never kills by itself),
  and goes only for what says `Cures=Malaria` (the Fever Tonic: not the Antidote, nothing else). Morwen, in Saltmarsh,
  tells what it is and gives the first tonic; it's brewed of bog myrtle and mangrove bark (`dev/migrate/build_mangroves.py`: mangroves stand in the mud where marshland meets the sea; Strip Bark).
- **What doesn't keep** (Entities.ini `Shelf.Minutes`, `Spoils.To`; `player_items.py` shelf_*): real time, wherever it is;
  an item's `wear` is the second it was made, so it goes with it through the bank, the ground, the market, a trade and
  a grave. `keeps_wear` is what says each one has its own; anything new that stores an item keeps it, or refuses it.
- **The Dark Mage** (`build_dark_mage.py`; Entities.ini `Blink.Every`, `Blink.Near`; `npcs.py` npc_blink): in a fight it
  jumps away when you come near, when it's hit, or when it's stood long enough, always somewhere in sight of you on the
  same ground. It's beaten in the moment after a jump, before it can throw again, or held still by ice or a stun.
- Prey (hens, cows, sheep, rabbits, ducks, frogs, seals, otters) has `Flees=1` and is **Passive**, its kind and every
  map line (`dev/migrate/prey_passive.py`; validate.py holds it): it can be hunted, runs from whoever hits it and never
  fights back.
- Aggro needs line of sight; lookouts (`Face=`, `Sight.Cone=`) can be sneaked past, and a `Group=` raises the alarm.
- **A fight brings the others near it**: a monster that comes for you brings those of its side that would see it
  (their `Aggro.Range`) or hear it (`ROUSE_HEAR` by their `Hearing`), nothing solid between, and that could chase you
  where they are (`npcs.py` npc_rouse). One step: those it brings don't bring more. Not while you're hushed (Silence).
- **Every monster's senses are its kind's** (Entities.ini, set by `dev/migrate/build_senses.py`): `Sight.Cone` (how
  wide it sees, 360 all round), `Aggro.Range` (how far), `Hearing` (how far your noise carries to it: a bat 2, a
  skeleton 0.6) and `Chase.Radius`. They work in every stance: one that looks one way turns to a sound, one that sees
  all round comes for it; Sneaking only narrows them, and shows them (cones, and a dashed ring for hearing).
- **Creatures come and go as Shard essence**: one that comes back (a respawn, a raider, a risen remnant) is drawn
  together out of motes (`Shard_Form`, and its sound), and one that dies lets them go (`Shard_Fade`): `world.shard_form`
  and `shard_fade`, never a puff of smoke.
- Buffs and debuffs end on death (a disease doesn't: below). Dying keeps what's in your hands first (weapon, shield), then the dearest things
  (`Death.Keep.Items`); the grave's time starts once you're up again, not on the death screen.
- **The Isle's hard fights stay as they are** (the owner's choice): the Skeleton walking the chapel graveyard (3,1,0)
  and the hobgoblins' lair's four. Don't take them out or soften them to make the start easier.
- A skill can be **drained or boosted for a while** (status effects Weaken, Daze, Frailty on monsters' blows; a script's
  `Boost.Skill`): what asks for a level goes by it as it is now, the Stats tab always shows it out of its usual level
  (20/20; drained 18/20, red; boosted 23/20, green, a potion's or spell's boost to your blows counted in), and hitpoints and your level go by the usual one.
- **Stances** (`dsengine/stances.py`, `data/Stances.ini`; a round button for each by your health, never one that cycles
  (a phone: the one you're in, which opens the others; the chosen one fills a ring as it takes hold), or Q): none, Fighting
  (blows and guard up, magic hurts more), Channelling (spells stronger, wards and spell boosts longer, drains shrugged
  off; slower, a weaker guard; never potions: herbs), Sneaking (heard and seen less, more with Stealth; lookouts' sight
  cones shown; Pickpocket, Steal; slower). Each stance shows on whoever's in it (a red ring, a blue ring and motes, a
  crouch: `render.js` drawStance). A moment to change; a blow or a spell ends Sneaking. Monsters hear you
  (`noise_radius`): a lookout turns to look, but nothing sees or hears through a wall. A blow on one that never saw you
  is a sneak attack. Feedback: a ? over one that heard you, a ! and a sound when you're seen, a sound slipping past.
  Slipping past pays Stealth only for walking past it yourself, in its roam or near its patrol's path, against one
  above your level or not far under it, once a monster a while: standing still near one teaches nothing. Loud thieving (a chest
  forced, a rattle) wakes sleepers near (`wake_sleepers`); asleep, nobody sees your hand. A standing lookout's map
  line can say how often it glances about (`Turn=` seconds; 0 never, but to a sound and back).
- **Standing** (`dsengine/standing.py`, `data/Towns.ini`, `dev/Roadmap-6.md`): each town thinks of each player
  from Outlaw to Honoured, its own number for each; it sets their prices there, what its guards do when they're
  caught (a warning at Trusted, a fine at Honoured, more guards and sooner when Distrusted), and an Outlaw is
  refused at its shops and hunted by its watch till they pay its captain's fine. A rank change says a line and a
  sound; points alone say nothing. A theft nobody sees costs nothing. Never a main-quest door or NPC that asks for
  standing, and Galaith's guards wait for The True Heir.
- **Thieving** (`dsengine/thieving.py`, `data/Thieving.ini`): pockets by trade, shops' shelves, houses' Valuables
  (about half the houses: `build_stealth.py`); caught, a guard comes (levels above you), seen by everyone but after you
  alone, and that shopkeeper won't serve you a while. **Locks** (`dsengine/locks.py`, `data/Locks.ini`): chests have a
  lock by place (the easiest on the Isle, to learn on; never on a chest a quest needs); key, Pick Lock (Stealth) or
  Break Open (Strength), but an iron-bound chest (`Sturdy`: the high locks and a share of the rest, never the Isle's)
  is only picked or keyed; unlocked is yours, saved. Secrets (51, by every settlement) and traps (every monster-held
  level under the world, and the wild camps) are scattered by `build_whimsy.py`. **A thief's eye**
  (`dsengine/senses.py`): hidden traps and secrets noticed as you come near; a seen trap is marked, can be disarmed,
  and doesn't spring as you sneak over it. All of it each player's own.
- **Tricks** (`dsengine/tricks.py`): invisibility (no monster sees you; strike or cast and it's over) and body swaps
  (`Swap=1` creatures and townsfolk, for a strict time: no hands, monsters pay you no mind, `$Player.Form` says what
  you are, e.g. a cat flap's `$Player.Form=Cat`). A script can `Turn.Into` a creature for a while. **Silence**
  (Effect=Silence): a hush round you for a while; whatever you fight makes no sound to bring the others, a camp can't
  raise its alarm and your fighting isn't heard. **Dread** (a bolt's `Fear=` seconds, `player_combat.py` frighten):
  the foe runs from you, and a blow doesn't turn it; never a boss, a `Slain.By` one or a `Fear.Immune=1` one.
  (`dev/migrate/build_hush_and_dread.py`: Silence's scroll at the wizards', Dread's in Redrock Manor's vault, behind
  Ambrose's quest, The Redrock Signet.)
- **Secret rooms in the caves** (`dev/migrate/build_secret_caves.py`): a chamber in the rock behind a cave's wall, under
  a black roof of its own (`Hidden_Dark001`, a roof group: gone once you're under it, so nothing shows from outside),
  reached by walking through a wall that isn't there (`Cave_Wall_Hollow001`, a hairline seam; a `Hidden_Way_<map>`
  Trigger says so once). A chest each inside, by what lives there. A thief's eye may catch the draught first
  (`senses.py`). More can be drawn by hand from those two tiles.
- **The Shifting Deep** (`dsengine/deep.py`, `data/Deep.ini`, `dev/migrate/build_deep.py`): an old Shard mine south
  of Greyford whose floors (40,40,-11 and down) are made in memory, never files, and made again every
  `Shift.Minutes` once nobody's inside: rooms and tunnels, monsters by depth, chests (once each a shift; now and then
  a mimic), hidden traps, a secret room behind a cracked wall, and the Deep's Heart at the bottom. Its things are the
  engine's (`deep_do`), not scripts.
- **Random encounters** (`dsengine/encounters.py`, `data/Encounters.ini`, `dev/migrate/build_encounters.py`): about every
  `Every.Minutes` a player's turn comes round, out of doors with nothing else going on, and someone or something turns
  up near them for all to see: the **travelling salesman** (different goods each visit: ItemRacks.ini `Pick=N` of its
  items, chosen as he arrives, the same for everyone; what's bought is gone till his next visit), the **jester** (jokes;
  riddles that pay once each; a trick every ten minutes, from a coin behind your ear to a chicken), the **Shard
  Abomination** (`Where=Wild`, `Min.Level=`: as strong as the player it found, `Boss=1`, plenty of remnants). A kind's
  `Requires=` keeps them off the Isle's first days. People walk in and walk off once their time's up; a monster nobody's
  fighting comes apart. Never saved. A script or the admin panel can send one: `Start.Encounter`. A new one is a
  section of Encounters.ini.
- **The seasons** (`dsengine/seasons.py`, `data/Seasons.ini`): a year of `Year.Days` real days, from the clock. Longer days in summer, longer nights in winter; winter's snow instead of rain, rivers and lakes frozen over (bodies of water under `River.Most`) to **thin, cracked ice you can't walk on** (`Thin_Ice001`, a big seamless texture of long cracks: `dev/migrate/build_thin_ice.py`; the Rime's thick `Ice001` is the one that carries you), `Season.Absent=Winter` kinds gone; the catch swaps (`[Swap.<Season>]`, on every script's Give.Item), crops grow by `Crop.Growth`. What's only seen is the page's (`ground.js` seasonal, snowPatches: worked out once for each picture, never a canvas filter). `$World.Season` for a script.
- **What happens on its own** (`dsengine/wonders.py`, `data/Wonders.ini`, `dev/migrate/build_wonders.py`): shard storms; ghost ships on foggy nights, gone by morning; the Wandering Inn (a different `Inn_Spot_<n>` each day); mimics (a misspelt name, a glint, `Glint=1`; accuse one and it stops pretending); grudges (what killed you or got away hurt comes back scarred and stronger, attributes `Grudge.*`); the Tax Collector, polite and unkillable, walking after anyone over `Tax.Gold`; the year's Champion (arena wins in winter, crowned in spring, a statue on the boulevard); letters by carrier (`/letter Name [+Item] text`, friends only, a courier finds them). Your own legend (`data/Legend.ini`) is told with the rumours (`legend_due`); a line's condition is any script condition.
- **Zones by level** (`dev/migrate/build_zones.py` ZONES, MOBS: the one table of what's how hard): the Sallow Waste (it was the Dustlands, round Greyford, which was Moorcross, and the Greyflats, which were Greymoor: `rename_sallowcross.py`, `rename_greyford.py`) 6-9, the Mire and Emberwatch gates 10-12, the Shattered Reach 10-14 (only magic things), the Rime 12-16, the Ashfall 14-18, the Scar 16-20, the Stoneways 18-23. Mithril and gem rocks, yews and swordfish lie above ground only in these
  (`build_zone_sites.py --rare`). Each zone has places of its own (`dev/migrate/build_zone_sites.py` SITES: their own
  ground, real buildings, landmarks, monsters; the quest givers live in a few, with company, and no monster on their
  doorstep); never a ruin's outline: a few ruins, each its own shape (a corner, a tower's stump, a hall's wall,
  a wall with an arch, a foundation: `--ruins`), rubble round them and the odd thing to pick up.  You leave the Isle at level 3 (Wim won't take you before).
- **The zones' points of interest** (`dev/migrate/build_middle_quests.py`, beside the main quest's places there): bosses
  of their own (`Boss=1`, a trophy each: the Scavenger King on Bonebreak Mesa, Old Whitefang by Yeti Hollow, the Slag
  Wyrm in the Lava Fields, the Sand-Mother at the Drakes' Bones), side quests (Cael the penitent at the Cinder Chapel
  and his sister Oska; the Wandering Echo's riddles on Shardglass Field; Old Skadi's true-or-lie tales at Frostwatch
  Lodge) and games and odd folk (Lucky Lem's rat races at Rustwater Halt, Vesna's fortunes at Ashfall Outpost, the
  Mirage Trader, the Echo Pool's song in the Fungus Grotto, Fenn's mushrooms at the Delvers' Camp). Keep adding them.
- **Mary's notes** (`dev/migrate/build_wonders.py` NOTES): seven notes where she went; all found make a map to her cache at the Mirror Tarn (`Mary's Notes`), the Seam Splinter. Found, never told.
- **Banter** (`dsengine/banter.py`, `data/Banter.ini`, `dev/migrate/build_banter.py`): the world's people and animals carry
  on with each other where a player can see it. About every `Every.Seconds`, two near that player whom a scene fits stop,
  turn to each other and have a few words in bubbles (never the chat log); a dog sends a cat running (`After=Scatter`); the
  jester and the salesman have scenes with the guards and the trades; `B=Player` scenes are said to you when you've given
  cause (`When=` a chicken, any other shape, Sneaking, Hurt). Only how things look: never a hint or a quest, and nobody with
  a script of their own (`<Verb> <Id>`), hostile, asleep or fighting. A new scene is a section of Banter.ini.
- **Rumours** (`dsengine/rumours.py`, `dev/migrate/build_rumours.py`): townsfolk who gossip (Entities.ini `Gossip=1`:
  the trades, shopkeepers, guards) and have no words of their own (no `Talk to <Id>` script) now and then mention a
  quest you could start and haven't, before their usual talk; what's said is the quest's `Rumour=` (`Rumour.2=`...)
  in Quests.ini; how often is Config.ini `[Rumours]` (one every Every.Minutes, Chance in 100, each quest Times at
  most). A script can tell one: `Tell.Rumour`. Never for the main story (found, not told). A new side quest gets a
  rumour.
- **Every pub has its games** (`dev/migrate/build_pub_dice.py`): a Dice_Table, and a barkeep's Play (Three Cups, High or Low).
- **The world has a sense of humour, secrets and traps**: odd quests (Pip the invisible apprentice, Lady Pettigrew's
  hat and the geese, Granny Bramble's practice hex, the philosophical scarecrow, Duchess the talking cow, the Mayor's
  trousers), Bert's cat flap and big red button, a secret to Search by every settlement's square, traps in the old
  dungeons (a map `Trigger Trap_<Kind>`: `deep.py` world_trap), animals that talk to you in an animal's body
  (`tricks.py` ANIMAL_TALK); `dev/migrate/build_whimsy.py` places them. Keep adding them, in what things and people
  say and do; a sign still never hints.
- **The Shardfall Deep** (`dev/migrate/build_shardfall.py`, art `shardfall_art.py`): the level 20+ zone under the sea north of Ashford, round 8,-13,-1 (maps 4..12 by -17..-5 on level -1), where a great Shard fell into the sea. The way in is Gull Point's sea cave (12,-5,0) and the Wardens' Seal (a Lock: `ShardfallGate>=5`, the signet woken with Shards and Shardcraft 15). Its areas each have their own ground (textures), walls (each wall terrain its own rock tile, so the editor never mixes their faces), decor and monsters: the Drowned Stair, the Glimmering Galleries (a secret grotto, the Singing Geode), the Brinewater (glowfin, Fishing 22; the Brine Mother), the Lantern Wood (the delvers' camp and a shardstone, nothing hostile near it), Leviathan's Rest, the Wardens' Hold (dressed stone rooms, traps; the Hollow Marshal) and the Shardfall (Shard pools; the Shardborn; the Fallen Shard, Shards once a real day). **It's dim at every hour** (Config.ini `[Darkness] Maps`, `sky.js` dimHere): lit only by what has a `Light=` in it. Its maps are laid out once (`--maps` lays them out again, over edits to them).
- **The cold** (`dsengine/cold.py`, `data/Cold.ini`): out on snow or ice and not warm, health drops a little at a time
  after a grace (Cold by your health). Warm is a roof, a fire near, something worn with `Warm=1` (Fur Cap, Wool Hood,
  Wool Mittens: `build_cold.py`), or a Warming Draught lately (herbs: a potion).
- **Animals keep out of houses by where they roam**, not by a rule: an animal's `Zone=`/`Chase=` leave out the roofed
  tiles of its map (but the building it starts in, and its Home); cats and dogs come in. A new animal near houses gets
  its zone drawn round them (the editor's Paint tiles, or `dev/migrate/assign_homes.py`).
- **Homes and beds**: an NPC's `Home=` (an area) is where it is for the hours its Schedule keeps it in - townsfolk in
  their house at night, hens in their coop - and its `Bed=x,y` the bed it sleeps in at night (`<Name>_Sleep4`, made
  by `build_sleepers.py`; Talk gets "fast asleep"). Townsfolk have a house each (`assign_homes.py`: never a building
  someone else lives or works in). Without either, a person goes out of the nearest door (no door on its map: into the
  nearest tent, `Shelter=1` in Tiles.ini: `dev/migrate/houseless_tents.py`), an animal slips away once nobody's near.
  A zzz rises over whoever's asleep, in bed or in a tent. `Schedule=Night` is a night owl (home by day, asleep if it
  has a bed, out after dark: one plain townsperson a town, `night_folk.py`); `Schedule=Always` never goes home or to
  bed (guards and tavern keepers have no bed: up all night already). `Roost=` is the old name of `Home=` (still read).
- **Townsfolk climb stairs and ladders** (`npcs.py` npc_to_level, `dev/migrate/npc_stairs.py`): a bed upstairs is
  `Bed=x,y Bed.Level=1` (a home on another level, `Home.Level=`); at night they walk up to it and in the morning come
  back down, and with nobody who could see either end they're simply there (seen and heard only in sight of it:
  never through a wall, nor under a roof you're outside of: `world.sees_spot`). `Zone.Levels=0,1` makes a Zone
  hold on both floors (the same tiles): now and then its roam takes it up or down (`dev/migrate/zone_levels.py`
  gave it to the townsfolk who roam a house with stairs or a ladder in it). Only tiles with `Climb=1` lead them (the house
  stairs, and a ladder up to a hatch: one the other way at the same spot of the next level), never a cave's hole, a
  tunnel's or a quest's ladder, the chapel's stair or one behind a `Lock`. One person is one NPC: never a day self
  downstairs and a night self upstairs (Edwin and Maren were).
- **Every NPC has a level** (its kind's, a little above or below; a map line's `Level=`: `world.py` set_npc_level), and
  a creature you can fight shows it on hover, its name coloured by how it stands to yours (grey far below, green, yellow
  about yours, orange, red far above: `tips.js` difficulty).
- Every hostile monster has a `Level=` (1-25, from its stats: `dev/migrate/build_remnants.py`). **A kill gives no
  Shards and no bones**: it may leave Shard Remnants on the ground (Absorb them, in the pack, for Shards), or, less
  often, its magic rises as a **Shard Remnant** (`Living_Remnant`), as strong as the monster's level, that goes for
  the killer and leaves more remnants when it's killed (`dsengine/remnants.py`; the numbers: Shards.ini
  `[Remnants]`).

### Magic and Shards
- **What a potion is and what a spell is.** A potion is herbs: it works only inside whoever drinks it (mends,
  strengthens, sharpens the senses, cures), needs no Shards and is used up. A spell is Shard magic: it reaches out of
  you into the world (strikes, freezes, carries things, carries you) or binds Shards round you as a ward. Shards can't
  mend a body or sharpen an eye, and herbs can't make Shards. A new thing is one or the other by that rule
  (`dev/migrate/potions_and_spells.py` put Healing and Farsight among the potions and made Stone Skin the Shard Ward).
- **A spell of your own**: Magister Quill's The Spellwright teaches it; at the Spellwright's Lectern (the Court's great
  hall) you choose its effect, power and reach, and its Shards and rest are worked out to balance
  (`dsengine/ownspell.py`, Shards.ini `[Spellwright]`: a bolt, a burst, a frost, a mire that slows, a ward). It's
  `Own_Spell`, known like any other.
- Magic runs on **Shards**, a balance each player has, shown on the bar under their health: **never an item in the
  pack** (`dsengine/shards.py`; a script's `Give.Item Shard` or an old save's Shards go on the balance). They never
  come back by themselves. Shard Remnants, chests, digging, dismantling and quests (`Reward.Shards`) give them; spells,
  enchanting and shardstones (a price to activate one, then a few Shards a journey) spend them, through `spend_shards` or
  `>Pay.Shards`: never below nothing, nothing taken unless the thing goes ahead, and a Denied word when you're short.
  No mana, anywhere: a quest or text that would need it uses Shards.
- **Every Shard number is in `data/Shards.ini`** (the balance, shardstones, chests, `[Dismantle]` rates by kind,
  `[Upgrade.<Spell>]` ranks, `[Remnants]`, `[Channeling]`, `[Shardcraft]`, `[Enchant]`): the builders only add what's
  missing there, so edit them in the ini.
- **Rare shards** (`Ember_Shard`, `Storm_Shard`, `Ward_Shard`) are items, not Shards: dismantling gear now and then
  leaves one, and Enchant binds it into a weapon or armour in the pack, making it its enchanted kind
  (`Emberbound_Iron_Sword`: `Base=` the gear, `Enchanted=` the word; drawn and mended as its base). All made by
  `dev/migrate/build_shardcraft.py`; gear a script asks for by name, and quest gear, has none.
- A woman is a woman in the story too: scripts say `$Player.Son`, `$Player.Boy`, `$Player.Lord`, `$Player.King`
  (daughter, girl, lady, Queen for her), never a fixed "son" or "King" for the player.
- The fast-travel stones are **Shardstones** (`dsengine/shardcraft.py`, `data/Shardstones.ini`). Each is **dormant**
  (`Shardstone_Dormant`: still, no glow) to a player until they **Activate** it; active ones animate. Travelling
  opens a copy of the world map with every stone you've activated: tap one to go. The menu never counts your Shards.
  The attunements in saves keep their old names (attribute `Waystone.<Key>`, place Id `Waystone_<Key>`): don't
  rename those.
- **A scroll only teaches.** Learn it and the spell is yours for good, the scroll used up (if your Channeling is high
  enough; else it's kept); a scroll for a spell you know says "You already know this" (dismantle it for Shards).
  Spells are cast from **Spells**, the Stats box's third tab (click: cast; right-click: on or off the hotbar), or
  the hotbar; a spell that needs a target and has none is held ready for the next click. Never "Cast" on a scroll.
- **Scrolls are rare** (`dev/migrate/rare_scrolls.py`): one at a time (`Stackable=1`), none at the start, none from
  beasts or ordinary chests, and nobody writes them. They come from quests, a few chests in places of their own (the
  standing stones', the cinder cache's), the Shifting Deep's Heart, and the wizards' shops, dearly (Value 100 + 40 a
  level). A scroll a quest gives or a chest holds is never for sale (`Value=0`, `Droppable=0`). Upgrade scrolls (`Rank=2`, Fire_Bolt_Scroll_II) raise a known
  spell a rank; each rank's values are `Key.<rank>` in Shards.ini `[Upgrade.<Spell>]`. Quests give items with
  `Reward.Items` and skill xp with `Reward.XP` (`Strength 3 Defence 3`), and a finished quest shows its reward
  screen. Set by `dev/migrate/build_shards.py`.

### Skills
- Skills go to **25** (Config `Skill.Max.Level`). A level asked for anywhere is on that scale; a script's success
  roll counts the skill twice (`($Variable.1*2+34)>$Random.Percent`). Gains are `XP.Scale` times what's given.
  Old saves are scaled as they load (`skills_of` in a save). `dev/migrate/scale_skills.py` did it, once.
- The skills, in this order: Strength, Defence, **Channeling**, **Shardcraft**, Hitpoints, Cooking, Crafting, Fishing,
  Mining, Woodcutting, **Alchemy**, **Homesteading**, **Stealth** (`dev/migrate/rename_skills.py`; an old name in a
  save or a script means the skill it's part of now: `renames.py SKILL_NAMES`).
  - **Stealth** is going unseen and light-fingered: sneaking past, sneak attacks, pickpocketing and stealing, picking
    locks, spotting and disarming traps, noticing secrets (`dev/migrate/build_stealth.py`).
  - **Channeling** (was Magic) is using magic: casting. Each level past the first takes Shards.ini `[Channeling]`
    percent off a spell's Shards, to a limit, never under a Shard (`channeled_cost`, and `castCost` in the page).
  - **Shardcraft** is making and working Shard magic: activating shardstones and the Shardgate, dismantling, absorbing
    remnants, writing your own spell, enchanting, shaping your pocket of the realm.
  - **Crafting** is Smithing and Crafting made one; **Homesteading** is Construction and Farming made one; **Alchemy**
    is herbs and potions (was Potion Making, before that Herblore). A merged skill in an old save keeps the better.
- A skill's name is one word in data (`Shardcraft`), and shown with spaces wherever a player reads it (`pretty`).
- The journal's **Skills** tab: each skill (not Hitpoints), how it's levelled (`data/Skills.ini` `Trains=`, in the
  player's words) and what each level opens up. That list is worked out from where each thing is set (crafting lists,
  `Gathering.ini`, `Spells.ini` and upgrades, `Requires=` on gear, `Buildables.ini`, `Thieving.ini`, `[Enchant]`), so
  it's never out of date: never write it out by hand. Only what no file says goes in `Opens.N=<level> <what>`
  (`skill_pages` in `dsengine/quests.py`). A skill's guide script (left-click it in Stats) agrees with the data too.

### Doing things
- Work is seen: a gathering script shows the skill over the player's head as it starts (`Show.Skill`) and plays
  its work with `Play.Animation <Anim> <Times> <Sound>` (chips, sparks, splashes; a lunge each beat).
  `dev/migrate/work_animations.py` adds them to new Chop/Mine/Fish/Pick scripts.
- **All tools wear** (`Durability`, no `Slot`): a use each go, and a broken one doesn't count until it's mended.

### Places and furniture
- The maps: `X,Y,Z.txt`: 25x21 tiles of 32 px. Z<0 underground, Z>0 upstairs. Levels of their own (nothing joins them): the arena 0,0,10, the Shardrealm 21,4,-10, the Shifting Deep 40,40,-11 and down (in memory), homesteads 0,0,1000+n (in memory). The Shardfall Deep is on -1 under the sea north of Ashford (4..12, -17..-5)
- Inside walls are `*_Thin_Plank*` floor tiles with the wall drawn along their edge (001-008 round a rectangle, 009-018
  the inner corners, passages and dead ends: `house_tiles.THIN_EDGES`, `dev/migrate/thin_wall_pieces.py`; a set's
  pieces after a gap row are put down by hand, the nine before it stretched). Beds, bookshelves, chests,
  sacks and work stations stand on the back-wall tile, against the wall, not a floorboard out from it.
- **Rooms have things in them** (`dev/migrate/build_interiors.py`): pictures, mirrors, tapestries, pegs and wall shelves
  (walked past) and cupboards, wardrobes, dressers, desks, tables, washstands and long clocks (solid), by what the room
  is and how big, against the walls: never in a door's or stair's way, where someone stands or a
  script puts someone, and a room's floor stays all one. The side walls have theirs too, seen side on (`Side_*_W` against
  a west wall, `Side_*_E` the same mirrored for an east one). Redrock Manor has its own.
- **A house shows its levels** (`dev/migrate/build_house_levels.py`): rooms under and over the world have a south wall; a flagged room's walls are `*_Thin_Flag*`, stone right up to them; a building with an upstairs has the upper storey's front (`<Wall>_Upper001/002`) in its roof's group, never a church's.
- Beds are 1.5 tiles: `Bed001` (the head) with `Bed002` (the foot) in the tile below. Never place one without
  the other.
- **Locked doors** (`dev/migrate/build_locked_doors.py`): a door locked for good (a private home, a boarded-up house)
  has an empty Condition and words that settle it ("Locked. Whoever lives here likes it that way."), never anything that
  reads as a puzzle; boarded ones wear `Door_Boards001`. A door that can be picked (`Pick=` on its Lock line) keeps the
  pickable message and has `Once=` loot behind it worth its level. Never lock a door of a room someone lives in
  (`Home=`), and never lock for good one with a ladder or hatch (a picked one can have one, to an empty floor). Northport's and Ashford's fenced yards (railings, an `Iron_Gate001`
  chained at Pick=24) are for Grasp through the railings or a master thief.
- Ladders and hatches line up exactly with the ladder on the floor above or below.
- **The floors over and under the world are roofed dark** (`dev/migrate/build_level_roofs.py`, the owner's wish): on
  levels 1 and -1 every building's rooms are under a black roof (`Hidden_Dark001`), each building its own group, so
  from inside one you don't see into the next across the dark. Caves and mines are left open (a cave runs from map to
  map and a roof only lifts on the map you're on). Run it again after adding an upper floor or a cellar.
- On the world map, places with no map look the same as unexplored ones. A level under or over the world is drawn in
  the world's frame and scale (`ui.js` worldFrame), so a cellar lies just under its house; only the levels of their
  own fill the map.
- **The mainland** (`dev/World Plan.md`) is built by `dev/migrate/build_estforlan.py` (its parts in
  `dev/migrate/estforlan`): change the plan there and run it again, never the maps by hand. The Isle is left alone.
  Galaith is a huge walled city on the sea west of the West Range (which runs down the whole west coast), on maps
  with columns below 0: the sea on its west and south (a harbour gate, a quay and a pier), its own mountains north
  (the mine in them, its level -7,11,-1) and east; the dragon guards its scorched field before the east gate, and the
  barrier fills the pass through the range. Inside, quarters: the Royal (walled again: the palace), the Nobles', the
  Merchants' (the square), the Commons (far from the palace). Land looks natural: no straight edges to coasts,
  mountains or deserts. The quest places are lifted from the old maps (`world_parts`) and set down at their old
  tiles, so scripts' coordinates stay right.
- **Passes over the built mainland** (the maps since have the owner's hand on them, so they're changed in place, not
  rebuilt): `coast_reshape.py` (the coast in big strokes, bays, a peninsula, islets: only wild ground and open sea, never
  near anything made or placed, nor on the owner's maps; `coast_repair.py` put back the land it ate by roads and
  sank the specks it left), `build_galaith_city.py` (Galaith redrawn: every building
  lifted whole, Ids and all, and set down in its quarter; what names the palace's or the mine's coordinates moved
  with them), `build_mirefen.py` (the west finished: the Mirefen swamp and Mirefold, its hut hamlet; the sea south of
  Galaith), and the owner's redrawing (`world_edit.py` holds what they share: the world as one grid of cells, what's
  natural and what's built, rewilding, roads joined again): `remove_towns.py` (Fenwick, Highwatch and Ravensgate gone,
  their quests moved: Morwen and Elder Pike to Saltmarsh, Granny Bramble to Thornwick, Captain Hale to Frosthold;
  Fenwick's cathedral kept), `move_keep.py` (King Rupert's Keep five maps south, onto Ravensgate's ground: maps
  renamed, so its solar is 26,18,1; Ravensgate's graves in a graveyard west of it; its old iron mine stays in the
  hills), `reshape_west.py` (the coast, the mountains' edges and the Mire Tunnel as the owner drew them: the Mirefen is
  reached **only** through the tunnel under the West Range, and the dragon's field opens on Galaith's valley only at
  the east gate), `move_ashford.py` (Ashford seven maps north, onto a peninsula grown for it: maps up to row -6),
  `build_manors.py` (Fenmoor Hall and Redrock Manor, bandit manors where Fenwick and Highwatch stood, and the Drowned
  Abbey; Redrock Manor a maze on three floors - its rooms shut off from each other, reached only by ladders and stairs
  up and down, the vault last: GAPS and LINKS say which, and a test holds that the way through is the long one; its
  rooms each floor's own sizes and each furnished for what it is, LAYOUT and FURNITURE, laid out again by
  `refurnish_redrock.py`). **Running `build_estforlan.py` again would undo all of them and the owner's edits**: don't, unless they're
  run again after it.
- **The marshes** (the Mirefen and the marsh round Saltmarsh): their water is **marsh water** (`Bog001`, a greeny brown, `build_marsh.py`; painted with the Bog terrain), the sea's `Water001` only out at the sea itself (`marsh_water.py`, once on the maps). A long boardwalk wanders, a single line of planks (`wind_boardwalks.py` ROUTES); a street near a settlement's middle stays straight. Places out in them (`build_marsh_places.py`): the Sunken Barge, the Peat Cuttings and the Wisp Ring in the Mirefen, the Eel-Catcher's Hut and the Drowned Bell by Saltmarsh, none needed by a quest.
- **The wide empty places and dead ends have something in them** (`build_wilds.py`, the owner's wish): each its own
  thing (an odd person, a tiny quest, an event, a minigame: the Ringing Rocks' CHIMES), a footpath to it from the
  nearest road, on the world map unless it's a secret (the fairy rings). A shared event (the Fen Horn, the Smugglers'
  Signal) does everything shared before its script reads an `$Attr`; what each player gets once is theirs.
- **Galaith's layout, the owner's sketch** (`dev/migrate/rearrange_galaith.py`, once): west to east the Royal quarter (walled, its gate on the boulevard, royal guards outside) with the Nobles' above and below; the fountain, graveyard, orchard and gardens; the Merchants' and the market; the hovels; then two more walls and the ground before the east gate, kept for war (ramparts, palisades, stores, guards). A tree-lined marble boulevard runs from the east gate to the palace door (`BLVD`). The palace is on -10,14,0 now.
- **Galaith's Royal quarter is a household** (`dev/migrate/build_royal_quarter.py`, the owner's wish): the palace has three storeys, the throne hall (-10,14,0) left exactly as the story's scenes need it; a stair down at (2,2) to the kitchens, servants' hall, larder and wine cellar (-10,14,-1), the King's stair up at (18,2) to the solar, Queen Mary's chamber, the nursery and the King's bedchamber (-10,14,1). Round it: the servants' quarters and the guards' lodgings, the royal stables with a riding yard and a farrier, kennels, a drill yard and gardens, everyone in it with a bed or a watch that never sleeps, the named folk with words of their own.
- **Galaith is paved inside its walls** (`dev/migrate/build_galaith_grounds.py`, the owner's wish; once on the maps): the
  Royal quarter in `Royal_Paving001`, the Nobles' in `Marble_Paving001` (the owner's repaving; it was `Noble_Paving001`), the rest in `Flagstone001`; **no paths or streets of their own
  on it** (`dev/migrate/galaith_no_paths.py`, the owner's wish: it's all stone, so a line of cobble or marble is only a line;
  the market square and the Fountain Court keep their marble, the two lawns their gravel); a tree stands in its own `Tree_Pit001` (an Under: it works on any paving). Just inside the east gate:
  the **Fountain Court** (`Galaith_Fountain`: the raised pool is a Stretch set, `Fountain_Pool`; its shadow on the paving
  is `Pool_Shadow_*` under what's there; the Grand Fountain stands in it, Toss a Coin), the **Graveyard**
  (`Galaith_Graveyard`: iron rails, `Lawn001`, every stone its own `Examine <Id>`; the royal firstborn's are empty) and the
  **Orchard** (`Galaith_Orchard`: Pick the apples and pears, `Apple_Pie` in Cooking; the gardener's cottage in it). No grass
  or dirt inside the walls but those two lawns and the gardens (a strip from the north wall to the south: the graveyard, the
  fountain, the orchard, then lawns, hedges, walks and a pond down to the south wall). The hovels stand about at random. A thing can be heard only near it: Entities.ini `Sound.Loop`, `Sound.Reach`
  (`audio.js` nearLoopTick: the fountain, louder as you come, nothing past its reach or under a roof): use it, not a whole
  map's Ambient.ini, for something that's in one spot.
- Settlements have a size, and what each size has (`estforlan/settlements.py` SIZES): Galaith a huge city; Northport a
  large city (its City Hall is the Parliament for now); King Rupert's Keep and the Wizards' Court medium cities;
  Ashford a small city; Frosthold and Wardhaven towns; Oakhollow, Thornwick and Emberwatch
  villages; Greyford, Dunerest, Wildwood, Saltmarsh and Mirefold (in the Mirefen, its huts on boardwalks) hamlets.
- **At most two merchants of a trade in a settlement** (a trade is what's sold: a market stall's meat and a butcher's
  shop are both the butcher's; taverns too). SIZES keeps to it; `dev/migrate/cap_merchants.py` shut the shops past two
  that were built before (their keepers stay and say so; a tavern past two is an inn, rooms only), and a test holds it.
- **Shops' stock varies** (`player_items.py` shop_stock): a rack's stock is the most it has; each delivery
  (Config `Shop.Stock.Hours`) it has a third of it up, now and then none (`Shop.Sold.Out` percent), while Config
  `Shop.Vary.Stock=1` (a rack's own `Vary.Stock=` wins). What's bought comes back after `Shop.Restock.Seconds` (an hour,
  up to four for dear things).
- **Horses and carts** (`dsengine/carts.py`, `data/Carts.ini`, `dev/migrate/build_carts.py`): a city's cart keeps to
  its route's points (set in the map editor, on Entities, or in the file: `PointN=` in turn, or `NodeN=` taken in its
  `Order=1,2,3,2,4`, a node more than once when it goes by again), stop to stop, waiting `Wait=` seconds at each,
  to the end and back (`Loop=1`: round and round). Hail it as it passes and it pulls up; Get In, pick a stop, pay the
  `Fare=`, and it takes you there, at a walk with nobody aboard and three times that with anyone in it. The rider stands
  in its box (the page draws them over it above its `Seat.<dir>` panel line); Get Out where it stops.
- Settlements stand far apart, wild country between. The market square is near the middle, paved roads off it; the
  shardstone stands by it. Every house is different, with space between; buildings never cover a road.
  Streets are straight and paved in the place's own stone near the middle (sandstone in the desert, boardwalks in the
  marsh...), and wander and turn to gravel and dirt further out.
- Roads join every settlement and place of interest on the same land; rivers are crossed by bridges. A city on a coast
  has a port; anything smaller a jetty; places of interest none. A quest place out of town stays out of town.

### Homesteads (`dsengine/homes.py`, `dev/migrate/build_pocket.py`)
- A homestead is a **pocket of the Shardrealm's calm rim** (the settlers' Stillwater), held by your **Hearth Anchor**
  (it was the Access Crystal). There are no homestones: any shardstone you've activated takes you home, and the
  **Pocket Anchor** in the pocket takes you back and says who may visit. A pocket is **always safe**: nothing hostile
  is ever added to one (`world.add_npc`).
- A new pocket is raw rim (`Rim_Mist001` round a little `Rim_Glass001`); you **terraform** it with Shards (Shards.ini
  `[Terraform]`) and Shardcraft: mist stills only beside held ground; grass and dirt won't lie on glass till it's soil.
  **Shard Blooms** are the best single source of Shards (Shards.ini `[Homestead]`), limited by Shardcraft, harvested
  by their owner in person. Building is Homesteading; terraforming is Shardcraft.

### Items
- Healing draughts come in three strengths: `Minor_Healing_Draught` (8-12), `Healing_Draught` (15-20),
  `Major_Healing_Draught` (26-32), brewed from more herbs as they get stronger; the Mega Potion is above them.
- Chicken meat is Poultry (`Raw_Poultry`, `Cooked_Poultry`, `Burnt_Poultry`). For any rename, add the old name to
  `dsengine/renames.py` so old saves load.
- New characters start with no sword.

## Look and sound

### Names

- The game is **Shards of Ashen** (the page, the app, the docs), the kingdom **Ashen** (it was Estforlan), and the
  port city **Northport** (it was Southport, then Northport). Everything else is named for it too
  (`dev/migrate/rename_shards_of_ashen.py`): the GitHub repository `kriscs1/shardsofashen`, the Docker image
  `ghcr.io/kriscs1/shardsofashen`,
  the Python package `ashen/`, the database `ashen.db` (an old `dragonsword.db` beside it is moved over as the server
  starts), the Android app `io.github.kriscs1.shardsofashen`, and "Shards of Ashen Editor.py". Not the weapon (the
  Dragon Sword, `Dragon_Sword`) or `dsengine/`, `dsedit/` and the `DS_` settings. The builders keep `estforlan` in their
  file names. Northport's Ids, scripts, shardstone and builders' town key are Northport too (`Northport_Square`,
  `Waystone.Northport`: `dev/migrate/rename_northport.py`; a save's `Waystone.Southport` is read as Northport's,
  `renames.py` RENAMED_WORDS). Its landing and its port are one place, `Northport_Port`; the ferry's pier is
  `Northport_Pier`.
- A character is a man or a woman (`look.body`: `f` is a woman, the `PlayerF` sprites, long hair and a skirt, drawn by
  `build_player.py`); the look's colours recolour either. Anything drawn on a player works on both.

### Art and sound

- Tiles and sprites are 32x32 pixel art. Creatures and objects have a 1 px dark outline (the mask-silhouette method
  in `build_wolf.py` and `build_cats.py`), and walk in frames `<Name>2a-c` (right) and `<Name>8a-c` (mirrored).
- Art and sounds are made in code by `dev/migrate/build_*.py` (pygame drawing; synthesized 22050 Hz mono WAVs).
  Change the builder and run it again; don't hand-edit its output. Nothing from another game or a commercial
  library: anything not made here is CC0 (or as free) and listed in `CREDITS.md`.
- Keep things in proportion to a 32 px person: cats and butterflies small (a cat about a third of a person's height:
  `build_cats.py` draws every pose, then makes it `SCALE` as big on the same ground line), beds 1.5 tiles, a horse a
  little taller and half again as long as a person (40 x 34, `build_towns.py`; drawn facing east, its cart behind it).
- A creature's poses are one size and stand on one line; a cat sits before it lies down and sits up before it walks,
  and lying asleep it neither turns about nor fidgets (`npcs.py` npc_ease_pose).
- **Townsfolk in other colours, from one picture**: the trades in `build_people.py` VARIED have Entities.ini `Looks`
  (three colourings: shirt, trousers, hair, skin) over `Look.Parts` (each part's exact shades); the browser swaps them
  shade for shade (`look.js` npcImage). Which one a placed NPC wears goes by its Id (or its spot), or `Look=N` on its
  map line (0: as drawn). Only how it looks: its name, words and quests are its own. One-of-a-kind people and guards'
  uniforms aren't varied.
- **Nothing looks like a grid.** Ground that covers wide areas (mountains, streets, the forest canopy, grass, sand, the sea,
  and lava, whose texture moves: `Texture.Frames`, `dev/migrate/build_ground_textures.py`) is painted from a
  big seamless texture (marsh is the exception, the owner's wish: varied tiles, `build_marsh.py`, each its own
  feature kept in from its edges so any two meet without a seam, mixed by weight by its terrain) (`Texture=` in Tiles.ini, `sprites/Textures`, `dev/migrate/build_terrain.py`), never one
  picture repeated every tile; a range is peaks of all sizes overlapping. Trees, bushes, rocks, grass and flowers
  are sized and nudged per tile (`ground.js` paintDecor), always inside their own cell. Small things to put down anywhere
  (stones, pebbles, shells, twigs, fallen leaves: `dev/migrate/build_small_decor.py`) are decor, some scattered by
  the terrains they suit.
  Where two grounds of different `Blend` meet, a few flecks of each lie across on the other's side (`ground.js` flecksOf).
  A range's edge has no right angles: its corners are cut on the slant as the ground's painted (`ground.js`
  paintSlants), and a bay's inner corner filled with rock.
- **A creature looks like what it is** (the owner's correction: the scorpions were the spider, recoloured): a recolour
  (`gm`, `build_zones.py` MOBS, `build_middle_quests.py` BOSSES) only ever makes another of the same animal. A new kind
  of animal is drawn (the scorpion in `build_sprites.py`: pincers, eight legs, the tail curled over with its sting). A
  recolour keeps its parts apart: one colour over the whole picture (`tint`) turns wings, body and belly one mud, so a
  creature that must stand out on its ground (the Sand Drake on sand) goes along a ramp of colours (`ramp_tint`).
- Nothing shows as a placeholder ("?") while its picture loads: draw nothing till it has.
- **Drawing stays cheap**: no canvas `filter` (blur...) or high-quality scaling of the whole view every frame. Work it
  out once when it changes (the fog is blurred on a small picture, then stretched).
- Every distinct event deserves its own fitting sound (fizzle for a failed spell, "duh-derr" for an empty chest).
- **Sounds belong to the old world**: plucked strings, wood, low bells, breath, voices, never a clean electronic
  tone or anything shrill (a chime above C6 goes down an octave). The yes/no, magic and small creatures' sounds are
  `dev/migrate/build_soundscape.py`'s (`build_sounds.arpeggio` plucks a harp); a sound with takes (`Fail`, `Fail_2`,
  `Fail_3`) is played at random among them.
- A sound carries only as far as it should: `world.sound(..., radius=)`. Doors and animals' calls are heard from
  close by only (`HEAR_DOOR`, `HEAR_CALL`), never from a building or a pond you can't see.

### The view, the screen and the client

- The camera stays on the player: past the last map there's only black (never held back at the edge of the maps).
- Going somewhere else at once (a shardstone, a script, dying; not a ladder or a stair) fades the view out and in, over
  at least 2 seconds. A stair or a ladder is heard first, then you move (`>Map.Exists`, the sound, `Wait 0.4`, the
  `Teleport`: `dev/migrate/climb_sound_first.py`).
- Walking keeps to the walk masks: a fence thinner than a path cell stops the path (`maps.py` cross_r/cross_d) and
  the feet (a step never skips over it).
- A tile changing (a door, a chopped tree) sends just that tile (`mapcells`), not the whole map again: keep it so.
  The phone and many NPCs make full-map repaints the thing that lags.
- **The sidebar runs the whole height** of the desktop layout, the chat bar only under the view (`ui.js` layout; the
  art: `build_gui.py` STAT_H, INV_ROWS): the Stats box 240 high, the pack's well under it with its heading drawn by
  the page (Inventory, and how full it is). The pack is Config `InventoryItems.Rows` by `Columns` (9 by 5), read the
  same by the server and both layouts.
- **The hotbar has as many slots as each player chooses**, 1 to 10 (Options; kept with the character: `hotbar_n`),
  keys 1-9 and 0; on a phone it goes in two rows when one would run under the stick.
- The Stats box's tabs are Stats, Gear and Spells. Quests live in the journal (H), in two tabs: In hand (begun, and
  those you can start now, never the ones still locked) and Done; no rewards, and a click on one follows it.
- Hover text is at most 4 lines, at the top middle of the view (both layouts). Your level, health and Shards are top
  left of the view, not in the sidebar.
- **One client, two layouts.** The same `web/js` is the desktop game and the phone's (`mobile.js`: `M.on` on touch
  screens and in the Android app). The phone's has no sidebar or chat bar: a round minimap top right (tap: the world
  map), the Bag, Chat, Journal and Menu buttons, a stick, tap and hold. No Talk or Map buttons. The phone turns
  either way (the app's `fullSensor`): held upright the game is 480 wide and as tall as the screen, a box sits under
  the minimap with the pack below it, and the bag puts the Stats box over the pack (`L.upright` in `layout`).
  Anything new on screen must work in both layouts, and on a phone both ways up, with finger-sized targets; nothing for the app goes in `android/` that the page
  could do.

### Servers, apps and accounts

- **The phone can be the server.** The Android app runs `server/` itself (Python 3.11 through Chaquopy, with its
  aiohttp) so others on the same network can join; `server/lan.py` lets the app find games on the network. A public server on a cloud VM:
  `deploy/docker-compose.cloud.yml` and `deploy/cloud-setup.sh` (Caddy for HTTPS, `DS_TRUST_PROXY=1` so the limits
  go by each player's own address, sign-ups limited by `DS_REGISTER_PER_DAY`, admins' `/kick`,
  `/ban`, `/mute`): README-Server.md says how. Every game has a name
  (the host's, in Options; else `DS_NAME`: on Unraid, "Server name"), on the login screen, in the app's list and in the start screen's Public servers. The app opens on Single player
  (`solo.db`, this device only: 127.0.0.1) or joining a game. So
  `server/` and `dsengine/` stay standard library plus aiohttp: no pygame, numpy or anything that needs a shell.
- **Getting into a game is simple, the owner's rule** (README-Server.md "How you get in"). A server's own address shows a
  browser nothing (`make_app` index: a 404) unless it has a ticket (or `joined`, what's left of one) or comes from an app
  (`app`), or it's this machine, or an app's own game open to its network, at the address its host's Options show. The
  **website** has sign-in, the Public servers (login needed) and a friend's link (`/play/<id>/` sends you to sign in, then
  on in), nothing else. The **apps** ask you to sign in, and can skip it: Single player (no login); Friends' games; Join a
  local game (found by UDP broadcast on the network, never through the central server, or an address, or a friend's link;
  no login, and everything stays on the network); Public servers (login needed).
- **A server of its own is always a remote server, the owner's rule** (Unraid, a cloud VM: `GameServer.remote`; there's no
  setting for it): with `DS_CENTRAL` it announces itself, is listed once it's approved, wants a Hallisium account even from its
  own network, never answers the network's search, and a ticket is only given for its listed address. Local games are only
  ever an app's own.
- **A character is tied to where it's made, the owner's rule**: the creation screen says so (`PLACE_WORDS`, `place_of`).
  Nothing made on a device ever reaches a public server. A public server's character can be **copied one way** to the
  player's own device (`export_character`, `import_character`: only an app's own game takes one, from its host), and the
  original stays on the server. **A remote server's page shows only for a ticket** (or the `joined` token its page was
  given for one), never for its own network or machine, and it's never joined by address; the Public servers list has no
  addresses (a ticket brings the one you join).
- **The apps have one game, opened from inside it** (Options; `ds_host.py`, `make_app(own=True)`): closed each time it
  starts, on 127.0.0.1. Open to your network: it binds to the network and answers its broadcast, needing no login, its
  address shown to the host. Open to the internet, needing the host signed in: `server/relay.py`, the game still running on
  the host's machine, its link shown to the host, the host's friends let in. Either or both, any time, nobody playing
  dropped by it. Signing out stops it. There's no hosting as a separate thing, and no listing an app's game publicly.
- **Every version has the same start screen** (`web/home/`): sign in to your Hallisium account first (or make one, or a
  forgotten password by email; in the apps, or play without one), then what's above.
  Signing out forgets the keys games know your account by; a guest's keys stay, so its characters are still there.
  Joining takes a ticket from the central server made out to that server's id. **The central server is
  `https://shardsofashen.hallisium.com`** (`web/home/config.js`, a cloud server's `DS_CENTRAL`); `deploy/central-setup.sh`
  sets one up on a VM in one line.
- **Ads, and paying once to remove them** (the owner's wish): the start screen shows AdMob in the Android app, AdSense in a
  browser (`DS_ADSENSE_CLIENT`, `DS_ADSENSE_SLOT`; `/ads.txt` from the central server), else the central server's own.
  The Android app sells **Remove ads**, a one-time Google Play product (`android/.../Billing.java`, `DS_ADFREE_PRODUCT`,
  `remove_ads` unless set): bought, its start screen shows no ads at all, and Google Play restores it on a reinstall. Never
  an ad in a game.
- **Open to the internet goes through the central server** (`server/relay.py`, `central/relay.py`): the host's game
  connects out (no router port, any network) with the key the host's ticket brought; friends open
  `<central>/play/<game id>/` and the central server passes the page, its files (kept there per version) and the game
  both ways. A relayed connection is "relay:<address>" (`auth.RELAY_KEY`): never this machine or its network, and let
  in only as the host's account or a friend's. So the game page's paths are relative (`assets/...`, `ws` beside the
  page): keep them so. Change the start
  screen in `web/home/` only, then run `tools/sync_home.py`; anything the apps do for it goes through `window.DSApp`
  (Android's Bridge, the desktop's `desktop/app.py`), the same names in both. Remote servers are listed only once
  approved on the central server's admin page (`/admin`), and players are told everywhere that a character lives on
  its server only.
- **Characters have no passwords; the Hallisium account is the only login** (`server/game.py` authenticate,
  README-Server.md "Who's who"). A character belongs to an account (`owner` "a:Name": the central server's ticket) or
  a device (`owner` "d:...": a key the start screen gives each game, each its own), at most `MOST_CHARACTERS` on a
  server, its name one of a kind there; the game page opens on that player's characters (choose one, or make one). A
  device's key alone does on an app's own game, from its machine and network, or anywhere on a server with no central
  server, never on a remote one. The app's own game lets the start screen in by the host's key (`DS_HOST_KEY`, the start screen's own),
  so playing alone needs no network. A device that came in by an account is that account's on that server after, unless
  the central server has banned it (`central_banned`: asked each time and every minute in play; no answer isn't a ban;
  it says only yes or no, so the reason shows where they've proved who they are: signing in, or a ticket). The central
  server's admin page deletes an account two ways, its email, password, friends and keys gone either way, never an
  admin's: **Delete** keeps the name back (`accounts.deleted`, so nobody gets its characters), **Delete and free the
  name** takes the row too; an account the central server doesn't have counts as banned on a game server.
  A connection through a proxy nobody declared (`DS_TRUST_PROXY`) is `proxied:...`, never this machine or its network.
  Never add a password or a recovery code to a game server again. A Hallisium account has no recovery code either: every
  account has an email, confirmed before it can join a game (no ticket till then; the app's own game needs none), and a
  forgotten password goes only to a confirmed one. The logo is pixel art made by
  `dev/migrate/build_logo.py` (web/img/logo.png, web/home/logo.png).
- Never commit `.env`, tokens or `server-data/`. Admin rights come only from the DB flag or `DS_ADMINS` (Shards accounts, proved by the central server's ticket or the host's key), or `DS_CENTRAL_ADMINS` on the central server, where a name with no account yet is made only with the claim code the server logs as it starts, never by whoever signs up first.

### Answering the player

- **Prices show the game's coin, never a "g"**: `COIN` in `util.js` (drawText draws it, and writes "12 gold" so);
  `coinHTML` for page text. The same coin everywhere a price or a sum of gold is shown.
- **Every finished quest has its screen** (`reward_tick`, `showReward`), apart from the chat, its name and what it gave,
  even when it gave nothing but thanks.
- **A click is answered at once**: what's clicked is marked the moment it's clicked (registered: a gold ring; a foe a
  red one that tightens at each blow, hit or miss), then green when it's done or red, with a cross, when it's refused or
  comes to nothing. The server says which (`act`: `Session.act_done`, from its messages, sounds, boxes, items and
  work); something new a player does by clicking calls `act_done` when it succeeds or fails, if nothing else does.
- Text centred in a row uses `drawTextMid` (it measures the font's capital height): never guess offsets.

### The central server

- **Every character's progress is on the central server** (`server/progress.py`, `central/store.py`, the admin page's
  Characters, Quests and Skills): every game with `DS_CENTRAL` tells it level, skills, quests' stages, Shards, gold and
  map, from the saves, only what's changed. Never a device's key, the look, what's carried or what's said. **An app's own
  game is anonymous, the owner's wish**: no game name, account or character's name, only the device's random id (and a
  first-run notice on the start screen says so). Something new
  worth counting is added there, and to the privacy policy (`central/pages/privacy.html`) in the same commit. Anyone can
  send a report, so what's in one is cleaned (`clean_characters`), and written to the admin page only through `esc`.
- **The admin page stays plain** (`central/pages/admin.html`, the owner's wish): the browser's own font and colours, no
  pictures, gradients, shadows or rounded corners, nothing from anywhere else, nothing loaded till its tab's opened,
  lists a page at a time, and it works on a phone (each row a few lines, no sideways scrolling).
- **The central server is light on the wire**: a game keeps one connection to it (`central_post`), says nothing when
  nothing's changed (`have`/`same`, a report's hash), zips what's big; a browser gets a 304 for what it has. Nothing
  polls: a call made for every player every minute must have earned it.
- **Sign in with Google** (`central/google.py`, `DS_GOOGLE_CLIENT_ID`, `DS_GOOGLE_CLIENT_SECRET`): the code flow on the
  server, the same for a browser and the apps; never Google's own script (it can't work in an app's web view). An app
  opens the device's browser (`DSApp.openLink`, the same name in both) and has a code typed in. **An account made with
  Google signs in with it instead of a password** (the owner's wish): found by Google's id, its email kept in
  `accounts.email` like anyone's, no password ("Forgotten?" gives it no code). **A Google account with the same address
  as an account's confirmed email signs in to it** (the owner's wish), matched each time: nothing's stored on that
  account, its password goes on working. Only ever a confirmed address, one Google has verified.

## Code and data conventions

### Code and data files

- **Every value in a query is a `?` parameter, never in its text**: in `central/store.py` and `server/store.py` only the
  file's own table and column names are put in with `%s` (a test reads the code and holds it). A search goes through
  `like()`. Once it's opened the central database may only read and write rows (`no_schema_changes`). A multi-statement
  write rolls back on any exception, not only SQLite's.

- Match the surrounding code: its naming, its comment density, and its comment voice (short plain-English
  asides in parentheses, e.g. `# (a rug: under whatever stands there)`).
- The folders in the main folder are **lowercase** (`data`, `dev`, `maps`, `sounds`, `sprites`), and paths
  to them are written lowercase: the server runs on Linux, where `Data` isn't `data`. (Folders inside them keep
  their names: `data/Scripts`, `sprites/Tiles`.)
- Data files and maps are **cp1252 with CRLF**. Preserve both when editing; write them in binary mode from Python.
- Map cells: `Tile+Under(Rug)+Decor(Name)+Roof(Piece.Group)+Infront(...)`. Entity lines are tab-separated:
  `NPC|StaticObject|MapItem Name x y options`. In builders, use `build_isle.Map` and `obj_line` (1-based tiles).
- Scripts: `NN<TAB>Command<TAB>args`. `>Conditional COND LINE` goes on when COND is true and jumps to LINE when
  it's false. Generated scripts say which builder made them in their first line; edit the builder too.
- What a quest puts down for one player (Add.Entity after `$Attr` / `Get.Value ATTRIBUTE`) goes when they leave the
  game: a map's entry script puts back what must still be there (the letter on the table, Tobias in his cage).
- Open and Search on a StaticObject make it a chest (its script's Give.Items fill a loot box): a quest object that
  gives something uses its own verb (Reach In, Pick Lock).
- `build_walk.py` deletes walking frames it didn't make (the cats', Brother Aldous's...): after running it, put the
  deleted ones back with `git checkout -- sprites/Walk`.
- Builders and migrations in `dev/migrate/` are safe to run again (a second run does nothing, or redraws the
  same). A migration that is superseded refuses to run. A builder that takes over a script an earlier one wrote is
  named in `story_kit.TAKES_OVER`, so the earlier one run again leaves it be.

### The map editor

- The map editor's map: the mouse wheel zooms (Shift+wheel, middle-drag or Space+drag move the view); an area is
  marked across as many maps as it likes and copied or cut with the inspector's buttons, then each click puts it down,
  across maps too (`dsedit/region.py` parts); after a change only the maps changed are drawn again, and nothing goes
  black while new pictures are made: **a picture on the canvas is held till its new one is there** (`retire_photos`: Tk
  blanks an image that's let go of), and during a stroke only the tiles changed go on the canvas (`show_stroke`), so it
  keeps up with the mouse. What's read for every cell of a map comes from one pass (`tile_values`), never `tiles_ini.get`.
  **A map is drawn as the game draws it at its edges**: whatever looks at a neighbouring tile takes it from the next map
  (`render.py` `_tile_at`), and a change to a map's edge draws the maps round it again (`maps_round`).
  **Every line drawn on the map says what it is**: a `line:<key>` tag and an entry in `LINES` (the mouse's label reads it;
  "What are the lines?" lists them); an NPC draws no zone or chase it doesn't use (standing still, friendly). The Ground layer shows the decor and creatures faded over it, so you can see where you paint. A thing dragged off a map lands on the next one, whatever it is (a trigger, lock or place too; where there's no map it stays and says so), and on Entities an area marked and dragged moves just the entities in it (`move_area_ents`). **An NPC's zone, chase area and patrol go with it when it's dragged, the owner's wish** (`zone_follows`); its home, bed and nap are real places, and stay.
  Zoomed far out, a double-click zooms in on that tile at 100%. Every level under or over the world is laid out in the
  world's frame (`dsedit/world.py` own_level): one frame round every map on any of them, so a tile is at the same spot
  of the canvas on every level, and **going up or down keeps the view exactly** (the same scroll and zoom, every tile
  over the one below it), even where the other level has no map there. A slow job shows a banner over the window
  (`app.busy`) or a spinner in the header for one in the background (`app.working`): never a window that looks stuck.
  **Wherever something is referenced, the editor shows exactly what** (`dsedit/refs.py`): under each script, quest or
  file that points at it, the very lines (a script's, numbered, a click away). **A thing's "What it runs"** names the
  script the game finds for each verb, as `find_action_script` does (its own by Id, or one shared by every one of its
  name or kind), and for a shared one that the map decides (`>On.Map`), just the lines that can run where it stands.
  Right-click lets go of an area being pasted. Dragging an entity moves only its picture (the map is drawn once
  without it), and the palette makes only the pictures in view: keep both so.
- **The map editor's Auto palette and brushes** (`dsedit/terrain.py`): a terrain (`data/TileSets.ini` `Kind=Terrain`,
  `dev/migrate/build_terrains.py`: its ground mixed by weight, decor and creatures scattered at a density, `Water=1`,
  a wall's `Face=`), a set or a family of look-alikes is one palette entry that puts the right tile down itself;
  Detail shows every tile. Every palette entry has its name under it; Auto's are in sections under headings
  (Terrains; walls, fences and joins; roofs; sets; look-alikes; single tiles: `PAL_SECTIONS`). Terrains are painted with a brush of any size, Fill, Rectangle, or an Outline drawn round a
  place; painting rolls the decor and creatures afresh, takes off what another terrain scattered (never anything with
  an Id, a name, a zone or a patrol, nor built decor) and turns cave rock to its face over open ground (the coasts
  round themselves: see below). A new kind of ground or a wall gets a terrain in the data, not code. An NPC's `Zone=`/`Chase=` can be any
  shape: rectangles joined by `/`, painted tile by tile. Whole maps are moved, copied or deleted from the map's
  right-click menu (`dsedit/mapops.py`: what names them follows; the code that names them is listed). An entity's
  options are fields of their own (`OPT_SPECS` in `dsedit/pages/maps.py`): a new map option gets one there too.
- The map editor shows a level as one map (`dsedit/world.py`). **How tiles go together is in the data, never the
  editor's code**: a set in `data/TileSets.ini` has a `Kind=` (Stretch: a 3-column grid of corners, edges and middle;
  Rug: that and its "runner"s; Join: pieces that join their neighbours, each with `Joins=` in Tiles.ini, the sides it
  joins, `*` a tower, `-` a post, and `Below=` for one two tiles tall; Shore: where two grounds meet on the slant, its
  `Land`, its `Water` (the ground its pieces lie on: the sea, a lake, sand), `Corners` and `Small` pieces of one
  corner and `Pieces=NE+NW:name` of more; Whole: one thing more than a tile big, a bed's head and foot, put down and
  taken up whole). A
  tile kept only for old maps has `Retired=1`: the Auto palette leaves it to Detail. The terrains are edited on
  their own Terrains page. A Join set (fences, palisades, the town wall, Galaith's wall) is painted freehand (the whole stroke
  laid again each step, so it comes out the same whichever way it's drawn, and the mouse outrunning it leaves no gaps), or
  with Rectangle a line or round a rectangle, and its pieces round it are joined again, painting or erasing; `Joins.Too=` on
  a set names the tiles that count as more of it without being changed (a gate in the wall). `dev/migrate/tile_joins.py`
  wrote them. Tiles numbered alike with no set of their own are look-alikes, one at random: anything that needs a
  particular piece in each place gets a set.
  Give a new set its Kind, and its pieces their `Piece=` (and `Joins=`).

### Ground and tiles, as drawn

- **Where natural grounds meet, they round themselves** (Tiles.ini `Round=1`: water, lakes, bog, sand, grass, marsh,
  dirt, snow...; `dev/migrate/round_world.py` set it and turned every laid corner piece back to its base): the game
  (`ground.js` paintRounds) and the editor (`render.py` _rounds) work it out at every corner of the grid from the four
  cells round it, so a map holds only plain tiles. A cell's corner whose two neighbours there are both another ground
  takes that ground out to the middle of its two edges, on a curve that leaves each edge along it (no angle where it
  starts), how full it is by that grid corner's own hash: a lone tile is
  round (no two alike), a one-tile pond a pool, a staircase a slope, an inlet's end a bay, two and two across a corner
  joined by the higher `Blend`. Where the ground filling it spills its blend over this cell's edges anyway, its curve
  runs round the bands (`INSET`: the game's, the editor drawing no bands), and a side rounded at both ends has no band
  at all, its curve its edge (so a lone tile is a full round, not a square of bands); where a corner is rounded away, its own ground's band stops at the middle of that
  edge, and the foam follows the water. Don't paint coasts with pieces or run a smoothing over the maps.
- **Corner pieces are only for a shape the rounding can't make** (`dev/migrate/build_ground_pieces.py`, laid by hand
  from Detail): a piece says what it's made of (Tiles.ini `Corner.Base`, `Corner.Land`, `Corner.Mask` NE,SE,SW,NW,
  `Corner.Leg`) and is painted from those, its corners from the land's own texture (`ground.js` cornerJoins,
  `render.py` _corner_poly where two pieces' corners run into each other). `retile_world.py` and `tarn_to_lake.py`
  are superseded.
- **What's raised off the ground** (Tiles.ini `Raised=1`: the boardwalk, `dev/migrate/build_crossings.py`) casts its
  shadow south and east, shows its front edge and the posts it stands on, isn't blended over, and turns its planks
  across the way where it runs east and west (`ground.js` paintRaised, `render.py`). The fancy bridge is two Stretch
  sets (`Fancy_Bridge_NS`, `Fancy_Bridge_EW`: dragged over the water, its balustrade not walked over, its corner lamps
  lit at night); Galaith's wall is drawn there too.
- **Wooden bridges are one Join set** (`Wood_Bridge`, `dev/migrate/build_wood_bridge.py`, laid over every old plank pier by
  `wood_bridges_swap.py`): sixteen pieces by the sides they join (`Joins=` NESW, `-` alone), the deck's boards across the way
  you walk, a rail on posts with a toe-board and the support beams' ends on every open side (the outer row of the walk mask
  is the rail), the landward end left open. Not `Raised=1` (that turns a picture on an east-west run: these are drawn the right way).
- **Ruined walls are two Join sets** (the owner's wish: blocks side by side never made one wall): `Ruined_Wall` (tall,
  no seeing past) and `Ruined_Wall_Low` (seen over), sixteen pieces each by the sides they join, decor on any ground,
  `dev/migrate/build_ruined_walls.py`; one footprint down the middle of the tile, so a run is one wall, crumbling between
  joins and at a broken end, and a tall run and a low one join each other. `Ruined_Wall001/002` are retired
  (`ruined_walls_swap.py` turned every one on the maps into its piece): any wall that runs gets a Join set, never single blocks.
- **Fires that aren't campfires**: the `Blaze` (`build_blaze.py`, 8 frames of wreckage burning) is Galaith's, on its field and
  ramparts till The Royal Guard is done; it warms like any fire (`cold.py` FIRES). **Planks and marble are drawn nicer**
  (`build_nicer_floors.py`: four boards a tile, nails and knots; polished veined marble and a big slab texture for the streets).
  **The palace's inner walls are one thin strip like every house's** (`lay_rooms` draws a shared wall once).

### The validator, the clock and the tick

- New `Entities.ini` or `Tiles.ini` keys, script commands or map options must be added to
  `dev/migrate/validate.py`.
- **The validator stays quick** (under half a minute): each file is read once a run, and a file's existence comes
  from its folder's listing. The world's walking is each map's areas (`label_map`) joined at map edges and ladders;
  a lock is checked by working out only its own map again. Each map's areas and each sprite's size are kept between
  runs (`Kept`, in the PC's temp folder, never the game's folder) while the map or file is unchanged. A change to
  `label_map` bumps the number in `AREAS = Kept("areas", N)`.
- Don't use shell heredocs for edits with backslashes; write a patch script to the scratchpad, or use Edit.
- **The world's clock is UTC** (`clock_ms`, `clock_seconds`: from 1901, as LB's were), never local time: the clocks
  going back an hour must never make a wait an hour longer. A world saved before (no `"clock": "utc"`) is shifted once
  as it loads.
- **One player can't hold up the rest**: each player's tick, view and command runs in `World.guarded` (a fault is
  logged once and the world goes on); what's dear to make for a client (the journal) is sent at most once a second;
  every save is everyone online and the world in one transaction (`GameServer.save_all`).
