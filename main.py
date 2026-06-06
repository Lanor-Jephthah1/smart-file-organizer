"""
Smart file organizer for Windows folders (e.g., Downloads/Desktop).

Features:
- Sort files by type and month
- Optional watch mode for continuous organization
- Duplicate detection by SHA-256 hash
- Dry-run support
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple


EXTENSION_MAP = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"},
    "videos": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "documents": {".pdf", ".txt", ".rtf", ".md"},
    "spreadsheets": {".csv", ".xls", ".xlsx", ".ods"},
    "presentations": {".ppt", ".pptx", ".key", ".odp"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "code": {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".html",
        ".css",
        ".java",
        ".c",
        ".cpp",
        ".go",
        ".rs",
        ".php",
        ".json",
        ".yaml",
        ".yml",
        ".sql",
    },
    "executables": {".exe", ".msi", ".bat", ".cmd", ".ps1"},
}

IGNORED_DIRS = {"$recycle.bin", "system volume information", ".git", "__pycache__"}
INDEX_FILENAME = ".organizer_index.json"


@dataclass
class Config:
    source: Path
    destination: Path
    dry_run: bool
    recursive: bool
    keep_empty: bool
    sort_mode: str


def classify_file(path: Path) -> str:
    ext = path.suffix.lower()
    for category, exts in EXTENSION_MAP.items():
        if ext in exts:
            return category
    return "other"


def month_bucket(path: Path) -> str:
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return modified.strftime("%Y-%m")


def source_bucket(path: Path) -> str:
    """Best-effort source/workflow classifier based on path and filename patterns."""
    name = path.name.lower()
    parent = str(path.parent).lower()
    ext = path.suffix.lower()

    if "whatsapp" in name or "whatsapp" in parent:
        return "whatsapp"
    if "telegram" in name or "telegram" in parent:
        return "telegram"
    if "discord" in name or "discord" in parent:
        return "discord"
    if "slack" in name or "slack" in parent:
        return "slack"

    if name.startswith("screenshot") or "screen shot" in name or name.startswith("snip"):
        return "screenshots"
    if name.startswith("img_") or name.startswith("dsc_") or name.startswith("pxl_"):
        return "camera_exports"

    if "chrome" in name or "edge" in name or "firefox" in name:
        return "browser_downloads"
    if ext in {".crdownload", ".part"}:
        return "browser_partial_downloads"

    if "zoom" in name or "meeting" in name or "teams" in name:
        return "meetings"

    if ext in {".torrent"}:
        return "torrent"

    return "manual_or_unknown"


def sha256sum(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(target: Path) -> Path:
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def load_index(index_path: Path) -> Dict[str, str]:
    if not index_path.exists():
        return {}
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_index(index_path: Path, index: Dict[str, str], dry_run: bool) -> None:
    if dry_run:
        return
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def should_ignore(path: Path, destination: Path) -> bool:
    if not path.is_file():
        return True
    if any(part.lower() in IGNORED_DIRS for part in path.parts):
        return True
    if path.name == INDEX_FILENAME:
        return True
    # Skip files already in destination tree.
    try:
        path.resolve().relative_to(destination.resolve())
        return True
    except ValueError:
        return False


def list_candidate_files(source: Path, destination: Path, recursive: bool) -> Iterable[Path]:
    iterator = source.rglob("*") if recursive else source.glob("*")
    for path in iterator:
        if should_ignore(path, destination):
            continue
        yield path


def move_file(src: Path, dst: Path, dry_run: bool) -> Path:
    dst = safe_name(dst)
    if dry_run:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.move(str(src), str(dst)))


def organize_file(path: Path, config: Config, index: Dict[str, str]) -> Tuple[str, str]:
    category = classify_file(path)
    if config.sort_mode == "source":
        bucket = source_bucket(path)
    else:
        bucket = month_bucket(path)
    base_target = config.destination / category / bucket / path.name

    digest = sha256sum(path)
    known_path_str = index.get(digest)
    known_path = Path(known_path_str) if known_path_str else None

    if known_path and known_path.exists() and known_path.resolve() != path.resolve():
        duplicate_target = config.destination / "duplicates" / bucket / path.name
        final_path = move_file(path, duplicate_target, config.dry_run)
        return ("duplicate", str(final_path))

    final_path = move_file(path, base_target, config.dry_run)
    index[digest] = str(final_path)
    return ("moved", str(final_path))


def prune_empty_dirs(root: Path, keep_empty: bool) -> None:
    if keep_empty:
        return
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def organize_pass(config: Config) -> Tuple[int, int]:
    config.destination.mkdir(parents=True, exist_ok=True)
    index_path = config.destination / INDEX_FILENAME
    index = load_index(index_path)

    moved = 0
    duplicates = 0
    files = list(list_candidate_files(config.source, config.destination, config.recursive))
    for file_path in files:
        try:
            status, target = organize_file(file_path, config, index)
            if status == "duplicate":
                duplicates += 1
                print(f"[DUPLICATE] {file_path} -> {target}")
            else:
                moved += 1
                print(f"[MOVED] {file_path} -> {target}")
        except Exception as exc:  # pragma: no cover
            print(f"[ERROR] {file_path} ({exc})")

    save_index(index_path, index, config.dry_run)
    prune_empty_dirs(config.source, config.keep_empty)
    return moved, duplicates


def watch_loop(config: Config, interval: int) -> None:
    print(f"Watching '{config.source}' every {interval}s. Press Ctrl+C to stop.")
    while True:
        moved, duplicates = organize_pass(config)
        if moved or duplicates:
            print(f"Cycle complete: moved={moved}, duplicates={duplicates}")
        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    default_source = Path.home() / "Downloads"
    default_destination = default_source / "Organized"

    parser = argparse.ArgumentParser(description="Smart file organizer with duplicate detection.")
    parser.add_argument("--source", type=Path, default=default_source, help="Folder to scan.")
    parser.add_argument("--destination", type=Path, default=default_destination, help="Folder for organized files.")
    parser.add_argument("--watch", action="store_true", help="Run continuously.")
    parser.add_argument("--interval", type=int, default=15, help="Watch interval in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without moving files.")
    parser.add_argument("--non-recursive", action="store_true", help="Only process top-level files.")
    parser.add_argument("--keep-empty", action="store_true", help="Do not remove empty folders from source.")
    parser.add_argument(
        "--sort-mode",
        choices=("date", "source"),
        default="date",
        help="Sort by month bucket ('date') or source/workflow bucket ('source').",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config(
        source=args.source.expanduser().resolve(),
        destination=args.destination.expanduser().resolve(),
        dry_run=args.dry_run,
        recursive=not args.non_recursive,
        keep_empty=args.keep_empty,
        sort_mode=args.sort_mode,
    )

    if not config.source.exists() or not config.source.is_dir():
        raise SystemExit(f"Source folder does not exist or is not a directory: {config.source}")

    if config.source == config.destination:
        raise SystemExit("Source and destination cannot be the same folder.")

    if args.watch:
        watch_loop(config, max(1, args.interval))
        return

    moved, duplicates = organize_pass(config)
    print(f"Done. moved={moved}, duplicates={duplicates}, dry_run={config.dry_run}")


if __name__ == "__main__":
    main()
