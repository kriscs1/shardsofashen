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

1. Make a GitHub account if you don't have one: https://github.com/signup
2. Make the repository: **+** (top right) > **New repository** > name it `dragonsword` > **Private** > **Create
   repository**. Don't add a README.
3. Double-click **Link GitHub.bat** in the game folder and paste the repository's address
   (`https://github.com/<you>/dragonsword.git`). The first time, a browser window asks you to sign in to GitHub.
4. On github.com, open the repository's **Actions** tab. Wait for "Build the server image" to go green (5–10
   minutes the first time).
5. Make a token for the server PC to download with: your picture (top right) > **Settings** > **Developer settings**
   > **Personal access tokens** > **Tokens (classic)** > **Generate new token (classic)**. Tick only
   **read:packages**, choose **No expiration** (or a long one), then **Generate**, and copy the token.

### On the server PC

1. Install Docker Desktop (https://www.docker.com/products/docker-desktop/) and start it. Then in its Settings >
   General, tick **Start Docker Desktop when you sign in to your computer**.
2. Copy this folder (`deploy\server-pc`) to the server PC, e.g. to `C:\DragonSword`. A USB stick works, or download
   it from your repository on github.com.
3. Double-click **Start Server.bat**. The first time, it opens the settings (`.env`) in Notepad:
   - `DS_IMAGE`: `ghcr.io/<your GitHub user name in lower case>/dragonsword:latest`
   - `GHCR_USER`: your GitHub user name
   - `GHCR_TOKEN`: the token from step 5 above
4. Save the settings, close Notepad, and double-click **Start Server.bat** again. It downloads the game, starts it,
   and shows the address players use (`http://<the server PC's address>:8080`).

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
