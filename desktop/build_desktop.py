"""Makes the desktop app a program of its own (PyInstaller): dist/ShardsOfAshen/ShardsOfAshen(.exe), with everything it
needs beside it: the game's data, maps and pictures, the page, the server (to host a game), and the start screen.
web/assets must be made first (tools/export_web_assets.py).

  pip install -r desktop/requirements.txt
  python desktop/build_desktop.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEP = ";" if os.name == "nt" else ":"
CARRIED = ["data", "maps", "sprites", "web", "server", "dsengine", "ashen", "VERSION",
           os.path.join("saves", "TEMPLATE.ini"),
           os.path.join("android", "app", "src", "main", "python", "ds_host.py")]


def main():
    if not os.path.isdir(os.path.join(ROOT, "web", "assets")):
        sys.exit("web/assets is missing: run python -I tools/export_web_assets.py first")
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--name", "ShardsOfAshen",
            "--distpath", os.path.join(ROOT, "dist"), "--workpath", os.path.join(ROOT, "build", "desktop"),
            "--specpath", os.path.join(ROOT, "build", "desktop"),
            "--collect-all", "aiohttp", "--collect-all", "webview", "--hidden-import", "sqlite3"]
    for item in CARRIED:
        src = os.path.join(ROOT, item)
        dest = os.path.dirname(item) if os.path.isfile(src) else item
        args += ["--add-data", "%s%s%s" % (src, SEP, dest or ".")]
    icon = os.path.join(ROOT, "web", "img", "icon.ico")
    if os.path.exists(icon):
        args += ["--icon", icon]
    args.append(os.path.join(HERE, "app.py"))
    print(" ".join(args[:6]) + " ...")
    subprocess.check_call(args, cwd=ROOT)
    print("Made dist/ShardsOfAshen/")


if __name__ == "__main__":
    main()
