"""
One-key-at-a-time capture window for the Cherry CyMotion Master XPress.

Nothing is recorded until you click the big button.  Then the next key you press
(press + release) is recorded, the window names it from the driver table, and it
disarms again - so typing elsewhere never pollutes the capture.

Raw Input with RIDEV_INPUTSINK means this window never needs keyboard focus.
Writes discovery/keymap.json after every key.  Reuses rawinput_logger.py.
"""
import json, os, sys, time, queue, tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rawinput_logger import RawInputCapture, KEYMAP_PATH, is_release, sig, save_keymap, list_devices

QUIET_MS = 800   # after the first press, wait this long with no new events, then record
ARM_TIMEOUT_S = 20


class App:
    def __init__(self, root):
        self.root = root
        root.title("Cherry key capture")
        root.geometry("820x640+100+60")
        root.attributes("-topmost", True)
        self.cap = RawInputCapture(echo=False).start()
        self.keymap = {}
        if os.path.exists(KEYMAP_PATH):
            try:
                self.keymap = json.load(open(KEYMAP_PATH, encoding="utf-8")).get("keys", {})
            except Exception:
                self.keymap = {}
        self.armed = False
        self.armed_at = 0
        self.pending = []
        self.last_event_t = None

        f = ttk.Frame(root, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="How it works: 1) type a short description of the key (optional)   2) click the green button   "
                          "3) press that ONE key on the keyboard.\nThe window records it, names it, and waits for the next "
                          "click. Nothing is recorded while the button is not armed, so you can type elsewhere freely.",
                  font=("Segoe UI", 10), wraplength=790).pack(anchor="w")

        row = ttk.Frame(f)
        row.pack(fill="x", pady=(10, 4))
        ttk.Label(row, text="Key description (what is printed on it / where it is):").pack(side="left")
        self.desc = ttk.Entry(row, width=48)
        self.desc.pack(side="left", padx=6, fill="x", expand=True)

        self.combo = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="This is a combination: I will HOLD the KeyM@n key and tap another key "
                                "(records everything until the keys are quiet)", variable=self.combo).pack(anchor="w")

        self.arm_btn = tk.Button(f, text="CLICK HERE, THEN PRESS THE KEY", font=("Segoe UI", 16, "bold"),
                                 bg="#1a9c4b", fg="white", activebackground="#157a3b", height=2, command=self.arm)
        self.arm_btn.pack(fill="x", pady=8)
        self.status = ttk.Label(f, text="Not armed. Click the green button when you are ready.",
                                font=("Segoe UI", 12, "bold"))
        self.status.pack(anchor="w")
        self.result = ttk.Label(f, text="", font=("Segoe UI", 12), foreground="#0a5", wraplength=790)
        self.result.pack(anchor="w", pady=(2, 6))

        b = ttk.Frame(f)
        b.pack(fill="x", pady=4)
        ttk.Button(b, text="Undo last recording", command=self.undo).pack(side="left", padx=4)
        ttk.Button(b, text="Finish and save", command=self.finish).pack(side="right", padx=4)

        ttk.Label(f, text="Recorded keys:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(f, height=9, font=("Consolas", 9))
        self.listbox.pack(fill="x")
        ttk.Label(f, text="Raw events (for reference, newest at the bottom):", font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        self.log = tk.Text(f, height=7, font=("Consolas", 8), state="disabled", wrap="none")
        self.log.pack(fill="both", expand=True)

        self.order = list(self.keymap.keys())
        self.refresh_list()
        devs = list_devices()
        self.logline("Cherry collections visible to Raw Input: " + ", ".join(d["collection"] for d in devs))
        root.after(50, self.poll)
        root.protocol("WM_DELETE_WINDOW", self.finish)

    # ---------- helpers ----------
    def logline(self, s):
        self.log.configure(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def refresh_list(self):
        self.listbox.delete(0, "end")
        for k in self.order:
            v = self.keymap.get(k, {})
            self.listbox.insert("end", "%-34s = %s" % (k[:34], v.get("auto_name") or v.get("note") or
                                                      " | ".join(p["decoded"] for p in v.get("press", []))))
        self.listbox.see("end")

    @staticmethod
    def auto_name(press):
        parts = []
        for e in press:
            if "consumer" in e["collection"]:
                parts.append(e["decoded"].split(" consumer usage=")[-1].split("  **")[0])
            elif e["type"] == "keyboard":
                parts.append("keyboard scan 0x%02X%s vkey 0x%02X" % (e["make_code"], " E0" if e["flags"] & 2 else "", e["vkey"]))
            else:
                parts.append(e["decoded"])
        return ", ".join(parts) if parts else "(nothing received)"

    # ---------- actions ----------
    def arm(self):
        self.armed = True
        self.armed_at = time.time()
        self.pending = []
        self.last_event_t = None
        self.arm_btn.configure(bg="#d9a400", text="ARMED - PRESS THE KEY NOW")
        self.status.configure(text="ARMED: press the key now (one press, then let go)." if not self.combo.get()
                              else "ARMED: hold KeyM@n, tap the other key, release both.")
        self.result.configure(text="")

    def disarm(self):
        self.armed = False
        self.arm_btn.configure(bg="#1a9c4b", text="CLICK HERE, THEN PRESS THE KEY")

    def poll(self):
        try:
            while True:
                ev = self.cap.events.get_nowait()
                self.logline("[%8.3f] %-16s %-10s %s" % (ev["t"], ev["collection"], ev["bytes"], ev["decoded"]))
                if not self.armed:
                    continue
                if not self.pending and is_release(ev):
                    continue
                self.pending.append(ev)
                self.last_event_t = time.time()
                self.status.configure(text="got %d event(s) ... let go of the key" % len(self.pending))
        except queue.Empty:
            pass
        if self.armed:
            if self.pending and self.last_event_t and (time.time() - self.last_event_t) * 1000 >= QUIET_MS:
                self.commit()
            elif not self.pending and time.time() - self.armed_at > ARM_TIMEOUT_S:
                self.disarm()
                self.status.configure(text="Nothing arrived within %d s - this key sends nothing Windows can see. "
                                           "Recorded as 'no signal'." % ARM_TIMEOUT_S)
                self.record([], note="no raw input received within %d s" % ARM_TIMEOUT_S)
        self.root.after(50, self.poll)

    def commit(self):
        self.disarm()
        self.record(self.pending)
        self.pending = []

    def record(self, evs, note=None):
        desc = self.desc.get().strip()
        press = [e for e in evs if not is_release(e)]
        release = [e for e in evs if is_release(e)]
        auto = self.auto_name(press)
        same = [k for k, v in self.keymap.items() if press and
                [p["bytes"] for p in v.get("press", [])] == [e["bytes"] for e in press]]
        base = desc or ("KeyM@n combo" if self.combo.get() else "Key")
        name = base
        n = 2
        while name in self.keymap:
            name = "%s (%d)" % (base, n)
            n += 1
        self.keymap[name] = {"group": "KeyM@n combination" if self.combo.get() else "extra key", "description": desc,
                             "press": [sig(e) for e in press], "release": [sig(e) for e in release],
                             "events": evs, "auto_name": auto, "same_as": same}
        if note:
            self.keymap[name]["note"] = note
        self.order.append(name)
        save_keymap(self.keymap)
        self.refresh_list()
        txt = "Recorded '%s' = %s" % (name, auto)
        if same:
            txt += "\n(this is the same signal as: %s)" % ", ".join(same)
        self.result.configure(text=txt)
        self.status.configure(text="Saved. Describe the next key (optional) and click the green button again.")
        self.desc.delete(0, "end")
        self.combo.set(False)

    def undo(self):
        if not self.order:
            return
        k = self.order.pop()
        self.keymap.pop(k, None)
        save_keymap(self.keymap)
        self.refresh_list()
        self.result.configure(text="Removed '%s'" % k)

    def finish(self):
        save_keymap(self.keymap)
        self.cap.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
