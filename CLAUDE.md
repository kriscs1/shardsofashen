# Shards of Ashen: rules for every change

Read this before changing anything. It holds what must stay consistent: the story, the game's rules, the look and
sound, and how code and data are written and checked. When the owner gives a rule that should last ("always",
"never", "from now on", or a correction of something done wrong), add it to the right section here, in the same commit.

## What this is

A top-down pixel-art RPG, played in the browser by up to 5 players sharing one world.

| Folder | What it is |
|---|---|
| `dsengine/` | The game's rules (authoritative, headless, many players) |
| `server/` | aiohttp: the page, assets, the game over a WebSocket at 20 ticks/s, SQLite (`DS_DB`) |
| `web/js/` | The browser client: canvas, ES modules, no build step. `web/assets/` is generated, never edited |
| `android/` | The Android app: carries the server and page; a phone hosts a game for its network, or joins one |
| `desktop/` | The desktop app (pywebview, built by PyInstaller): the same start screen and choices as the Android app |
| `central/` | The central server: everyone's account, the remote game servers' list, the start screen's ads |
| `web/home/` | The start screen, the same in every version (`tools/sync_home.py` copies it into the Android app) |
| `data/` | `Entities.ini`, `Tiles.ini`, `Quests.ini`, `Config.ini`, `WorldMap.ini`... and `data/Scripts/*.txt` |
| `maps/` | `X,Y,Z.txt`: 25x21 tiles of 32 px. Z<0 underground, Z>0 upstairs. Levels of their own (nothing joins them): the arena 0,0,10, the Shardrealm 21,4,-10, the Shifting Deep 40,40,-11 and down (in memory), homesteads 0,0,1000+n (in memory) |
| `dev/migrate/` | Builders and migrations that draw sprites, make sounds and place content (see below) |
| `dsedit/` | The map/data editor |
| `ashen/` | Shared helpers (`ini`, `lb`); the old desktop game is retired |
| `tests/` | `test_engine.py`, `test_server.py` (pytest) |

References: `README-Server.md` (running, deploying, shared vs personal), `dev/Data Formats.md`,
`dev/Script Commands.txt`.

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

1. **The Last Will** (`LastWill`). A new character stands at Mary's fresh grave in the chapel's graveyard (3,1,0's
   entry script runs `The Funeral`). The mourners go; **Edwin** the lawyer walks you home and leaves her letter on the
   table. The cottage door stays locked (a Lock) until you've read it: the letter (`Last_Will`, Read) tells you who
   you are, and little else: that she hid something, that the Isle kept her secrets, that your father waits in
   Galaith. **The main quest is discovered, not laid out**: no letter or stage text says where a thing is hidden or
   who has a boat; people and places reveal it as you go (the Amulet of Succession's stages say "something of your
   mother's", not "the amulet at the back of the caves").
2. **Dinner at Edwin's** (`DinnerQuest`). Edwin the lawyer and **Maren**, the Isle's doctor, live in the brick house
   by the chapel (2,1,0, two storeys; it was the bank, and its place Id is still `Isle_Bank`): her surgery and his desk
   downstairs by day, their rooms upstairs (2,1,1), going up at night. There's no bank on the Isle. Three logs for her range (with the axe she
   lends you), an egg from Bess's coop fried on her range, the egg to Edwin. Maren gives the chapel trapdoor's key
   and makes you promise not to go down without a sword and shield.
3. **The Amulet of Succession** (`AmuletQuest`). **Bess** the milkmaid won't sail without her father's compass; her
   husband **Frank** the blacksmith (his smithy by the dairy, smoke from its chimney by day) helps you make a wooden
   sword and shield. **Brother Aldous** opens the trapdoor to you once you wield both and Strength and Defence are
   level 2. The amulet lies behind bars at the back of the caves (1,1,-2); Aldous follows you down with a scroll of
   Grasp, and gives you the key of the hobgoblins' lair door.
4. **Passage to the Mainland** (`Passage`, done at 5). Bess's father **Tobias** is missing; his house (the old brick
   house, 1,1,0, "Maren & Bess's Father's Home") is locked. The hobgoblins' lair (2,2,-2) is behind an iron door in the
   caves: four hobgoblins (killed ones come back when someone next comes in), the house key in the corner barrel,
   Tobias in a cage you pick the lock of (he gives you his house and moves in with Maren). A hidden ladder climbs into
   a tent in their palisaded camp (2,2,0): only a tent until you've climbed it from below. In his house a floorboard
   squeaks: stand on it, then Search it, for the compass. Bess sails you to Northport; **Wim** the ferryman crosses
   for a coin after that.

**The Isle teaches the game through play**, in what people say and give you, never in signs: Edwin hands over Mary's
jar of Shards (the bar under your health), Maren gives healing draughts (herbs mend you; Shards can't), Frank gives his
old dagger to break down for a Shard (Dismantle) and tells how to pick or force a lock (the Isle's chests have the
easiest), Brother Aldous shows you a dead beast's Shard Remnants (Absorb) and the Grasp scroll (learnt for good, cast
for Shards), and Bess points out Northport's shardstone. Anything new a player
must learn early is taught the same way, on the Isle.

On the mainland (built by `dev/migrate/build_estforlan.py`; the quests' scripts by `build_heir_mainland.py`):
5. **The Temporary Capital** (`ParliamentQuest`): the guard at Northport's port; the **Speaker** in Northport's City
   Hall, which is Ashen's Parliament while Galaith is lost. Only **Bert**, the great wizard of the **Wizards'
   Court** (the old King's Castle, 21,5,0; Bert at the top of its tower, 21,5,1), can break the barrier.
6. **The Ashford Road** (`AshfordQuest`): the **Mayor** in Ashford's Town Hall; the goblins' raid on the farms.
7. **The Steward's Hunt** (`HobgoblinQuest`): the **King's Steward** at **King Rupert's Keep** (the old Tyron's Keep;
   King Tyron is gone from the game), five hobgoblins in the old iron mine.
8. **Bert's Three Treasures** (`BertQuest`): 9. **The Staff of Ashen** (the King's solar, 22,11,1, up a locked
   stair in the keep); 10. **The Sunken Grimoire** (the scholar in Dunerest; a buried library under a mound in the
   desert, 3,18,-1); 11. **The Ember Ring** (the Warden in Emberwatch; the Ashen Priest wears it). Bert only wanted
   the ring: he teaches the spell (`BarrierSpell`), gives you the staff and warns of the **Sword of Valour**.
12. **A Ship for Dragon Island** (Captain Rook, on the shore south of Ravensgate, 27,19,0), 13. **The Island of
   Dragons** (26,23,0: drakes, three Valour Seals), 14. **The Sword of Valour** (the Temple of Valour's guardian).
15. **The Shardgate** (`ShardgateQuest`, `dev/migrate/build_shardgate.py`): with the sword, the staff at the barrier
   fails, because the dragon anchored it in the **Shardrealm**, where all broken magic goes. Bert gives the plans; you
   build a Shardgate in the old ring of stones on the hill north of the Wizards' Court (21,4,0: silver, sapphires, a
   Remnant's core, Shards, Shardcraft 5, and at least 8 shardstones active to steady it: Shards.ini `Shardgate.Stones`).
   Shardstones reach only the realm's calm **rim**; the anchor is in its **core**, a storm where broken magic pools,
   and only a great anchor like the ring can pierce it. It's on the world map once you've built yours. Through it, the
   realm's core (21,4,-10): past its Warden, the staff shatters the anchor. The gate stays, and you can go back (remnants roam the realm; its clusters
   give Shards).
16. **The Dragon of Galaith** (`GalaithQuest`): the staff used on the barrier (in the pass, 0,14,0) breaks it; the dragon speaks;
   it has `Slain.By=Sword_of_Valour` (any other weapon leaves it at 1 hp). Its death opens Galaith's gate (its east gate,
   onto the field; its Id is still `Galaith_West_Gate`).
17. **The Royal Guard** (`GuardQuest`): the captain at the palace door (-9,14,0), the Lord Chancellor (Galaith's
   Parliament), the Royal Archivist (its City Hall) with the amulet, back to the Chancellor, the warrant to the
   captain.
18. **The True Heir** (`KingQuest`): King Rupert on his throne; the amulet, the will, the crown. Open play after;
   **Jimmy** sleeps on the throne and in your house on the Isle, and the mine behind Galaith opens: at its far wall
   the **King's Shard Seam** gives the Crown Shards once a (real) day (`dev/migrate/build_kings_seam.py`).

**The secret under it all: the Heart of Ashen** (being written into the chapters: `dev/Roadmap.md` group 8). Shards
are the pieces of the Heart of Ashen, a crystal of all the world's magic that the first king broke to bind the dragon
(the Breaking). Every piece wants to be whole again: that's why a dead beast's remnants go for its killer, and why
broken magic sinks into the Shardrealm, the hollow where the Heart lay. The dragon took the Pact to stay bound; its
price is a royal firstborn each generation, whose blood keeps the pieces apart, and the dragon carries the largest
piece itself. The King's Shard Seam is where the Heart was broken. Mary found the Pact's price at the Wizards' Court
and ran to learn how it was made; her notes are found as you go. Each chapter gives a piece (Aldous: the pieces "want
to go home"; the Sunken Grimoire: the Breaking; the Ember Ring: the Pact's seal; the Shardrealm's core: the hollow;
the dragon, dying: what it carried), still discovered, never laid out. At the Seam you choose: keep the pieces apart
(the Binding) or bind the dragon's piece into the crown; the game plays the same after either. You don't leave the
Isle till you know what Shard Remnants are (Bess and Wim won't sail till you've absorbed some).

The old chapters (The Ashen Hand, The Ashen Omens, The Dragon of Ashpeak and its lair 0,0,-9) and the side quest
The Beggar's Lost Key are gone; their places stay, quiet. `dev/Story and Quests.md` has every quest, step by step.

Side quests hang off these by `Requires.Quests` and `Requires.Level`. A new quest must fit this world: its places
named in `WorldMap.ini`, its giver a placed NPC, its stages written in `Quests.ini` with `Marker<N>` place Ids.

## Game rules to keep

**Shared vs personal**
- Shared, seen by everyone: chopped trees, mined rocks, fires, dropped items, NPC deaths and kill loot (the
  killer's for 10 s), shop stock, unlocked doors, the time and the weather, the horses and carts going round.
- Personal: quest attributes, quest doors and `Lock` lines, `Once=` items, NPC attitudes set by quests, fog of war.
- **Chests are per player**: everyone finds a chest's loot, once each. A chest script tracks its loot with an
  attribute, never with shared state.
- The world keeps running while everyone is logged out.

**Playing together** (`dsengine/together.py`, `dev/migrate/build_together.py`; the plan: `dev/Roadmap.md` group 15)
- **Every story moment is yours; the world round it is everyone's.** Nothing in the story ever needs a second player;
  company makes it quicker and safer, never required. A scene's actors are added for the one player (`Add.Entity`
  after `$Attr`); a line about the other heirs is said only when one is near (`$Players.Near`).
- **A kill counts for everyone who fought it** in the last minute (a blow either way) and for the killer's party near:
  its Kill script runs for each, each gets their own loot roll. A boss (`Boss=1`) has more health for each fighter
  (`[Together] Boss.Per.Player`); a raid sends more for each player there. One alone still wins at the base numbers.
- **Parties** (right-click a player: Invite to party; `/p` talks to it, `/leave`): a quest stage one member reaches,
  the members near at that same stage reach too, with the quest's own things.
- **Friends** (right-click a player, or `/friend Name`): kept with the world; the journal's Friends page (who's about,
  where; Whisper, Invite, Remove); told when one comes or goes; your homestead's friends are yours. **Trading**
  (right-click a player: Trade): a window with both offers, gold too; both accept and it changes hands at once, any
  change undoing both accepts. The journal's tabs: Crafting, Gathering, Quests, Spells, Records, Friends, Controls.
- **Gifts**: use an item on a player; they take it or not. **Town projects** (`data/Projects.ini`): anyone gives to
  the foreman; finished, what has `Project=<Key>` on its map line appears and the perk holds, for everyone. The town
  crier tells the news, the bounty clerk sets a hunt a day, the record keeper keeps the records (`/records`), the
  Pocket Anchor has a guestbook and a gift box, and a day away ends with what happened while you were gone.
- **Companions**: Jimmy follows the crowned heir (he finds secrets), a sellsword can be hired; they step aside when a
  real player in your party is near. Townsfolk greet the crowned heir (a speech bubble, now and then: never the
  chat log). The arena: talk to the Arena Master (in Ashford) once and the arena's shardstone knows you.

**Writing**
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

**Creatures**
- `Attitude=Good` NPCs are friendly and can't be attacked. Only NPCs that would attack you keep you from sleeping.
- Prey (hens, cows, sheep, rabbits, ducks) has `Flees=1`: it runs from whoever hits it and never fights back.
- Aggro needs line of sight; lookouts (`Face=`, `Sight.Cone=`) can be sneaked past, and a `Group=` raises the alarm.
- **Every monster's senses are its kind's** (Entities.ini, set by `dev/migrate/build_senses.py`): `Sight.Cone` (how
  wide it sees, 360 all round), `Aggro.Range` (how far), `Hearing` (how far your noise carries to it: a bat 2, a
  skeleton 0.6) and `Chase.Radius`. They work in every stance: one that looks one way turns to a sound, one that sees
  all round comes for it; Sneaking only narrows them, and shows them (cones, and a dashed ring for hearing).
- **Creatures come and go as Shard essence**: one that comes back (a respawn, a raider, a risen remnant) is drawn
  together out of motes (`Shard_Form`, and its sound), and one that dies lets them go (`Shard_Fade`): `world.shard_form`
  and `shard_fade`, never a puff of smoke.
- Buffs and debuffs end on death.
- **The Isle's hard fights stay as they are** (the owner's choice): the Skeleton walking the chapel graveyard (3,1,0)
  and the hobgoblins' lair's four. Don't take them out or soften them to make the start easier.
- A skill can be **drained or boosted for a while** (status effects Weaken, Daze, Frailty on monsters' blows; a script's
  `Boost.Skill`): what asks for a level goes by it as it is now, the Stats tab always shows it out of its usual level
  (20/20; drained 18/20, red; boosted 23/20, green, a potion's or spell's boost to your blows counted in), and hitpoints and your level go by the usual one.
- **Stances** (`dsengine/stances.py`, `data/Stances.ini`; the round button by your health, or Q): none, Fighting
  (blows and guard up, magic hurts more), Channelling (spells stronger, wards and spell boosts longer, drains shrugged
  off; slower, a weaker guard; never potions: herbs), Sneaking (heard and seen less, more with Stealth; lookouts' sight
  cones shown; Pickpocket, Steal; slower). Each stance shows on whoever's in it (a red ring, a blue ring and motes, a
  crouch: `render.js` drawStance). A moment to change; a blow or a spell ends Sneaking. Monsters hear you
  (`noise_radius`): a lookout turns to look, but nothing sees or hears through a wall. A blow on one that never saw you
  is a sneak attack. Feedback: a ? over one that heard you, a ! and a sound when you're seen, a sound slipping past.
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
  you are, e.g. a cat flap's `$Player.Form=Cat`). A script can `Turn.Into` a creature for a while.
- **The Shifting Deep** (`dsengine/deep.py`, `data/Deep.ini`, `dev/migrate/build_deep.py`): an old Shard mine south
  of Moorcross whose floors (40,40,-11 and down) are made in memory, never files, and made again every
  `Shift.Minutes` once nobody's inside: rooms and tunnels, monsters by depth, chests (once each a shift; now and then
  a mimic), hidden traps, a secret room behind a cracked wall, and the Deep's Heart at the bottom. Its things are the
  engine's (`deep_do`), not scripts.
- **The world has a sense of humour, secrets and traps**: odd quests (Pip the invisible apprentice, Lady Pettigrew's
  hat and the geese, Granny Bramble's practice hex, the philosophical scarecrow, Duchess the talking cow, the Mayor's
  trousers), Bert's cat flap and big red button, a secret to Search by every settlement's square, traps in the old
  dungeons (a map `Trigger Trap_<Kind>`: `deep.py` world_trap), animals that talk to you in an animal's body
  (`tricks.py` ANIMAL_TALK); `dev/migrate/build_whimsy.py` places them. Keep adding them, in what things and people
  say and do; a sign still never hints.
- **The cold** (`dsengine/cold.py`, `data/Cold.ini`): out on snow or ice and not warm, health drops a little at a time
  after a grace (Cold by your health). Warm is a roof, a fire near, something worn with `Warm=1` (Fur Cap, Wool Hood,
  Wool Mittens: `build_cold.py`), or a Warming Draught lately (herbs: a potion).
- **Animals stay out of houses** (a roofed cell): `Indoors=0` in Entities.ini (`dev/migrate/animals_outdoors.py`), on
  every animal but cats and dogs. One that starts under a roof may walk out; a hen goes into her own coop (`Roost=`).
- Animals with a home sleep in it: `Roost=x1,y1,x2,y2` (hens in their coop) rather than vanishing at night.
- Every hostile monster has a `Level=` (1-25, from its stats: `dev/migrate/build_remnants.py`). **A kill gives no
  Shards and no bones**: it may leave Shard Remnants on the ground (Absorb them, in the pack, for Shards), or, less
  often, its magic rises as a **Shard Remnant** (`Living_Remnant`), as strong as the monster's level, that goes for
  the killer and leaves more remnants when it's killed (`dsengine/remnants.py`; the numbers: Shards.ini
  `[Remnants]`).

**Magic and Shards**
- **What a potion is and what a spell is.** A potion is herbs: it works only inside whoever drinks it (mends,
  strengthens, sharpens the senses, cures), needs no Shards and is used up. A spell is Shard magic: it reaches out of
  you into the world (strikes, freezes, carries things, carries you) or binds Shards round you as a ward. Shards can't
  mend a body or sharpen an eye, and herbs can't make Shards. A new thing is one or the other by that rule
  (`dev/migrate/potions_and_spells.py` put Healing and Farsight among the potions and made Stone Skin the Shard Ward).
- **A spell of your own**: Magister Quill's The Spellwright teaches it; at the Spellwright's Lectern (the Court's great
  hall) you choose its effect, power and reach, and its Shards and rest are worked out to balance
  (`dsengine/ownspell.py`, Shards.ini `[Spellwright]`). It's `Own_Spell`, known like any other.
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
  Spells are cast from **Channeling**, the Stats box's third tab (click: cast; right-click: on or off the hotbar), or
  the hotbar; a spell that needs a target and has none is held ready for the next click. Never "Cast" on a scroll.
- **Scrolls are rare** (`dev/migrate/rare_scrolls.py`): one at a time (`Stackable=1`), none at the start, none from
  beasts or ordinary chests, and nobody writes them. They come from quests, a few chests in places of their own (the
  standing stones', the cinder cache's), the Shifting Deep's Heart, and the wizards' shops, dearly (Value 100 + 40 a
  level). A scroll a quest gives or a chest holds is never for sale (`Value=0`, `Droppable=0`). Upgrade scrolls (`Rank=2`, Fire_Bolt_Scroll_II) raise a known
  spell a rank; each rank's values are `Key.<rank>` in Shards.ini `[Upgrade.<Spell>]`. Quests give items with
  `Reward.Items` and skill xp with `Reward.XP` (`Strength 3 Defence 3`), and a finished quest shows its reward
  screen. Set by `dev/migrate/build_shards.py`.

**Skills**
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

**Doing things**
- Work is seen: a gathering script shows the skill over the player's head as it starts (`Show.Skill`) and plays
  its work with `Play.Animation <Anim> <Times> <Sound>` (chips, sparks, splashes; a lunge each beat).
  `dev/migrate/work_animations.py` adds them to new Chop/Mine/Fish/Pick scripts.
- **All tools wear** (`Durability`, no `Slot`): a use each go, and a broken one doesn't count until it's mended.

**Places and furniture**
- Inside walls are `*_Thin_Plank*` floor tiles with the wall drawn along their edge. Beds, bookshelves, chests,
  sacks and work stations stand on the back-wall tile, against the wall, not a floorboard out from it.
- Beds are 1.5 tiles: `Bed001` (the head) with `Bed002` (the foot) in the tile below. Never place one without
  the other.
- Ladders and hatches line up exactly with the ladder on the floor above or below.
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
  with them), `build_mirefen.py` (the west finished: the Mirefen swamp and Mirefold, its hut hamlet, reached along the
  West Range's northern beach; the sea south of Galaith). **Running `build_estforlan.py` again would undo all of them
  and the owner's edits**: don't, unless they're run again after it.
- Settlements have a size, and what each size has (`estforlan/settlements.py` SIZES): Galaith a huge city; Northport a
  large city (its City Hall is the Parliament for now); King Rupert's Keep, the Wizards' Court, Fenwick and Ravensgate
  medium cities; Ashford a small city; Highwatch, Frosthold and Wardhaven towns; Oakhollow, Thornwick and Emberwatch
  villages; Moorcross, Dunerest, Wildwood, Saltmarsh and Mirefold (in the Mirefen, its huts on boardwalks) hamlets.
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

**Homesteads** (`dsengine/homes.py`, `dev/migrate/build_pocket.py`)
- A homestead is a **pocket of the Shardrealm's calm rim** (the settlers' Stillwater), held by your **Hearth Anchor**
  (it was the Access Crystal). There are no homestones: any shardstone you've activated takes you home, and the
  **Pocket Anchor** in the pocket takes you back and says who may visit. A pocket is **always safe**: nothing hostile
  is ever added to one (`world.add_npc`).
- A new pocket is raw rim (`Rim_Mist001` round a little `Rim_Glass001`); you **terraform** it with Shards (Shards.ini
  `[Terraform]`) and Shardcraft: mist stills only beside held ground; grass and dirt won't lie on glass till it's soil.
  **Shard Blooms** are the best single source of Shards (Shards.ini `[Homestead]`), limited by Shardcraft, harvested
  by their owner in person. Building is Homesteading; terraforming is Shardcraft.

**Items**
- Healing draughts come in three strengths: `Minor_Healing_Draught` (8-12), `Healing_Draught` (15-20),
  `Major_Healing_Draught` (26-32), brewed from more herbs as they get stronger; the Mega Potion is above them.
- Chicken meat is Poultry (`Raw_Poultry`, `Cooked_Poultry`, `Burnt_Poultry`). For any rename, add the old name to
  `dsengine/renames.py` so old saves load.
- New characters start with no sword.

## Look and sound

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
- **Nothing looks like a grid.** Ground that covers wide areas (mountains, streets, the forest canopy) is painted from a
  big seamless texture (`Texture=` in Tiles.ini, `sprites/Textures`, `dev/migrate/build_terrain.py`), never one
  picture repeated every tile; a range is peaks of all sizes overlapping. Trees, bushes, rocks, grass and flowers
  are sized and nudged per tile (`ground.js` paintDecor), always inside their own cell.
  A range's edge has no right angles: its corners are cut on the slant as the ground's painted (`ground.js`
  paintSlants), and a bay's inner corner filled with rock.
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
- The camera stays on the player: past the last map there's only black (never held back at the edge of the maps).
- Going somewhere else at once (a shardstone, a script, dying; not a ladder or a stair) fades the view out and in.
- Walking keeps to the walk masks: a fence thinner than a path cell stops the path (`maps.py` cross_r/cross_d) and
  the feet (a step never skips over it).
- A tile changing (a door, a chopped tree) sends just that tile (`mapcells`), not the whole map again: keep it so.
  The phone and many NPCs make full-map repaints the thing that lags.
- The Stats box's tabs are Stats, Gear and Channeling. Quests live in the journal (H): it shows the quests in hand,
  done, and those you can start now (never the ones still locked), no rewards, and a click on one follows it.
- Hover text is at most 4 lines, at the top middle of the view (both layouts). Your level, health and Shards are top
  left of the view, not in the sidebar.
- **One client, two layouts.** The same `web/js` is the desktop game and the phone's (`mobile.js`: `M.on` on touch
  screens and in the Android app). The phone's has no sidebar or chat bar: a round minimap top right (tap: the world
  map), the Bag, Chat, Journal and Menu buttons, a stick, tap and hold. No Talk or Map buttons. The phone turns
  either way (the app's `fullSensor`): held upright the game is 480 wide and as tall as the screen, a box sits under
  the minimap with the pack below it, and the bag puts the Stats box over the pack (`L.upright` in `layout`).
  Anything new on screen must work in both layouts, and on a phone both ways up, with finger-sized targets; nothing for the app goes in `android/` that the page
  could do.
- **The phone can be the server.** The Android app runs `server/` itself (Python 3.11 through Chaquopy, with its
  aiohttp) so others on the same network can join; `server/lan.py` lets the app find games on the network. The host
  (or an admin) can close it to the network in Options: then only that machine may join, and it doesn't answer the
  network (`lan_open`, kept with the world; `DS_LAN_OPEN=0` starts closed). A public server on a cloud VM:
  `deploy/docker-compose.cloud.yml` and `deploy/cloud-setup.sh` (Caddy for HTTPS, `DS_TRUST_PROXY=1` so the limits
  go by each player's own address, sign-ups limited by `DS_PASSWORD_MIN` and `DS_REGISTER_PER_DAY`, admins' `/kick`,
  `/ban`, `/mute`): README-Server.md says how. A forgotten password: the recovery code shown once when a character's
  made (and in Options, a new one), kept only as a hash, used up at each reset (no email needed). Every game has a name
  (the host's, in Options; else `DS_NAME`), on the login screen and in the app's list. The app opens on Play alone
  (`solo.db`, this phone only: 127.0.0.1, `DS_LAN=0`) or Play with others (host, the network's games, an address). So
  `server/` and `dsengine/` stay standard library plus aiohttp: no pygame, numpy or anything that needs a shell.
- **Every version has the same start screen** (`web/home/`): sign in to your Shards account first (or make one, or a
  forgotten password by email or recovery code, or play without one); then the menu: Play alone and Host a game (local: answered on its network; remote: announced to the
  central server) in the apps, and Join a local game (the network's, or an address; a browser: an address only) and
  Join a remote game (the central server's list) everywhere. Joining takes a ticket from the central server made out
  to that server's id; a game server's own accounts stay, for a network without the central server. Change the start
  screen in `web/home/` only, then run `tools/sync_home.py`; anything the apps do for it goes through `window.DSApp`
  (Android's Bridge, the desktop's `desktop/app.py`), the same names in both. Remote servers are listed only once
  approved on the central server's admin page (`/admin`); a character made by a Shards account has no password of its
  own, and players are told everywhere that a character lives on its server only. The logo is pixel art made by
  `dev/migrate/build_logo.py` (web/img/logo.png, web/home/logo.png).
- **Prices show the game's coin, never a "g"**: `COIN` in `util.js` (drawText draws it, and writes "12 gold" so);
  `coinHTML` for page text. The same coin everywhere a price or a sum of gold is shown.
- **A click is answered at once**: what's clicked is marked the moment it's clicked (registered: a gold ring; a foe a
  red one that tightens at each blow, hit or miss), then green when it's done or red, with a cross, when it's refused or
  comes to nothing. The server says which (`act`: `Session.act_done`, from its messages, sounds, boxes, items and
  work); something new a player does by clicking calls `act_done` when it succeeds or fails, if nothing else does.
- Text centred in a row uses `drawTextMid` (it measures the font's capital height): never guess offsets.

## Code and data conventions

- Match the surrounding code: its naming, its comment density, and its comment voice (short plain-English
  asides in parentheses, e.g. `# (a rug: under whatever stands there)`).
- The folders in the main folder are **lowercase** (`data`, `dev`, `maps`, `saves`, `sounds`, `sprites`), and paths
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
  same). A migration that is superseded refuses to run.
- The map editor's map: the mouse wheel zooms (Shift+wheel, middle-drag or Space+drag move the view); an area is
  copied or cut with the inspector's buttons, then each click puts it down; after a change only the maps changed are
  drawn again, and nothing goes black while new pictures are made. A thing dragged off a map lands on the next one.
  Zoomed far out, a double-click zooms in on that tile at 100%. Every level under or over the world is laid out in the
  world's frame (`dsedit/world.py` own_level): one frame round every map on any of them, so a tile is at the same spot
  of the canvas on every level, and **going up or down keeps the view exactly** (the same scroll and zoom, every tile
  over the one below it), even where the other level has no map there. A slow job shows a banner over the window
  (`app.busy`) or a spinner in the header for one in the background (`app.working`): never a window that looks stuck.
  Right-click lets go of an area being pasted. Dragging an entity moves only its picture (the map is drawn once
  without it), and the palette makes only the pictures in view: keep both so.
- **The map editor's Auto palette and brushes** (`dsedit/terrain.py`): a terrain (`data/TileSets.ini` `Kind=Terrain`,
  `dev/migrate/build_terrains.py`: its ground mixed by weight, decor and creatures scattered at a density, `Water=1`,
  a wall's `Face=`), a set or a family of look-alikes is one palette entry that puts the right tile down itself;
  Detail shows every tile. Terrains are painted with a brush of any size, Fill, Rectangle, or an Outline drawn round a
  place; painting rolls the decor and creatures afresh, takes off what another terrain scattered (never anything with
  an Id, a name, a zone or a patrol, nor built decor), smooths the coasts and turns cave rock to its face over open
  ground. A new kind of ground or a wall gets a terrain in the data, not code. An NPC's `Zone=`/`Chase=` can be any
  shape: rectangles joined by `/`, painted tile by tile. Whole maps are moved, copied or deleted from the map's
  right-click menu (`dsedit/mapops.py`: what names them follows; the code that names them is listed). An entity's
  options are fields of their own (`OPT_SPECS` in `dsedit/pages/maps.py`): a new map option gets one there too.
- The map editor shows a level as one map (`dsedit/world.py`). **How tiles go together is in the data, never the
  editor's code**: a set in `data/TileSets.ini` has a `Kind=` (Stretch: a 3-column grid of corners, edges and middle;
  Rug: that and its "runner"s; Join: pieces that join their neighbours, each with `Joins=` in Tiles.ini, the sides it
  joins, `*` a tower, `-` a post, and `Below=` for one two tiles tall; Shore: a coast's `Land`, `Water`, `Corners` and
  `Small` pieces). A Join set (fences, palisades, the town wall) is dragged as a line or round a rectangle, or painted
  freehand, and its pieces round it are joined again, painting or erasing. `dev/migrate/tile_joins.py` wrote them.
  Give a new set its Kind, and its pieces their `Piece=` (and `Joins=`).
- New `Entities.ini` or `Tiles.ini` keys, script commands or map options must be added to
  `dev/migrate/validate.py`.
- Don't use shell heredocs for edits with backslashes; write a patch script to the scratchpad, or use Edit.

## Before every commit

1. `python -I dev/migrate/validate.py`: **0 errors**. (A few known warnings are fine; don't add new ones.)
2. `python -m pytest -q tests`: all pass. New behaviour gets a test in `tests/test_engine.py` (helpers `join`,
   `leave`, `stock`; click with `s.choose_verb(verb, e, gx, gy)`).
3. After changing sprites, sounds or data: `python -I tools/export_web_assets.py`.
4. After changing maps: `python -I dev/migrate/build_minimaps.py`, and commit the changed `Minimap*.png`.
5. Client changes (`web/js`): load the game in a browser (Playwright, with `DS_DB=<scratch>/t.db
   DS_PORT=85xx python -m server`) and check there are no console errors and that it looks right, on a desktop and
   on a phone (a 915 x 412 touch viewport with `?app=android`).
6. Commit to `main` with a message saying what changed for players, then push. Deployment (Docker on Unraid,
   `ghcr.io/kriscs1/shardsofashen`) builds from GitHub.
7. Never commit `.env`, tokens or `server-data/`. Admin rights come only from the DB flag or `DS_ADMINS`
   (`DS_CENTRAL_ADMINS` on the central server); a name there with no account yet is made only with the claim code
   the server logs as it starts, never by whoever signs up first.
8. **The owner's uncommitted changes are kept.** Whatever is changed in the folder before you start (maps from the
   editor, sprites, scripts, from this PC or another synced one) is the owner's work: never revert or overwrite it
   unless asked to update it. Fix what it breaks and commit it along with your own work. A Google Drive
   `-mediapc` conflict copy is compared with the original, and only the copy that's left over is set aside.
