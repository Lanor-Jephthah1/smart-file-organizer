"""
Local "Jarvis" assistant with a desktop GUI.

Capabilities:
- GUI command console (Tkinter)
- Open project folders
- Run named routines/scripts
- Summarize log files
- Optional one-shot CLI mode
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tkinter as tk
from collections import Counter
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict


DEFAULT_CONFIG = {
    "open_mode": "explorer",
    "projects": {
        "codex": ".",
        "downloads": "~/Downloads",
        "desktop": "~/Desktop",
        "documents": "~/Documents",
        "pictures": "~/Pictures",
        "videos": "~/Videos",
        "music": "~/Music",
    },
    "routines": {
        "organize_downloads_dry_run": 'python main.py --source "%USERPROFILE%\\Downloads" --destination "%USERPROFILE%\\Downloads\\Organized" --dry-run',
        "organize_downloads": 'python main.py --source "%USERPROFILE%\\Downloads" --destination "%USERPROFILE%\\Downloads\\Organized"',
        "organize_desktop": 'python main.py --source "%USERPROFILE%\\Desktop" --destination "%USERPROFILE%\\Desktop\\Organized"',
    },
}

APP_DIR = Path(__file__).resolve().parent
HISTORY_FILE = APP_DIR / ".jarvis_history.log"


def load_config(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in config file: {path} ({exc})")

    if "projects" not in data or "routines" not in data:
        raise SystemExit("Config must contain top-level keys: 'projects' and 'routines'.")
    if "open_mode" not in data:
        data["open_mode"] = DEFAULT_CONFIG["open_mode"]

    # Auto-fill missing defaults so older config files keep improving.
    changed = False
    for key, value in DEFAULT_CONFIG["projects"].items():
        if key not in data["projects"]:
            data["projects"][key] = value
            changed = True
    for key, value in DEFAULT_CONFIG["routines"].items():
        if key not in data["routines"]:
            data["routines"][key] = value
            changed = True
    if "open_mode" not in data:
        data["open_mode"] = DEFAULT_CONFIG["open_mode"]
        changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return data


def append_history(command: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = HISTORY_FILE.read_text(encoding="utf-8") if HISTORY_FILE.exists() else ""
    HISTORY_FILE.write_text(existing + f"[{stamp}] {command}\n", encoding="utf-8")


def open_project(target: str, projects: Dict[str, str], open_mode: str = "explorer") -> str:
    if target.startswith("<") and target.endswith(">"):
        return "Usage: open <project_alias_or_path>. Example: open documents or open D:\\Work\\MyApp"

    raw_path = projects.get(target, target)
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (APP_DIR / path).resolve()
    else:
        path = path.resolve()

    if not path.exists():
        if target not in projects:
            known = ", ".join(sorted(projects))
            return f"Path not found: {path}\nTip: run 'list projects'. Known aliases: {known}"
        return f"Path not found: {path}"

    if open_mode.lower() == "vscode":
        code_check = subprocess.run(["where", "code"], capture_output=True, text=True, shell=True)
        if code_check.returncode == 0:
            subprocess.Popen(["code", str(path)], shell=True)
            return f"Opened in VS Code: {path}"

    os.startfile(str(path))  # type: ignore[attr-defined]
    return f"Opened in File Explorer: {path}"


def run_routine(name: str, routines: Dict[str, str]) -> str:
    command = routines.get(name)
    if not command:
        available = ", ".join(sorted(routines))
        return f"Unknown routine '{name}'. Available: {available}"

    completed = subprocess.run(command, shell=True, text=True, capture_output=True, cwd=str(APP_DIR))
    output = completed.stdout.strip()
    error = completed.stderr.strip()
    if completed.returncode == 0:
        return f"Routine '{name}' completed.\n{output}" if output else f"Routine '{name}' completed."
    return f"Routine '{name}' failed ({completed.returncode}).\n{error or output}"


def summarize_logs(log_path: Path, max_lines: int = 4000) -> str:
    if not log_path.exists() or not log_path.is_file():
        return f"Log file not found: {log_path}"

    raw = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    lines = raw[-max_lines:] if raw else []
    if not lines:
        return f"No content in {log_path}"

    error_count = sum(1 for line in lines if re.search(r"\berror\b|\bexception\b|\bfailed\b", line, re.IGNORECASE))
    warn_count = sum(1 for line in lines if re.search(r"\bwarn(?:ing)?\b", line, re.IGNORECASE))
    info_count = sum(1 for line in lines if re.search(r"\binfo\b", line, re.IGNORECASE))

    normalized = []
    for line in lines:
        if not re.search(r"\berror\b|\bexception\b|\bfailed\b|\bwarn(?:ing)?\b", line, re.IGNORECASE):
            continue
        cleaned = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?", "", line)
        cleaned = re.sub(r"\b\d+\b", "#", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            normalized.append(cleaned[:180])

    top_issues = Counter(normalized).most_common(5)
    header = (
        f"Log summary: {log_path}\n"
        f"- total lines scanned: {len(lines)}\n"
        f"- errors/exceptions: {error_count}\n"
        f"- warnings: {warn_count}\n"
        f"- info lines: {info_count}\n"
    )

    if not top_issues:
        return header + "- no repeating warning/error patterns detected."

    bullet_lines = "\n".join([f"  - {count}x {text}" for text, count in top_issues])
    return header + "- top repeated issue patterns:\n" + bullet_lines


def parse_and_execute(command: str, config: Dict[str, Dict[str, str]]) -> str:
    text = command.strip()
    if not text:
        return "No command provided."

    lower = text.lower()

    if lower in {"help", "commands"}:
        return (
            "Commands:\n"
            "- help\n"
            "- list routines\n"
            "- list projects\n"
            "- open <project_alias_or_path>\n"
            "- run <routine_name>\n"
            "- summarize <log_file_path>\n"
            "- history\n"
            "- exit"
        )

    if lower == "list routines":
        routines = "\n".join([f"- {name}" for name in sorted(config["routines"])])
        return f"Available routines:\n{routines}"

    if text in config["routines"]:
        return run_routine(text, config["routines"])

    if lower == "list projects":
        projects = "\n".join([f"- {name}: {path}" for name, path in sorted(config["projects"].items())])
        return f"Project aliases:\n{projects}"

    if lower == "history":
        if not HISTORY_FILE.exists():
            return "No history yet."
        last_lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-20:]
        return "Recent commands:\n" + "\n".join(last_lines)

    if lower.startswith("open "):
        target = text[5:].strip()
        return open_project(target, config["projects"], str(config.get("open_mode", "explorer")))

    if lower.startswith("run "):
        name = text[4:].strip()
        return run_routine(name, config["routines"])

    if lower.startswith("summarize "):
        path_str = text[10:].strip().strip('"')
        return summarize_logs(Path(path_str).expanduser())

    if "organize downloads" in lower:
        return run_routine("organize_downloads", config["routines"])

    if "organize desktop" in lower:
        return run_routine("organize_desktop", config["routines"])

    if lower in {"exit", "quit"}:
        return "Use the window close button to exit GUI mode."

    return "Unknown command. Type 'help' to see supported commands."


class JarvisGUI:
    def __init__(self, config: Dict[str, Dict[str, str]]) -> None:
        self.config = config
        self.root = tk.Tk()
        self.root.title("Jarvis Local Assistant")
        self.root.geometry("900x620")
        self.root.minsize(820, 540)
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(actions, text="Help", command=lambda: self.run_command("help")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(actions, text="List Routines", command=lambda: self.run_command("list routines")).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(actions, text="List Projects", command=lambda: self.run_command("list projects")).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(actions, text="Pick Log + Summarize", command=self.pick_and_summarize).pack(side=tk.LEFT, padx=6)

        quick = ttk.Frame(frame)
        quick.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(quick, text="Quick routine:").pack(side=tk.LEFT, padx=(0, 6))
        self.routine_var = tk.StringVar(value=sorted(self.config["routines"])[0] if self.config["routines"] else "")
        self.routine_menu = ttk.Combobox(
            quick, textvariable=self.routine_var, values=sorted(self.config["routines"]), state="readonly", width=36
        )
        self.routine_menu.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(quick, text="Run", command=self.run_selected_routine).pack(side=tk.LEFT)

        cmd_row = ttk.Frame(frame)
        cmd_row.pack(fill=tk.X, pady=(0, 8))
        self.command_var = tk.StringVar()
        entry = ttk.Entry(cmd_row, textvariable=self.command_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        entry.bind("<Return>", lambda _e: self.submit())
        ttk.Button(cmd_row, text="Execute", command=self.submit).pack(side=tk.LEFT)

        self.output = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10), state=tk.DISABLED)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.write("Jarvis GUI ready. Type 'help' or use the quick buttons above.")

    def write(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        stamp = datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{stamp}] {text}\n\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def run_command(self, command: str) -> None:
        append_history(command)
        result = parse_and_execute(command, self.config)
        self.write(f"> {command}\n{result}")

    def submit(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            return
        self.command_var.set("")
        self.run_command(command)

    def run_selected_routine(self) -> None:
        name = self.routine_var.get().strip()
        if not name:
            messagebox.showinfo("Jarvis", "No routine selected.")
            return
        self.run_command(name)

    def pick_and_summarize(self) -> None:
        file_path = filedialog.askopenfilename(title="Select a log/text file to summarize")
        if not file_path:
            return
        self.run_command(f'summarize "{file_path}"')

    def run(self) -> None:
        self.root.mainloop()


def run_once(config: Dict[str, Dict[str, str]], command: str) -> int:
    append_history(command)
    print(parse_and_execute(command, config))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local laptop automation assistant.")
    parser.add_argument("--config", type=Path, default=APP_DIR / "jarvis_config.json", help="Config JSON file.")
    parser.add_argument("--once", type=str, default="", help="Run one command and exit.")
    parser.add_argument("--cli", action="store_true", help="Use text CLI mode instead of GUI.")
    return parser.parse_args()


def cli_loop(config: Dict[str, Dict[str, str]]) -> None:
    print("Jarvis CLI ready. Type 'help' for commands. Ctrl+C to exit.")
    while True:
        try:
            command = input("jarvis> ")
            append_history(command)
            print(parse_and_execute(command, config))
        except KeyboardInterrupt:
            print("\nJarvis shutting down.")
            break


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    if args.once:
        raise SystemExit(run_once(config, args.once))

    if args.cli:
        cli_loop(config)
        return

    JarvisGUI(config).run()


if __name__ == "__main__":
    main()
