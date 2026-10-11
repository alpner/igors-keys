# Changelog

## 2.0.0 – 2026-10-11

Renamed from CherryKeys to **Igor's Keys**: an unofficial project should not look like a Cherry product.

* New name, new keycap icon. Program `IgorsKeys.exe`, settings in `%LOCALAPPDATA%\IgorsKeys` (CherryKeys 1.x
  settings are not moved automatically: use Back up / Restore, see the README).
* Import of KeyM@n `.csf` files: key macros keep their modifiers (Ctrl+K, Ctrl+C no longer becomes "K", "C");
  punctuation, numpad and media keys in macros are converted to names that work; accented characters in texts
  and paths are read in the Windows code page of the machine (č no longer turns into è on Slovenian Windows).
* Editor: after an import, a restore or **Clear all**, the form shows the new assignment of the selected key, so
  **Save** no longer writes the old values back. Backslashes in `text:` steps of a sequence are kept
  (`\n` is a new line, `\\` a backslash).
* The log no longer contains the texts your keys type, only their length.
* Changing the language from the tray menu no longer overwrites changes saved in the editor moments before.
* Only the tray program rotates the log file; correct Windows error codes in log messages; `--import` without a
  file name explains itself instead of failing; running from source starts without a console window.
* `discovery/`: the copied excerpt of Cherry's driver INF file is gone, and the driver table keeps only the 29
  rows (scan code, usage, name) needed to read `.csf` files.

## 1.1.0 – 2026-10-11

* Slovenian user interface: editor, tray menu, dialogs, key descriptions and preset lists. Chosen automatically
  from the Windows display language; tray menu **Language** overrides it (`"language": "auto" | "en" | "sl"` in
  `config.json`).
* Slovenian manual `README.sl.md` shipped next to the English one.
* Settings backup and restore (editor buttons and tray menu); automatic backups of the previous settings on
  every save (last 20). Record button and preset lists in the editor (added after 1.0.0 was tagged).

## 1.0.0 – 2026-10-11

First release.

* Tray program listening for the 27 extra keys of the CyMotion Master XPress through Raw Input; no driver needed.
* Actions: type text (Unicode), press a key combination, open a program / file / folder / web address, or run a
  sequence of steps with delays.
* Keys Windows already handles (volume, media, browser, calculator, e-mail) are left to Windows unless assigned;
  optional blocking of the Windows function for such keys.
* Editor with per-key assignments, **Record…** for key combinations, preset lists of common actions and common
  places, **Test now**, import of old KeyM@n `.csf` files, **Back up settings…** / **Restore settings…**.
* Automatic backup of the previous settings on every save (last 20 kept).
* Start with Windows (per-user Run entry), pause/resume, rotating log file.
* Discovery tool set: HID enumeration, Raw Input logger, guided capture window, Windows virtual-key check,
  Cherry driver table extractor, `.csf` parser, and `discovery/FINDINGS.md`.
