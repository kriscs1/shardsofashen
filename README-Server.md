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

## Bringing over desktop characters

```
python tools/import_saves.py              # every Saves\*.ini (their waiting respawns join the shared world)
python tools/admin.py password Kris       # imported characters need a password before they can log in
python tools/admin.py admin Kris on       # the Admin button (give items, set skills, god mode)
```

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
| `DS_DB` | `data/dragonsword.db` | |
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
