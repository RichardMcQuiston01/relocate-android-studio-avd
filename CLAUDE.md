# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file Windows-only Python script (`migrate_android_studio.py`) that relocates Android Studio AVD emulator images and project files from `C:\Users\richard` to `F:\richard` to free up C: drive space.

## Running the script

```powershell
# Preview changes without touching anything
python migrate_android_studio.py --dry-run

# Full migration (deletes originals after successful copy)
python migrate_android_studio.py

# Copy only; keep originals for manual verification
python migrate_android_studio.py --no-delete-originals

# Skip moving AndroidStudioProjects, only migrate AVDs
python migrate_android_studio.py --skip-projects
```

## Key design decisions

- **Hardcoded paths**: `SOURCE_AVD_DIR`, `DEST_AVD_DIR`, `SOURCE_PROJECTS_DIR`, `DEST_PROJECTS_DIR` are constants at the top of the file — change them there if the source/destination changes.
- **Config patching**: After copying, all absolute path strings inside `*.avd/config.ini`, `hardware-qemu.ini`, `emu-launch-params.txt`, and snapshot `hardware.ini` are rewritten to point to the new location. Both backslash and forward-slash variants are replaced.
- **Top-level INI files**: The `*.ini` files that sit directly in the AVD directory (one per AVD) are also patched — these are separate from the per-AVD config files inside `*.avd/` subdirectories.
- **Environment variable**: `ANDROID_AVD_HOME` is written as a persistent user-level `REG_EXPAND_SZ` value in `HKEY_CURRENT_USER\Environment` via `winreg`. A new shell/restart is required for it to take effect.
- **Windows-only guard**: The registry write is gated on `sys.platform == "win32"`. Dry-run works on any platform.
- **Deletion confirmation**: When `--no-delete-originals` is not passed, the script prompts for `yes` before deleting anything from C:.
