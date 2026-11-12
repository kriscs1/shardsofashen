"""The owner's music made small enough for a phone and the page: dev\\Music\\<name>.mp3 (royalty free, kept out of git:
about 60 MB) -> sounds\\music\\<name>.mp3, mono at 64 kbit/s, at most three minutes (a longer track fades out there and
starts again: a loop rather than a long track), each brought to the same loudness. About 1.4 MB a track.

Run:  python -I "dev\\migrate\\shrink_music.py"      (needs ffmpeg; safe to run again: a track is made again only when
its original is newer. The first run moves the originals out of sounds\\music into dev\\Music.)

Which track plays where: data\\Music.ini (build_music.py).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORIGINALS = os.path.join(ROOT, "dev", "Music")
OUT = os.path.join(ROOT, "sounds", "music")
LONGEST = 180            # seconds
FADE = 5
BITRATE = "64k"
BIG = 100_000            # (bits a second: more than this in sounds\music is an original, not one made here)


def probe(ffprobe, path, what):
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=" + what, "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip() or 0)
    except ValueError:
        return 0.0


def main():
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        sys.exit("needs ffmpeg and ffprobe on the PATH")
    os.makedirs(ORIGINALS, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for f in sorted(os.listdir(OUT)):          # (the first run: the originals moved out of the way, kept)
        path = os.path.join(OUT, f)
        if f.lower().endswith(".mp3") and probe(ffprobe, path, "bit_rate") > BIG:
            dst = os.path.join(ORIGINALS, f)
            if os.path.exists(dst):
                os.remove(path)
            else:
                shutil.move(path, dst)
            print("kept the original in dev\\Music: %s" % f)
    made = 0
    for f in sorted(os.listdir(ORIGINALS)):
        if not f.lower().endswith(".mp3"):
            continue
        src, dst = os.path.join(ORIGINALS, f), os.path.join(OUT, f.lower())
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        secs = probe(ffprobe, src, "duration")
        filters = ["loudnorm=I=-18:TP=-2:LRA=11"]
        if secs > LONGEST:
            filters.insert(0, "afade=t=out:st=%d:d=%d" % (LONGEST - FADE, FADE))
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", src, "-t", str(min(secs, LONGEST)) if secs else str(LONGEST),
                        "-af", ",".join(filters), "-ac", "1", "-ar", "44100", "-b:a", BITRATE, "-map_metadata", "-1",
                        "-fflags", "+bitexact", "-flags:a", "+bitexact", dst], check=True)
        made += 1
        print("  %s: %.0f s -> %.0f s, %.1f MB -> %.1f MB" % (f, secs, min(secs, LONGEST),
                                                         os.path.getsize(src) / 1e6, os.path.getsize(dst) / 1e6))
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.lower().endswith(".mp3"))
    print("music: %d made, %.1f MB in sounds\\music" % (made, total / 1e6))


if __name__ == "__main__":
    main()
