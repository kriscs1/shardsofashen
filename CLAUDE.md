# Shards of Ashen: rules for every change

This file is what applies to every task. **The rules in full are in `dev/Rules.md`**: the story, the game's rules, the
look and sound, the code and the editor, by section. Read the sections your task touches (the table below), not the
whole file. When the owner gives a rule that should last ("always", "never", "from now on", or a correction of
something done wrong), add it to the right section of `dev/Rules.md` (here only if it applies to every change), in the
same commit.

## What this is

A top-down pixel-art RPG, played in the browser by up to 5 players sharing one world.

| Folder | What it is |
|---|---|
| `dsengine/` | The game's rules (authoritative, headless, many players) |
| `server/` | aiohttp: the page, assets, the game over a WebSocket at 20 ticks/s, SQLite (`DS_DB`) |
| `web/js/` | The browser client: canvas, ES modules, no build step. `web/assets/` is generated, never edited |
| `android/` | The Android app: carries the server and page; a phone hosts a game for its network, or joins one |
| `desktop/` | The desktop app (pywebview, built by PyInstaller): the same start screen and choices as the Android app |
| `central/` | The central server: accounts, the remote servers' list, every character's progress, the start screen's ads |
| `web/home/` | The start screen, the same in every version (`tools/sync_home.py` copies it into the Android app) |
| `data/` | `Entities.ini`, `Tiles.ini`, `Quests.ini`, `Config.ini`, `WorldMap.ini`... and `data/Scripts/*.script` |
| `maps/` | `X,Y,Z.map`: 25x21 tiles of 32 px. Z<0 underground, Z>0 upstairs; levels of their own in `dev/Rules.md` |
| `dev/migrate/` | Builders and migrations that draw sprites, make sounds and place content |
| `dsedit/` | The map/data editor |
| `ashen/` | Shared helpers (`ini`, `lb`); the old desktop game is retired |
| `tests/` | `test_engine.py`, `test_server.py`, `test_central.py`, `test_desktop.py` (pytest) |

References: `dev/Rules.md` (every rule), `dev/Story and Quests.md` (every quest, step by step), `dev/Spells.md` (every spell), `dev/World Plan.md`
(the mainland), `README-Server.md` (running, deploying, who's who), `dev/Selling the Game.md` (the stores), `dev/Data Formats.md`, `dev/Script Commands.txt`.

## What to read for a task

`grep -n '^##' "dev/Rules.md"` lists its sections with their lines; read just those (Read with offset and limit).

| The task touches | Read in `dev/Rules.md` |
|---|---|
| A quest, an NPC's words, the story | The story; Writing; and the quest in `dev/Story and Quests.md` |
| Anything a script or a player says | Writing |
| Monsters, animals, stances, thieving, the seasons, encounters, zones | Creatures |
| Spells, potions, Shards, scrolls, shardstones | Magic and Shards |
| Skills, gathering, tools | Skills; Doing things |
| Maps, towns, houses, furniture, the mainland | Places and furniture (never re-run `build_estforlan.py`) |
| Homesteads | Homesteads |
| Sprites, sounds, ground textures | Art and sound; Ground and tiles, as drawn |
| The page (`web/js`), phone layout | The view, the screen and the client; Answering the player |
| Server, apps, accounts, login, relays | Servers, apps and accounts; The central server |
| `central/`, `server/store.py`, SQL | The central server; Code and data files |
| The map editor (`dsedit/`) | The map editor; Ground and tiles, as drawn |
| Multiplayer behaviour | Shared vs personal; Playing together |

## Rules that apply to every change

- **The owner's uncommitted changes are kept.** Whatever is changed in the folder before you start (maps from the
  editor, sprites, scripts, from this PC or another synced one) is the owner's work: never revert or overwrite it
  unless asked to update it. Fix what it breaks and commit it along with your own work. A Google Drive `-mediapc`
  conflict copy is compared with the original, and only the copy that's left over is set aside.
- **Shared vs personal**: the world (trees, rocks, drops, deaths, shops, doors, time, weather) is everyone's; quests,
  quest doors and locks, `Once=` items, chests' loot and fog of war are each player's own. Nothing in the story needs
  a second player.
- **The main quest is discovered, not laid out**, and **notices, signs and the world map never hint**. Quest answers
  show only at their stage (`[if CONDITION]`). Red script messages say their sound (`Denied`, `Fail`, or `-`); good
  news says its own. The chat log isn't spammed. `$Player.Son`/`Lord`/`King`, never a fixed "son" or "King".
- **Shards are a balance, never an item**; every Shard number is in `data/Shards.ini`. A potion is herbs, a spell is
  Shard magic. Skills go to 25.
- **Art and sounds are made in code** by `dev/migrate/build_*.py`: change the builder and run it again, never its
  output. Nothing from another game; anything not made here is CC0 and in `CREDITS.md`.
- **Data files and maps are cp1252 with CRLF**: write them in binary mode from Python. Never `sed -i` (Git Bash strips
  the CRs) and no shell heredocs for edits with backslashes: a patch script in the scratchpad, or Edit.
- Folders in the main folder are **lowercase** and written so (`data`, `dev`, `maps`, `sounds`, `sprites`).
- Builders and migrations are safe to run again; a superseded one refuses to run; a builder that takes over another's
  script is in `story_kit.TAKES_OVER`. Generated scripts name their builder in their first line.
- New `Entities.ini`/`Tiles.ini` keys, script commands or map options go in `dev/migrate/validate.py`; a new map option
  gets a field in `OPT_SPECS` (`dsedit/pages/maps.py`). For any rename, the old name goes in `dsengine/renames.py`.
- `server/` and `dsengine/` stay standard library plus aiohttp (they run on a phone). Every SQL value is a `?`
  parameter. The world's clock is UTC. A tile change sends just that tile (`mapcells`).
- **One client, two layouts**: anything on screen works on a desktop and a phone, both ways up, finger-sized.
- Match the surrounding code: its naming, its comment density and its voice (short plain-English asides in
  parentheses).
- Never commit `.env`, tokens or `server-data/`. Admin rights come only from the DB flag, `DS_ADMINS`, or
  `DS_CENTRAL_ADMINS` (details: Servers, apps and accounts).

## Working economically

- Read only what the task needs: the sections above, the files you'll change and what they call. Search (Grep) before
  reading; read large files by line range. Don't scan the whole project unless a problem needs it, and don't re-read
  a file you've just edited.
- Don't repeat in reports what the docs or the diff already say.
- **Model and effort** (the owner chooses with `/model` and `/effort`; suggest, don't switch mid-task): Sonnet at
  medium effort for ordinary work (a quest, a builder, a fix with a clear cause); Opus and higher effort for hard
  debugging, architecture and changes across engine, server and client; Haiku for plain documentation edits.
- A new, unrelated task is best begun after `/clear`; `/compact` when carrying on with the same one.
- Subagents (`.claude/agents/`) only when the owner asks for one.

## Testing

**While working, run the tests that cover what changed. Before every commit, run the full suite.** Never skip a test
that covers the change to save time.

| Changed | While working |
|---|---|
| `dsengine/`, scripts, data | `python -m pytest -q tests/test_engine.py -k <word>` for the feature, and `validate.py` |
| `server/` | `tests/test_server.py` (and engine tests for what it calls) |
| `central/` | `tests/test_central.py` |
| `desktop/` | `tests/test_desktop.py` |
| `web/js` | the browser check (step 5 below) |
| A builder | run it, then `validate.py` and the tests that name what it makes |
| Docs only (`*.md`, `dev/*.txt`) | nothing |

Write long output to a log in the scratchpad, not the conversation, and read only the failures:
`python -m pytest -q tests > "<scratchpad>/pytest.log" 2>&1; tail -n 15 "<scratchpad>/pytest.log"`.

## Before every commit

1. `python -I dev/migrate/validate.py`: **0 errors**. (A few known warnings are fine; don't add new ones.)
2. `python -m pytest -q tests`: all pass. New behaviour gets a test in `tests/test_engine.py` (helpers `join`,
   `leave`, `stock`; click with `s.choose_verb(verb, e, gx, gy)`).
3. After changing sprites, sounds or data: `python -I tools/export_web_assets.py`.
4. After changing maps: `python -I dev/migrate/build_minimaps.py`, and commit the changed `Minimap*.png`.
5. Client changes (`web/js`): load the game in a browser (Playwright, at `http://127.0.0.1:85xx`, with
   `DS_DB=<scratch>/t.db DS_PORT=85xx python -m server`: this machine's the one address that shows the page without a
   ticket) and check there are no console errors and that it looks right, on a desktop and on a phone (a 915 x 412
   touch viewport with `?app=android`).
6. Commit to `main` with a message saying what changed for players, then push. Deployment (Docker on Unraid,
   `ghcr.io/kriscs1/shardsofashen`) builds from GitHub.

A commit of docs only (no code, data, maps or art) needs neither step 1 nor 2.

## Reporting

End a task with a short report: what changed (for players, and the files), what was tested and how it came out (passed,
failed, skipped, with any failure's message), anything outstanding, and whether it's committed and pushed. No more.
