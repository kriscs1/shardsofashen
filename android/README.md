# Shards of Ashen for Android

The app carries the whole game: the same server (`server/`, `dsengine/`, `data/`, `maps/`...) and the same web
page (`web/`) as any Shards of Ashen server, built from this folder. Its start screen offers three ways to play:

- **Host a game here.** The phone runs the game's server itself (in Python, through
  [Chaquopy](https://chaquo.com/chaquopy/)), and you play on it. Anyone on the same Wi-Fi, or on the phone's own
  hotspot, can join: from "Games on this network" in their app, or from any browser at the address the start screen
  shows (`http://<phone>:8484`). The world is kept on the phone (`world.db` in the app's files) and carries on next
  time. While it hosts, a notification says so, with a button to stop it. Stopping saves the world.
- **Games on this network.** The games answering on the Wi-Fi: phones hosting one, or a computer running the
  server (`python -m server`). Each server answers a UDP broadcast on port 8485 (`server/lan.py`). A server in
  Docker only answers with host networking.
- **Join by address.** Any other game: `192.168.1.20` (port 8484 unless you say otherwise) or
  `https://play.example.com`.

The game's page is the same everywhere, and on a phone it uses its touch layout (`web/js/mobile.js`). The Menu has
**Back to the start** to get back to the start screen (so does the phone's Back gesture).

Because the game is inside the app, every update to the game is a new app. GitHub builds one on every push to
`main`.

## Building it

GitHub builds it ("Build the Android app": Actions > the run > Artifacts > `shards-of-ashen-android`):

- `app-debug.apk`: install it on a phone to try it (allow installing from your browser or file manager; each build
  has its own debug key, so uninstall the last one first);
- `app-release.aab`: the bundle the Play Store wants, signed with your upload key.

To build it yourself, you need JDK 17, the Android SDK (platform 36), Gradle 8.11 and Python 3.11. First make
`web/assets` (`python -I tools/export_web_assets.py`), then run `gradle -p android assembleDebug`. The build packs the
game folder into the app as `game.zip` (the `packGame` task), and the phone unpacks it the first time it hosts. On
Windows, keep the folders short (AAPT2 fails on very long paths): copy `android/` somewhere short and give the game's
folder with `-PdsGame=<the game folder>`.

`dev/migrate/build_android.py` makes the icons from `web/img/icon.png`: the launcher's, the notification's, and the
Play Store's 512 px one (`android/store/icon-512.png`).

## The upload key (once)

The Play Store needs every bundle signed with the same **upload key**. Make one and keep it safe, never in the repo:

```
keytool -genkeypair -v -keystore upload.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000
```

Then on GitHub (Settings > Secrets and variables > Actions > Secrets):

| Secret | |
|---|---|
| `ANDROID_KEYSTORE` | the keystore as base64: `base64 -w0 upload.jks` (PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("upload.jks"))`) |
| `ANDROID_KEYSTORE_PASSWORD` | its password |
| `ANDROID_KEY_ALIAS` | `upload` |
| `ANDROID_KEY_PASSWORD` | the key's password (the same, unless you gave it its own) |

## No ads

The app has no ads and no ad SDK (no AdMob, no advertising ID). It used to: if the Play Console still has the AdMob
app, its ad units or a `remove_ads` product, they can go (deactivate `remove_ads`; anyone who bought it keeps the
purchase in Google Play, and now it's simply nothing). The GitHub variables `ADMOB_APP_ID`, `ADMOB_BANNER_ID`,
`ADMOB_REWARDED_ID` and `PLAY_CLOUD_PROJECT` aren't read any more and can be deleted.

## Buying (Google Play)

One one-time product, made in the Play Console (Monetize > In-app products), active with its price:

| Product id | What it is |
|---|---|
| `full_game` | The full game, $3.99: for the Hallisium account (checked by the central server) |

A different id for the full game is `DS_FULL_PRODUCT` (or `dsFullProduct`) when building, and the same on the central
server; `none` builds an app without it. Google Play restores it on a reinstall. The central server checks each
purchase with Google Play (its service account: `README-Server.md`, "Owning the game") before the account has it.

## Publishing

1. In the Play Console (a Google Play developer account, a one-off fee): Create app. Upload `app-release.aab` to a
   testing track (Internal testing is quickest), and fill in the store listing (the 512 px icon is
   `android/store/icon-512.png`), the content rating and the privacy details. Data safety: the account (a name, a
   password, an email if given) is kept on the central server; nothing is collected for ads ("Contains ads": no;
   the advertising ID: not used). The privacy policy is the central server's `/privacy`.
2. **The hosting service.** The app keeps a game running for the others while the host's phone does other things,
   which is a "special use" foreground service. The Play Console asks what it's for: *it runs a multiplayer game
   server for players on the same local network.*
3. The package name, `io.github.kriscs1.shardsofashen` (`dsPackage`), can never change once it's published.
   (It was `io.github.kriscs1.dragonsword` until the game was renamed: an app installed before that is a different
   app, and doesn't update to this one. Uninstall it.)
