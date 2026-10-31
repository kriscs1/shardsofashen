# Shards of Ashen in the browser

Up to five players share one world from any modern browser. The game runs on the server, which keeps everything:
accounts, characters and the shared world (SQLite).

| Folder | What it is |
|---|---|
| `dsengine/` | The game's rules without the window, for many players at once (taken from `ashen/`) |
| `server/` | The web server: the page, the pictures, and the game over a WebSocket (20 ticks a second) |
| `web/` | The browser game (HTML5 canvas, no build step). `web/assets` is made by `tools/export_web_assets.py` |
| `tools/` | `export_web_assets.py`, `admin.py` (whose characters are, admins, backups), `import_saves.py`, `bot.py` (test players), `browser_check.py` |
| `deploy/` | Docker, docker-compose with Caddy (HTTPS), a systemd unit |
| `android/` | The Android app: hosts a game on the phone for the network, or joins one (`android/README.md`) |
| `dsedit/` | The editor (`Shards of Ashen Editor.py`): F5 plays your changes in the browser, on a local server |
| `ashen/` | Helpers shared by the server, the editor and the tools (the desktop game itself is retired) |

## Playing locally

```
pip install -r requirements.txt
python tools/export_web_assets.py          # once, and again after changing sprites, sounds or data
python -m server                           # http://localhost:8484
```

Open http://localhost:8484 and make a character (a name and how they look: no password). **F11** (or the button at the top left of the
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
- **Dropping things.** Only you see what you drop for its first 10 seconds; then everyone does (Config
  `[Gameplay] Drop.Private.Seconds`).
- **Dying.**
  - You keep your 5 most valuable single items, worn or carried (Config `[Gameplay] Death.Keep.Items`).
  - You also keep whatever can't be dropped (`Droppable=0`: quest things, the Hearth Anchor; `Keep.On.Death`
    overrides it per item).
  - The rest, and the gold you didn't lose, goes in your grave.
- **Chat.** Enter talks to everyone. `/w <name> <words>` whispers to one player, and `/r <words>` answers the last
  whisper. Right-click a player: Whisper.

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
- **Rebuilding.** `dev/migrate/build_arena.py` makes the arena: `maps/0,0,10.txt`, a level of its own, plus its
  scripts and the Arena Master. Run it again after rebuilding the world with `build_world.py`; it only adds what's
  missing.

## Homesteads (a pocket of your own)

Your homestead is a pocket of the Shardrealm's calm rim, held by an anchor of your own. Settlers call these pockets
the **Stillwater**. A pocket is always safe: nothing hostile can be in one.

- **Getting one.** The settler by the shardstone in Ashford has the quest *A Place of Your Own*:
  - Bring her 10 planks and 4 stone blocks. Make them at her carpenter's bench: planks from logs, blocks from stone.
    Rocks can be mined for stone with a pickaxe.
  - She gives you the **Hearth Anchor** (it was the Access Crystal).
- **Going home.** Travel from any shardstone you've activated: its map has a **Your homestead** button while you
  carry the Hearth Anchor.
  - After the quest she also sells **Homestead Scrolls**. They take you home from anywhere.
  - The **Pocket Anchor** in your pocket takes you back to where you came from.
- **Visitors.** Visiting starts **closed** (only you). Your Pocket Anchor changes it:
  - Only you, your friends, or anyone.
  - Add friends from the players who are on.
  - Others visit from any shardstone's map (*Visit a homestead...*).
  - Closing it sends visitors back.
- **Terraforming.** A new pocket is raw rim: a little still glass in pale mist. The Build panel's **Terraform** tab
  shapes it with Shards and the **Shardcraft** skill:
  - still the mist into glass (only beside ground that's held already), glass to soil, soil to grass, water, rocks
    and saplings;
  - **Shard Blooms**: each gives you a few Shards every few real hours (harvest it yourself). One may grow at first,
    and one more for every few Shardcraft levels. No other source gives as many Shards.
  - Costs are in `data/Shards.ini` `[Terraform]` and `[Homestead]`.
- **Building.** At home, press **B** (or the Build button):
  - Choose a piece, then click or drag on your land. Esc or a right-click stops.
  - The pieces: floors, walls, doors, windows (on a matching wall), roofs (the pieces follow the roof's shape),
    furniture, lights, the garden (herbs, bushes, trees and wheat you can pick, chop and harvest), and workshops.
  - **Take down** removes the top thing on a tile and gives back half its materials (never Shards). It also clears
    the land's own trees, rocks and flowers.
  - Each piece needs materials and a level of **Homesteading**, and building gives Homesteading experience.
- **What works at home.**
  - A bed you've slept in is where you wake if you fall.
  - A chest opens onto your bank, and only for you.
  - The bench, range, anvil, furnace and alchemy table work like the towns' ones.
- **Shared.** Homes are part of the shared world and are saved with it. There's no fog of war on them.
- **Homes from before pockets** keep their land (a meadow: a pocket already shaped); their homestone is their
  Pocket Anchor now.
- **Changing it.**
  - `data/Buildables.ini`: what can be built, of what, at which level. Kinds: `Tile`, `Decor`, `Roof`, `Object`.
    `Tile=` is what a piece lays (the Terraform pieces), `Skill=` the skill it goes by (Homesteading if not said).
  - `data/Homestead.txt`: the land a new home starts as (in the editor: the map **Homestead**). Each home gets its
    own copy when it's made, so changing it only changes homes made after that.
  - Config `[Homestead]`: where you arrive, and the town a pocket sends you back to by default.
  - `dev/migrate/build_pocket.py` makes it (it superseded `build_homestead.py`).

## Farming

- **Sowing.** Buy seeds from the farmer on the farmlands east of Ashford, and use them on **tilled soil**.
  - His furrows by the cabbages are free for anyone to sow.
  - On your homestead, lay tilled soil from the Build panel (Garden: on soil or grass). Only you can sow there.
- **Growing.** Crops grow through three stages on the server's clock, even while you're logged out or the server is
  off. Everyone sees them grow. Examine one to see whose it is and when it'll be ripe.
- **Harvesting.** Only whoever sowed a crop can harvest it. A harvest gives produce (more at higher Homesteading), Homesteading
  experience, and sometimes a seed back. On the farmer's furrows a ripe crop withers if it waits an hour.
- **Crops.** Potato (Homesteading 1), onion, cabbage, wheat, carrot, herbs, and pumpkin (Homesteading 25). The range cooks baked
  potatoes, vegetable stew and pumpkin pie.
- **Changing it.** `data/Crops.ini`: the seed, level, minutes, yield, experience, seed-back chance and withering of
  each crop. `dev/migrate/build_farming.py` makes it all, like the other builders.

## The market, the shops, the tavern, digging and raids

- **The market.** One market for the whole world, at any **market board**: Ashford's market, and beside every
  town's shardstone.
  - **Browsing:** see everything everyone has for sale, cheapest first, with who's selling it.
  - **Selling:** right-click something in your pack, choose *Sell on the market*, and set the price each and how
    many. It's up at once, at every board.
  - **Your listings:** *Show only mine* to take things back or change a price. Up to 18 listings each.
  - **Takings:** buyers pay into your purse even while you're logged out; *Collect* it at any board.
  - Things that can't be dropped (quest items, the Hearth Anchor) can't be sold.
- **Ashford's stalls** are for traders now: a greengrocer, a fishmonger, a weaver, a tinker (spades, buckets...)
  and a butcher, each behind a stall with a shop of their own.
- **Shop signs.** Every shop has a signboard by its door with a picture of what it sells.
- **The Green Dragon** (behind Ashford's houses, north):
  - The innkeeper plays **Three Cups** (find the coin: 2.5 times your stake back) and **High or Low** (guess the next
    roll: 1.4 times back), and sells ale and food.
  - At a **dice table**, *Play* to start a round of **Dragon Dice**. Everyone nearby has 20 seconds to match the
    stake, then all roll three dice and the highest takes the pot (ties share). Alone? The innkeeper plays you.
- **Digging.** Right-click a spade: *Dig*, anywhere on open ground. About 1 dig in 14 turns something up: gold
  usually, sometimes stone, bones, ore, seeds, very rarely a gem. It leaves a hole that grasses over in 10 minutes.
  `data/Digging.ini` sets the chance, the ground and the finds. (On sand you get sand too.)
- **Monster raids.** `data/Waves.ini`: monsters attacking a place in waves.
  - **Surprise raids:** about every two hours, when 2 or more are playing, goblins raid Ashford.
  - **Defending:** a horn sounds and a banner shows the wave, how many are left and the time.
  - **Rewards:** whoever kills a raider gets gold, and everyone who held out shares the reward.
  - **Losing:** if time runs out, or everyone leaves, the raiders go.
  - **Any attack, any time:** a script's `Start.Wave <name>` starts one, so a quest can have a battle. Its
    `On.Win.Script` runs for each defender afterwards. Example: the farmer's *They're here now? I'll fight them off!*
    starts `Farm_Raid`.
  - Admins can start one from the Admin panel.
- **Chat.** A chime plays when another player says something (a softer one for a whisper); Options can turn it off.
- **Admins** can jump to any named place (Admin > *Go to a place*): `Ashford_Market`, `The_Green_Dragon`,
  `Waystone_Highwatch`...
- `dev/migrate/build_market.py` (signs) and `dev/migrate/build_town_life.py` (boards, vendors, tavern, digging,
  raids) make all of this.

## Who's who

Characters have no passwords. Each belongs to someone, and its name is one of a kind on its server:

- **A Shards account** (signed in on the start screen): the start screen gets a ticket from the central server for that
  one game, and the game shows the account's characters there (up to 5) or makes their first. The same account on
  another server is the same player, with that server's characters.
- **A device** (playing without an account): the start screen gives each game a key of this device's own, and the
  game knows it by that. A device's key lets you in from this machine and its network, or anywhere on a server that
  isn't joined to a central server; a public server joined to one wants an account.
- **The host**: the app's own game (Play alone, Host a game) lets the start screen in by the key it started the
  server with, as its Shards account, or this device: no ticket, so playing alone needs no network.

A device that came in by an account (a ticket, or the host's key) is that account's on that server from then on: a
reload, or the central server away, is still you. Signing out on the start screen gives every game a new key.

**Old characters** (made with a password of their own, before accounts) wait to be brought in: on the character
screen, "Bring in an old character" takes its name and password once, and it's yours for good, with no password. An
admin can give one a password to bring it in with (Admin > An old character's password, or
`tools/admin.py password <Name>`), or give it straight to an account (`tools/admin.py owner <Name> <Account>`).

## Bringing over old desktop characters

```
python tools/import_saves.py              # every saves\*.ini (their waiting respawns join the shared world)
python tools/admin.py owner Kris Kris     # give it to a Shards account (or: password Kris, to bring it in with)
python tools/admin.py admin Kris on       # the Admin button (give items, set skills, god mode)
```

## Changing the game and updating the server: one click

| On your PC (where you edit) | |
|---|---|
| **Test Locally.bat** | Builds the server from these files in Docker and starts it at http://localhost:8484, to try changes first. It has its own test characters. |
| **Publish Update.bat** | Saves your changes and sends them to your GitHub repository. GitHub builds the server image, and the server PC updates itself within minutes. |
| **Link GitHub.bat** | Once, at the start: links this folder to the GitHub repository. |

## The server: Unraid (or any Linux)

Each **Publish Update** sends your changes to https://github.com/kriscs1/shardsofashen. GitHub tests them and builds
the server image, `ghcr.io/kriscs1/shardsofashen`; you can watch it in the repository's **Actions** tab. The server
downloads the new image and restarts the game with it. Everyone's progress is kept through every update.

Once, before the first install: when the first build is green, check that the image is public, so the server can
download it without signing in. Go to https://github.com/users/kriscs1/packages/container/shardsofashen/settings: if
it says Private, **Change visibility** > **Public**. (New images can start out private even when the repository is
public.)

### Unraid

**A server from before the rename** (a DragonSword container, `ghcr.io/kriscs1/dragonsword`) gets no more updates.
Make a new container from the template below, and to keep its world, point **Game data** at the old folder
(`/mnt/user/appdata/dragonsword`), or copy that folder's files into the new one first. The first time the game starts
it renames `dragonsword.db` there to `ashen.db` by itself. Then remove the old container (its data stays).

1. **Add the template.** Open Unraid's **Terminal** (the `>_` icon at the top right) and paste:

   ```
   docker run --rm ghcr.io/kriscs1/shardsofashen cat unraid.xml > /boot/config/plugins/dockerMan/templates-user/my-ShardsOfAshen.xml
   ```

   (Its icon comes from GitHub: https://raw.githubusercontent.com/kriscs1/shardsofashen/main/web/img/icon.png.)

2. **Make the container.** On the **Docker** tab: **Add Container** > **Template** > choose **ShardsOfAshen**, then
   **Apply**. It's filled in already:
   - **Web port** (8484): the port players connect to. Change it if 8484 is taken.
   - **Game data** (`/mnt/user/appdata/shards-of-ashen`): where accounts, characters, the world and the daily backups
     are kept. Point it at another share if you like.
   - **Admins**: Shards accounts whose characters get the Admin button, comma-separated (e.g. `Kris,Ann`).
   - **Invite code**: if set, making a character needs it.
   - It runs as nobody:users.
3. **Keep it up to date by itself.** On the **Apps** tab, install **Auto Update Applications**. Then
   **Settings > Auto Update Applications > Docker Auto Update Settings**:
   - Update Check Frequency: **Hourly** (or Custom, e.g. `*/15 * * * *` for every 15 minutes).
   - Set ShardsOfAshen to update.

   (Without this, the Docker tab's **Check for Updates** does it by hand.)

Players open `http://<your Unraid server>:8484`; the WebUI entry of the container's menu opens it too. It starts with
the array and keeps everyone's progress in appdata (your appdata backups cover it).

Accounts (Unraid's Terminal):

```
docker exec -u 99:100 ShardsOfAshen python tools/admin.py list
docker exec -u 99:100 ShardsOfAshen python tools/admin.py owner <Name> <Account>  # give a character to an account
docker exec -u 99:100 ShardsOfAshen python tools/admin.py admin <Name> on
```

Characters have no passwords (see "Who's who" above).

### A plain Linux server

1. Install Docker (once): `curl -fsSL https://get.docker.com | sudo sh`
2. Set up and start the server, all from GitHub, with this one line:

   ```
   mkdir -p ~/shards-of-ashen && cd ~/shards-of-ashen &&    docker run --rm ghcr.io/kriscs1/shardsofashen cat docker-compose.yml > docker-compose.yml &&    docker compose up -d
   ```

That's all:

- **Starting:** Docker starts with Linux (no one needs to sign in), and the game and its updater start with Docker.
- **Updates:** they arrive by themselves, a few minutes after each **Publish Update**.
- **Connecting:** players use `http://<the server's address>:8484`.
- **Day to day,** in `~/shards-of-ashen`:
  - `docker compose logs -f` shows what it's doing.
  - `docker compose pull game && docker compose up -d` updates at once.
  - `docker compose stop` stops it.

**Settings.** Make a file called `.env` in `~/shards-of-ashen` (beside `docker-compose.yml`) with any of these, then
`docker compose up -d` again:

```
DS_PORT=8090                 # the port players connect to (8484)
DS_DATA=/srv/shards-of-ashen     # where the game's data is kept: a folder, or a Docker volume's name (gamedata)
DS_ADMINS=Kris,Ann           # Shards accounts whose characters get the Admin button
DS_INVITE_CODE=letmein       # making a character needs this code
DS_MAX_PLAYERS=5
DS_REGISTRATION=open         # closed: only accounts made with tools/admin.py
PUID=1000                    # the user and group the game runs as (they own the data folder)
PGID=1000
```

If you move the data to a folder, copy the old data over first, or the world starts new.



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
docker compose -f deploy/docker-compose.yml exec game python tools/admin.py owner <Name> <Account>
docker compose -f deploy/docker-compose.yml exec game python tools/admin.py admin <Name> on
```

### Where the data lives

- **The database.** It lives in the `gamedata` volume (`/data/ashen.db`). It is saved every minute, whenever
  someone leaves, and when the server stops.
- **Backups.** A copy goes to `/data/backups` once a day; the last 14 are kept.
- **Data files the game edits.** The admin panel's switched-off skills and god mode, and anything scripts write with
  `Add.Line.To.File`, live in the container's `data/` folder. They reset when the image is rebuilt.

Without Docker, `deploy/shards-of-ashen.service` runs it under systemd behind any HTTPS reverse proxy.

## The central server (accounts, the remote games list, ads)

One central server serves the whole game. Every version's start screen connects to it first (the Android app, the
desktop app, and a browser, which gets the start screen from it): players have one account there for every game, it
lists the remote game servers (each announces itself to it), and it serves the ads on the start screen.

- **What it is**: `central/` (standard library and aiohttp, like the game server), run from the same image as
  `python -m central` on port 8490. `deploy/docker-compose.central.yml` runs it behind Caddy for HTTPS on a VM of its
  own (a small one is plenty): a folder with that file, `deploy/Caddyfile.central` saved as `Caddyfile`, and a `.env`
  with `DS_CENTRAL_DOMAIN=central.example.com`, then `docker compose up -d`.
- **Pointing everything at it**: put its address in `web/home/config.js` (`window.DS_CENTRAL_DEFAULT =
  "https://central.example.com";`), run `python -I tools/sync_home.py`, and build the apps; give each game server
  `DS_CENTRAL=https://central.example.com`. A player can point their app at another under "Central server" at the
  foot of the start screen.
- **Joining a game**: the start screen asks the central server for a ticket made out to that one server (its id: on
  the network's answer, in the central list, or from its `/api/info`), and opens the game with it; the game server
  checks it with the central server (`/api/verify`) and shows the account's characters there (or makes their
  first). See "Who's who" below.
- **Remote and local**: a game server with `DS_PUBLIC=1` (and `DS_CENTRAL`) announces itself every minute: its id,
  name, how many are playing, and its address (`DS_PUBLIC_URL`, or where it calls from and `DS_PUBLIC_PORT`), and says
  goodbye as it stops. Without it, it only answers on its own network.
- **Approving servers**: a remote server that announces itself waits, unlisted, until an admin approves it on the
  admin page (`https://central.example.com/admin`, signed in with a Shards account named in `DS_CENTRAL_ADMINS` (one
  with no account yet is signed up with the admin code the central server's log gives as it starts) or
  made admin there). `DS_CENTRAL_APPROVED` lists servers (their ids) approved before they ever call. The admin page
  also finds accounts (ban, unban, make admin), edits the start screen's ads, and counts everything.
- **Email for a forgotten password**: set `DS_SMTP_HOST` (and `DS_SMTP_PORT`, `DS_SMTP_USER`, `DS_SMTP_PASSWORD`,
  `DS_SMTP_FROM`, `DS_SMTP_TLS`: any mail service's SMTP, e.g. Brevo, Mailgun, SES, or Gmail with an app password).
  Players may give an email when they sign up or in their account; "Forgotten?" then emails a code good for 30
  minutes. Without SMTP, the recovery code is the only way back in.
- **The privacy policy** is at `/privacy`: set `DS_CENTRAL_OPERATOR` (who runs it) and `DS_CENTRAL_CONTACT` (an email
  to write to) for its blanks. Read it through before going public: it's written for this game, but it's yours.
- **AdSense** (browsers only: Google's rules put apps on AdMob instead): set `DS_ADSENSE_CLIENT` (`ca-pub-...`) and
  `DS_ADSENSE_SLOT`; the start screen shows the ad unit in a browser, `/ads.txt` gives Google its line, and the
  privacy policy names it. Add the site in AdSense and, for players in the EEA and UK, turn on Google's consent
  message there (Privacy & messaging).
- **AdMob** (the Android app; android/README.md says how to build it in): set `DS_ADMOB_APP` (`ca-app-pub-...~...`)
  here too, so `/app-ads.txt` gives AdMob its line and the privacy policy names it. Give this server's address as
  the developer website in the Play Store listing (AdMob looks for `app-ads.txt` there). The desktop app keeps
  showing your own ads.
- **Ads**: a JSON list at `DS_CENTRAL_ADS` (`/data/ads.json` in the compose file):
  `[{"text": "...", "link": "https://...", "image": "banner.png"}]`, the pictures in `DS_CENTRAL_ADS_DIR`
  (`/data/ads/`). One is shown on the start screen each time it opens. Without the file, a few of the game's own
  notes. (House ads, chosen by you, shown wherever AdSense and AdMob aren't.)
- **Its settings**: `DS_CENTRAL_DB`, `DS_CENTRAL_PORT` (8490), `DS_CENTRAL_NAME`, `DS_CENTRAL_MOTD`,
  `DS_REGISTRATION`, `DS_PASSWORD_MIN` (8), `DS_REGISTER_PER_DAY` (3), `DS_TRUST_PROXY`.

## A public server on a cloud VM (anyone can sign up)

What you need: a small Linux VM (2 CPUs and 2 GB of memory keep 20 to 30 players smooth: a Hetzner CX22, a
DigitalOcean or Linode 2 GB droplet, an AWS Lightsail 2 GB instance, about 5 to 12 a month), Ubuntu 22.04 or 24.04 or
Debian 12 on it, and a domain name you can add a DNS record to.

1. **Point the domain at the VM.** Add an A record (`play.example.com` -> the VM's public IPv4 address), and an AAAA
   record if it has IPv6. Wait until `ping play.example.com` answers from the VM's address.
2. **Run the setup on the VM** (it installs Docker, opens only SSH, HTTP and HTTPS, adds a little swap on a small VM,
   asks for the domain and your admin character's name, and starts everything in `/opt/shards-of-ashen`):

   ```
   curl -fsSL https://raw.githubusercontent.com/kriscs1/shardsofashen/main/deploy/cloud-setup.sh | sudo sh
   ```

   (If the repository is private, copy `deploy/cloud-setup.sh` to the VM and run `sudo sh cloud-setup.sh`, with
   `GHCR_USER` and `GHCR_TOKEN` set in `/opt/shards-of-ashen/.env` so the VM can pull the image.)
3. **Admins are Shards accounts** (`DS_ADMINS`): their characters get the Admin button, proved by the central
   server's ticket. Without a central server (`DS_CENTRAL`), make someone admin with `tools/admin.py admin <Name> on`.
4. **Players make characters on the character screen**: one address can make 3 a day (`DS_REGISTER_PER_DAY`), an
   account or a device at most 5 on a server, and names like Admin and Moderator are kept back. For a private server,
   set `DS_INVITE_CODE` (a code they must give), or `DS_REGISTRATION=closed`.

The pieces (`deploy/docker-compose.cloud.yml`): the game, Caddy in front of it (it gets and renews the HTTPS
certificate by itself, so the game's connection is `wss://`, and it passes on each player's own address:
`DS_TRUST_PROXY=1`), and the updater, which pulls a new image every 5 minutes when there is one and restarts the
game with it (players are saved first and simply log in again).

**Who's who.** Characters have no passwords: they belong to a Shards account, or to a device. See "Who's who"
above.

**Running it.**

- Settings: `/opt/shards-of-ashen/.env` (`deploy/cloud.env.example` explains each), then `docker compose up -d` in
  that folder.
- Moderating, in the game's chat, as an admin: `/kick Name`, `/ban Name why`, `/unban Name`, `/bans`,
  `/mute Name minutes`, `/unmute Name`. A ban is on the character and on whose it is (the account, or the device).
- Characters: `docker compose exec game python tools/admin.py list` (and `owner <Name> <Account>`, `admin <Name> on`).
- Logs: `docker compose logs -f game`. Health: `https://play.example.com/health` (who's on, the tick time).
- Backups: one a day in the `gamedata` volume's `backups` folder (14 kept). Copy them off the VM now and then, for
  example `docker compose cp game:/data/backups ./backups`, or turn on your provider's VM snapshots.
- Updating the VM itself: `sudo apt update && sudo apt upgrade` now and then (the game updates itself).
- More players than one VM keeps smooth: start a second server (another VM, another domain) rather than a bigger one:
  each server is a world of its own.

## Settings (environment)

| Variable | Default | |
|---|---|---|
| `DS_PORT` | 8484 | |
| `DS_HOST` | 0.0.0.0 | |
| `DS_DB` | `server-data/ashen.db` | (not `data/`: on Windows that is the game's own `Data` folder) |
| `DS_MAX_PLAYERS` | 5 | more are told the server is full |
| `DS_REGISTRATION` | open | `closed`: only accounts made with `tools/admin.py` |
| `DS_INVITE_CODE` | (none) | needed to make a character, if set |
| `DS_ADMINS` | (none) | Shards accounts whose characters get the Admin button, comma-separated (besides `tools/admin.py admin <Name> on`): the central server's ticket proves the account, so nobody can take the name. An old character it named before keeps the button |
| `DS_NAME` | `Shards of Ashen on <computer>` | the game's name in the Android app's "Games on this network" |
| `DS_LAN` | 1 | answer "who's there?" broadcasts on UDP `DS_LAN_PORT` (8485), so phones on the network find it; `0`: don't |
| `DS_LAN_OPEN` | 1 | a new world starts open to the network; `0`: closed (only this machine may join). The host changes it in Options |
| `DS_TRUST_PROXY` | (off) | `1` behind a reverse proxy (Caddy): each player's own address from `X-Forwarded-For`, for the wrong-password wait and the sign-up limit. Only the last address in it counts (the one the proxy put there), and only from a proxy on this machine or a private network |
| `DS_ORIGINS` | (none) | other pages allowed to open the game's connection, comma-separated (e.g. `https://play.example.com`). The game's own page always may; any other site's page is turned away |
| `DS_PASSWORD_MIN` | 4 | the shortest password an admin may give an old character (to bring it in with) |
| `DS_CENTRAL` | (none) | the central server's address: players come in by its tickets |
| `DS_PUBLIC` | (off) | `1`: a remote server, announced to the central server and listed for everyone |
| `DS_PUBLIC_URL` | (where it calls from) | the address it's listed by, e.g. `https://play.example.com` |
| `DS_PUBLIC_PORT` | `DS_PORT` | the port it's listed by, when it has no `DS_PUBLIC_URL` |
| `DS_REGISTER_PER_DAY` | 5 | characters one address may make in a day (`0`: no limit) |

## Checking it works

```
python -m pytest tests                               # the rules (shared vs personal), accounts, saving
python tools/bot.py --count 5 --seconds 60           # five test players at once; prints traffic and the tick time
python tools/browser_check.py --out shots            # plays in a headless browser (pip install playwright;
                                                     # python -m playwright install chromium) and takes screenshots
```

`http://<server>/health` shows who's on and how long a tick takes.
