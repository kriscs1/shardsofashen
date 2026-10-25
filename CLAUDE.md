# Dragon Sword: rules for every change

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
| `data/` | `Entities.ini`, `Tiles.ini`, `Quests.ini`, `Config.ini`, `WorldMap.ini`... and `data/Scripts/*.txt` |
| `maps/` | `X,Y,Z.txt`: 25x21 tiles of 32 px. Z<0 underground, Z>0 upstairs |
| `dev/migrate/` | Builders and migrations that draw sprites, make sounds and place content (see below) |
| `dsedit/` | The map/data editor |
| `dragonsword/` | Shared helpers (`ini`, `lb`); the old desktop game is retired |
| `tests/` | `test_engine.py`, `test_server.py` (pytest) |

References: `README-Server.md` (running, deploying, shared vs personal), `dev/Data Formats.md`,
`dev/Script Commands.txt`.

## The story

**You are the true heir of Estforlan.** Every generation the dragon takes the king's firstborn heir, or it keeps
Galaith, the capital, shut behind a magical barrier: the city that holds the only land route across the world, with
the gold and mana mines in the mountains behind it. Your mother, **Queen Mary**, ran from Galaith with you as a baby
to save you and to break the curse. The city has been sealed since your birth; King **Rupert**, your father, is shut
in it. You grew up poor on the Isle, in the **cottage on its east** (map 4,0,0), with **Jimmy**, a strawberry-blond
ginger cat. New characters start with no sword.

The main quest line (`Type=Main` in `data/Quests.ini`, in chapters; the Isle's are built by
`dev/migrate/build_heir_isle.py`):

1. **The Last Will** (`LastWill`). A new character stands at Mary's fresh grave in the chapel's graveyard (3,1,0's
   entry script runs `The Funeral`). The mourners go; **Edwin** the lawyer walks you home and leaves her letter on the
   table. The cottage door stays locked (a Lock) until you've read it: the letter (`Last_Will`, Read) tells you who
   you are, in the owner's own words.
2. **Dinner at the Bank** (`DinnerQuest`). The bank (2,1,0, two storeys, brick) is Edwin and **Maren**'s: she keeps
   the counter by day, and they live upstairs (2,1,1), going up at night. Three logs for her range (with the axe she
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
   squeaks: stand on it, then Search it, for the compass. Bess sails you to Southport; **Wim** the ferryman crosses
   for a coin after that.

On the mainland (`build_heir_mainland.py`; Galaith and its pass, maps 10-14 by 5-7, by `build_galaith.py`):
5. **The Temporary Capital** (`ParliamentQuest`): the guard at Southport's port; the **Speaker** in Southport's City
   Hall, which is Estforlan's Parliament while Galaith is lost. Only **Bert**, the great wizard of the **Wizards'
   Court** (the old King's Castle, 4,4,0; Bert at the top of its tower, 4,4,1), can break the barrier.
6. **The Ashford Road** (`AshfordQuest`): the **Mayor** in Ashford's Town Hall; the goblins' raid on the farms.
7. **The Steward's Hunt** (`HobgoblinQuest`): the **King's Steward** at **King Rupert's Keep** (the old Tyron's Keep;
   King Tyron is gone from the game), five hobgoblins in the old iron mine.
8. **Bert's Three Treasures** (`BertQuest`): 9. **The Staff of Estforlan** (the King's solar, 2,4,1, up a locked
   stair in the keep); 10. **The Sunken Grimoire** (the scholar in Dunerest; a buried library under a mound in the
   desert, 1,9,-1); 11. **The Ember Ring** (the Warden in Emberwatch; the Ashen Priest wears it). Bert only wanted
   the ring: he teaches the spell (`BarrierSpell`), gives you the staff and warns of the **Sword of Valour**.
12. **A Ship for Dragon Island** (Captain Rook, on the shore east of Ravensgate, 9,8,0), 13. **The Island of
   Dragons** (8,10,0: drakes, three Valour Seals), 14. **The Sword of Valour** (the Temple of Valour's guardian).
15. **The Dragon of Galaith** (`GalaithQuest`): the staff used on the barrier (10,6,0) breaks it; the dragon speaks;
   it has `Slain.By=Sword_of_Valour` (any other weapon leaves it at 1 hp). Its death opens Galaith's west gate and
   Wardhaven.
16. **The Royal Guard** (`GuardQuest`): the captain at the palace door (12,5,0), the Lord Chancellor (Galaith's
   Parliament), the Royal Archivist (its City Hall) with the amulet, back to the Chancellor, the warrant to the
   captain.
17. **The True Heir** (`KingQuest`): King Rupert on his throne; the amulet, the will, the crown. Open play after;
   **Jimmy** sleeps on the throne and in your house on the Isle, and the mine behind Galaith opens.

The old chapters (The Ashen Hand, The Ashen Omens, The Dragon of Ashpeak and its lair 0,0,-9) and the side quest
The Beggar's Lost Key are gone; their places stay, quiet. `dev/Story and Quests.md` has every quest, step by step.

Side quests hang off these by `Requires.Quests` and `Requires.Level`. A new quest must fit this world: its places
named in `WorldMap.ini`, its giver a placed NPC, its stages written in `Quests.ini` with `Marker<N>` place Ids.

## Game rules to keep

**Shared vs personal**
- Shared, seen by everyone: chopped trees, mined rocks, fires, dropped items, NPC deaths and kill loot (the
  killer's for 10 s), shop stock, unlocked doors, the time and the weather.
- Personal: quest attributes, quest doors and `Lock` lines, `Once=` items, NPC attitudes set by quests, fog of war.
- **Chests are per player**: everyone finds a chest's loot, once each. A chest script tracks its loot with an
  attribute, never with shared state.
- The world keeps running while everyone is logged out.

**Writing**
- **Notices and signs never give hints or instructions.** They name or describe a place (and a signpost says which
  way places lie), nothing about quests, keys, secrets, who sells what or what you need to get in.
- **No hint text on the world map.**
- **Conversation answers that belong to a quest stage show only at that stage**: append `[if CONDITION]` to the
  answer, e.g. `About a ferry ticket... [if $Attr.Passage>=1 and $Attr.Passage<=10]`.
- Refusals are plain: "The chest is empty." (with the `Empty` sound), not hints.
- NPCs can have their own names through the map option `Name=` (underscores become spaces).
- **One of a kind gets its own script**: a thing's `Id=`, or a tile's place ID (an `Id` line; in the editor,
  right-click a tile, "Name this tile"), makes `<Verb> <Id>` run before `<Verb> <Kind>` (every grave has its own
  `Examine Grave_...`). Don't give many tiles one text when each could say its own.
- **The chat log isn't spammed**: no line per blow in a fight (the numbers over heads show hits and misses).
  Log what matters: kills, loot, level-ups, warnings, quest news.
- **Bad news is heard as well as read.** In scripts it's written there: `Display.Message COLOUR MESSAGE [SOUND]`
  (or a `Play.Sound` beside it). Every red script message (DarkRed, Red) says its sound: **`Denied`** (a computer's
  no) when you can't (too far, no axe, level too low); **`Fail`** (a lute's "oh well") when an attempt comes to nothing
  in the world ("..but fail to get any logs!"); **`-`** for none on purpose (arriving somewhere, a story's moment).
  Script messages are otherwise silent. The engine's own messages (not from a
  script) that say no get the Denied tell from `Session.take_out`.

**Creatures**
- `Attitude=Good` NPCs are friendly and can't be attacked. Only NPCs that would attack you keep you from sleeping.
- Prey (hens, cows, sheep, rabbits, ducks) has `Flees=1`: it runs from whoever hits it and never fights back.
- Aggro needs line of sight; lookouts (`Face=`, `Sight.Cone=`) can be sneaked past, and a `Group=` raises the alarm.
- Buffs and debuffs end on death.
- Animals with a home sleep in it: `Roost=x1,y1,x2,y2` (hens in their coop) rather than vanishing at night.

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
- On the world map, places with no map look the same as unexplored ones.
- Settlements have a size, and what each size has (`dev/migrate/build_towns.py`, grown by `towns.py` into the free
  ground round them): Galaith a huge city; Southport a large city (its City Hall is the Parliament for now); King
  Rupert's Keep, the Wizards' Court, Fenwick and Ravensgate medium cities; Ashford a small city; Highwatch and
  Frosthold towns; Oakhollow, Thornwick and Emberwatch villages; Moorcross, Dunerest, Wildwood and Saltmarsh hamlets.
  New buildings in a town go on free ground only, joined to its roads; nothing there already moves.

**Items**
- Chicken meat is Poultry (`Raw_Poultry`, `Cooked_Poultry`, `Burnt_Poultry`). For any rename, add the old name to
  `dsengine/renames.py` so old saves load.
- New characters start with no sword.

## Look and sound

- Tiles and sprites are 32x32 pixel art. Creatures and objects have a 1 px dark outline (the mask-silhouette method
  in `build_wolf.py` and `build_cats.py`), and walk in frames `<Name>2a-c` (right) and `<Name>8a-c` (mirrored).
- Art and sounds are made in code by `dev/migrate/build_*.py` (pygame drawing; synthesized 22050 Hz mono WAVs).
  Change the builder and run it again; don't hand-edit its output.
- Keep things in proportion to a 32 px person: cats and butterflies small, beds 1.5 tiles.
- Every distinct event deserves its own fitting sound (fizzle for a failed spell, "duh-derr" for an empty chest).
- Hover text is at most 4 lines.
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
   DS_PORT=85xx python -m server`) and check there are no console errors and that it looks right.
6. Commit to `main` with a message saying what changed for players, then push. Deployment (Docker on Unraid,
   `ghcr.io/kriscs1/dragonsword`) builds from GitHub.
7. Never commit `.env`, tokens or `server-data/`. Admin rights come only from the DB flag or `DS_ADMINS`.
