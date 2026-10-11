"""
Shows which VIRTUAL KEYS Windows itself generates for the keyboard's extra keys.

A WH_KEYBOARD_LL hook sees exactly the keyboard input that Windows synthesises
from consumer-control usages (VK_VOLUME_UP, VK_MEDIA_PLAY_PAUSE, VK_BROWSER_BACK, ...).
An extra key that shows up here is handled natively by Windows; one that does not
show up is invisible to Windows and to AutoHotkey.  Results -> discovery/vk_check.json
"""
import ctypes, ctypes.wintypes as w, json, os, time, tkinter as tk
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vk_check.json")
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
LLKHF_INJECTED = 0x10

VK = {0xA6: "VK_BROWSER_BACK", 0xA7: "VK_BROWSER_FORWARD", 0xA8: "VK_BROWSER_REFRESH", 0xA9: "VK_BROWSER_STOP",
      0xAA: "VK_BROWSER_SEARCH", 0xAB: "VK_BROWSER_FAVORITES", 0xAC: "VK_BROWSER_HOME", 0xAD: "VK_VOLUME_MUTE",
      0xAE: "VK_VOLUME_DOWN", 0xAF: "VK_VOLUME_UP", 0xB0: "VK_MEDIA_NEXT_TRACK", 0xB1: "VK_MEDIA_PREV_TRACK",
      0xB2: "VK_MEDIA_STOP", 0xB3: "VK_MEDIA_PLAY_PAUSE", 0xB4: "VK_LAUNCH_MAIL", 0xB5: "VK_LAUNCH_MEDIA_SELECT",
      0xB6: "VK_LAUNCH_APP1", 0xB7: "VK_LAUNCH_APP2", 0x5F: "VK_SLEEP", 0x70: "VK_F1", 0x75: "VK_F6",
      0xFF: "VK__ (0xFF, unknown)"}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", w.DWORD), ("scanCode", w.DWORD), ("flags", w.DWORD), ("time", w.DWORD),
                ("dwExtraInfo", ctypes.POINTER(w.ULONG))]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, w.WPARAM, w.LPARAM)
user32.SetWindowsHookExW.restype = w.HANDLE
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, w.HINSTANCE, w.DWORD]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.CallNextHookEx.argtypes = [w.HANDLE, ctypes.c_int, w.WPARAM, w.LPARAM]
kernel32.GetModuleHandleW.restype = w.HMODULE
kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]

for _i in range(12):
    VK[0x70 + _i] = "VK_F%d" % (_i + 1)
events = []
seen = {}


class App:
    def __init__(self, root):
        self.root = root
        root.title("Windows virtual-key check")
        root.geometry("760x520+140+100")
        root.attributes("-topmost", True)
        f = ttk.Frame(root, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Press every extra key once (volume, mute, media, internet, calculator, e-mail, browser, "
                          "play/pause, stop, prev, next, eject, and the 10 side keys).\nKeys that Windows handles itself "
                          "appear below as a virtual key. Keys that do not appear are invisible to Windows.\n"
                          "Close the window when done.", font=("Segoe UI", 10), wraplength=730).pack(anchor="w")
        self.text = tk.Text(f, height=22, font=("Consolas", 10), state="disabled")
        self.text.pack(fill="both", expand=True, pady=8)
        self.proc = HOOKPROC(self.hook)
        self.hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.proc, kernel32.GetModuleHandleW(None), 0)
        if not self.hhook:
            err = ctypes.get_last_error() or kernel32.GetLastError()
            self.hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.proc, None, 0)
            self.line("first attempt failed (error %d), retry with NULL module: %s" % (err, bool(self.hhook)))
        self.line("hook installed: %s" % bool(self.hhook))
        root.protocol("WM_DELETE_WINDOW", self.finish)
        root.after(100, self.tick)

    def line(self, s):
        self.text.configure(state="normal")
        self.text.insert("end", s + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def hook(self, nCode, wParam, lParam):
        if nCode >= 0:
            k = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            ev = {"t": time.time(), "vk": k.vkCode, "scan": k.scanCode, "flags": k.flags,
                  "down": wParam in (WM_KEYDOWN, WM_SYSKEYDOWN), "injected": bool(k.flags & LLKHF_INJECTED)}
            events.append(ev)
        return user32.CallNextHookEx(self.hhook, nCode, wParam, lParam)

    def tick(self):
        while events:
            ev = events.pop(0)
            if ev["down"]:
                name = VK.get(ev["vk"], "vk 0x%02X" % ev["vk"])
                if ev["vk"] in VK or ev["vk"] >= 0xA6 or ev["scan"] == 0:
                    seen.setdefault(name, 0)
                    seen[name] += 1
                    self.line("KEY DOWN  %-24s scan=0x%02X flags=0x%02X%s" % (
                        name, ev["scan"], ev["flags"], "  (injected)" if ev["injected"] else ""))
        self.root.after(50, self.tick)

    def finish(self):
        if self.hhook:
            user32.UnhookWindowsHookEx(self.hhook)
        json.dump({"seen_virtual_keys": seen, "captured": time.strftime("%Y-%m-%d %H:%M:%S")},
                  open(OUT, "w", encoding="utf-8"), indent=2)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
