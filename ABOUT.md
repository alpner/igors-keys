# About Igor's Keys

Igor's Keys is a small Windows tray program that gives the extra keys of the CHERRY CyMotion Master XPress
keyboard (G86-21050) a job again. Cherry's original KeyM@n software was discontinued and its kernel driver
does not install on current Windows, which left the ten side keys and the Eject key dead.

It was written for my father, Igor, so that his keyboard does everything it used to again. Hence the name.

*Unofficial: not affiliated with, endorsed by or supported by Cherry. CHERRY, CyMotion and KeyM@n are trademarks
of their respective owners.*

## How it works

* The keyboard exposes its extra keys on a separate USB HID interface (usage page 0x0C "Consumer Control").
  Its report descriptor declares a maximum usage of 0x023C, but the side keys send 0x0279 and 0x0301–0x0303,
  which the Windows HID parser discards; the remaining side keys (scroll up/down, cut, copy, paste, undo) are in
  range but have no Windows function.
* Igor's Keys registers for that interface with the Raw Input API (`RegisterRawInputDevices`, `RIDEV_INPUTSINK`)
  and receives every report as raw bytes, including the ones the parser would drop. It matches the three-byte
  press report against a table captured from the real keyboard (`keys.json`) and runs the assigned action.
* Actions are executed with `SendInput` (Unicode text, key combinations) and `ShellExecute` (programs, files,
  folders, web addresses). The normal keyboard interface is never touched.
* The old KeyM@n configuration (`.csf`) is a Microsoft MFC `CArchive` serialization keyed by PS/2 scan codes;
  the mapping from those codes to the USB usages was extracted from Cherry's filter driver `Ch64USB.sys`.

The full discovery write-up and the capture tools are in `discovery/` (start with `FINDINGS.md`).

## Built with

Python 3.13, `ctypes` (Win32 APIs), `pystray` and `Pillow` (tray icon), `tkinter` (editor), PyInstaller
(stand-alone folder). No other runtime dependencies.

## Acknowledgements

The Linux kernel's `hid-cherry` driver documented the descriptor bug and the 0x0301–0x0303 usages years ago.
The rest was measured on the keyboard itself.

## Licence

MIT. See `LICENSE`.
