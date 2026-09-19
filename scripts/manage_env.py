#!/usr/bin/env python3
"""
manage_env.py

Creates and edits the .env file consumed by migrate_android_studio.py.
Comments and unrelated lines in an existing .env are preserved; only the
known SOURCE_*/DEST_*/LOG_FILE keys are added or updated.

Usage:
  python scripts/manage_env.py init [--force]
  python scripts/manage_env.py set KEY VALUE
  python scripts/manage_env.py get KEY
  python scripts/manage_env.py list
  python scripts/manage_env.py edit
"""

import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = SCRIPT_DIR.parent
ENV_FILE: Path = REPO_ROOT / ".env"
TEMPLATE_FILE: Path = REPO_ROOT / ".env.example"

KNOWN_KEYS: list[str] = [
    "SOURCE_AVD_DIR",
    "DEST_AVD_DIR",
    "SOURCE_PROJECTS_DIR",
    "DEST_PROJECTS_DIR",
    "LOG_FILE",
]

KEY_PROMPTS: dict[str, str] = {
    "SOURCE_AVD_DIR": "Source AVD directory (e.g. C:\\Users\\YourName\\.android\\avd)",
    "DEST_AVD_DIR": "Destination AVD directory (e.g. D:\\YourName\\.android\\avd)",
    "SOURCE_PROJECTS_DIR": "Source AndroidStudioProjects directory",
    "DEST_PROJECTS_DIR": "Destination AndroidStudioProjects directory",
    "LOG_FILE": "Log file path (optional, leave blank for default)",
}


def read_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def parse_env_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped: str = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def set_env_line_value(lines: list[str], key: str, value: str) -> list[str]:
    """Return lines with `key` set to `value`, updating in place or appending."""
    updated: list[str] = []
    found: bool = False
    for line in lines:
        stripped: str = line.strip()
        if not found and "=" in stripped and not stripped.startswith("#"):
            existing_key, _, _ = stripped.partition("=")
            if existing_key.strip() == key:
                updated.append(f"{key}={value}")
                found = True
                continue
        updated.append(line)
    if not found:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(f"{key}={value}")
    return updated


def write_env_lines(lines: list[str]) -> None:
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    if ENV_FILE.exists() and not args.force:
        print(f"ERROR: {ENV_FILE} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1
    if not TEMPLATE_FILE.exists():
        print(f"ERROR: Template file not found: {TEMPLATE_FILE}", file=sys.stderr)
        return 1
    shutil.copy2(TEMPLATE_FILE, ENV_FILE)
    print(f"Created {ENV_FILE} from {TEMPLATE_FILE.name}.")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    if args.key not in KNOWN_KEYS:
        print(
            f"WARNING: '{args.key}' is not a recognized key ({', '.join(KNOWN_KEYS)}).",
            file=sys.stderr,
        )
    lines: list[str] = set_env_line_value(read_env_lines(ENV_FILE), args.key, args.value)
    write_env_lines(lines)
    print(f"Set {args.key} in {ENV_FILE}.")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    values: dict[str, str] = parse_env_values(read_env_lines(ENV_FILE))
    if args.key not in values:
        print(f"ERROR: '{args.key}' is not set in {ENV_FILE}.", file=sys.stderr)
        return 1
    print(values[args.key])
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    values: dict[str, str] = parse_env_values(read_env_lines(ENV_FILE))
    if not values:
        print(f"No values set in {ENV_FILE}.")
        return 0
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    if not ENV_FILE.exists():
        if TEMPLATE_FILE.exists():
            shutil.copy2(TEMPLATE_FILE, ENV_FILE)
            print(f"Created {ENV_FILE} from {TEMPLATE_FILE.name}.")
        else:
            ENV_FILE.write_text("", encoding="utf-8")

    lines: list[str] = read_env_lines(ENV_FILE)
    values: dict[str, str] = parse_env_values(lines)

    for key in KNOWN_KEYS:
        current: str = values.get(key, "")
        prompt_label: str = KEY_PROMPTS.get(key, key)
        suffix: str = f" [{current}]" if current else ""
        response: str = input(f"{prompt_label}{suffix}: ").strip()
        if response:
            lines = set_env_line_value(lines, key, response)
        elif current:
            lines = set_env_line_value(lines, key, current)

    write_env_lines(lines)
    print(f"\nSaved {ENV_FILE}.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and edit the project's .env file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create .env from .env.example")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing .env file")
    init_parser.set_defaults(func=cmd_init)

    set_parser = subparsers.add_parser("set", help="Set a single key's value")
    set_parser.add_argument("key")
    set_parser.add_argument("value")
    set_parser.set_defaults(func=cmd_set)

    get_parser = subparsers.add_parser("get", help="Print a single key's value")
    get_parser.add_argument("key")
    get_parser.set_defaults(func=cmd_get)

    list_parser = subparsers.add_parser("list", help="Print all key=value pairs")
    list_parser.set_defaults(func=cmd_list)

    edit_parser = subparsers.add_parser("edit", help="Interactively edit all known keys")
    edit_parser.set_defaults(func=cmd_edit)

    return parser.parse_args()


def main() -> int:
    args: argparse.Namespace = parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
