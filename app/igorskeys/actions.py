"""Executes mapped actions: type text, press key combinations, open things, run sequences.

All input is sent with SendInput.  Text is sent as Unicode characters, so it works for any
language and layout.  Key combinations are written like "Ctrl+Shift+V", "Win+E", "Alt+F4", "Enter".
"""
import ctypes
import ctypes.wintypes as w
import logging
import os
import queue
import threading
import time

log = logging.getLogger("igorskeys.actions")

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0
SW_SHOWNORMAL = 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", w.WORD), ("wScan", w.WORD), ("dwFlags", w.DWORD), ("time", w.DWORD),
                ("dwExtraInfo", ctypes.POINTER(w.ULONG))]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", w.LONG), ("dy", w.LONG), ("mouseData", w.DWORD), ("dwFlags", w.DWORD), ("time", w.DWORD),
                ("dwExtraInfo", ctypes.POINTER(w.ULONG))]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", w.DWORD), ("wParamL", w.WORD), ("wParamH", w.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", w.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = [w.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = w.UINT
shell32.ShellExecuteW.argtypes = [w.HWND, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, ctypes.c_int]
shell32.ShellExecuteW.restype = w.HINSTANCE

# ---- key names -> virtual-key codes ----
VK = {
    "ctrl": 0x11, "control": 0x11, "lctrl": 0xA2, "rctrl": 0xA3,
    "shift": 0x10, "lshift": 0xA0, "rshift": 0xA1,
    "alt": 0x12, "lalt": 0xA4, "ralt": 0xA5, "altgr": 0xA5,
    "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C, "windows": 0x5B,
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "space": 0x20, "backspace": 0x08,
    "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "ins": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21,
    "pgup": 0x21, "pagedown": 0x22, "pgdn": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "printscreen": 0x2C, "prtsc": 0x2C, "scrolllock": 0x91, "pause": 0x13, "capslock": 0x14, "numlock": 0x90,
    "apps": 0x5D, "menu": 0x5D, "sleep": 0x5F,
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63, "numpad4": 0x64, "numpad5": 0x65,
    "numpad6": 0x66, "numpad7": 0x67, "numpad8": 0x68, "numpad9": 0x69, "multiply": 0x6A, "add": 0x6B,
    "subtract": 0x6D, "decimal": 0x6E, "divide": 0x6F,
    "volumeup": 0xAF, "volumedown": 0xAE, "volumemute": 0xAD, "mute": 0xAD, "medianext": 0xB0, "mediaprev": 0xB1,
    "mediastop": 0xB2, "mediaplaypause": 0xB3, "playpause": 0xB3, "launchmail": 0xB4, "launchmedia": 0xB5,
    "launchapp1": 0xB6, "launchapp2": 0xB7, "calculator": 0xB7, "browserback": 0xA6, "browserforward": 0xA7,
    "browserrefresh": 0xA8, "browserstop": 0xA9, "browsersearch": 0xAA, "browserfavorites": 0xAB,
    "browserhome": 0xAC,
    "plus": 0xBB, "minus": 0xBD, "comma": 0xBC, "period": 0xBE,
}
for _i in range(1, 25):
    VK["f%d" % _i] = 0x6F + _i
EXTENDED = {0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x5B, 0x5C, 0x5D, 0xA3, 0xA5, 0x6F, 0x90,
            0x2C} | set(range(0xA6, 0xB8))
MODIFIERS = {"ctrl", "control", "lctrl", "rctrl", "shift", "lshift", "rshift", "alt", "lalt", "ralt", "altgr",
             "win", "lwin", "rwin", "windows"}


class ActionError(Exception):
    pass


def parse_chord(text):
    """'Ctrl+Shift+V' -> ([0x11, 0x10], 0x56).  Single characters use VkKeyScan for the current layout."""
    t = text.replace(" ", "")
    if t == "+":
        t = "plus"
    elif t.endswith("++"):          # "Ctrl++" means Ctrl and the plus key
        t = t[:-2] + "+plus"
    parts = [p for p in t.split("+") if p]
    if not parts:
        raise ActionError("empty key combination")
    mods, key = [], None
    for p in parts:
        lp = p.lower()
        if lp in MODIFIERS:
            mods.append(VK[lp])
        elif key is not None:
            raise ActionError("more than one non-modifier key in %r" % text)
        elif lp in VK:
            key = VK[lp]
        elif lp.startswith("0x") and len(lp) > 2:     # raw virtual-key code, e.g. "0xBC"
            try:
                key = int(lp, 16)
            except ValueError:
                raise ActionError("unknown key name %r" % p)
            if not 0 < key < 0xFF:
                raise ActionError("virtual-key code out of range in %r" % text)
        elif len(p) == 1 and (p.isascii() and p.isalnum()):
            key = ord(p.upper())      # letters and digits: the virtual key is the upper-case ASCII code
        elif len(p) == 1:
            r = user32.VkKeyScanW(ord(p))
            if r == -1 or r == 0xFFFF:
                raise ActionError("no key for character %r in the current keyboard layout" % p)
            key = r & 0xFF
            shift_state = (r >> 8) & 0xFF
            if shift_state & 1 and VK["shift"] not in mods:
                mods.append(VK["shift"])
            if shift_state & 2 and VK["ctrl"] not in mods:
                mods.append(VK["ctrl"])
            if shift_state & 4 and VK["alt"] not in mods:
                mods.append(VK["alt"])
        else:
            raise ActionError("unknown key name %r" % p)
    if key is None:  # a modifier alone, e.g. "Win"
        key = mods.pop()
    return mods, key


def _key_input(vk, up):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = vk
    inp.u.ki.wScan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    inp.u.ki.dwFlags = (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if vk in EXTENDED else 0)
    return inp


def _unicode_input(ch, up):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wScan = ord(ch)
    inp.u.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    return inp


def _send(inputs):
    if not inputs:
        return
    arr = (INPUT * len(inputs))(*inputs)
    n = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if n != len(inputs):
        raise ActionError("SendInput sent %d of %d events (error %d)" % (n, len(inputs), ctypes.get_last_error()))


def send_keys(chord):
    mods, key = parse_chord(chord)
    seq = [_key_input(m, False) for m in mods] + [_key_input(key, False), _key_input(key, True)] + \
          [_key_input(m, True) for m in reversed(mods)]
    _send(seq)
    log.debug("keys %r sent", chord)


def send_text(text, chunk=40):
    """Type text as Unicode. Newlines become Enter; tabs become Tab."""
    buf = []
    for ch in text:
        if ch == "\r":
            continue
        if ch == "\n":
            buf += [_key_input(0x0D, False), _key_input(0x0D, True)]
        elif ch == "\t":
            buf += [_key_input(0x09, False), _key_input(0x09, True)]
        else:
            if 0x10000 <= ord(ch):  # outside the BMP (emoji etc.): send the two UTF-16 code units
                enc = ch.encode("utf-16-le")
                for unit in (enc[:2], enc[2:]):
                    code = int.from_bytes(unit, "little")
                    for up in (False, True):
                        inp = INPUT()
                        inp.type = INPUT_KEYBOARD
                        inp.u.ki.wScan = code
                        inp.u.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
                        buf.append(inp)
            else:
                buf += [_unicode_input(ch, False), _unicode_input(ch, True)]
        if len(buf) >= chunk * 2:
            _send(buf)
            buf = []
            time.sleep(0.005)
    _send(buf)
    log.debug("text of %d characters typed", len(text))


def open_target(target, args=""):
    target = os.path.expandvars(target.strip())
    args = os.path.expandvars(args or "")
    r = shell32.ShellExecuteW(None, "open", target, args or None, None, SW_SHOWNORMAL)
    code = ctypes.cast(r, ctypes.c_void_p).value or 0
    if code <= 32:
        raise ActionError("could not open %r (ShellExecute error %d)" % (target, code))
    log.debug("opened %r %r", target, args)


def run_action(action, depth=0):
    t = action.get("type", "none")
    if t == "none":
        return
    if t == "text":
        send_text(str(action.get("text", "")))
    elif t == "keys":
        send_keys(str(action.get("keys", "")))
    elif t == "open":
        open_target(str(action.get("target", "")), str(action.get("args", "")))
    elif t == "delay":
        time.sleep(min(max(int(action.get("ms", 0)), 0), 60000) / 1000.0)
    elif t == "sequence":
        if depth > 0:
            raise ActionError("nested sequence")
        for step in action.get("steps", []):
            run_action(step, depth + 1)
            time.sleep(0.02)
    else:
        raise ActionError("unknown action type %r" % t)


class Executor:
    """Runs actions one after another on a worker thread so the input listener is never blocked."""

    def __init__(self):
        self.q = queue.Queue(maxsize=32)
        self.thread = threading.Thread(target=self._loop, name="actions", daemon=True)
        self.thread.start()

    def submit(self, key_id, action):
        try:
            self.q.put_nowait((key_id, action))
        except queue.Full:
            log.warning("action queue full; dropped action for %s", key_id)

    def _loop(self):
        while True:
            key_id, action = self.q.get()
            t0 = time.perf_counter()
            try:
                run_action(action)
                log.info("%s -> %s done in %d ms", key_id, describe(action, private=True),
                         (time.perf_counter() - t0) * 1000)
            except Exception as e:
                log.error("%s -> %s FAILED: %s", key_id, describe(action, private=True), e)


def describe(action, private=False):
    """Short description for the editor and the log.  private=True leaves out typed text (for the log file,
    which users are asked to send when they need help)."""
    t = action.get("type", "none")
    if t == "text":
        s = str(action.get("text", ""))
        if private:
            return "type a text of %d characters" % len(s)
        return "type %r" % (s if len(s) <= 30 else s[:27] + "...")
    if t == "keys":
        return "press %s" % action.get("keys", "")
    if t == "open":
        return "open %s %s" % (action.get("target", ""), action.get("args", "") or "")
    if t == "delay":
        return "wait %s ms" % action.get("ms", 0)
    if t == "sequence":
        return "sequence of %d steps" % len(action.get("steps", []))
    return "nothing"
