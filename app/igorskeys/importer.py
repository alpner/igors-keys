"""Import an old Cherry KeyM@n configuration (.csf, "Cherry-Shortcut-FileV2") into Igor's Keys mappings.

How the bridge works
--------------------
KeyM@n stored every assignment under the PS/2 scan code of the physical key (e.g. E071).  The Cherry
filter driver translated those to the HID consumer usages the USB keyboard really sends (E071 -> 0x0301);
that table was extracted from Ch64USB.sys and the relevant rows are carried in keys.json ("ps2" field).

What is converted
-----------------
  CExecutableSC  -> open (program / web address / folder, with parameters)
  CTextMacroSC   -> text
  CKeyMacroSC    -> keys (modifiers + one key) or a sequence of key presses
  CBrowserSC     -> keys BrowserBack / BrowserForward / BrowserStop / BrowserRefresh / BrowserHome
  CMediaSC       -> keys MediaNext / MediaPrev / MediaStop / PlayPause
  CSystemSC      -> cut/copy/paste/undo/redo -> Ctrl+X/C/V/Z/Y; scroll up/down -> PageUp/PageDown
  CListSC        -> open the first program of the list, otherwise the matching Windows launch key
  CPowerSC       -> not converted (standby); noted
Entries for the KeyM@n layer (flags bit 31) are skipped: the keyboard itself turns the side keys into
F1-F10 while KeyM@n is held.  Entries for keys this keyboard does not have are skipped and noted.
"""
import logging

from . import csf

log = logging.getLogger("igorskeys.importer")

VK_NAME = {0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc", 0x20: "Space", 0x21: "PageUp", 0x22: "PageDown",
           0x23: "End", 0x24: "Home", 0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down", 0x2D: "Insert",
           0x2E: "Delete", 0x5B: "Win", 0x5C: "RWin", 0x5D: "Apps", 0x10: "Shift", 0x11: "Ctrl", 0x12: "Alt",
           0xA0: "Shift", 0xA1: "RShift", 0xA2: "Ctrl", 0xA3: "RCtrl", 0xA4: "Alt", 0xA5: "AltGr",
           0x90: "NumLock", 0x91: "ScrollLock", 0x14: "CapsLock", 0x2C: "PrintScreen", 0x13: "Pause"}
for _i in range(1, 25):
    VK_NAME[0x6F + _i] = "F%d" % _i
for _c in range(0x30, 0x3A):
    VK_NAME[_c] = chr(_c)
for _c in range(0x41, 0x5B):
    VK_NAME[_c] = chr(_c)
for _i in range(10):
    VK_NAME[0x60 + _i] = "Numpad%d" % _i
# names that actions.parse_chord understands; anything else is written as a raw "0xNN" code, which it also accepts
VK_NAME.update({0x5F: "Sleep", 0x6A: "Multiply", 0x6B: "Add", 0x6D: "Subtract", 0x6E: "Decimal", 0x6F: "Divide",
                0xBB: "Plus", 0xBC: "Comma", 0xBD: "Minus", 0xBE: "Period",
                0xA6: "BrowserBack", 0xA7: "BrowserForward", 0xA8: "BrowserRefresh", 0xA9: "BrowserStop",
                0xAA: "BrowserSearch", 0xAB: "BrowserFavorites", 0xAC: "BrowserHome", 0xAD: "VolumeMute",
                0xAE: "VolumeDown", 0xAF: "VolumeUp", 0xB0: "MediaNext", 0xB1: "MediaPrev", 0xB2: "MediaStop",
                0xB3: "PlayPause", 0xB4: "LaunchMail", 0xB5: "LaunchMedia", 0xB6: "LaunchApp1", 0xB7: "LaunchApp2"})
MODS = {"Shift", "RShift", "Ctrl", "RCtrl", "Alt", "AltGr", "Win", "RWin"}


def _vk_name(vk):
    return VK_NAME.get(vk, "0x%02X" % vk)

BROWSER = {1: "BrowserBack", 2: "BrowserForward", 3: "BrowserStop", 4: "BrowserRefresh", 7: "BrowserHome"}
MEDIA = {1: "MediaNext", 2: "MediaPrev", 3: "MediaStop", 4: "PlayPause"}
SYSTEM = {0x17: "PageUp", 0x18: "PageDown", 0x1b: "Ctrl+X", 0x1c: "Ctrl+C", 0x1d: "Ctrl+V", 0x1e: "Ctrl+Y", 0x1f: "Ctrl+Z"}
LIST_KEY = {2: "LaunchMail", 3: "LaunchMedia", 4: "BrowserHome"}


def _macro_to_action(macro):
    """CKeyMacroSC key events -> one keys chord, or a sequence of chords.

    The modifiers held down at the moment of each key press go with that press, so Ctrl down, K, C, Ctrl up
    becomes the two steps Ctrl+K and Ctrl+C."""
    held, chords = [], []
    for ev in macro:
        name = _vk_name(ev["vkey"])
        if name in MODS:
            if ev["up"]:
                if name in held:
                    held.remove(name)
            elif name not in held:
                held.append(name)
        elif not ev["up"]:
            chords.append("+".join(held + [name]))
    if not chords:   # modifiers only, e.g. a lone Win press
        mods = []
        for ev in macro:
            name = _vk_name(ev["vkey"])
            if not ev["up"] and name not in mods:
                mods.append(name)
        if not mods:
            return {"type": "none"}
        chords = ["+".join(mods)]
    if len(chords) == 1:
        return {"type": "keys", "keys": chords[0]}
    return {"type": "sequence", "steps": [{"type": "keys", "keys": c} for c in chords]}


def convert(csf_bytes, keys):
    """Return (mappings, notes).  mappings is a config 'mappings' dict; notes is a list of human-readable lines."""
    res = csf.parse(csf_bytes)
    by_ps2 = {}
    for k in keys.keys:
        try:
            by_ps2[int(k.ps2 or "0", 16)] = k
        except ValueError:
            pass
    mappings, notes = {}, []
    for o in res["objects"]:
        key = by_ps2.get(o["key"])
        kname = key.id if key else o.get("key_name", "?")
        if o["keyman_layer"]:
            notes.append("skipped KeyM@n-layer entry for %s (%s): the keyboard provides F-keys itself" % (kname, o["action"]))
            continue
        if key is None:
            notes.append("skipped %s (%s): not an extra key of this keyboard" % (kname, o["action"]))
            continue
        cls = o["class"]
        action, comment = None, "imported from KeyM@n: %s" % o["action"]
        if cls == "CExecutableSC":
            action = {"type": "open", "target": o["path"]}
            if o.get("parameters"):
                action["args"] = o["parameters"]
            comment = "imported from KeyM@n: %s" % (o["name"] or o["path"])
        elif cls == "CTextMacroSC":
            action = {"type": "text", "text": o["text"]}
        elif cls == "CKeyMacroSC":
            action = _macro_to_action(o["macro"])
        elif cls == "CBrowserSC" and o["function"] in BROWSER:
            action = {"type": "keys", "keys": BROWSER[o["function"]]}
        elif cls == "CMediaSC" and o["function"] in MEDIA:
            action = {"type": "keys", "keys": MEDIA[o["function"]]}
        elif cls == "CSystemSC" and o["function"] in SYSTEM:
            action = {"type": "keys", "keys": SYSTEM[o["function"]]}
        elif cls == "CListSC":
            progs = [c for c in o.get("children", []) if c["class"] == "CExecutableSC"]
            if progs:
                action = {"type": "open", "target": progs[0]["path"]}
                if progs[0].get("parameters"):
                    action["args"] = progs[0]["parameters"]
                comment = "imported from KeyM@n program list: %s" % (progs[0]["name"] or progs[0]["path"])
            elif o["function"] in LIST_KEY:
                action = {"type": "keys", "keys": LIST_KEY[o["function"]]}
        if action is None or action.get("type") == "none":
            notes.append("not converted: %s = %s (%s)" % (kname, o["action"], cls))
            continue
        same_as_windows = (
            (action.get("type") == "keys" and action["keys"] in (*BROWSER.values(), *MEDIA.values(), *LIST_KEY.values()))
            or (key.id == "Calculator" and action.get("type") == "open" and action["target"].lower().endswith("calc.exe")))
        if key.windows_handles_it and same_as_windows:
            notes.append("left to Windows: %s already does '%s' by itself" % (kname, o["action"]))
            continue
        if kname in mappings:
            notes.append("duplicate entry for %s; kept the first one (%s)" % (kname, mappings[kname]["comment"]))
            continue
        mappings[kname] = {"action": action, "comment": comment}
        notes.append("%s -> %s" % (kname, comment))
    return mappings, notes
