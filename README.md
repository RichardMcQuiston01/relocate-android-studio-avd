# relocate-android-studio-avd

## Author

- **Name:** Richard McQuiston
- **Email:** [Contact Me](https://richardmcquiston.com/web-development-contact)
- **Website:** [https://richardmcquiston.com](https://wwww.richardmcquiston.com/)
- **Donate:** [Buy Me a Coffee](https://www.paypal.com/ncp/payment/VDTESHTRR7684)

## Description

A Windows utility that migrates Android Studio AVD (Android Virtual Device) emulator images and the `AndroidStudioProjects` directory from one drive to another — typically from a space-constrained C: drive to a secondary drive. After copying, it rewrites all absolute paths embedded in AVD config files and sets the `ANDROID_AVD_HOME` environment variable so Android Studio picks up the new location automatically with no manual IDE configuration required.

## Requirements

- Windows 10/11
- Python 3.9+
- Android Studio (any recent version)

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/richardmcquiston/relocate-android-studio-avd.git
   cd relocate-android-studio-avd
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set your source and destination paths:
   ```
   copy .env.example .env
   ```
   Then edit `.env`:
   ```
   SOURCE_AVD_DIR=C:\Users\YourName\.android\avd
   DEST_AVD_DIR=D:\YourName\.android\avd
   SOURCE_PROJECTS_DIR=C:\Users\YourName\AndroidStudioProjects
   DEST_PROJECTS_DIR=D:\YourName\AndroidStudioProjects
   ```

## Usage

**Close Android Studio before running.**

```
python migrate_android_studio.py [options]
```

| Option                       | Description                                                    |
| ---------------------------- | -------------------------------------------------------------- |
| `--dry-run`                  | Preview all actions without making any changes                 |
| `--no-delete-originals`      | Copy files but keep the originals on the source drive          |
| `--skip-projects`            | Migrate AVDs only; skip `AndroidStudioProjects`                |
| `--source-avd-dir PATH`      | Override `SOURCE_AVD_DIR` from `.env`                          |
| `--dest-avd-dir PATH`        | Override `DEST_AVD_DIR` from `.env`                            |
| `--source-projects-dir PATH` | Override `SOURCE_PROJECTS_DIR` from `.env`                     |
| `--dest-projects-dir PATH`   | Override `DEST_PROJECTS_DIR` from `.env`                       |
| `--log-file PATH`            | Override log file path (default: `migrate_android_studio.log`) |

**Recommended first run** — preview everything before committing:

```
python migrate_android_studio.py --dry-run
```

**Full migration** — copies files, patches configs, sets `ANDROID_AVD_HOME`, then deletes originals:

```
python migrate_android_studio.py
```

**Safe migration** — copy first, verify AVDs work in Android Studio, then delete originals manually:

```
python migrate_android_studio.py --no-delete-originals
```

All output is written to the console and appended to `migrate_android_studio.log` (configurable via `--log-file` or `LOG_FILE` in `.env`).

## License

MIT — see [LICENSE](LICENSE) for details.

## Copyright

(c)2026 R. M. McQuiston. All rights reserved.
