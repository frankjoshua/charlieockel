#!/usr/bin/env python3
"""Build web media and the photo gallery page from originals/.

- Photos -> public/img/full/<slug>.jpg (max 2000px) and public/img/thumb/<slug>.jpg (max 640px),
  auto-rotated with metadata (including GPS) stripped.
- Videos -> public/video/<slug>.mp4 (H.264, max 1280px wide) plus a poster frame.
- gallery.template.html -> public/images.html, with {{ITEMS}} replaced by every item,
  oldest first (EXIF date, else a date in the filename, else filename order).

Outputs are skipped when newer than their source. Requires ImageMagick, ffmpeg and exiftool.
Runs automatically before `firebase deploy` (see firebase.json predeploy).
"""

import json
import re
import subprocess
from pathlib import Path

PET_NAME = "Charlie"
ROOT = Path(__file__).resolve().parent
ORIGINALS = ROOT / "originals"
PUBLIC = ROOT / "public"
PHOTO_EXT = {".jpg", ".jpeg", ".png"}
VIDEO_EXT = {".mov", ".mp4", ".3gp", ".avi"}
FILENAME_DATE = re.compile(r"(20\d\d)[-_]?(\d\d)[-_]?(\d\d)")


def slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


def stale(src: Path, out: Path) -> bool:
    return not out.exists() or out.stat().st_mtime < src.stat().st_mtime


def run(*args: str) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def resize(src: Path, out: Path, size: int, quality: int) -> None:
    if not stale(src, out):
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    run("convert", f"{src}[0]", "-auto-orient", "-strip", "-resize", f"{size}x{size}>",
        "-sampling-factor", "4:2:0", "-interlace", "JPEG", "-quality", str(quality), str(out))


def transcode(src: Path, out: Path, poster: Path) -> None:
    if stale(src, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        run("ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
            "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-crf", "26", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            "-map_metadata", "-1", str(out))
    if stale(src, poster):
        run("ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(out),
            "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2", "-q:v", "4", str(poster))


def capture_dates(files: list[Path]) -> dict[str, str]:
    """Map filename -> 'YYYY:MM:DD HH:MM:SS' from EXIF/QuickTime metadata, when present."""
    result = subprocess.run(
        ["exiftool", "-json", "-q", "-DateTimeOriginal", "-CreateDate", *map(str, files)],
        check=False, capture_output=True, text=True)
    dates = {}
    for entry in json.loads(result.stdout or "[]"):
        value = str(entry.get("DateTimeOriginal") or entry.get("CreateDate") or "")
        if value[:4].isdigit() and not value.startswith("0000"):
            dates[Path(entry["SourceFile"]).name] = value
    return dates


def sort_key(path: Path, dates: dict[str, str]) -> tuple:
    if path.name in dates:
        return (0, dates[path.name], path.name.lower())
    if match := FILENAME_DATE.search(path.name):
        return (0, ":".join(match.groups()), path.name.lower())
    return (1, "", path.name.lower())


def main() -> None:
    files = sorted(p for p in ORIGINALS.iterdir() if p.suffix.lower() in PHOTO_EXT | VIDEO_EXT)
    slugs = [slug(p) for p in files]
    duplicates = {s for s in slugs if slugs.count(s) > 1}
    if duplicates:
        raise SystemExit(f"originals/ has files that map to the same name: {sorted(duplicates)}")

    items = []
    dates = capture_dates(files)
    for src in sorted(files, key=lambda p: sort_key(p, dates)):
        name = slug(src)
        if src.suffix.lower() in VIDEO_EXT:
            video = PUBLIC / "video" / f"{name}.mp4"
            poster = PUBLIC / "video" / f"{name}.jpg"
            transcode(src, video, poster)
            items.append(
                f'<li class="wide"><video controls preload="none" poster="video/{name}.jpg">'
                f'<source src="video/{name}.mp4" type="video/mp4"></video></li>')
        else:
            resize(src, PUBLIC / "img" / "full" / f"{name}.jpg", 2000, 82)
            resize(src, PUBLIC / "img" / "thumb" / f"{name}.jpg", 640, 78)
            items.append(
                f'<li><a href="img/full/{name}.jpg" data-full>'
                f'<img src="img/thumb/{name}.jpg" alt="{PET_NAME}, photo {len(items) + 1}" loading="lazy"></a></li>')

    template = (ROOT / "gallery.template.html").read_text()
    (PUBLIC / "images.html").write_text(template.replace("{{ITEMS}}", "\n        ".join(items)))
    print(f"Built {len(items)} gallery items")


if __name__ == "__main__":
    main()
