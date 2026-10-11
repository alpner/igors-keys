# CHERRY CyMotion Master XPress (G86-21050) on Windows 11 – Phase 1 findings

Date: 2026-10-11. Machine: Windows 11 Pro 10.0.26200, Python 3.13. Keyboard attached via USB.

## 1. What the keyboard exposes to Windows

The keyboard enumerates as **USB `046A:0023`** – the very PID the Linux kernel `hid-cherry` driver
patches, so the "Linux edition" and this keyboard are the same hardware.  It is a composite device
with two interfaces and three HID top-level collections (`discovery/hid_enumeration.txt`):

| Interface | Collection | Usage page / usage | Windows device | Report |
|---|---|---|---|---|
| 0 | boot keyboard | 0x01 / 0x06 | HID Keyboard Device (kbdhid) | 8 bytes, no report ID: modifiers, 6 key usages; LED output report |
| 1, Col01 | consumer control | 0x0C / 0x01 | HID-compliant consumer control device | report ID 1, one 16-bit usage (array) |
| 1, Col02 | system control | 0x01 / 0x80 | HID-compliant system controller | report ID 2, 3 bits: power-down / sleep / wake |

No vendor-defined usage pages, no feature reports, no output reports except the keyboard LEDs.

### The descriptor bug

The consumer-control report descriptor is, byte for byte, the one `hid-cherry` fixes up:

```
05 0c  09 01  a1 01  85 01  19 00  2a 3c 02  15 00  26 3c 02  75 10  95 01  81 00  c0
                                     ^^^^^ Usage Max 0x023C      ^^^^^ Logical Max 0x023C
```

Linux rewrites bytes 11/12 and 16/17 to `0x03FF`.  Windows' HID parser (`HidP_GetUsages`) rejects any
report value above the declared maximum, so every XPress key that sends a usage above 0x023C is simply
invisible to normal HID clients and to the Windows consumer-control → `WM_APPCOMMAND` path.

**Raw Input does not care.**  `WM_INPUT` for a HID collection hands over the raw report bytes, and the
capture below proves the out-of-range usages (0x0279, 0x0301–0x0303) arrive intact.  No driver, no
descriptor patch and no admin rights are needed.

### What Raw Input can and cannot see

`GetRawInputDeviceList` lists only the keyboard (01/06) and consumer (0C/01) collections for this
device.  The system-control collection (01/80) is consumed by the kernel power manager and is **not**
delivered to user mode; whatever key sends on it (Sleep/Power) is handled by Windows itself.

The boot keyboard collection is delivered as `RAWKEYBOARD` (scan code / virtual key), not raw bytes.
Usages that `kbdhid.sys` cannot translate to a PS/2 scan code are dropped before Raw Input.

## 2. What Cherry's own software did (hints from the KeyM@n/CDI packages)

* `Ch64USB.sys` / `ch2kusb.sys` is a **USB lower filter under HidUsb** on both interfaces
  (`LowerFilters = Ch64USB` in `ch764usb.inf`, section `ChyMasterXPUSBKbdDev`).  It inspects the raw
  interrupt packets ("DiagUSBPacket … ReportId"), so it never needed the descriptor to be valid, and it
  forwards hotkeys to user mode through `\\.\ChUSB` IOCTLs (`cdi.exe`: `CDriverHID::ExecuteHidCommand`).
* The driver carries a 208-entry table **PS/2 scan code → HID usage → name**.  The 29 non-standard entries
  are the extra keys of this keyboard family (the rest is the ordinary keyboard page); only those 29, as
  scan code, usage and name, are kept in `discovery/driver_hotkey_table.json` (`parse_driver_table.py`
  regenerates it from a local copy of the driver, which is not part of this repository).  KeyM@n's `.csf` files
  store keys as those PS/2 codes, so the table is the bridge between the user's old config and what the
  USB keyboard actually sends.
* **Nothing is stored on the keyboard.**  None of `KeyMan.exe`, `cdi.exe`, `ComLib.dll`,
  `cymotion.dll` or the drivers import `HidD_SetFeature`/`HidD_SetOutputReport`; the only HID imports are
  `HidD_GetAttributes`, `HidD_GetPreparsedData`, `HidP_GetCaps` (enumeration).  The descriptor has no
  feature reports.  All remapping was done on the host, so there is nothing to program and nothing
  that needs to be sent to the device.

### The "KeyM@n" (Fn) key

The driver table names PS/2 `E0 0E` → keyboard-page usage **0xA5 "Cherry Fn-Key"**.  0xA5 is a reserved
keyboard usage; `kbdhid.sys` has no scan code for it, so the key itself is not expected to reach user
mode (see capture results).  KeyM@n implemented the "second layer" in its kernel filter
(`UpdateModifierFlags … ContextKey dn/up`) for PS/2 keyboards; on this USB unit the capture shows the layer is done by the keyboard firmware (section 4).

## 3. The old configuration file (`CyMotionMasterXPress.csf`)

The "exported CSV" is actually a **binary Cherry-Shortcut-FileV2**, an MFC `CArchive` serialization.
`discovery/csf_parse.py` parses it completely (40 shortcut objects, all 1615 payload bytes consumed) and
documents the format in its docstring.  Summary of the user's assignments:

| Physical key (PS/2 → HID usage) | Plain | With KeyM@n layer |
|---|---|---|
| XPress 1 (E00B → 0x0233) | system "scroll up" (+ a 2nd entry, function 0x19) | F1 |
| XPress 2 (E012 → 0x0234) | system "scroll down" (+ function 0x1A) | F2 |
| XPress 3 (E017 → 0x021C) | cut | F3 |
| XPress 4 (E00A → 0x021D) | paste | F4 |
| XPress 5 (E018 → 0x021B) | copy | F5 |
| XPress 6 (E071 → 0x0301) | open "My Documents" (`explorer.exe ::{450D8FBA-…}`) | F6 |
| XPress 7 (E02C → 0x0302) | open folder `C:\Users\<old user>\Videos` | F7 |
| XPress 8 (E072 → 0x0303) | "XPress list" | F8 |
| XPress 9 (E007 → 0x0279) | redo | F9 |
| XPress 10 (E008 → 0x021A) | undo | F10 |
| WWW Search (E065 → 0x0221) | open http://www.cymotion.com | – |
| WWW Home/Back/Forward/Stop/Refresh | browser home/back/forward/stop/refresh | – |
| Mail (E06C → 0x018A) | e-mail program list | – |
| Media Select (E06D → 0x0183) | multimedia program list | – |
| Play/Pause, Stop, Prev, Next | media functions | – |
| CD Open (E070 → 0x00B8) | eject | – |
| Calculator (E021 → 0x0192) | `calc.exe` | – |
| WakeUp (E063 → 0x0204) | – | power function 3 after 3000 ms (standby) |
| Num Lock (0x45) | – | type "€" |
| Keypad . (0x53) | type "," | type "." |

Not in the file (never customised, or not customisable): Mute, Volume ±, Favorites, My Computer, Sleep.

## 4. Per-key capture results

All raw events are in `discovery/rawinput_log.jsonl` (kept out of the repository: it also records ordinary typing during the session); the per-key signatures (press and release bytes) are in
`discovery/keymap.json` (captured with `capture_gui.py`); which virtual keys Windows itself generates was recorded with a
low-level keyboard hook (`vk_check.py` → `discovery/vk_check.json`).

Physical layout (your description): a column of five keys left of the main block (labelled F1–F5 with icons), a column
of five right of it (F6–F10), and the main/premium/internet/multimedia keys along the top. There is **no Power key** on
this unit, so 28 of the 29 extras exist and all 28 were captured. Every one of them arrives on the **consumer-control
collection** (interface 1, report ID 1) as a 3-byte report `01 lo hi`, with `01 00 00` on release. Nothing arrives on
the keyboard collection for any of them (except the KeyM@n layer, see below) and nothing on any other collection.

| # | Key | Where / label | Raw report press | Usage | Cherry driver name (PS/2) | What Windows does | Native? | AutoHotkey name |
|---|---|---|---|---|---|---|---|---|
| 1 | **XPress 1** | left, first from the top, label says f1 with up and right arrow | `01 33 02` | 0x0233 | Scroll Up (E00B) | in range, but Windows has no action for AC Scroll Up/Down | NO - invisible (hook confirmed) | - |
| 2 | **XPress 2** | left, second from the top, label says f2 with down and left arrow | `01 34 02` | 0x0234 | Scroll Down (E012) | in range, but Windows has no action for AC Scroll Up/Down | NO - invisible (hook confirmed) | - |
| 3 | **XPress 3** | left, third from the top, label says f3 with scissors - probably cut | `01 1c 02` | 0x021C | Cut (E017) | in range; no virtual key (hook confirmed); paste key tested in Notepad and Explorer: nothing happens | NO - effectively invisible | - |
| 4 | **XPress 4** | left, fourth from the top, label says f4 with sheet of paper, probably paste | `01 1d 02` | 0x021D | Paste (E00A) | in range; no virtual key (hook confirmed); paste key tested in Notepad and Explorer: nothing happens | NO - effectively invisible | - |
| 5 | **XPress 5** | left, fifth from the top, label says f5 with two sheets of paper, probably copy | `01 1b 02` | 0x021B | Copy (E018) | in range; no virtual key (hook confirmed); paste key tested in Notepad and Explorer: nothing happens | NO - effectively invisible | - |
| 6 | **XPress 6** | right, first from the top, label says f6 with sheet of paper and 1 | `01 01 03` | 0x0301 | XPress1 (E071) | out of descriptor range: dropped by the HID parser | NO - invisible | - |
| 7 | **XPress 7** | right, second from the top, label says f7 with sheet of paper and 2 | `01 02 03` | 0x0302 | XPress2 (E02C) | out of descriptor range: dropped by the HID parser | NO - invisible | - |
| 8 | **XPress 8** | right, third from the top, label says f8 with sheet of paper and 3 | `01 03 03` | 0x0303 | XPress3 (E072) | out of descriptor range: dropped by the HID parser | NO - invisible | - |
| 9 | **XPress 9** | right, fourth from the top, label says f9 with forward arrow | `01 79 02` | 0x0279 | Redo (E007) | out of descriptor range: dropped by the HID parser | NO - invisible | - |
| 10 | **XPress 10** | right, fifth from the top, label says f10 with back arrow | `01 1a 02` | 0x021A | Undo (E008) | in range; no virtual key (hook confirmed); paste key tested in Notepad and Explorer: nothing happens | NO - effectively invisible | - |
| 11 | **Calculator** | above numpad, from left to right, first key, calculator | `01 92 01` | 0x0192 | Calculator (E021) | native: Windows synthesises VK_LAUNCH_APP2 (hook confirmed) | YES | Launch_App2 |
| 12 | **E-Mail** | above numpad, from left to right, second key, email | `01 8a 01` | 0x018A | Mail (E06C) | native: Windows synthesises VK_LAUNCH_MAIL (hook confirmed) | YES | Launch_Mail |
| 13 | **WWW Home** | above numpad, from left to right, third key, home | `01 23 02` | 0x0223 | WWW Home (E032) | native: Windows synthesises VK_BROWSER_HOME (hook confirmed) | YES | Browser_Home |
| 14 | **Volume -** | Volume - | `01 ea 00` | 0x00EA | Volume Down (E02E) | native: Windows synthesises VK_VOLUME_DOWN (hook confirmed) | YES | Volume_Down |
| 15 | **Volume +** | Volume + | `01 e9 00` | 0x00E9 | Volume Up (E030) | native: Windows synthesises VK_VOLUME_UP (hook confirmed) | YES | Volume_Up |
| 16 | **Mute** | Mute | `01 e2 00` | 0x00E2 | Mute (E020) | native: Windows synthesises VK_VOLUME_MUTE (hook confirmed) | YES | Volume_Mute |
| 17 | **Media player** | Media | `01 83 01` | 0x0183 | Media Select (E06D) | native: Windows synthesises VK_LAUNCH_MEDIA_SELECT (hook confirmed) | YES | Launch_Media |
| 18 | **Internet Back** | Internet Back | `01 24 02` | 0x0224 | WWW Back (E06A) | native: Windows synthesises VK_BROWSER_BACK (hook confirmed) | YES | Browser_Back |
| 19 | **Internet Forward** | Internet Forward | `01 25 02` | 0x0225 | WWW Forward (E069) | native: Windows synthesises VK_BROWSER_FORWARD (hook confirmed) | YES | Browser_Forward |
| 20 | **Internet Stop** | Internet Close | `01 26 02` | 0x0226 | WWW Stop (E068) | native: Windows synthesises VK_BROWSER_STOP (hook confirmed) | YES | Browser_Stop |
| 21 | **Internet Refresh** | Internet Refresh | `01 27 02` | 0x0227 | WWW Refresh (E067) | native: Windows synthesises VK_BROWSER_REFRESH (hook confirmed) | YES | Browser_Refresh |
| 22 | **Internet Search** | Internet Search | `01 21 02` | 0x0221 | WWW Search (E065) | native: Windows synthesises VK_BROWSER_SEARCH (hook confirmed) | YES | Browser_Search |
| 23 | **Media Play/Pause** | Media Play/Pause | `01 cd 00` | 0x00CD | Play / Pause (E022) | native: Windows synthesises VK_MEDIA_PLAY_PAUSE (hook confirmed) | YES | Media_Play_Pause |
| 24 | **Media Stop** | Media Stop | `01 b7 00` | 0x00B7 | Stop (E024) | native: Windows synthesises VK_MEDIA_STOP (hook confirmed) | YES | Media_Stop |
| 25 | **Media Previous** | Media Previous | `01 b6 00` | 0x00B6 | Scan Previous Track (E010) | native: Windows synthesises VK_MEDIA_PREV_TRACK (hook confirmed) | YES | Media_Prev |
| 26 | **Media Next Track** | Media Next Track | `01 b5 00` | 0x00B5 | Scan Next Track (E019) | native: Windows synthesises VK_MEDIA_NEXT_TRACK (hook confirmed) | YES | Media_Next |
| 27 | **Media Eject** | Media Eject | `01 b8 00` | 0x00B8 | CD Open (E070) | Eject: no virtual key on Windows (hook confirmed, nothing seen) | NO - invisible | - |
| 28 | **KeyM@n + XPress 1** | keyman modifier + left, top one of five, f1 | `keyboard scan 0x3B / vkey 0x70` | kbd 0x3A | F-key | keyboard collection: plain F-key (firmware layer) | yes, as F1/F6 | F1 / F6 |
| 29 | **KeyM@n + XPress 6** | keyman + right, top one of five, f6 | `keyboard scan 0x40 / vkey 0x75` | kbd 0x3F | F-key | keyboard collection: plain F-key (firmware layer) | yes, as F1/F6 | F1 / F6 |

### What this means

* **Windows handles these 16 natively** (all 16 seen as virtual keys by the hook): Calculator, E-Mail, WWW Home, Volume -, Volume +, Mute, Media player, Internet Back, Internet Forward, Internet Stop, Internet Refresh, Internet Search, Media Play/Pause, Media Stop, Media Previous, Media Next Track.  They work today without any software, AutoHotkey
  could remap them, and our app does not need to touch them.  If the app ever remaps one, the native action still
  fires unless the app also blocks the virtual key with a low-level hook (possible, optional).
* **These 11 are invisible to Windows and to every other program**: XPress 1, XPress 2, XPress 3, XPress 4, XPress 5, XPress 6, XPress 7, XPress 8, XPress 9, XPress 10, Media Eject.  Four (0x0279, 0x0301–0x0303) are above
  the descriptor's range and dropped by the HID parser; scroll up/down and Eject are in range but have no Windows
  action; the four edit keys produce no virtual key and did nothing in Notepad or Explorer when tested.  These are
  the keys the app exists for.
* **The KeyM@n key is a firmware layer, not a key.** It never produces any report by itself (nothing on any collection,
  matches the driver table's reserved usage 0xA5 that `kbdhid.sys` cannot translate).  But while it is held the ten
  side keys send plain keyboard **F1–F10** (Raw Input capture: XPress 1 → scan 0x3B, XPress 6 → scan 0x40; hook run:
  all ten, VK_F1…VK_F10, one each).  So the old "KeyM@n + side key = F-key" layer works for free, exactly as the
  `.csf` configured it, and no tray toggle or substitute modifier is needed.  The flip side: that layer is indistinguishable from the real F-keys, so it cannot be
  remapped separately.

## 5. Recommendation

**Build the tray app on Raw Input over the consumer-control collection (0x0C/0x01).**  Every extra key is
unambiguous there (`01 lo hi` press, `01 00 00` release), the collection is not opened exclusively by anything, no
driver or admin rights are needed, and the main keyboard collection is left entirely alone, so normal typing can never
be swallowed.  The discovery logger (`rawinput_logger.py`) already is that listener; the app reuses it.

Implementation: **Python 3.13 + PyInstaller (one-folder build)**.

* Raw Input via `ctypes` (written and proven above); tray icon via `pystray` + `Pillow`; actions via `SendInput`
  (`ctypes`: Unicode text and key chords) and `os.startfile` for programs, files and URLs; `logging` to a rotating
  file; config in a plain JSON file; a small `tkinter` editor; autostart through a shortcut in the user's Startup folder
  (no admin).  Boring, well-known pieces, and the discovery code carries straight over.
* C#/.NET would be equally suitable, but no .NET SDK is installed on this machine and the Python prototype exists.
* AutoHotkey alone is not enough: it cannot see the eleven invisible keys, which are exactly the ones worth remapping.

Behaviour rules for the app:

1. Match the exact report bytes from `keymap.json`; log and ignore anything else.  Act on press only.
2. The 16 native keys are **not listened to by default** (they already work).  They can be mapped, with a note in the
   editor that Windows' own action will fire as well unless "block the Windows action" is ticked (low-level hook).
3. The 11 invisible keys are the ones the app maps.  Edit keys (cut/copy/paste/undo/redo) get Ctrl+X/C/V/Z/Y
   suggestions, because Windows does nothing with them (paste test).
4. Never touch the keyboard collection; never send anything to the device (nothing to program).
5. KeyM@n layer: nothing to do, the firmware provides F1–F10.
6. **Scope decided with you**: the shipped config is empty except for suggestions for XPress 6 (open My Documents) and
   XPress 7 (open the Videos folder) taken from the old `.csf` (with the user folder corrected); everything else is
   left for the end user to assign in the editor.  The `.csf` importer stays available for anyone who wants the full
   old layout (`csf_parse.py` + `driver_hotkey_table.json` bridge).
7. Fail silently: any exception in the input path is logged and swallowed; the listener keeps running.

Nothing is left open; every claim above was observed on the device.
