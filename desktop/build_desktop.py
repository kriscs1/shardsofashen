"""Makes the desktop app a program of its own (PyInstaller): dist/ShardsOfAshen/ShardsOfAshen(.exe), with everything it
needs beside it: the game's data, maps and pictures, the page, the server (to host a game), and the start screen.
web/assets must be made first (tools/export_web_assets.py).

  pip install -r desktop/requirements.txt
  python desktop/build_desktop.py

The store it's for (desktop/owning.py): DS_STORE=steam (with DS_STEAM_APP, the app's id, and DS_STEAM_SDK, the
Steamworks SDK's folder: its steam_api64.dll goes with it), itch or epic. Without DS_STORE it's a build of your own,
owned.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEP = ";" if os.name == "nt" else ":"
CARRIED = ["data", "maps", "sprites", "web", "server", "dsengine", "ashen", "VERSION",
           os.path.join("android", "app", "src", "main", "python", "ds_host.py")]


def main():
    if not os.path.isdir(os.path.join(ROOT, "web", "assets")):
        sys.exit("web/assets is missing: run python -I tools/export_web_assets.py first")
    work = os.path.join(tempfile.gettempdir(), "ShardsOfAshen-build")   # (its half-made exe can't run: kept out of sight)
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--name", "ShardsOfAshen",
            "--distpath", os.path.join(ROOT, "dist"), "--workpath", work, "--specpath", work,
            "--collect-all", "aiohttp", "--collect-all", "webview", "--hidden-import", "sqlite3"]
    for item in CARRIED:
        src = os.path.join(ROOT, item)
        dest = os.path.dirname(item) if os.path.isfile(src) else item
        args += ["--add-data", "%s%s%s" % (src, SEP, dest or ".")]
    store = os.environ.get("DS_STORE", "").strip().lower()
    if store not in ("", "steam", "itch", "epic"):
        sys.exit("DS_STORE is steam, itch or epic")
    told = {"store": store}
    if store == "steam":
        told["steam_app"] = os.environ.get("DS_STEAM_APP", "").strip()
        lib = os.path.join(os.environ.get("DS_STEAM_SDK", ""), "redistributable_bin", "win64", "steam_api64.dll")
        if not told["steam_app"].isdigit() or not os.path.exists(lib):
            sys.exit("The Steam build needs DS_STEAM_APP (its id) and DS_STEAM_SDK (the Steamworks SDK's folder)")
        args += ["--add-binary", "%s%s." % (lib, SEP)]
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, "store.json"), "w", encoding="utf-8") as f:
        json.dump(told, f)
    args += ["--add-data", "%s%s." % (os.path.join(work, "store.json"), SEP)]
    icon = os.path.join(ROOT, "web", "img", "icon.ico")
    if os.path.exists(icon):
        args += ["--icon", icon]
    args.append(os.path.join(HERE, "app.py"))
    print(" ".join(args[:6]) + " ...")
    subprocess.check_call(args, cwd=ROOT)
    print("Made dist/ShardsOfAshen/" + (" for " + store if store else ""))


if __name__ == "__main__":
    main()
