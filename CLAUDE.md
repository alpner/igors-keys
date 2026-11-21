# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Igor's Keys is a Windows-only tray program (Python, `ctypes` Win32 calls, `pystray`/`Pillow` tray, `tkinter`
editor) that gives the extra keys of one specific keyboard, the CHERRY CyMotion Master XPress G86-21050
(USB `046A:0023`), a job again. It replaces Cherry's discontinued KeyM@n. It is unofficial; the docs take care
to say it is not affiliated with Cherry. Keep that wording when you edit user-facing text.

## Commands

All run from `app/`. Python 3.11 or newer, Windows only (the modules call `ctypes.windll`/`winreg` when
imported).

```
pip install -r requirements.txt
python main.py              # tray program (logs also go to the console when run from source)
python main.py --debug      # tray program with DEBUG logging
python main.py --edit       # key-assignment editor
python main.py --import X.csf   # convert an old KeyM@n file into config.json
python main.py --backup | --restore   # the backup/restore dialogs
python check_i18n.py        # translation coverage check; exit code 1 if a Slovenian string is missing
powershell -ExecutionPolicy Bypass -File build.ps1   # PyInstaller one-folder build -> app\dist\IgorsKeys\
```

There is no test suite. `check_i18n.py` is the only automated check. Set `IGORSKEYS_LANG=sl` (or `en`) to
force the UI language when testing.

## Architecture

**One exe, several processes.** `main.py` dispatches on argv: no flag runs the long-lived tray process
(`igorskeys/app.py`), while `--edit`, `--backup`, `--restore` and `--import` run short-lived helpers. The tray
starts the editor and the backup/restore dialogs as subprocesses (`paths.exe_command()`, which handles both
frozen and source runs). The helpers and the tray never talk to each other directly. They share
`%LOCALAPPDATA%\IgorsKeys\config.json`: helpers write it, and the tray polls its mtime every 2 s
(`App.watch_config`) and reloads. Two consequences:
- Anything that writes config must load the current file from disk first, not an in-memory copy (see
  `App.set_language`). It must also refuse to overwrite a file that `config.config_is_readable()` reports as
  unreadable.
- Only the tray process rotates the shared log (`setup_logging(rotate=False)` in helpers): Windows cannot
  rename a file another process has open.

**Input path (tray process):**
1. `rawinput.Listener` registers *only* the consumer-control collection (usage page 0x0C, usage 0x01) with
   `RIDEV_INPUTSINK` on a hidden window and its own message-loop thread. It filters by VID/PID. It never
   registers the normal keyboard collection, so it cannot affect typing. Raw Input is used because the
   keyboard's HID descriptor declares usage max 0x023C while several side keys send higher usages, which the
   Windows HID parser drops (details in `discovery/FINDINGS.md`).
2. `App.on_report` matches the raw 3-byte press report against `keys.json` (`Keys.by_press`), ignores
   release reports and double reports under 80 ms, and hands the mapping to `actions.Executor`.
3. `actions.Executor` runs actions one at a time on a worker thread through `SendInput` (Unicode text, key
   chords parsed by `parse_chord`) and `ShellExecuteW`. Action types: `none | text | keys | open | sequence`,
   plus `delay`, which is allowed only inside a sequence. Sequences cannot nest. `config.validate_action` and
   `actions.run_action` enforce the same rules; keep them in sync.
4. `hookblock.Blocker` is optional: it is a low-level keyboard hook that swallows the native VK codes of keys
   Windows already handles (volume, media and so on) when the user ticked `block_windows_action`. The hook must
   live on a thread with a message loop, so it is installed and removed on the listener thread through
   `listener.run_on_thread(...)`.

**Data files:**
- `igorskeys/keys.json` is bundled and read-only. It was captured from the real keyboard and holds each key's
  id, press/release bytes, HID usage, PS/2 scan code (needed for `.csf` import), native VK and
  `windows_handles_it`. Key ids such as `"XPress 6"` are the stable keys in `config.json` and must not change.
- `config.json` is user data. Its format is documented in the `igorskeys/config.py` docstring.
  `save_config` writes atomically and keeps the last 20 previous versions in `backups/`.
- `paths.py` is where frozen and source locations are resolved: `resource_dir` uses `_MEIPASS` when frozen.
  New bundled resources also need an `--add-data` line in `build.ps1`.

**KeyM@n import:** `csf.py` parses the MFC `CArchive` `.csf` format (the module docstring documents the
format). `importer.py` converts the parsed entries to mappings by matching PS/2 scan codes through the `ps2`
field in `keys.json`. Strings in `.csf` are in the Windows ANSI code page, not UTF-8.

**i18n:** the English source strings are the translation keys. `tr("...")` looks them up in `i18n.SL`, and
key labels come from `i18n.KEY_LABELS_SL`. Every new `tr()` literal in `editor.py`, `app.py` or `main.py`, and
every new editor preset, help text, key group or key id, needs a Slovenian entry. `check_i18n.py` verifies
this. Pass `tr()` a string literal: `check_i18n.py` finds strings by parsing the source, so it misses
computed strings.

**Privacy rule:** the log is meant to be sent when asking for help, so it must never contain the text a key
types. Use `actions.describe(action, private=True)` for anything that is logged.

## Docs and releases

- `README.md` (English) and `README.sl.md` (Slovenian) are parallel user manuals. Change both together.
  `FAQ.md`, `ABOUT.md`, `CHANGELOG.md` and `LICENSE` are copied into the build by `build.ps1`.
- The version lives only in `igorskeys/__init__.py` (`__version__`). Add a matching `CHANGELOG.md` entry.
  `build.ps1` runs `make_version.py`, which turns that version into `build\version_info.txt`, the Windows
  version resource of the exe.
- The exe is not code-signed. `build.ps1` adds file details (`--version-file`) and turns off UPX (`--noupx`),
  so antivirus programs flag it less. Keep both. The user-facing advice for each kind of security warning is
  in `FAQ.md`.
- Release zips (`IgorsKeys-<version>-win64.zip`) are attached to GitHub releases, not committed. `.csf` files,
  Cherry's proprietary packages (`CDI/`, `KeyMan/`, `other/`) and `discovery/rawinput_log.jsonl` are
  git-ignored on purpose. Do not add them.
- `discovery/` holds the reverse-engineering tools and the write-up (`FINDINGS.md`). It is not part of the app.
