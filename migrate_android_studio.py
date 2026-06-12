#!/usr/bin/env python3
"""
migrate_android_studio.py

Migrates Android Studio AVD device images and (optionally) the AndroidStudioProjects
directory from one location to another (configured via .env).

Actions performed:
  1. Copies SOURCE_AVD_DIR  -> DEST_AVD_DIR
  2. Patches all absolute paths inside AVD config files to reflect the new location
  3. Sets the ANDROID_AVD_HOME user environment variable so Android Studio picks up
     the new location automatically (no manual IDE config needed)
  4. Optionally moves SOURCE_PROJECTS_DIR -> DEST_PROJECTS_DIR

Usage:
  python migrate_android_studio.py [--dry-run] [--skip-projects] [--no-delete-originals]
                                   [--source-avd-dir PATH] [--dest-avd-dir PATH]
                                   [--source-projects-dir PATH] [--dest-projects-dir PATH]

Flags:
  --dry-run             Print what would happen without making any changes
  --skip-projects       Skip moving the AndroidStudioProjects directory
  --no-delete-originals Keep the original files after a successful copy
  --source-avd-dir      Override SOURCE_AVD_DIR from .env
  --dest-avd-dir        Override DEST_AVD_DIR from .env
  --source-projects-dir Override SOURCE_PROJECTS_DIR from .env
  --dest-projects-dir   Override DEST_PROJECTS_DIR from .env
"""

import argparse
import os
import shutil
import sys
import winreg
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_log_file = None  # open file handle, set by main() before any logging

# Config files inside each *.avd directory that may contain absolute paths
AVD_CONFIG_FILES: list[str] = [
    "config.ini",
    "hardware-qemu.ini",
    "emu-launch-params.txt",
    os.path.join("snapshots", "default_boot", "hardware.ini"),
]

# The environment variable Android Studio honours for a custom AVD location
ANDROID_AVD_HOME_VAR: str = "ANDROID_AVD_HOME"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(message: str, dry_run: bool = False) -> None:
    prefix: str = "[DRY-RUN] " if dry_run else ""
    ts: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for line in message.splitlines():
        formatted = f"{ts} {prefix}{line}" if line.strip() else ""
        print(formatted)
        if _log_file is not None:
            print(formatted, file=_log_file, flush=True)


def ensure_parent_exists(path: Path, dry_run: bool) -> None:
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dest: Path, dry_run: bool) -> None:
    """Recursively copy src -> dest, skipping files that already exist at dest."""
    if not src.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src}")

    log(f"Copying directory tree:\n  {src}\n  -> {dest}", dry_run)

    if dry_run:
        total_files: int = sum(1 for _ in src.rglob("*") if _.is_file())
        log(f"  Would copy {total_files} file(s).", dry_run)
        return

    dest.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        relative: Path = item.relative_to(src)
        target: Path = dest / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def delete_tree(path: Path, dry_run: bool) -> None:
    log(f"Deleting original: {path}", dry_run)
    if not dry_run:
        shutil.rmtree(path)


# ---------------------------------------------------------------------------
# Path-patching inside AVD config files
# ---------------------------------------------------------------------------

def patch_avd_config_files(
    avd_dir: Path,
    old_base: Path,
    new_base: Path,
    dry_run: bool,
) -> None:
    """
    Replace all occurrences of old_base path strings in AVD config files with new_base.
    Both forward-slash and back-slash variants are handled.
    """
    avd_subdirs: list[Path] = [d for d in avd_dir.iterdir() if d.is_dir() and d.suffix == ".avd"]

    if not avd_subdirs:
        log("  No *.avd subdirectories found — nothing to patch.", dry_run)
        return

    # Build replacement pairs for both slash styles
    old_str_back: str = str(old_base)
    new_str_back: str = str(new_base)
    old_str_fwd: str = old_str_back.replace("\\", "/")
    new_str_fwd: str = new_str_back.replace("\\", "/")

    for avd_subdir in avd_subdirs:
        log(f"  Patching config files in: {avd_subdir.name}", dry_run)
        for relative_cfg in AVD_CONFIG_FILES:
            cfg_path: Path = avd_subdir / relative_cfg
            if not cfg_path.exists():
                continue

            original_text: str = cfg_path.read_text(encoding="utf-8", errors="replace")
            patched_text: str = (
                original_text
                .replace(old_str_back, new_str_back)
                .replace(old_str_fwd, new_str_fwd)
            )

            if patched_text == original_text:
                log(f"    {relative_cfg}: no changes needed", dry_run)
                continue

            changed_lines: int = sum(
                1
                for a, b in zip(original_text.splitlines(), patched_text.splitlines())
                if a != b
            )
            log(f"    {relative_cfg}: patching ~{changed_lines} line(s)", dry_run)

            if not dry_run:
                cfg_path.write_text(patched_text, encoding="utf-8")

    # Also patch the top-level *.ini files (one per AVD, lives in avd_dir itself)
    for ini_file in avd_dir.glob("*.ini"):
        original_text = ini_file.read_text(encoding="utf-8", errors="replace")
        patched_text = (
            original_text
            .replace(old_str_back, new_str_back)
            .replace(old_str_fwd, new_str_fwd)
        )
        if patched_text != original_text:
            log(f"  Patching top-level INI: {ini_file.name}", dry_run)
            if not dry_run:
                ini_file.write_text(patched_text, encoding="utf-8")
        else:
            log(f"  {ini_file.name}: no changes needed", dry_run)


# ---------------------------------------------------------------------------
# Windows environment variable (user-level, persistent)
# ---------------------------------------------------------------------------

def set_user_env_var(name: str, value: str, dry_run: bool) -> None:
    """
    Write a persistent user-level environment variable via the Windows registry.
    Does NOT affect the current process environment (a new shell is required).
    """
    log(f"Setting user environment variable: {name} = {value}", dry_run)
    if dry_run:
        return

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)
        log(
            f"  SUCCESS — restart Android Studio (or open a new terminal) "
            "for the change to take effect."
        )
    except OSError as exc:
        log(
            f"  ERROR: Could not write registry key for {name}: {exc}\n"
            "  You can set it manually via:\n"
            f"    setx {name} \"{value}\""
        )


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

def migrate_avd(src: Path, dest: Path, delete_originals: bool, dry_run: bool) -> bool:
    """Copy AVDs to dest, patch configs, set env var. Returns True on success."""
    log("\n=== Step 1: Migrate AVD directory ===")

    if not src.exists():
        log(f"ERROR: Source AVD directory not found: {src}")
        return False

    # 1a. Copy the whole avd directory tree
    try:
        copy_tree(src, dest, dry_run)
    except Exception as exc:
        log(f"ERROR during copy: {exc}")
        return False

    # 1b. Patch paths inside config files
    log("\n--- Patching absolute paths in AVD config files ---")
    patch_avd_config_files(
        avd_dir=dest if not dry_run else src,
        old_base=src.parent.parent,
        new_base=dest.parent.parent,
        dry_run=dry_run,
    )

    # 1c. Set ANDROID_AVD_HOME so Android Studio uses the new location
    log("\n--- Setting ANDROID_AVD_HOME environment variable ---")
    set_user_env_var(ANDROID_AVD_HOME_VAR, str(dest), dry_run)

    # 1d. Remove originals if requested
    if delete_originals:
        log("\n--- Removing original AVD directory ---")
        delete_tree(src, dry_run)

    return True


def migrate_projects(src: Path, dest: Path, delete_originals: bool, dry_run: bool) -> bool:
    """Copy AndroidStudioProjects to dest. Returns True on success."""
    log("\n=== Step 2: Migrate AndroidStudioProjects directory ===")

    if not src.exists():
        log(f"WARNING: Source projects directory not found: {src}")
        log("  Skipping projects migration.")
        return True  # Non-fatal; projects dir may not exist yet

    try:
        copy_tree(src, dest, dry_run)
    except Exception as exc:
        log(f"ERROR during copy: {exc}")
        return False

    if delete_originals:
        log("\n--- Removing original projects directory ---")
        delete_tree(src, dry_run)

    log(
        "\nNOTE: Update Android Studio's project location in:\n"
        "  File > Settings > System Settings > Android SDK\n"
        f"  (or just open projects from their new location: {dest})",
        dry_run,
    )

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate Android Studio AVDs and projects to a new location.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without making any changes",
    )
    parser.add_argument(
        "--skip-projects",
        action="store_true",
        help="Skip moving the AndroidStudioProjects directory",
    )
    parser.add_argument(
        "--no-delete-originals",
        action="store_true",
        help="Keep the original files after a successful copy (useful for a safety check)",
    )
    parser.add_argument(
        "--source-avd-dir",
        default=os.getenv("SOURCE_AVD_DIR"),
        metavar="PATH",
        help="Source AVD directory (overrides SOURCE_AVD_DIR from .env)",
    )
    parser.add_argument(
        "--dest-avd-dir",
        default=os.getenv("DEST_AVD_DIR"),
        metavar="PATH",
        help="Destination AVD directory (overrides DEST_AVD_DIR from .env)",
    )
    parser.add_argument(
        "--source-projects-dir",
        default=os.getenv("SOURCE_PROJECTS_DIR"),
        metavar="PATH",
        help="Source AndroidStudioProjects directory (overrides SOURCE_PROJECTS_DIR from .env)",
    )
    parser.add_argument(
        "--dest-projects-dir",
        default=os.getenv("DEST_PROJECTS_DIR"),
        metavar="PATH",
        help="Destination AndroidStudioProjects directory (overrides DEST_PROJECTS_DIR from .env)",
    )
    parser.add_argument(
        "--log-file",
        default=os.getenv("LOG_FILE", "migrate_android_studio.log"),
        metavar="PATH",
        help="Path to log file (default: migrate_android_studio.log, overrides LOG_FILE from .env)",
    )
    return parser.parse_args()


def main() -> int:
    global _log_file
    args = parse_args()

    _log_file = open(args.log_file, "a", encoding="utf-8")  # noqa: SIM115
    try:
        return _run(args)
    finally:
        _log_file.close()


def _run(args: argparse.Namespace) -> int:
    # Validate required paths (CLI args take precedence over .env via argparse defaults)
    missing = [
        flag
        for flag, val in [
            ("SOURCE_AVD_DIR / --source-avd-dir", args.source_avd_dir),
            ("DEST_AVD_DIR / --dest-avd-dir", args.dest_avd_dir),
            ("SOURCE_PROJECTS_DIR / --source-projects-dir", args.source_projects_dir),
            ("DEST_PROJECTS_DIR / --dest-projects-dir", args.dest_projects_dir),
        ]
        if not val
    ]
    if missing:
        for flag in missing:
            log(f"ERROR: '{flag}' is not set. Provide it via .env or the CLI flag.")
        return 1

    source_avd_dir = Path(args.source_avd_dir)
    dest_avd_dir = Path(args.dest_avd_dir)
    source_projects_dir = Path(args.source_projects_dir)
    dest_projects_dir = Path(args.dest_projects_dir)

    dry_run: bool = args.dry_run
    delete_originals: bool = not args.no_delete_originals

    log("Android Studio Migration Script")
    log("================================")
    if dry_run:
        log("** DRY-RUN MODE — no changes will be made **")

    if not dry_run and sys.platform != "win32":
        log("ERROR: This script is intended for Windows only (registry access required).")
        return 1

    # Confirm before doing anything destructive
    if delete_originals and not dry_run:
        confirm: str = input(
            "\nOriginals will be DELETED after a successful copy.\n"
            "Make sure Android Studio is closed before continuing.\n"
            "Type 'yes' to proceed: "
        ).strip().lower()
        if confirm != "yes":
            log("Aborted.")
            return 0

    # --- AVD migration ---
    avd_ok: bool = migrate_avd(source_avd_dir, dest_avd_dir, delete_originals, dry_run)
    if not avd_ok:
        log("AVD migration failed. Aborting.")
        return 1

    # --- Projects migration ---
    if not args.skip_projects:
        projects_ok: bool = migrate_projects(source_projects_dir, dest_projects_dir, delete_originals, dry_run)
        if not projects_ok:
            log("Projects migration failed.")
            return 1

    log("\n=== Migration complete ===")
    if not dry_run:
        log(
            "\nNext steps:\n"
            "  1. Start Android Studio — your AVDs should appear in Device Manager.\n"
            "  2. If any AVD shows 'Download needed', click the blue Download button.\n"
            f"  3. If projects were moved, open them from {dest_projects_dir}.\n"
            "  4. If you used --no-delete-originals, manually verify everything works\n"
            "     before deleting the originals."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
