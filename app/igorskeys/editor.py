"""The key-assignment editor (tkinter).  Runs as its own process: IgorsKeys.exe --edit.
Saves config.json; the running tray program reloads it by itself."""
import ctypes
import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import __version__, actions, config, i18n, importer, paths
from .i18n import tr

log = logging.getLogger("igorskeys.editor")

TYPES = ["none", "text", "keys", "open", "sequence"]
TYPE_TEXT = {"none": "Do nothing", "text": "Type a text", "keys": "Press a key combination",
             "open": "Open a program, file, folder or web address", "sequence": "Run several steps in a row"}

KEY_PRESETS = [
    ("Copy", "Ctrl+C"), ("Cut", "Ctrl+X"), ("Paste", "Ctrl+V"), ("Undo", "Ctrl+Z"), ("Redo", "Ctrl+Y"),
    ("Select all", "Ctrl+A"), ("Save", "Ctrl+S"), ("Print", "Ctrl+P"), ("Find", "Ctrl+F"),
    ("New browser tab", "Ctrl+T"), ("Close tab / document", "Ctrl+W"), ("Close window", "Alt+F4"),
    ("Zoom in", "Ctrl++"), ("Zoom out", "Ctrl+-"), ("Page up", "PageUp"), ("Page down", "PageDown"),
    ("Show desktop", "Win+D"), ("File Explorer", "Win+E"), ("Windows Settings", "Win+I"),
    ("Screenshot (snip)", "Win+Shift+S"), ("Task view", "Win+Tab"), ("Start menu", "Win"),
    ("Volume up", "VolumeUp"), ("Volume down", "VolumeDown"), ("Mute", "Mute"), ("Play / pause", "PlayPause"),
    ("Next track", "MediaNext"), ("Previous track", "MediaPrev"), ("Stop media", "MediaStop"),
    ("Open calculator (Windows key function)", "Calculator"), ("Open e-mail program", "LaunchMail"),
    ("Browser home", "BrowserHome"), ("Browser back", "BrowserBack"), ("Browser forward", "BrowserForward"),
    ("Browser refresh", "BrowserRefresh"), ("Browser search", "BrowserSearch"),
]
OPEN_PRESETS = [
    ("Documents folder", "shell:Personal", ""), ("Downloads folder", "shell:Downloads", ""),
    ("Pictures folder", "shell:My Pictures", ""), ("Videos folder", "shell:My Video", ""),
    ("Music folder", "shell:My Music", ""), ("Desktop folder", "shell:Desktop", ""),
    ("This PC", "shell:MyComputerFolder", ""), ("Recycle Bin", "shell:RecycleBinFolder", ""),
    ("Control Panel", "shell:ControlPanelFolder", ""), ("Windows Settings", "ms-settings:", ""),
    ("Notepad", "notepad.exe", ""), ("Calculator", "calc.exe", ""), ("Paint", "mspaint.exe", ""),
    ("Snipping tool", "ms-screenclip:", ""), ("Task Manager", "taskmgr.exe", ""),
    ("Command prompt", "cmd.exe", ""), ("Lock the computer", "rundll32.exe", "user32.dll,LockWorkStation"),
    ("Put the computer to sleep", "rundll32.exe", "powrprof.dll,SetSuspendState 0,1,0"),
    ("Google", "https://www.google.com", ""), ("YouTube", "https://www.youtube.com", ""),
    ("Gmail", "https://mail.google.com", ""), ("Wikipedia", "https://www.wikipedia.org", ""),
]

HELP_KEYS = ("Examples: Ctrl+C    Ctrl+Shift+Esc    Win+E    Alt+F4    Enter    F5    PageDown\n"
             "Special names: VolumeUp, VolumeDown, Mute, PlayPause, MediaNext, MediaPrev, MediaStop,\n"
             "BrowserBack, BrowserHome, LaunchMail, Calculator, PrintScreen, Home, End, Tab, Esc")
HELP_OPEN = "Examples: notepad.exe    C:\\Users\\Name\\Documents    https://www.google.com    shell:Personal (= Documents)"
HELP_SEQ = ("One step per line:\n"
            "  keys: Ctrl+C          press a key combination\n"
            "  text: Hello there     type a text\n"
            "  wait: 500             wait 500 milliseconds\n"
            "  open: C:\\path\\x.exe   open a program, file, folder or web address")

VK_TO_NAME = dict(importer.VK_NAME)
VK_TO_NAME.update({0xAF: "VolumeUp", 0xAE: "VolumeDown", 0xAD: "Mute", 0xB3: "PlayPause", 0xB0: "MediaNext",
                   0xB1: "MediaPrev", 0xB2: "MediaStop", 0xB4: "LaunchMail", 0xB7: "Calculator",
                   0xAC: "BrowserHome", 0xA6: "BrowserBack", 0xA7: "BrowserForward", 0xA8: "BrowserRefresh",
                   0xA9: "BrowserStop", 0xAA: "BrowserSearch", 0xBB: "+", 0xBD: "-", 0xBC: ",", 0xBE: ".",
                   0x6A: "Multiply", 0x6B: "Add", 0x6D: "Subtract", 0x6E: "Decimal", 0x6F: "Divide"})
MODIFIER_VKS = {0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C}


def chord_from_event(event):
    """Build a 'Ctrl+Shift+X' string from a tkinter KeyPress (on Windows, keycode is the virtual-key code)."""
    vk = event.keycode
    if vk in MODIFIER_VKS or vk == 0:
        return None

    def down(v):
        return ctypes.windll.user32.GetAsyncKeyState(v) & 0x8000

    mods = []
    if down(0x11):
        mods.append("Ctrl")
    if down(0x12):
        mods.append("Alt")
    if down(0x10):
        mods.append("Shift")
    if down(0x5B) or down(0x5C):
        mods.append("Win")
    if vk in VK_TO_NAME:
        name = VK_TO_NAME[vk]
    else:
        ch = ctypes.windll.user32.MapVirtualKeyW(vk, 2) & 0xFFFF   # MAPVK_VK_TO_CHAR
        name = chr(ch) if ch and chr(ch).isprintable() and ch != 0x20 else "0x%02X" % vk
    return "+".join(mods + [name])


def steps_to_text(steps):
    lines = []
    for s in steps:
        t = s.get("type")
        if t == "keys":
            lines.append("keys: " + s.get("keys", ""))
        elif t == "text":
            lines.append("text: " + s.get("text", "").replace("\\", "\\\\").replace("\n", "\\n"))
        elif t == "delay":
            lines.append("wait: %s" % s.get("ms", 0))
        elif t == "open":
            lines.append("open: " + s.get("target", "") + ((" | " + s["args"]) if s.get("args") else ""))
    return "\n".join(lines)


def _unescape(s):
    """'text:' steps: \\n is a new line and \\\\ a backslash; any other backslash is kept as it is."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in "n\\":
            out.append("\n" if s[i + 1] == "n" else "\\")
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def text_to_steps(text):
    steps = []
    for ln, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError("line %d: expected 'keys:', 'text:', 'wait:' or 'open:'" % ln)
        kind, _, rest = line.partition(":")
        kind, rest = kind.strip().lower(), rest.strip()
        if kind == "keys":
            steps.append({"type": "keys", "keys": rest})
        elif kind == "text":
            steps.append({"type": "text", "text": _unescape(rest)})
        elif kind == "wait":
            steps.append({"type": "delay", "ms": int(rest)})
        elif kind == "open":
            target, _, args = rest.partition("|")
            st = {"type": "open", "target": target.strip()}
            if args.strip():
                st["args"] = args.strip()
            steps.append(st)
        else:
            raise ValueError("line %d: unknown step '%s'" % (ln, kind))
    return steps


class Editor:
    def __init__(self, root):
        self.root = root
        root.title(tr("Igor's Keys %s - key assignments") % __version__)
        root.geometry("1000x680+80+60")
        root.minsize(880, 600)
        self.keys = config.Keys()
        self.cfg = config.load_config()
        self.mappings = self.cfg.setdefault("mappings", {})
        self.current = None
        self.dirty = False
        self.type_labels = {t: tr(TYPE_TEXT[t]) for t in TYPES}
        self.label_types = {v: k for k, v in self.type_labels.items()}
        self.key_preset_labels = [tr(l) for l, _ in KEY_PRESETS]
        self.open_preset_labels = [tr(l) for l, _, _ in OPEN_PRESETS]
        self._build()
        self._fill_tree()
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ---- layout ----
    def _build(self):
        pw = ttk.Panedwindow(self.root, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=8, pady=8)
        left = ttk.Frame(pw)
        right = ttk.Frame(pw, padding=(12, 0, 0, 0))
        pw.add(left, weight=1)
        pw.add(right, weight=2)

        ttk.Label(left, text=tr("Keys of the keyboard"), font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(left, columns=("action",), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text=tr("Key"))
        self.tree.heading("action", text=tr("Does"))
        self.tree.column("#0", width=220)
        self.tree.column("action", width=220)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        bl = ttk.Frame(left)
        bl.pack(fill="x", pady=(6, 0))
        ttk.Button(bl, text=tr("Import old KeyM@n file..."), command=self.import_csf).pack(side="left")
        ttk.Button(bl, text=tr("Clear all"), command=self.clear_all).pack(side="left", padx=6)
        bl2 = ttk.Frame(left)
        bl2.pack(fill="x", pady=(4, 0))
        ttk.Button(bl2, text=tr("Back up settings..."), command=self.export_settings).pack(side="left")
        ttk.Button(bl2, text=tr("Restore settings..."), command=self.restore_settings).pack(side="left", padx=6)

        self.title = ttk.Label(right, text=tr("Select a key on the left"), font=("Segoe UI", 13, "bold"))
        self.title.pack(anchor="w")
        self.subtitle = ttk.Label(right, text="", wraplength=560, foreground="#555")
        self.subtitle.pack(anchor="w", pady=(0, 8))

        row = ttk.Frame(right)
        row.pack(fill="x")
        ttk.Label(row, text=tr("When this key is pressed:")).pack(side="left")
        self.type_var = tk.StringVar(value=self.type_labels["none"])
        self.type_box = ttk.Combobox(row, textvariable=self.type_var, values=[self.type_labels[t] for t in TYPES],
                                     state="readonly", width=44)
        self.type_box.pack(side="left", padx=6)
        self.type_box.bind("<<ComboboxSelected>>", lambda e: self._show_fields())

        self.fields = ttk.Frame(right)
        self.fields.pack(fill="both", expand=True, pady=8)

        # text
        self.f_text = ttk.Frame(self.fields)
        ttk.Label(self.f_text, text=tr("Text to type (Enter starts a new line):")).pack(anchor="w")
        self.text_box = tk.Text(self.f_text, height=8, font=("Segoe UI", 10), wrap="word")
        self.text_box.pack(fill="both", expand=True)
        # keys
        self.f_keys = ttk.Frame(self.fields)
        ttk.Label(self.f_keys, text=tr("Key combination:")).pack(anchor="w")
        rk = ttk.Frame(self.f_keys)
        rk.pack(fill="x")
        self.keys_entry = ttk.Entry(rk, font=("Segoe UI", 11))
        self.keys_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(rk, text=tr("Record..."), command=self.record_chord).pack(side="left", padx=4)
        rp = ttk.Frame(self.f_keys)
        rp.pack(fill="x", pady=(6, 0))
        ttk.Label(rp, text=tr("Or pick a common action:")).pack(side="left")
        self.key_preset = ttk.Combobox(rp, values=self.key_preset_labels, state="readonly", width=40)
        self.key_preset.pack(side="left", padx=6)
        self.key_preset.bind("<<ComboboxSelected>>", self._pick_key_preset)
        ttk.Label(self.f_keys, text=tr(HELP_KEYS), foreground="#555", justify="left").pack(anchor="w", pady=6)
        # open
        self.f_open = ttk.Frame(self.fields)
        ttk.Label(self.f_open, text=tr("Program, file, folder or web address:")).pack(anchor="w")
        r2 = ttk.Frame(self.f_open)
        r2.pack(fill="x")
        self.open_entry = ttk.Entry(r2, font=("Segoe UI", 10))
        self.open_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(r2, text=tr("Browse file..."), command=self._browse_file).pack(side="left", padx=4)
        ttk.Button(r2, text=tr("Browse folder..."), command=self._browse_folder).pack(side="left")
        rp2 = ttk.Frame(self.f_open)
        rp2.pack(fill="x", pady=(6, 0))
        ttk.Label(rp2, text=tr("Or pick a common place:")).pack(side="left")
        self.open_preset = ttk.Combobox(rp2, values=self.open_preset_labels, state="readonly", width=40)
        self.open_preset.pack(side="left", padx=6)
        self.open_preset.bind("<<ComboboxSelected>>", self._pick_open_preset)
        ttk.Label(self.f_open, text=tr("Parameters (optional):")).pack(anchor="w", pady=(6, 0))
        self.args_entry = ttk.Entry(self.f_open, font=("Segoe UI", 10))
        self.args_entry.pack(fill="x")
        ttk.Label(self.f_open, text=tr(HELP_OPEN), foreground="#555", wraplength=560, justify="left").pack(anchor="w", pady=6)
        # sequence
        self.f_seq = ttk.Frame(self.fields)
        ttk.Label(self.f_seq, text=tr("Steps:")).pack(anchor="w")
        self.seq_box = tk.Text(self.f_seq, height=8, font=("Consolas", 10))
        self.seq_box.pack(fill="both", expand=True)
        ttk.Label(self.f_seq, text=tr(HELP_SEQ), foreground="#555", justify="left", font=("Consolas", 9)).pack(anchor="w", pady=6)

        self.block_var = tk.BooleanVar(value=False)
        self.block_chk = ttk.Checkbutton(right, text=tr("Also stop Windows' own function of this key"),
                                         variable=self.block_var, command=self._mark_dirty)
        self.block_chk.pack(anchor="w")

        br = ttk.Frame(right)
        br.pack(fill="x", pady=(10, 0))
        ttk.Button(br, text=tr("Apply to this key"), command=self.apply_current).pack(side="left")
        ttk.Button(br, text=tr("Test now"), command=self.test_current).pack(side="left", padx=6)
        ttk.Button(br, text=tr("Save and close"), command=self.save_close).pack(side="right")
        ttk.Button(br, text=tr("Save"), command=self.save).pack(side="right", padx=6)
        self.status = ttk.Label(right, text="", foreground="#06a", wraplength=560)
        self.status.pack(anchor="w", pady=(6, 0))

    def _fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        for group, keys in self.keys.groups().items():
            g = self.tree.insert("", "end", text=i18n.group_label(group), open=True)
            for k in keys:
                m = self.mappings.get(k.id, {})
                self.tree.insert(g, "end", iid=k.id, text=k.id, values=(self._summary(k, m),))
        # the form must show the new mappings too, otherwise the next Save would write its old values back
        if self.current is not None and self.tree.exists(self.current.id):
            self.tree.selection_set(self.current.id)
            self._on_select()

    @staticmethod
    def _native_name(k):
        return k.native_vk.replace("VK_", "").replace("_", " ").lower() if k.native_vk else ""

    def _summary(self, k, m):
        a = m.get("action", {"type": "none"}) if isinstance(m, dict) else {"type": "none"}
        if a.get("type", "none") == "none":
            return "(Windows: %s)" % self._native_name(k) if k.windows_handles_it else tr("nothing")
        return actions.describe(a)

    # ---- selection / fields ----
    def _on_select(self, _e=None):
        sel = self.tree.selection()
        if not sel or sel[0] not in self.keys.by_id:
            return
        k = self.keys.by_id[sel[0]]
        self.current = k
        self.title.configure(text="%s   -   %s" % (k.id, i18n.key_label(k)))
        if k.windows_handles_it:
            self.subtitle.configure(text=tr("Windows already gives this key a function (%s). You can add your own; "
                                            "tick the box below to switch the Windows function off.") % self._native_name(k))
            self.block_chk.state(["!disabled"])
        else:
            self.subtitle.configure(text=tr("Windows ignores this key, so it is free for your own use."))
            self.block_chk.state(["disabled"])
        m = self.mappings.get(k.id, {})
        a = m.get("action", {"type": "none"}) if isinstance(m, dict) else {"type": "none"}
        self.type_var.set(self.type_labels.get(a.get("type", "none"), self.type_labels["none"]))
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", a.get("text", "") if a.get("type") == "text" else "")
        self.keys_entry.delete(0, "end")
        self.keys_entry.insert(0, a.get("keys", "") if a.get("type") == "keys" else "")
        self.open_entry.delete(0, "end")
        self.open_entry.insert(0, a.get("target", "") if a.get("type") == "open" else "")
        self.args_entry.delete(0, "end")
        self.args_entry.insert(0, a.get("args", "") if a.get("type") == "open" else "")
        self.seq_box.delete("1.0", "end")
        self.seq_box.insert("1.0", steps_to_text(a.get("steps", [])) if a.get("type") == "sequence" else "")
        self.block_var.set(bool(m.get("block_windows_action")) if isinstance(m, dict) else False)
        self._show_fields()
        self.status.configure(text="")

    def _show_fields(self):
        for f in (self.f_text, self.f_keys, self.f_open, self.f_seq):
            f.pack_forget()
        t = self.label_types.get(self.type_var.get(), "none")
        frame = {"text": self.f_text, "keys": self.f_keys, "open": self.f_open, "sequence": self.f_seq}.get(t)
        if frame is not None:
            frame.pack(fill="both", expand=True)

    def _mark_dirty(self):
        self.dirty = True

    def _pick_key_preset(self, _e=None):
        idx = self.key_preset.current()
        if idx >= 0:
            self.keys_entry.delete(0, "end")
            self.keys_entry.insert(0, KEY_PRESETS[idx][1])
        self.key_preset.set("")

    def _pick_open_preset(self, _e=None):
        idx = self.open_preset.current()
        if idx >= 0:
            _, target, args = OPEN_PRESETS[idx]
            self.open_entry.delete(0, "end")
            self.open_entry.insert(0, target)
            self.args_entry.delete(0, "end")
            self.args_entry.insert(0, args)
        self.open_preset.set("")

    def record_chord(self):
        win = tk.Toplevel(self.root)
        win.title(tr("Record a key combination"))
        win.geometry("460x170")
        win.transient(self.root)
        win.resizable(False, False)
        ttk.Label(win, text=tr("Press the key combination now,\nfor example hold Ctrl and tap C.\n\nPress Esc to cancel."),
                  font=("Segoe UI", 12), justify="center").pack(expand=True)
        result = {}

        def on_key(event):
            if event.keycode == 0x1B:   # Esc cancels
                win.destroy()
                return "break"
            chord = chord_from_event(event)
            if chord:
                result["chord"] = chord
                win.destroy()
            return "break"

        win.bind("<KeyPress>", on_key)
        win.grab_set()
        win.focus_force()
        self.root.wait_window(win)
        if result.get("chord"):
            self.keys_entry.delete(0, "end")
            self.keys_entry.insert(0, result["chord"])
            self.status.configure(text=tr("Recorded: %s") % result["chord"])

    def _browse_file(self):
        p = filedialog.askopenfilename(parent=self.root, title=tr("Choose a program or file"))
        if p:
            self.open_entry.delete(0, "end")
            self.open_entry.insert(0, os.path.normpath(p))

    def _browse_folder(self):
        p = filedialog.askdirectory(parent=self.root, title=tr("Choose a folder"))
        if p:
            self.open_entry.delete(0, "end")
            self.open_entry.insert(0, os.path.normpath(p))

    def _action_from_fields(self):
        t = self.label_types.get(self.type_var.get(), "none")
        if t == "none":
            return {"type": "none"}
        if t == "text":
            return {"type": "text", "text": self.text_box.get("1.0", "end-1c")}
        if t == "keys":
            chord = self.keys_entry.get().strip()
            actions.parse_chord(chord)  # raises ActionError with a readable message
            return {"type": "keys", "keys": chord}
        if t == "open":
            a = {"type": "open", "target": self.open_entry.get().strip()}
            if self.args_entry.get().strip():
                a["args"] = self.args_entry.get().strip()
            return a
        if t == "sequence":
            steps = text_to_steps(self.seq_box.get("1.0", "end-1c"))
            for s in steps:
                if s["type"] == "keys":
                    actions.parse_chord(s["keys"])
            return {"type": "sequence", "steps": steps}
        return {"type": "none"}

    # ---- commands ----
    def apply_current(self):
        if self.current is None:
            return False
        try:
            a = self._action_from_fields()
            problems = config.validate_action(a)
            if problems:
                raise ValueError("; ".join(problems))
        except Exception as e:
            messagebox.showerror(tr("Cannot apply"), str(e), parent=self.root)
            return False
        if a["type"] == "none":
            self.mappings.pop(self.current.id, None)
        else:
            m = {"action": a}
            if self.current.windows_handles_it and self.block_var.get():
                m["block_windows_action"] = True
            self.mappings[self.current.id] = m
        self.tree.item(self.current.id, values=(self._summary(self.current, self.mappings.get(self.current.id, {})),))
        self.dirty = True
        self.status.configure(text=tr("Applied to %s (not saved yet)") % self.current.id)
        return True

    def test_current(self):
        try:
            a = self._action_from_fields()
        except Exception as e:
            messagebox.showerror(tr("Cannot test"), str(e), parent=self.root)
            return
        if a["type"] in ("text", "keys", "sequence"):
            if not messagebox.askokcancel(tr("Test"), tr("The keystrokes will go to whatever window is active 2 seconds "
                                                        "after you click OK. Click OK, then click into the window where "
                                                        "they should land (e.g. Notepad)."), parent=self.root):
                return
            self.root.after(2000, lambda: self._run_test(a))
        else:
            self._run_test(a)

    def _run_test(self, a):
        try:
            actions.run_action(a)
            self.status.configure(text=tr("Test done: %s") % actions.describe(a))
        except Exception as e:
            messagebox.showerror(tr("Test failed"), str(e), parent=self.root)

    def save(self):
        if self.current is not None and not self.apply_current():
            return False
        try:
            config.save_config(self.cfg)
        except Exception as e:
            messagebox.showerror(tr("Cannot save"), tr("Could not write %s:\n%s") % (paths.config_path(), e), parent=self.root)
            return False
        self.dirty = False
        self.status.configure(text=tr("Saved. The tray program picks the change up within a few seconds."))
        return True

    def save_close(self):
        if self.save():
            self.root.destroy()

    def close(self):
        if self.dirty and not messagebox.askyesno(tr("Discard changes?"), tr("You have unsaved changes. Close anyway?"),
                                                  parent=self.root):
            return
        self.root.destroy()

    def clear_all(self):
        if messagebox.askyesno(tr("Clear all"), tr("Remove every key assignment?"), parent=self.root):
            self.mappings.clear()
            self._fill_tree()
            self.dirty = True

    def export_settings(self):
        if self.dirty and not self.save():
            return
        p = filedialog.asksaveasfilename(parent=self.root, title=tr("Save a backup of the settings"),
                                         initialfile=config.suggested_backup_name(), defaultextension=".json",
                                         filetypes=[(tr("Igor's Keys settings"), "*.json")])
        if not p:
            return
        try:
            config.export_config(p)
            self.status.configure(text=tr("Backup written to %s") % p)
        except Exception as e:
            messagebox.showerror(tr("Backup failed"), str(e), parent=self.root)

    def restore_settings(self):
        p = filedialog.askopenfilename(parent=self.root, title=tr("Choose a settings backup to restore"),
                                       filetypes=[(tr("Igor's Keys settings"), "*.json"), (tr("All files"), "*.*")])
        if not p:
            return
        if not messagebox.askyesno(tr("Restore"), tr("Replace all current key assignments with the ones in\n%s ?") % p,
                                   parent=self.root):
            return
        try:
            n = config.import_config(p)
        except Exception as e:
            messagebox.showerror(tr("Restore failed"), str(e), parent=self.root)
            return
        self.cfg = config.load_config()
        self.mappings = self.cfg.setdefault("mappings", {})
        self.dirty = False
        self._fill_tree()
        self.status.configure(text=tr("Restored %d assignment(s) from %s") % (n, os.path.basename(p)))

    def import_csf(self):
        p = filedialog.askopenfilename(parent=self.root, title=tr("Choose the old KeyM@n configuration"),
                                       filetypes=[(tr("Cherry shortcut file"), "*.csf"), (tr("All files"), "*.*")])
        if not p:
            return
        try:
            mappings, notes = importer.convert(open(p, "rb").read(), self.keys)
        except Exception as e:
            messagebox.showerror(tr("Import failed"), tr("This does not look like a KeyM@n .csf file:\n%s") % e, parent=self.root)
            return
        if not messagebox.askyesno(tr("Import"), tr("%d key assignment(s) found. Add them (existing assignments for the "
                                                    "same keys are replaced)?\n\n%s") % (len(mappings), "\n".join(notes[:25])),
                                   parent=self.root):
            return
        self.mappings.update(mappings)
        self._fill_tree()
        self.dirty = True
        self.status.configure(text=tr("Imported %d assignment(s) from %s (not saved yet)") % (len(mappings), os.path.basename(p)))


def main(argv):
    i18n.init(config.load_config().get("language", "auto"))
    root = tk.Tk()
    try:
        root.iconbitmap(paths.icon_path())
    except Exception:
        pass
    Editor(root)
    root.mainloop()
    return 0
