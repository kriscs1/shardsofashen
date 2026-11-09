# Selling the game: setting up the stores

The steps, in order, to sell the full game (the plan: `dev/Roadmap-7.md`; each setting in full: `README-Server.md`
"Owning the game" and "The time pass", and `android/README.md`). Until the last step nothing changes for players:
nobody is in the demo till `DS_DEMO=1`, a store that isn't set up refuses its purchases, and there's no time pass
without `DS_ADMOB_REWARDED`.

| Where | Price | How it's owned |
|---|---|---|
| Android (Google Play) | $3.99 | Free to try (the demo); one purchase, for the Hallisium account; it removes the ads too |
| PC on Steam | $7.99 | Steam says the Steam account owns it; its ticket gives the Hallisium account the full game |
| PC on itch.io | $7.99 | The download is the purchase; the itch.io link, pasted in the account popup, gives the account the full game |
| A browser | $7.99 | Follows the account; its Buy is itch.io's, claimed by the account's confirmed email |

## 1. Google Play: the product

In the Play Console: the app > **Monetize with Play > Products > In-app products** > Create:
- **`full_game`**: "The full game", $3.99, then **Activate**. (`remove_ads` is there already.)

Play asks for a payments profile first if there isn't one.

## 2. Google Play: a service account (purchases and Play Integrity)

1. [console.cloud.google.com](https://console.cloud.google.com): make or pick a project.
2. **APIs & Services > Library**: turn on **Google Play Android Developer API** and **Play Integrity API**.
3. **IAM & Admin > Service accounts** > Create. Then its **Keys > Add key > JSON**: save it as `play.json`. It's a
   secret: never in the repository.
4. Play Console > **Users and permissions > Invite new users**: the service account's email, and for this app
   **View financial data** and **Manage orders and subscriptions**.
5. Play Console > **Test and release > App integrity > Play Integrity API**: link the same Cloud project.

## 3. AdMob: the time pass

1. [apps.admob.com](https://apps.admob.com) > the app > **Ad units > Add > Rewarded**; the reward: 1 "Hour".
2. GitHub > Settings > Secrets and variables > Actions > **Variables**: **`ADMOB_REWARDED_ID`** = the unit's id
   (`ca-app-pub-.../...`).
3. Do step 6 first (AdMob calls the central server to check the URL), then in the ad unit's settings turn on
   **Server-side verification** with the callback URL `https://shardsofashen.hallisium.com/api/pass/reward`.

## 4. Steam

There's no Greenlight (Valve closed it in 2017): it's **Steam Direct**, open to anyone.
1. [partner.steamgames.com](https://partner.steamgames.com): sign up (your identity, bank and tax details), and pay
   the **$100 fee** for the app (paid back once the game has made $1,000 on Steam).
2. Make the store page (screenshots, a capsule image, a description, the price, $7.99) and the build; Valve reviews
   both, usually in a few days. The store page must show as "Coming soon" for at least two weeks, and the game can be
   released 30 days after the fee is paid at the earliest.
3. Note the **app id**, and make a **publisher Web API key**: Steamworks > **Users & Permissions > Manage Groups** >
   your group.
4. Build the Steam version (the Steamworks SDK's folder, unzipped, from Steamworks' downloads):

       DS_STORE=steam DS_STEAM_APP=<id> DS_STEAM_SDK=<the SDK's folder> python desktop/build_desktop.py

   and upload `dist/ShardsOfAshen/` with Steamworks' SteamPipe.

## 5. itch.io

1. Make the game's page at [itch.io](https://itch.io): $7.99, "Paid" (no free download).
2. The **game id**: the number in its edit page's address (`itch.io/game/edit/<id>`). An **API key**: itch.io >
   **Settings > API keys** > Generate.
3. Build and upload: `DS_STORE=itch python desktop/build_desktop.py`, then `dist/ShardsOfAshen/` zipped (or with
   itch.io's butler).

itch.io takes the payment and the sales tax. The browser's start screen has a Buy button too (step 6's `DS_BUY_URL`):
it opens the game's itch.io page, and "I've bought it" finds the purchase by the account's confirmed email, so a
player buys with the same email as their Hallisium account (or pastes the link from their purchase's page in Account).

## 6. The central server's settings

On the VM, in `/opt/shards-of-ashen-central`:
1. Bring it up to date: `curl -fsSL https://raw.githubusercontent.com/kriscs1/shardsofashen/main/deploy/central-setup.sh | sudo sh`
   (it keeps the `.env` and the accounts).
2. The key, into its data folder: `docker compose cp ~/play.json central:/data/play.json`
3. In `.env`:

       DS_PLAY_SERVICE_ACCOUNT=/data/play.json
       DS_PLAY_INTEGRITY=1
       DS_ADMOB_REWARDED=ca-app-pub-.../...
       DS_STEAM_APP=...         (once there is one)
       DS_STEAM_KEY=...
       DS_ITCH_GAME=...
       DS_ITCH_KEY=...
       DS_BUY_URL=https://<you>.itch.io/<game>   (the browser's Buy)
       DS_BUY_PRICE=$7.99
       DS_DEMO=                 (empty till step 8)

4. `docker compose up -d`

## 7. Release the Android app

1. Run the GitHub Android build (Actions). It's the first build with the Java for the full game, the time pass and
   Play Integrity: if it fails, the error is in its log.
2. Put it on an **internal testing** track, and add yourself under Play Console > Setup > **License testing** (test
   purchases cost nothing).
3. On your phone, from the track (an app installed by hand fails Play Integrity): buy the full game, and watch a time
   pass's ad. The admin page's Accounts then shows the account's full game, or its pass.

## 8. Turn the demo on: last

`DS_DEMO=1` puts **every account that hasn't bought it** in the demo, the players you have already among them (their
characters outside the Isle go back to its pier). So first, on the admin page (`/admin` > Accounts), **Give the full
game** to everyone who should keep it. Then `DS_DEMO=1` in `.env`, and `docker compose up -d`.
