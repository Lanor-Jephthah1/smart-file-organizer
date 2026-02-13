# Smart File Organizer

Automate file organization for folders like `Downloads` and `Desktop`.

This script sorts files by:
- Category (`images`, `videos`, `documents`, `code`, etc.)
- Month bucket (`YYYY-MM`)

It also detects duplicates using SHA-256 hashes and moves duplicates into a dedicated `duplicates` folder.

## Features

- One-time organization pass
- Continuous watch mode
- Duplicate detection by content hash
- Safe filename collision handling (`name (1).ext`)
- Dry-run preview mode

## Requirements

- Python 3.9+
- Standard library only (no extra dependencies)

## Usage

### 1. One-time run (Downloads)

```powershell
python main.py --source "$HOME\Downloads" --destination "$HOME\Downloads\Organized"
```

### 2. Watch mode (every 20 seconds)

```powershell
python main.py --source "$HOME\Downloads" --destination "$HOME\Downloads\Organized" --watch --interval 20
```

### 3. Dry run (no file moves)

```powershell
python main.py --source "$HOME\Downloads" --destination "$HOME\Downloads\Organized" --dry-run
```

### 4. Desktop example

```powershell
python main.py --source "$HOME\Desktop" --destination "$HOME\Desktop\Organized" --watch --interval 20
```

## Notes

- The script stores a hash index at `<destination>/.organizer_index.json`.
- Use `Ctrl+C` to stop watch mode.
- Use `--non-recursive` to process only top-level files.
