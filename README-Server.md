# Dragon Sword in the browser

Up to five players share one world from any modern browser. The game runs on the server, which keeps everything:
accounts, characters and the shared world (SQLite).

| Folder | What it is |
|---|---|
| `dsengine/` | The game's rules without the window, for many players at once (taken from `dragonsword/`) |
| `server/` | The web server: the page, the pictures, and the game over a WebSocket (20 ticks a second) |
| `web/` | The browser game (HTML5 canvas, no build step). `web/assets` is made by `tools/export_web_assets.py` |
| `tools/` | `export_web_assets.py`, `admin.py` (passwords, admins, backups), `import_saves.py`, `bot.py` (test players), `browser_check.py` |
| `deploy/` | Docker, docker-compose with Caddy (HTTPS), a systemd unit |
| `dragonsword/`, `dsedit/` | The desktop game and the editor, as before |

## Playing locally

```
pip install -r requirements.txt
python tools/export_web_assets.py          # once, and again after changing sprites, sounds or data
python -m server                           # http://localhost:8080
```

Open http://localhost:8080 and make a character (name and password). **F11** (or the button at the top left of the
view) goes full screen. Press **Enter** to chat with the other players.

## What's shared and what's yours

- **Shared.** Everyone sees these, and they persist:
  - Trees chopped, rocks mined and plants picked, until they grow back.
  - Fires lit.
  - Things dropped or picked up (they respawn as before).
  - Monsters killed, and their loot.
  - Shop stock.
  - Doors opening.
  - The time of day and the weather.
- **Yours.** These are your character's alone:
  - Inventory, bank, skills, gear and quests.
  - Doors and gates your quests unlock (others still find them locked).
  - One-time items: everyone can pick up their own.
  - NPCs your story turned friend or foe.
  - Anything a quest script changes after it has looked at your quest attributes (`$Attr`, `Get.Value ATTRIBUTE`,
    `>Quest.Can.Start`).
- **Forcing it in a script.** The new commands `Personal` and `Shared` set what a script's following lines change.
- **Sleeping.** The night passes only when everyone online is asleep. Otherwise you just wake up healed.

## The arena (players fighting players)

- **Getting there.** The Arena Master, a guard in the middle of Ashford, takes you there. The Arena Keeper by the gate
  brings you back.
- **Where you can fight.** Players can only fight each other on the arena's sand: right-click another player, then
  Attack. The paving round it is safe for watching. Swords, bows and attack scrolls all work, and your gear counts.
- **Losing.** You lose nothing: no gold, no grave. You wake by the gate, healed. Everyone in the arena hears who won.
- **Records.** Wins and losses are kept as the attributes `ArenaWins` and `ArenaLosses`. Examine a player to see
  theirs.
- **Settings.** Config `[PvP]`:
  - `Maps`: the arena maps (several are separated by `;`).
  - `Ground`: the tiles you must both stand on.
  - `Respawn.Map`, `Respawn.X`, `Respawn.Y`: where the beaten wake.
  - Anywhere else, players can't fight each other.
- **Rebuilding.** `Dev/migrate/build_arena.py` makes the arena: `Maps/0,0,5.txt`, a level of its own, plus its
  scripts and the Arena Master. Run it again after rebuilding the world with `build_world.py`; it only adds what's
  missing.

## Homesteads (a home of your own)

- **Getting one.** The settler by the homestone in Ashford has the quest *A Place of Your Own*:
  - Bring her 10 planks and 4 stone blocks. Make them at her carpenter's bench: planks from logs, blocks from stone.
    Rocks can be mined for stone with a pickaxe.
  - She gives you the **Access Crystal**.
- **Going home.** Touch a **homestone**, the amber obelisk beside every town's waystone, and choose *Take me home*.
  You need the crystal in your pack.
  - After the quest she also sells **Homestead Scrolls**. They take you home from anywhere and need Magic 12.
  - Your homestone at home takes you back to where you came from.
- **Visitors.** Visiting starts **closed** (only you). Your homestone at home changes it:
  - Only you, your friends, or anyone.
  - Add friends from the players who are on.
  - Others visit from any homestone (*Visit someone's home...*).
  - Closing it sends visitors back.
- **Building.** At home, press **B** (or the Build button):
  - Choose a piece, then click or drag on your land. Esc or a right-click stops.
  - The pieces: floors, walls, doors, windows (on a matching wall), roofs (the pieces follow the roof's shape),
    furniture, lights, the garden (herbs, bushes, trees and wheat you can pick, chop and harvest), and workshops.
  - **Take down** removes the top thing on a tile and gives back half its materials. It also clears the land's own
    trees, rocks and flowers.
  - Each piece needs materials and a level of the new **Construction** skill, and building gives Construction
    experience.
- **What works at home.**
  - A bed you've slept in is where you wake if you fall.
  - A chest opens onto your bank, and only for you.
  - The bench, range, anvil, furnace and alchemy table work like the towns' ones.
- **Shared.** Homes are part of the shared world and are saved with it. There's no fog of war on them.
- **Changing it.**
  - `Data/Buildables.ini`: what can be built, of what, at which level. Kinds: `Tile`, `Decor`, `Roof`, `Object`.
  - `Data/Homestead.txt`: the land a new home starts as.
  - Config `[Homestead]`: where you arrive, and the town a homestone sends you back to by default.
  - `Dev/migrate/build_homestead.py` makes all of it: run it again after rebuilding the world; it only adds what's
    missing.

## Bringing over desktop characters

```
python tools/import_saves.py              # every Saves\*.ini (their waiting respawns join the shared world)
python tools/admin.py password Kris       # imported characters need a password before they can log in
python tools/admin.py admin Kris on       # the Admin button (give items, set skills, god mode)
```

## Changing the game and updating the server: one click

| On your PC (where you edit) | |
|---|---|
| **Test Locally.bat** | Builds the server from these files in Docker and starts it at http://localhost:8080, to try changes first. It has its own test characters. |
| **Publish Update.bat** | Saves your changes and sends them to your private GitHub repository. GitHub builds the server image, and the server PC updates itself within minutes. |
| **Link GitHub.bat** | Once, at the start: links this folder to the GitHub repository. |

## The server: Unraid (or any Linux)

Each **Publish Update** sends your changes to https://github.com/kriscs1/dragonsword. GitHub tests them and builds
the server image, `ghcr.io/kriscs1/dragonsword`; you can watch it in the repository's **Actions** tab. The server
downloads the new image and restarts the game with it. Everyone's progress is kept through every update.

Once, before the first install: when the first build is green, make the image public, so the server can download it
without signing in. Go to https://github.com/users/kriscs1/packages/container/dragonsword/settings > **Change
visibility** > **Public**. Your code stays private.

### Unraid

1. **Add the template.** Open Unraid's **Terminal** (the `>_` icon at the top right) and paste:

   ```
   docker run --rm ghcr.io/kriscs1/dragonsword cat unraid.xml > /boot/config/plugins/dockerMan/templates-user/my-DragonSword.xml
   ```

2. **Make the container.** On the **Docker** tab: **Add Container** > **Template** > choose **DragonSword**, then
   **Apply**. It's filled in already:
   - Port 8080.
   - Game data in `/mnt/user/appdata/dragonsword`.
   - It runs as nobody:users.
   - Set an invite code here if you like.
3. **Keep it up to date by itself.** On the **Apps** tab, install **Auto Update Applications**. Then
   **Settings > Auto Update Applications > Docker Auto Update Settings**:
   - Update Check Frequency: **Hourly** (or Custom, e.g. `*/15 * * * *` for every 15 minutes).
   - Set DragonSword to update.

   (Without this, the Docker tab's **Check for Updates** does it by hand.)

Players open `http://<your Unraid server>:8080`; the WebUI entry of the container's menu opens it too. It starts with
the array and keeps everyone's progress in appdata (your appdata backups cover it).

Accounts (Unraid's Terminal):

```
docker exec -u 99:100 DragonSword python tools/admin.py list
docker exec -u 99:100 DragonSword python tools/admin.py password <Name>
docker exec -u 99:100 DragonSword python tools/admin.py admin <Name> on
```

### A plain Linux server

1. Install Docker (once): `curl -fsSL https://get.docker.com | sudo sh`
2. Set up and start the server, all from GitHub, with this one line:

   ```
   mkdir -p ~/dragonsword && cd ~/dragonsword &&    docker run --rm ghcr.io/kriscs1/dragonsword cat docker-compose.yml > docker-compose.yml &&    docker compose up -d
   ```

That's all:

- **Starting:** Docker starts with Linux (no one needs to sign in), and the game and its updater start with Docker.
- **Updates:** they arrive by themselves, a few minutes after each **Publish Update**.
- **Connecting:** players use `http://<the server's address>:8080`.
- **Day to day,** in `~/dragonsword`:
  - `docker compose logs -f` shows what it's doing.
  - `docker compose pull game && docker compose up -d` updates at once.
  - `docker compose stop` stops it.



## A server on a Linux VPS (Docker)

1. Point a DNS name at the VPS (an A record), and open ports 80 and 443.
2. Copy this folder to the VPS, then:

   ```
   cp deploy/example.env deploy/.env            # set DS_DOMAIN (and DS_INVITE_CODE to keep strangers out)
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
   ```

3. Play at `https://<your domain>`. Caddy gets the certificate, so the game's WebSocket is `wss://`.

Managing accounts inside the container:

```
docker compose -f deploy/docker-compose.yml exec game python tools/admin.py list
docker compose -f deploy/docker-compose.yml exec game python tools/admin.py password <Name>
docker compose -f deploy/docker-compose.yml exec game python tools/admin.py admin <Name> on
```

### Where the data lives

- **The database.** It lives in the `gamedata` volume (`/data/dragonsword.db`). It is saved every minute, whenever
  someone leaves, and when the server stops.
- **Backups.** A copy goes to `/data/backups` once a day; the last 14 are kept.
- **Data files the game edits.** The admin panel's switched-off skills and god mode, and anything scripts write with
  `Add.Line.To.File`, live in the container's `Data/` folder. They reset when the image is rebuilt.

Without Docker, `deploy/dragonsword.service` runs it under systemd behind any HTTPS reverse proxy.

## Settings (environment)

| Variable | Default | |
|---|---|---|
| `DS_PORT` | 8080 | |
| `DS_HOST` | 0.0.0.0 | |
| `DS_DB` | `server-data/dragonsword.db` | (not `data/`: on Windows that is the game's own `Data` folder) |
| `DS_MAX_PLAYERS` | 5 | more are told the server is full |
| `DS_REGISTRATION` | open | `closed`: only accounts made with `tools/admin.py` |
| `DS_INVITE_CODE` | (none) | needed to make a character, if set |

## Checking it works

```
python -m pytest tests                               # the rules (shared vs personal), accounts, saving
python tools/bot.py --count 5 --seconds 60           # five test players at once; prints traffic and the tick time
python tools/browser_check.py --out shots            # plays in a headless browser (pip install playwright;
                                                     # python -m playwright install chromium) and takes screenshots
```

`http://<server>/health` shows who's on and how long a tick takes.
