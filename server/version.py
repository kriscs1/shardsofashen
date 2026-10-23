"""The game's version, shown on the login screen and at /health: "<VERSION>.<build>", e.g. 1.0.23.

  * VERSION (in the game folder): the main number. Change it by hand for a big release (1.0 -> 1.1, 2.0).
  * The build: how many commits the game has had, so it goes up by itself with every Publish Update. A Docker image
    has it baked in when it's built (DS_BUILD, DS_COMMIT, DS_BUILD_DATE: GitHub's build, Test Locally.bat); run from
    the folder, it's read from git. With neither, the version says "dev"."""
import os
import subprocess


def git(root, *args):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def version_info(root):
    try:
        with open(os.path.join(root, "VERSION"), encoding="utf-8") as f:
            base = f.read().strip() or "1.0"
    except OSError:
        base = "1.0"
    build = os.environ.get("DS_BUILD", "").strip()
    commit = os.environ.get("DS_COMMIT", "").strip()
    date = os.environ.get("DS_BUILD_DATE", "").strip()
    changed = False
    if not build:
        build = git(root, "rev-list", "--count", "HEAD")
        commit = commit or git(root, "rev-parse", "--short", "HEAD")
        date = date or git(root, "log", "-1", "--format=%cs")
        changed = bool(build) and bool(git(root, "status", "--porcelain", "--untracked-files=no"))
    version = "%s.%s" % (base, build) if build else "%s-dev" % base
    if changed:
        version += "+"                          # (run from a folder with changes not yet committed)
    return {"version": version, "commit": commit[:7], "date": date}
