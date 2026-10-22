# Running the server on its own PC

When you change the game on your own PC and click **Publish Update.bat**, the server PC updates itself:

1. Your changes go to your private GitHub repository.
2. GitHub builds the server and stores it in its registry (ghcr.io). This takes about 5–10 minutes; you can watch it
   in the repository's **Actions** tab.
3. Within 5 minutes after that, the server PC downloads the new version and restarts the game with it.

Everyone's characters and the world are kept through every update. Players online are disconnected for a few seconds
and log in again.

## Setting up (once)

### On your own PC (where you edit the game)

1. Double-click **Publish Update.bat**. The first time, a "Connect to GitHub" window asks you to sign in (choose the
   browser). It sends the game to https://github.com/kriscs1/dragonsword.
2. Wait for the build to finish: https://github.com/kriscs1/dragonsword/actions (green tick, 5–10 minutes the
   first time).
3. Make the game's image public so the server PC can download it without signing in:
   https://github.com/users/kriscs1/packages/container/dragonsword/settings > at the bottom, **Change visibility** >
   **Public**. (Your code stays private; anyone who knows the image's name could download the game itself.)

### On the server PC

1. Install Docker Desktop (https://www.docker.com/products/docker-desktop/) and start it. In its Settings > General,
   tick **Start Docker Desktop when you sign in to your computer**.
2. Copy this folder (`deploy\server-pc`) to the server PC (a USB stick works), e.g. to `C:\DragonSword`.
3. In that folder, either double-click **Start Server.bat**, or open a terminal there and run:

   ```
   docker compose up -d
   ```

   That's all: it downloads the game, starts it, and keeps it up to date. Players connect to
   `http://<the server PC's address>:8080`.

(If you'd rather keep the image private: make a token at
https://github.com/settings/tokens/new?scopes=read:packages&description=dragonsword-server, copy `example.env` to `.env`,
and fill in `GHCR_USER=kriscs1` and `GHCR_TOKEN=` with it. Run `docker login ghcr.io -u kriscs1` once with the token
as the password, then `docker compose up -d`.)

From then on the server starts by itself whenever Docker Desktop starts (when someone signs in to Windows) and keeps
itself up to date. For a server that is always on:

- **Sleep:** Windows Settings > System > Power > Screen and sleep > when plugged in, put my device to sleep: **Never**.
- **Signing in:** Docker Desktop only starts once someone signs in to Windows, so after a power cut, sign in again
  (or set Windows to sign in automatically).

## The buttons (in this folder)

| | |
|---|---|
| **Start Server.bat** | Starts the server (and signs in to GitHub's registry). Run it again after changing `.env`. |
| **Update Now.bat** | Gets the newest version now, instead of within 5 minutes. |
| **Stop Server.bat** | Stops it; everyone's progress is saved first. |
| **Server Log.bat** | Shows what the server is doing: who logs in, updates. |

## Playing from elsewhere

- **The same network.** Players open `http://<the server PC's address>:8080`. If Windows asks whether Docker may use
  the network, allow it.
- **Over the internet**, choose one:
  - Forward port 8080 on your router to the server PC, and give friends `http://<your public IP>:8080`.
  - Use Tailscale (free, no router changes).
  - For a proper address with HTTPS, put the server on a VPS with `deploy/docker-compose.yml` (Caddy).

## Accounts and backups

These commands are run on the server PC, in this folder:

```
docker compose exec game python tools/admin.py list
docker compose exec game python tools/admin.py password <Name>
docker compose exec game python tools/admin.py admin <Name> on
```

- **Where the data lives.** Everything is in Docker's `dragonsword_gamedata` volume, which survives updates.
- **Backups.** A backup is made there every day, in the volume's `backups` folder.
- **Taking a copy off the server PC:**
  `docker compose cp game:/data/dragonsword.db dragonsword-copy.db`
