"""Optional: suppress the built-in Windows action of a native key (volume, media, browser, calculator, mail)
when the user has mapped that key to something else and ticked "block_windows_action".

Implemented with a low-level keyboard hook that swallows only the exact virtual keys listed.
It never touches any other key.  If the hook cannot be installed, the program carries on without it.
The hook must live on a thread with a message loop, so it is installed on the Raw Input listener thread.
"""
import ctypes
import ctypes.wintypes as w
import logging

log = logging.getLogger("igorskeys.hookblock")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
WH_KEYBOARD_LL = 13
LLKHF_INJECTED = 0x10


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", w.DWORD), ("scanCode", w.DWORD), ("flags", w.DWORD), ("time", w.DWORD),
                ("dwExtraInfo", ctypes.POINTER(w.ULONG))]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, w.WPARAM, w.LPARAM)
user32.SetWindowsHookExW.restype = w.HANDLE
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, w.HINSTANCE, w.DWORD]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.CallNextHookEx.argtypes = [w.HANDLE, ctypes.c_int, w.WPARAM, w.LPARAM]
user32.UnhookWindowsHookEx.argtypes = [w.HANDLE]
kernel32.GetModuleHandleW.restype = w.HMODULE
kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]


class Blocker:
    def __init__(self):
        self.blocked = set()
        self.hhook = None
        self._proc = HOOKPROC(self._hook)

    def set_blocked(self, vk_codes):
        """Update the set of virtual keys to swallow. Call install()/remove() on the listener thread as needed."""
        self.blocked = set(int(v) for v in vk_codes if v)

    def install(self):
        if self.hhook or not self.blocked:
            return
        self.hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        if not self.hhook:
            self.hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if self.hhook:
            log.info("blocking Windows' own action for virtual keys %s", sorted("0x%02X" % v for v in self.blocked))
        else:
            log.error("could not install keyboard hook (error %d); native keys will not be blocked",
                      ctypes.get_last_error())

    def remove(self):
        if self.hhook:
            user32.UnhookWindowsHookEx(self.hhook)
            self.hhook = None
            log.info("keyboard hook removed")

    def _hook(self, nCode, wParam, lParam):
        try:
            if nCode >= 0 and self.blocked:
                k = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if k.vkCode in self.blocked and not (k.flags & LLKHF_INJECTED):
                    return 1  # swallow: Windows' own action does not happen
        except Exception:
            log.exception("hook error (ignored)")
        return user32.CallNextHookEx(self.hhook, nCode, wParam, lParam)
