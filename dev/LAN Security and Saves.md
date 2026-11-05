# LAN games: sign-in, security and where saves live

(Checked against `server/game.py` authenticate / devices_welcome / ticket_name / choose, `README-Server.md` "Who's who",
`android/.../HostService.java` and `desktop/app.py`.)

## Sign-in on a LAN game

A game opened to your network (Options) needs no login. It is the host's own single-player world, shared with the
network. A joiner needs no Shards account.

A joiner is identified one of two ways:
- **Signed in:** the start screen gets a ticket from the central server, and the game checks it (`ticket_name`).
  Their characters are owned by `a:AccountName`.
- **No account:** the start screen gives each game a random device key (16+ characters). Characters are owned by
  `d:<key>`. Device keys are accepted only from a loopback or private-network address (`devices_welcome`); a remote or
  cloud server refuses them and wants an account.

## Can users log in as each other?

Not through the game, and not casually.
- Characters have no passwords. Each belongs to an owner (account or device key), and `choose()` refuses any
  character whose owner isn't you ("That isn't one of your characters here."). Names are unique per server.
- An account's characters need a central-server ticket made out to that game's id, so someone else on the LAN can't
  claim them.
- A device key is a secret held by that browser or app. Someone who copied it (e.g. from the browser's local storage)
  could play as that device. It is a convenience identity, not strong security; nobody can guess one.
- The host's key (`DS_HOST_KEY`) is accepted only from the host's machine, and makes the host an admin. The host can
  see and use everything in the world.
- Anyone on the LAN can join and make their own characters (up to `MOST_CHARACTERS`). That is intended: only people
  you let onto your Wi-Fi can reach the game.

## Where saves are

On the **host's device only**, in the single-player game's database:
- Android: `solo.db` in the app's private files folder (`getFilesDir()`).
- Desktop app: `solo.db` in the app's data directory (`data_dir()`).

Joiners' characters and progress live in that same file, in the host's world, not on the joiner's device. If the host
uninstalls the app or clears its data, everyone's characters are gone. The central server only gets a progress summary
(level, skills, quest stages, gold, map), never the full save.
