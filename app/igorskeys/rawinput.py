"""Raw Input listener for the keyboard's consumer-control collection (usage page 0x0C, usage 0x01).

Only that collection is registered, with RIDEV_INPUTSINK, so the program sees the extra keys
no matter which window is active and never touches the normal keyboard collection.
Raw Input is observation only: it cannot swallow or alter input, by design.

Every unexpected report or exception is logged and ignored; the loop never dies.
"""
import ctypes
import ctypes.wintypes as w
import logging
import re
import threading

log = logging.getLogger("igorskeys.rawinput")

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
user32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
kernel32.GetModuleHandleW.restype = w.HMODULE
kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]

WM_INPUT = 0x00FF
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_APP_RUN = 0x8001          # posted to run a callable on the listener thread
RIDEV_INPUTSINK = 0x00000100
RIM_TYPEHID = 2
RID_INPUT = 0x10000003
RIDI_DEVICENAME = 0x20000007
HEADER_SIZE = 24  # RAWINPUTHEADER on x64


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", w.USHORT), ("usUsage", w.USHORT), ("dwFlags", w.DWORD), ("hwndTarget", w.HWND)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", w.HINSTANCE), ("hIcon", w.HANDLE), ("hCursor", w.HANDLE), ("hbrBackground", w.HANDLE),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


class Listener:
    """Calls on_report(report_bytes) for every HID report from the configured device.

    on_report runs on the listener thread; keep it quick (the executor hands work to its own thread).
    """

    def __init__(self, vid, pid, usage_page, usage, on_report):
        self.vid, self.pid, self.usage_page, self.usage = vid, pid, usage_page, usage
        self.on_report = on_report
        self.hwnd = None
        self.thread = None
        self.ready = threading.Event()
        self.error = None
        self._names = {}
        self._pending = []
        self._pending_lock = threading.Lock()
        self.reports_seen = 0
        self.reports_matched = 0

    # ---- lifecycle ----
    def start(self):
        self.thread = threading.Thread(target=self._run, name="rawinput", daemon=True)
        self.thread.start()
        self.ready.wait(5)
        if self.error:
            raise self.error
        return self

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        if self.thread:
            self.thread.join(3)

    def run_on_thread(self, fn):
        """Run fn() on the listener thread (needed for installing hooks that require a message loop)."""
        with self._pending_lock:
            self._pending.append(fn)
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_APP_RUN, 0, 0)

    # ---- internals ----
    def _device_matches(self, hdev):
        if hdev in self._names:
            return self._names[hdev]
        size = w.UINT(0)
        user32.GetRawInputDeviceInfoW(hdev, RIDI_DEVICENAME, None, ctypes.byref(size))
        buf = ctypes.create_unicode_buffer(size.value + 1)
        user32.GetRawInputDeviceInfoW(hdev, RIDI_DEVICENAME, buf, ctypes.byref(size))
        name = buf.value
        m = re.search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", name)
        ok = bool(m) and int(m.group(1), 16) == self.vid and int(m.group(2), 16) == self.pid
        log.info("raw input device %s -> %s", name, "this keyboard" if ok else "ignored")
        self._names[hdev] = ok
        return ok

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_INPUT:
                self._on_input(lparam)
                return 0
            if msg == WM_APP_RUN:
                with self._pending_lock:
                    fns, self._pending = self._pending, []
                for fn in fns:
                    try:
                        fn()
                    except Exception:
                        log.exception("deferred call failed")
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            log.exception("error in window procedure (ignored)")
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _on_input(self, lparam):
        size = w.UINT(0)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), HEADER_SIZE)
        if size.value == 0 or size.value > 4096:
            return
        buf = ctypes.create_string_buffer(size.value)
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size), HEADER_SIZE) != size.value:
            return
        raw = buf.raw
        if int.from_bytes(raw[0:4], "little") != RIM_TYPEHID:
            return
        hdev = int.from_bytes(raw[8:16], "little")
        if not hdev or not self._device_matches(hdev):
            return
        szhid = int.from_bytes(raw[HEADER_SIZE:HEADER_SIZE + 4], "little")
        count = int.from_bytes(raw[HEADER_SIZE + 4:HEADER_SIZE + 8], "little")
        data = raw[HEADER_SIZE + 8:HEADER_SIZE + 8 + szhid * count]
        for i in range(count):
            report = data[i * szhid:(i + 1) * szhid]
            self.reports_seen += 1
            try:
                if self.on_report(report):
                    self.reports_matched += 1
            except Exception:
                log.exception("report handler failed for %s (ignored)", report.hex())

    def _run(self):
        try:
            hinst = kernel32.GetModuleHandleW(None)
            self._proc = WNDPROC(self._wndproc)
            wc = WNDCLASSW()
            wc.lpfnWndProc = self._proc
            wc.hInstance = hinst
            wc.lpszClassName = "IgorsKeysRawInput"
            if not user32.RegisterClassW(ctypes.byref(wc)):
                raise ctypes.WinError()
            self.hwnd = user32.CreateWindowExW(0, "IgorsKeysRawInput", "IgorsKeysRawInput", 0, 0, 0, 0, 0,
                                               None, None, hinst, None)
            if not self.hwnd:
                raise ctypes.WinError()
            rid = (RAWINPUTDEVICE * 1)(RAWINPUTDEVICE(self.usage_page, self.usage, RIDEV_INPUTSINK, self.hwnd))
            if not user32.RegisterRawInputDevices(rid, 1, ctypes.sizeof(RAWINPUTDEVICE)):
                raise ctypes.WinError()
            log.info("listening on usage page 0x%02X usage 0x%02X for VID %04X PID %04X",
                     self.usage_page, self.usage, self.vid, self.pid)
        except Exception as e:
            self.error = e
            self.ready.set()
            return
        self.ready.set()
        msg = w.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        log.info("listener stopped")
