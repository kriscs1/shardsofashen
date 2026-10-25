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
| `Data/` | `Entities.ini`, `Tiles.ini`, `Quests.ini`, `Config.ini`, `WorldMap.ini`... and `Data/Scripts/*.txt` |
| `Maps/` | `X,Y,Z.txt`: 25x21 tiles of 32 px. Z<0 underground, Z>0 upstairs |
| `Dev/migrate/` | Builders and migrations that draw sprites, make sounds and place content (see below) |
| `dsedit/` | The map/data editor |
| `dragonsword/` | Shared helpers (`ini`, `lb`); the old desktop game is retired |
| `tests/` | `test_engine.py`, `test_server.py` (pytest) |

References: `README-Server.md` (running, deploying, shared vs personal), `Dev/Data Formats.md`,
`Dev/Script Commands.txt`.

## The story

The player wakes in a small **cottage on the east of the Isle** (map 4,0,0) with no sword, and **Jimmy**, a
strawberry-blond ginger cat, at home there. The main quest line (`Type=Main` in `Data/Quests.ini`, in chapters):

1. **Passage to the Mainland** (the Isle, the tutorial). Maren the ferrywoman (south pier) needs a ticket. Her
   sister Bess the milkmaid (north farm) lost her ticket book to a goblin from the chapel cellar. Bess teaches,
   in this order: chop logs, collect and fry an egg, make and wield a wooden sword and shield. Then Brother
   Aldous (the chapel) has lost the cellar key; it's in the cellar's barrels and crates and is only found by the
   armed. The trapdoor lets you down with the key (it stays shut and needs no sword). The book is in a goblin's
   cage; Aldous gives a Grasp scroll to pull it out. Bess stamps a ticket and Maren sails to Southport.
2. **King's Hobgoblin Hunt**: King Tyron, south of Ashford; hobgoblins in the old iron mine.
3. **The Ashen Hand**: a cult in the Cinderlands.
4. **The Ashen Omens**: the cult means to wake a dragon; tell the court wizard.
5. **The Dragon of Ashpeak**: the finale.

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
- **Notices and signs never give hints.** They name or describe a place, nothing about quests, keys or secrets.
- **No hint text on the world map.**
- **Conversation answers that belong to a quest stage show only at that stage**: append `[if CONDITION]` to the
  answer, e.g. `About a ferry ticket... [if $Attr.Passage>=1 and $Attr.Passage<=10]`.
- Refusals are plain: "The chest is empty." (with the `Empty` sound), not hints.
- NPCs can have their own names through the map option `Name=` (underscores become spaces).
- **The chat log isn't spammed**: no line per blow in a fight (the numbers over heads show hits and misses).
  Log what matters: kills, loot, level-ups, warnings, quest news.
- **Bad news is heard as well as read.** In scripts it's written there: `Display.Message COLOUR MESSAGE [SOUND]`
  (or a `Play.Sound` beside it). Every red script message (DarkRed, Red) says its sound, usually `Denied`; give a
  failure its own sound where one fits. Script messages are otherwise silent. The engine's own messages (not from a
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
  `Dev/migrate/work_animations.py` adds them to new Chop/Mine/Fish/Pick scripts.
- **All tools wear** (`Durability`, no `Slot`): a use each go, and a broken one doesn't count until it's mended.

**Places and furniture**
- Inside walls are `*_Thin_Plank*` floor tiles with the wall drawn along their edge. Beds, bookshelves, chests,
  sacks and work stations stand on the back-wall tile, against the wall, not a floorboard out from it.
- Beds are 1.5 tiles: `Bed001` (the head) with `Bed002` (the foot) in the tile below. Never place one without
  the other.
- Ladders and hatches line up exactly with the ladder on the floor above or below.
- On the world map, places with no map look the same as unexplored ones.

**Items**
- Chicken meat is Poultry (`Raw_Poultry`, `Cooked_Poultry`, `Burnt_Poultry`). For any rename, add the old name to
  `dsengine/renames.py` so old saves load.
- New characters start with no sword.

## Look and sound

- Tiles and sprites are 32x32 pixel art. Creatures and objects have a 1 px dark outline (the mask-silhouette method
  in `build_wolf.py` and `build_cats.py`), and walk in frames `<Name>2a-c` (right) and `<Name>8a-c` (mirrored).
- Art and sounds are made in code by `Dev/migrate/build_*.py` (pygame drawing; synthesized 22050 Hz mono WAVs).
  Change the builder and run it again; don't hand-edit its output.
- Keep things in proportion to a 32 px person: cats and butterflies small, beds 1.5 tiles.
- Every distinct event deserves its own fitting sound (fizzle for a failed spell, "duh-derr" for an empty chest).
- Hover text is at most 4 lines.
- Text centred in a row uses `drawTextMid` (it measures the font's capital height): never guess offsets.

## Code and data conventions

- Match the surrounding code: its naming, its comment density, and its comment voice (short plain-English
  asides in parentheses, e.g. `# (a rug: under whatever stands there)`).
- Data files and maps are **cp1252 with CRLF**. Preserve both when editing; write them in binary mode from Python.
- Map cells: `Tile+Under(Rug)+Decor(Name)+Roof(Piece.Group)+Infront(...)`. Entity lines are tab-separated:
  `NPC|StaticObject|MapItem Name x y options`. In builders, use `build_isle.Map` and `obj_line` (1-based tiles).
- Scripts: `NN<TAB>Command<TAB>args`. `>Conditional COND LINE` goes on when COND is true and jumps to LINE when
  it's false. Generated scripts say which builder made them in their first line; edit the builder too.
- Builders and migrations in `Dev/migrate/` are safe to run again (a second run does nothing, or redraws the
  same). A migration that is superseded refuses to run.
- New `Entities.ini` or `Tiles.ini` keys, script commands or map options must be added to
  `Dev/migrate/validate.py`.
- Don't use shell heredocs for edits with backslashes; write a patch script to the scratchpad, or use Edit.

## Before every commit

1. `python -I Dev/migrate/validate.py`: **0 errors**. (A few known warnings are fine; don't add new ones.)
2. `python -m pytest -q tests`: all pass. New behaviour gets a test in `tests/test_engine.py` (helpers `join`,
   `leave`, `stock`; click with `s.choose_verb(verb, e, gx, gy)`).
3. After changing sprites, sounds or data: `python -I tools/export_web_assets.py`.
4. After changing maps: `python -I Dev/migrate/build_minimaps.py`, and commit the changed `Minimap*.png`.
5. Client changes (`web/js`): load the game in a browser (Playwright, with `DS_DB=<scratch>/t.db
   DS_PORT=85xx python -m server`) and check there are no console errors and that it looks right.
6. Commit to `main` with a message saying what changed for players, then push. Deployment (Docker on Unraid,
   `ghcr.io/kriscs1/dragonsword`) builds from GitHub.
7. Never commit `.env`, tokens or `server-data/`. Admin rights come only from the DB flag or `DS_ADMINS`.
