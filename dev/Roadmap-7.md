# Roadmap, round 7: the full game, the demo and the Friend Pass

The owner's plan of 2026-11-09, in groups. Work down it; tick a box when it's done, tested and committed. Owning the
game comes first: the demo, the Friend Pass and the time pass are all built on it.

## The owner's decisions
- **On PC (Steam, Epic, itch.io) the game is paid for once, up front, $7.99, with no demo**: the desktop app plays only
  once it's owned. **The PC build never has an ad**: none in a game and none on its start screen (today it shows the
  central server's own).
- **On a phone (Android) it's free to try**, and one purchase unlocks the full game (and LAN and online play beyond
  the demo), $3.99; **it removes the ads too**. **Remove ads** stays a purchase of its own, for those who want only
  that.
- **The demo is the Isle, and level 5 at most.** It ends where the Isle ends: Wim's passage and the ferries don't carry a
  demo player to the mainland.
- **A time pass, on a phone, for those who haven't paid**: watch a rewarded ad on the start screen for a while of the
  full game: **an hour** each. Only in the Android app, only on the start screen, never in a game.
- **The browser follows the account**: the full game if it's owned, the demo if not, the Friend Pass on a friend's
  link.
- **The Friend Pass**: a demo player in a game whose host owns the full game has the full game there, the whole world
  and no level cap, while someone who owns it is in the game. Their progress is kept; back in a game of their own
  they're in the demo again; buying the game keeps everything they've done.

## What stays true
- **Owning the game belongs to the Hallisium account**, kept by the central server, wherever it was bought (Google
  Play, Steam, Epic, itch.io): bought once, it's the full game on every device and in a browser. The apps also know
  what's bought on the device itself (Google Play, the PC build), so Single player needs no account.
- **Never an ad in a game. Nothing that changes play is sold or given for an ad**: no loot buff, no XP boost, no item.
  The time pass gives only time in the full game, the same game everyone who paid has.
- **A demo character is a whole character**: when a pass ends nothing is taken away; only where they can go and how far
  they level is held back. XP past level 5 isn't lost: it counts once the game's owned (or in a Friend Pass game).
- **Shared vs personal**: the demo's border is each player's own, like a quest door. Nothing in the shared world
  changes for a demo player, and nothing in the story needs a second player, the Friend Pass included.
- **The game says it plainly, never a character**: Wim and the Isle's people speak as they always do; what's held back
  is said by the game itself, once, with where to buy it (no pestering, no countdowns in play).
- **Every number in a data file**: the demo's maps and cap in `data/Config.ini` `[Demo]`; the time pass's length and
  how many a day on the central server.

## 1. Owning the game (the central server)
- [ ] `accounts.full_game` (when, and where it was bought); a time pass's end (`pass_until`). The admin page shows and
      sets them (Characters' account rows).
- [ ] The ticket says whether its player has the full game (owned, or a pass running) and whether the host of the game
      it's made out to owns it (for the Friend Pass). A game asks again every so often only while someone in it is
      on a pass (no polling for everyone).
- [ ] A purchase is checked by the central server before it counts, never taken on the app's word: Google Play's
      purchase token (the Play Developer API), Steam's ownership (Sign in with Steam linking the Steam id; the Web
      API's `CheckAppOwnership`), an itch.io download key claimed on the account; Epic later.
- [ ] The privacy policy (`central/pages/privacy.html`) says what's kept; `README-Server.md` the new settings.
- [ ] Tests (`tests/test_central.py`).

## 2. The demo (the engine)
- [ ] `data/Config.ini` `[Demo]`: its maps (the Isle, maps 0..4 by -3..2, with its upstairs and its caves) and
      `Level=5`; `validate.py`.
- [ ] A session knows whether its player has the full game (the ticket; the app's own game, the device); a player
      without it: their level stops at 5 (the XP kept), and they can't go to a map outside `[Demo]` Maps by any way
      (Wim's passage, a ferry, a scroll, a shardstone, a portal, a summons).
- [ ] At the border, the game says so once (`Denied`): "The full game goes on from here." with where to get it.
- [ ] A demo character found outside the demo (a pass run out, a Friend Pass game left) is put at the Isle's dock as it
      comes in; nothing of theirs is taken.
- [ ] Tests (`tests/test_engine.py`): the cap, every way off the Isle, the dock, XP kept and counted once owned.

## 3. The Friend Pass (the engine and server)
- [ ] In a game whose host owns the full game, while someone who owns it is in it, a demo player has the full game
      (no border, no cap). A local network game an app opens counts by its host's device or account.
- [ ] When the last owner leaves: the demo players outside the Isle are told, and after a minute (`[Demo]
      FriendGrace`) are taken back to the Isle's dock; their level shows as 5 again (the XP kept).
- [ ] Tests: joining, the owner leaving and coming back, two demo players, a relayed game (`/play/<id>/`).

## 4. The page and the start screen (`web/js`, `web/home/`)
- [ ] The character list and the Stats tab say "Demo: the Isle, level 5" for a demo character; a Friend Pass badge
      under the Online line (like the PvP one): "Friend Pass: <host>'s game".
- [ ] The border's box: what's held back, and Buy (the apps' own store) or where to buy it (a browser).
- [ ] The start screen: the full game's price and Buy in the Android app (once bought, gone); a time pass's time left.
- [ ] A look in the browser, on a desktop and on a phone (915 x 412, `?app=android`).

## 5. Android
- [ ] `Billing.java`: a second one-time product, the full game (`DS_FULL_PRODUCT`, `full_game` unless set), bought,
      sent to the central server for the account and kept on the device; Google Play restores it on a reinstall.
      It removes the ads as Remove ads does (`adFree` is true for either).
- [ ] The time pass: an AdMob rewarded ad, offered on the start screen only to those who haven't bought the game;
      the reward checked by the central server (AdMob's server-side verification), never the app's word; a few a day
      at most; an hour each (the central server's setting). Nothing of it on a device that's bought the game.

## 6. PC (the desktop app)
- [ ] No ads at all on the desktop start screen (`desktop/app.py`'s `DSApp` says it's the PC build).
- [ ] Owning it: the Steam build checks with Steam; the itch.io and Epic builds by their own keys. Not owned, the
      desktop app shows only how to get it (no demo).
- [ ] Tests (`tests/test_desktop.py`).

## 7. The browser (the website, `https://shardsofashen.hallisium.com`)
- [ ] It follows the account (the owner's decision): the full game if the account owns it (or a pass is running),
      the demo if not, and the Friend Pass on a friend's link (`/play/<id>/`). On a public server (no host) the
      Friend Pass is a friend's: a demo player has the full game while one of their Hallisium friends who owns it is in
      that game (not just any owner, or a busy server would be the full game for everyone). The website has no Single
      player, so a browser's demo is played on a public server.
- [ ] No time pass in a browser (its ads are AdSense on the start screen, as now).
- [ ] Tests (`tests/test_server.py`): a demo account and an owning one on a remote server, by ticket.

## 8. Finished
- [ ] `dev/Rules.md` (Servers, apps and accounts: the ads paragraph rewritten, owning the game, the demo, the
      Friend Pass, the time pass; Shared vs personal: the border), `dev/Story and Quests.md` (Passage to the Mainland
      for a demo player), `README-Server.md`, the privacy policy, `CREDITS.md` if anything new is used.
- [ ] `validate.py` 0 errors, the full tests, `export_web_assets.py`, a look in the browser (desktop and phone),
      committed and pushed.

## Still to decide
- How many time passes a day (the plan's default: 3).

(The prices are set in each store, not in the game: Google Play's full-game product at $3.99, the PC build at $7.99.)
