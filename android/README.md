# Dragon Sword for Android

The app is a **Trusted Web Activity**: it opens the game's own web page (`https://<your server>/?app=android`) in
Chrome, full screen and sideways, with nothing of the browser showing. There's no game inside the app, so:

- **every update to the server is an update to the app**: the maps, quests, pictures, sounds and the client's code
  all come from the server, the same as in a browser;
- a new app only needs publishing when something in `android/` changes (its icon, its name, the address).

On a phone or tablet the page uses its touch layout (`web/js/mobile.js`). Tap to do the first thing (walk, talk,
attack), hold for everything you can do, use the stick bottom left to walk. The Bag, Chat, Journal and Menu buttons
are down the right, and tapping the minimap opens the world map. Any phone browser gets the same layout (or add
`?touch=1` to the address on a computer to try it; `?touch=0` turns it off again).

## What it needs

1. **The server on a public HTTPS address** (the Play Store won't take an app that opens a plain `http://` page, and
   phones away from home can't reach `http://<your Unraid server>:8484`). The Caddy setup in `deploy/` does this
   (`DS_DOMAIN`), or any HTTPS reverse proxy in front of the Unraid container (Nginx Proxy Manager, a Cloudflare
   Tunnel...).
2. **That address in the app.** Set `dsHost` in `android/gradle.properties`, or on GitHub: Settings > Secrets and
   variables > Actions > Variables > `DS_APP_HOST`.
3. **A Google Play developer account** (a one-off fee) at https://play.google.com/console.

## Building it

GitHub builds it on every push that changes `android/` (the "Build the Android app" workflow; Actions > the run >
Artifacts > `dragonsword-android`):

- `app-debug.apk`: install it on your own phone to try it (allow installing from your browser or file manager; each
  build has its own debug key, so uninstall the last one first);
- `app-release.aab`: the bundle the Play Store wants, signed with your upload key.

To build it yourself: JDK 17, the Android SDK (platform 36) and Gradle 8.11, then `gradle -p android assembleDebug
bundleRelease`. On Windows keep the folders short (AAPT2 fails on very long paths).

`dev/migrate/build_android.py` makes the icons and the splash from `web/img/icon.png`, and the Play Store's 512 px icon
(`android/store/icon-512.png`).

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

## Publishing

1. In the Play Console: Create app, then upload `app-release.aab` to a testing track (Internal testing is quickest),
   and fill in the store listing (the 512 px icon is `android/store/icon-512.png`), the content rating and the
   privacy details.
2. **Let the app go full screen.** Until the site says the app is its own, the app shows a thin browser bar along the
   top. Play Console > Test and release > App integrity > App signing: copy the **SHA-256 fingerprints** of the app
   signing key and of the upload key. Put them in the server's `DS_ANDROID_CERTS` setting, comma-separated (the
   Unraid template's "Android app keys", or `deploy/.env`), and restart it. The server then answers
   `https://<your server>/.well-known/assetlinks.json` with them. To try the debug APK without the bar, add its key's
   fingerprint too: `keytool -list -v -keystore ~/.android/debug.keystore -storepass android`.
3. The package name, `io.github.kriscs1.dragonsword` (`dsPackage`), can never change once it's published.
