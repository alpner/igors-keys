"""
Raw Input logger for the Cherry CyMotion Master XPress (046a:0023).

Captures WM_INPUT from ALL top-level collections the keyboard exposes
(keyboard 01/06, consumer control 0C/01, system control 01/80) plus any
vendor-defined pages, using RIDEV_INPUTSINK so it works in the background.

Modes:
  python rawinput_logger.py monitor [seconds]     log everything, no prompts
  python rawinput_logger.py interactive           guided per-key capture -> keymap.json

All events go to discovery/rawinput_log.jsonl (timestamp, collection, raw bytes).
"""
import ctypes, ctypes.wintypes as w, threading, time, json, sys, os, re, queue

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "rawinput_log.jsonl")
KEYMAP_PATH = os.path.join(HERE, "keymap.json")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user32.CreateWindowExW.restype = w.HWND
user32.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID]
user32.GetRawInputData.argtypes = [w.HANDLE, w.UINT, w.LPVOID, ctypes.POINTER(w.UINT), w.UINT]
user32.GetRawInputDeviceInfoW.argtypes = [w.HANDLE, w.UINT, w.LPVOID, ctypes.POINTER(w.UINT)]
user32.GetRawInputDeviceList.argtypes = [w.LPVOID, ctypes.POINTER(w.UINT), w.UINT]
kernel32.GetModuleHandleW.restype = w.HMODULE

WM_INPUT = 0x00FF
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
RIDEV_INPUTSINK = 0x00000100
RIDEV_PAGEONLY = 0x00000020
RIM_TYPEMOUSE, RIM_TYPEKEYBOARD, RIM_TYPEHID = 0, 1, 2
RID_INPUT = 0x10000003
RIDI_DEVICENAME = 0x20000007
RIDI_DEVICEINFO = 0x2000000B
RI_KEY_BREAK = 1
RI_KEY_E0 = 2
RI_KEY_E1 = 4
VK_RETURN = 0x0D


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", w.USHORT), ("usUsage", w.USHORT), ("dwFlags", w.DWORD), ("hwndTarget", w.HWND)]


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [("hDevice", w.HANDLE), ("dwType", w.DWORD)]


class RID_DEVICE_INFO_HID(ctypes.Structure):
    _fields_ = [("dwVendorId", w.DWORD), ("dwProductId", w.DWORD), ("dwVersionNumber", w.DWORD),
                ("usUsagePage", w.USHORT), ("usUsage", w.USHORT)]


class RID_DEVICE_INFO_KEYBOARD(ctypes.Structure):
    _fields_ = [("dwType", w.DWORD), ("dwSubType", w.DWORD), ("dwKeyboardMode", w.DWORD),
                ("dwNumberOfFunctionKeys", w.DWORD), ("dwNumberOfIndicators", w.DWORD),
                ("dwNumberOfKeysTotal", w.DWORD)]


class RID_DEVICE_INFO_MOUSE(ctypes.Structure):
    _fields_ = [("dwId", w.DWORD), ("dwNumberOfButtons", w.DWORD), ("dwSampleRate", w.DWORD),
                ("fHasHorizontalWheel", w.BOOL)]


class RID_DEVICE_INFO_U(ctypes.Union):
    _fields_ = [("mouse", RID_DEVICE_INFO_MOUSE), ("keyboard", RID_DEVICE_INFO_KEYBOARD), ("hid", RID_DEVICE_INFO_HID)]


class RID_DEVICE_INFO(ctypes.Structure):
    _fields_ = [("cbSize", w.DWORD), ("dwType", w.DWORD), ("u", RID_DEVICE_INFO_U)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", w.HINSTANCE), ("hIcon", w.HANDLE), ("hCursor", w.HANDLE), ("hbrBackground", w.HANDLE),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


HEADER_SIZE = ctypes.sizeof(w.DWORD) * 2 + ctypes.sizeof(w.HANDLE) + ctypes.sizeof(w.WPARAM)  # 24 on x64

CONSUMER_USAGE_NAMES = {
    0x00B0: "Play", 0x00B1: "Pause", 0x00B2: "Record", 0x00B3: "Fast Forward", 0x00B4: "Rewind",
    0x00B5: "Scan Next Track", 0x00B6: "Scan Previous Track", 0x00B7: "Stop", 0x00B8: "Eject",
    0x00CD: "Play/Pause", 0x00E2: "Mute", 0x00E9: "Volume Increment", 0x00EA: "Volume Decrement",
    0x0183: "AL Consumer Control Configuration (Media player)", 0x018A: "AL Email Reader",
    0x0192: "AL Calculator", 0x0194: "AL Local Machine Browser (My Computer)",
    0x0221: "AC Search", 0x0223: "AC Home", 0x0224: "AC Back", 0x0225: "AC Forward", 0x0226: "AC Stop",
    0x0227: "AC Refresh", 0x022A: "AC Bookmarks/Favorites", 0x0030: "Power", 0x0032: "Sleep",
    0x0201: "AC New", 0x0202: "AC Open (Cherry driver: System Sleep)", 0x0203: "AC Close",
    0x0204: "AC Exit (Cherry driver: WakeUp)", 0x0207: "AC Save", 0x0208: "AC Print",
    0x021A: "AC Undo", 0x021B: "AC Copy", 0x021C: "AC Cut", 0x021D: "AC Paste", 0x021E: "AC Select All",
    0x021F: "AC Find", 0x0233: "AC Scroll Up", 0x0234: "AC Scroll Down", 0x0279: "AC Redo/Repeat",
    0x0301: "(reserved 0x301 -> Cherry XPress1 / Linux PROG1)", 0x0302: "(reserved 0x302 -> Cherry XPress2 / Linux PROG2)",
    0x0303: "(reserved 0x303 -> Cherry XPress3 / Linux PROG3)",
}
SYSTEM_USAGE_NAMES = {0x81: "System Power Down", 0x82: "System Sleep", 0x83: "System Wake Up"}

_devinfo_cache = {}


def device_info(hdev):
    """Return dict with name, type, vid/pid, usage page/usage for a raw-input device handle."""
    if hdev in _devinfo_cache:
        return _devinfo_cache[hdev]
    info = {"handle": hdev}
    size = w.UINT(0)
    user32.GetRawInputDeviceInfoW(hdev, RIDI_DEVICENAME, None, ctypes.byref(size))
    buf = ctypes.create_unicode_buffer(size.value + 1)
    user32.GetRawInputDeviceInfoW(hdev, RIDI_DEVICENAME, buf, ctypes.byref(size))
    info["name"] = buf.value
    di = RID_DEVICE_INFO()
    di.cbSize = ctypes.sizeof(RID_DEVICE_INFO)
    size = w.UINT(di.cbSize)
    if user32.GetRawInputDeviceInfoW(hdev, RIDI_DEVICEINFO, ctypes.byref(di), ctypes.byref(size)) > 0:
        info["type"] = di.dwType
        if di.dwType == RIM_TYPEHID:
            info.update(vid=di.u.hid.dwVendorId, pid=di.u.hid.dwProductId,
                        usage_page=di.u.hid.usUsagePage, usage=di.u.hid.usUsage)
        elif di.dwType == RIM_TYPEKEYBOARD:
            info.update(usage_page=1, usage=6, kbd_type=di.u.keyboard.dwType,
                        kbd_subtype=di.u.keyboard.dwSubType, num_keys=di.u.keyboard.dwNumberOfKeysTotal)
    m = re.search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", info["name"])
    if m:
        info["vid"] = int(m.group(1), 16)
        info["pid"] = int(m.group(2), 16)
    m = re.search(r"MI_(\d\d)", info["name"])
    info["interface"] = int(m.group(1)) if m else None
    m = re.search(r"Col(\d\d)", info["name"], re.I)
    info["collection_index"] = int(m.group(1)) if m else None
    up, u = info.get("usage_page"), info.get("usage")
    names = {(1, 6): "keyboard(01/06)", (0x0C, 1): "consumer(0C/01)", (1, 0x80): "system(01/80)"}
    if (up, u) in names:
        info["collection"] = names[(up, u)]
    elif up is not None:
        info["collection"] = "page%#06x/usage%#06x" % (up, u)
    else:
        info["collection"] = "unknown"
    _devinfo_cache[hdev] = info
    return info


def decode_event(ev):
    """Add a human-readable decode to an event dict."""
    col = ev["collection"]
    if ev["type"] == "keyboard":
        flags = ev["flags"]
        ev["decoded"] = "%s scan=0x%02X%s%s vkey=0x%02X msg=0x%04X" % (
            "BREAK(up)" if flags & RI_KEY_BREAK else "MAKE(down)", ev["make_code"],
            " E0" if flags & RI_KEY_E0 else "", " E1" if flags & RI_KEY_E1 else "", ev["vkey"], ev["message"])
    elif col.startswith("consumer") and len(ev["bytes"]) >= 6:
        data = bytes.fromhex(ev["bytes"])
        usage = data[1] | (data[2] << 8)
        name = CONSUMER_USAGE_NAMES.get(usage, "(not in HUT consumer table)" if usage else "release/none")
        ev["usage"] = usage
        ev["decoded"] = "report_id=%d consumer usage=0x%04X %s" % (data[0], usage, name)
        if usage > 0x23C:
            ev["decoded"] += "  ** OUT OF DESCRIPTOR RANGE (max 0x23C) -> Windows HID parser drops it **"
    elif col.startswith("system") and len(ev["bytes"]) >= 4:
        data = bytes.fromhex(ev["bytes"])
        bits = data[1]
        names = [SYSTEM_USAGE_NAMES[0x81 + i] for i in range(3) if bits & (1 << i)]
        ev["decoded"] = "report_id=%d system control bits=0x%02X %s" % (data[0], bits, names or "release/none")
    else:
        ev["decoded"] = "raw HID report"
    return ev


class RawInputCapture:
    def __init__(self, only_vid=0x046A, log_path=LOG_PATH, echo=True):
        self.only_vid = only_vid
        self.events = queue.Queue()
        self.log = open(log_path, "a", encoding="utf-8")
        self.echo = echo
        self.t0 = time.perf_counter()
        self.ready = threading.Event()
        self.error = None
        self.hwnd = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.all_count = 0

    def start(self):
        self.thread.start()
        self.ready.wait(5)
        if self.error:
            raise self.error
        return self

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        self.thread.join(2)
        self.log.close()

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            try:
                self._on_input(lparam)
            except Exception as e:  # never let an unexpected report kill the loop
                print("!! error handling WM_INPUT:", repr(e))
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _on_input(self, lparam):
        size = w.UINT(0)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), HEADER_SIZE)
        buf = ctypes.create_string_buffer(size.value)
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size), HEADER_SIZE) != size.value:
            return
        raw = buf.raw
        dwType = int.from_bytes(raw[0:4], "little")
        hDevice = int.from_bytes(raw[8:16], "little")
        info = device_info(hDevice) if hDevice else {"name": "(no device)", "collection": "unknown"}
        self.all_count += 1
        ts = time.perf_counter() - self.t0
        ev = {"t": round(ts, 6), "wall": time.strftime("%H:%M:%S"), "device": info.get("name"),
              "vid": info.get("vid"), "pid": info.get("pid"), "collection": info["collection"],
              "interface": info.get("interface")}
        if dwType == RIM_TYPEKEYBOARD:
            k = raw[HEADER_SIZE:HEADER_SIZE + 16]
            ev.update(type="keyboard", make_code=int.from_bytes(k[0:2], "little"),
                      flags=int.from_bytes(k[2:4], "little"), vkey=int.from_bytes(k[6:8], "little"),
                      message=int.from_bytes(k[8:12], "little"), extra=int.from_bytes(k[12:16], "little"),
                      bytes=k.hex())
        elif dwType == RIM_TYPEHID:
            szhid = int.from_bytes(raw[HEADER_SIZE:HEADER_SIZE + 4], "little")
            count = int.from_bytes(raw[HEADER_SIZE + 4:HEADER_SIZE + 8], "little")
            data = raw[HEADER_SIZE + 8:HEADER_SIZE + 8 + szhid * count]
            ev.update(type="hid", report_size=szhid, report_count=count, bytes=data.hex())
        else:
            ev.update(type="mouse", bytes=raw[HEADER_SIZE:].hex())
        if self.only_vid is not None and ev.get("vid") != self.only_vid:
            return
        decode_event(ev)
        self.log.write(json.dumps(ev) + "\n")
        self.log.flush()
        self.events.put(ev)
        if self.echo:
            print("  [%9.3f] %-16s %-32s %s" % (ev["t"], ev["collection"], ev["bytes"], ev["decoded"]))

    def _run(self):
        try:
            hinst = kernel32.GetModuleHandleW(None)
            self._proc = WNDPROC(self._wndproc)
            wc = WNDCLASSW()
            wc.lpfnWndProc = self._proc
            wc.hInstance = hinst
            wc.lpszClassName = "CherryRawInputLogger"
            if not user32.RegisterClassW(ctypes.byref(wc)):
                raise ctypes.WinError()
            self.hwnd = user32.CreateWindowExW(0, "CherryRawInputLogger", "CherryRawInputLogger", 0,
                                               0, 0, 0, 0, None, None, hinst, None)
            if not self.hwnd:
                raise ctypes.WinError()
            # Register for every page/usage the device exposes plus whole vendor pages, with INPUTSINK.
            targets = [(0x01, 0x06), (0x0C, 0x01), (0x01, 0x80)]
            rids = (RAWINPUTDEVICE * (len(targets) + 1))()
            for i, (up, u) in enumerate(targets):
                rids[i] = RAWINPUTDEVICE(up, u, RIDEV_INPUTSINK, self.hwnd)
            rids[len(targets)] = RAWINPUTDEVICE(0xFF00, 0, RIDEV_INPUTSINK | RIDEV_PAGEONLY, self.hwnd)
            if not user32.RegisterRawInputDevices(rids, len(rids), ctypes.sizeof(RAWINPUTDEVICE)):
                rids2 = (RAWINPUTDEVICE * len(targets))(
                    *[RAWINPUTDEVICE(up, u, RIDEV_INPUTSINK, self.hwnd) for up, u in targets])
                if not user32.RegisterRawInputDevices(rids2, len(rids2), ctypes.sizeof(RAWINPUTDEVICE)):
                    raise ctypes.WinError()
        except Exception as e:
            self.error = e
            self.ready.set()
            return
        self.ready.set()
        msg = w.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


def list_devices():
    n = w.UINT(0)
    user32.GetRawInputDeviceList(None, ctypes.byref(n), ctypes.sizeof(RAWINPUTDEVICELIST))
    arr = (RAWINPUTDEVICELIST * n.value)()
    user32.GetRawInputDeviceList(arr, ctypes.byref(n), ctypes.sizeof(RAWINPUTDEVICELIST))
    out = []
    for d in arr:
        info = device_info(d.hDevice)
        if info.get("vid") == 0x046A:
            out.append(info)
    return out


def drain(q):
    items = []
    while True:
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            return items


# ---- Keys to capture (names follow KeyM@n's own labels where known) ----
KEY_PLAN = [
    ("XPress side keys (the column of 10 keys)", ["XPress %d" % i for i in range(1, 11)]),
    ("Main keys (4)", ["Main key 1", "Main key 2", "Main key 3", "Main key 4"]),
    ("Premium keys (4)", ["Premium key 1", "Premium key 2", "Premium key 3", "Premium key 4"]),
    ("Internet keys", ["WWW / Home", "E-Mail", "Search", "Favorites", "Back", "Forward", "Refresh/Reload"]),
    ("Multimedia keys", ["Play/Pause", "Stop", "Previous Title", "Next Title", "Volume -", "Volume +", "Mute",
                         "Multimedia (player)"]),
    ("System / other", ["Calculator", "My Computer / My Documents", "Standby / Sleep", "Power", "Lock / Keylock",
                        "KeyM@n key (alone)"]),
    ("KeyM@n key combined with F-keys (hold KeyM@n, tap F-key)", ["KeyM@n + F%d" % i for i in range(1, 13)]),
]


def is_release(e):
    if e["type"] == "keyboard":
        return bool(e["flags"] & RI_KEY_BREAK)
    data = bytes.fromhex(e["bytes"])
    return all(b == 0 for b in data[1:])


def sig(e):
    s = {"collection": e["collection"], "bytes": e["bytes"], "decoded": e["decoded"]}
    if e["type"] == "keyboard":
        s.update(scan=e["make_code"], e0=bool(e["flags"] & RI_KEY_E0), vkey=e["vkey"])
    if "usage" in e:
        s["usage"] = e["usage"]
    return s


def save_keymap(keymap):
    doc = {"device": "Cherry CyMotion Master XPress G86-21050, USB 046A:0023",
           "captured": time.strftime("%Y-%m-%d %H:%M:%S"),
           "signature_format": "collection + raw report bytes (hex, report-id first) for press and release; "
                               "keyboard events carry scan code/E0 flag/vkey",
           "keys": keymap}
    with open(KEYMAP_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def interactive():
    cap = RawInputCapture(echo=True).start()
    print("Cherry raw-input devices seen by Windows:")
    for d in list_devices():
        print("   %-16s %s" % (d["collection"], d["name"]))
    print()
    print("For each key: press it ONCE (press and release), then hit ENTER in this window.")
    print("Type  s  then ENTER to skip a key,  r  to redo the previous key,  a  to add a key with your own name,")
    print("      q  to finish early.  If a key does not physically exist, skip it.")
    print("If pressing the key types characters here, that is fine - just hit ENTER afterwards.\n")
    keymap = {}
    if os.path.exists(KEYMAP_PATH):
        try:
            keymap = json.load(open(KEYMAP_PATH, encoding="utf-8")).get("keys", {})
            print("(loaded %d previously captured keys from keymap.json; recaptured keys overwrite)\n" % len(keymap))
        except Exception:
            keymap = {}
    queue_of_keys = []
    for group, keys in KEY_PLAN:
        for k in keys:
            queue_of_keys.append((group, k))
    i = 0
    last = None
    while i < len(queue_of_keys):
        group, name = queue_of_keys[i]
        print("\n=== [%d/%d] %s" % (i + 1, len(queue_of_keys), group))
        print(">>> Press  %s  now, then ENTER: " % name, end="", flush=True)
        drain(cap.events)
        try:
            typed = input()
        except EOFError:
            break
        cmd = typed.strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            print("   skipped")
            i += 1
            continue
        if cmd == "r":
            if last is not None:
                i = last
            continue
        if cmd == "a":
            custom = input("   name for the extra key: ").strip()
            if custom:
                queue_of_keys.insert(i, ("Custom", custom))
            continue
        time.sleep(0.25)  # let the release report of a slow key arrive
        evs = [e for e in drain(cap.events) if not (e["type"] == "keyboard" and e["vkey"] == VK_RETURN)]
        if not evs:
            print("   !! nothing was received from the keyboard for this key (type r to retry, s to skip)")
            keymap[name] = {"group": group, "events": [], "typed_text": typed, "note": "no raw input received"}
        else:
            press = [e for e in evs if not is_release(e)]
            release = [e for e in evs if is_release(e)]
            keymap[name] = {"group": group, "typed_text": typed,
                            "press": [sig(e) for e in press], "release": [sig(e) for e in release],
                            "events": evs}
            print("   captured %d event(s): " % len(evs) +
                  "; ".join("%s %s" % (e["collection"], e["bytes"]) for e in evs))
        last = i
        i += 1
        save_keymap(keymap)
    save_keymap(keymap)
    cap.stop()
    print("\nDone. %d keys recorded in %s. You can close this window." % (len(keymap), KEYMAP_PATH))
    try:
        input("Press ENTER to exit.")
    except EOFError:
        pass


def monitor(seconds):
    cap = RawInputCapture(echo=True).start()
    print("Cherry raw-input devices seen by Windows:")
    for d in list_devices():
        print("   %-16s %s" % (d["collection"], d["name"]))
    print("\nMonitoring all Cherry collections for %ss (events also appended to %s) ..." % (seconds, LOG_PATH))
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(0.2)
    cap.stop()
    print("monitor finished; total WM_INPUT messages seen (all devices): %d" % cap.all_count)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
    if mode == "monitor":
        monitor(float(sys.argv[2]) if len(sys.argv) > 2 else 30)
    else:
        interactive()
