"""Key definitions (keys.json, bundled) and the user's mappings (config.json, editable).

config.json format (plain JSON, one entry per key id):

{
  "version": 1,
  "mappings": {
    "XPress 6": {"action": {"type": "open", "target": "shell:Personal"}, "comment": "My Documents"},
    "XPress 3": {"action": {"type": "keys", "keys": "Ctrl+X"}},
    "XPress 1": {"action": {"type": "text", "text": "Kind regards,\nIgor"}},
    "XPress 2": {"action": {"type": "sequence", "steps": [
                    {"type": "keys", "keys": "Win+R"}, {"type": "delay", "ms": 400},
                    {"type": "text", "text": "notepad"}, {"type": "keys", "keys": "Enter"}]}},
    "Calculator": {"action": {"type": "open", "target": "C:\\Tools\\calc.exe"}, "block_windows_action": true}
  }
}

Action types:  none | text | keys | open | sequence (steps are the same objects, plus {"type":"delay","ms":N})
"open": target is a program, document, folder, shell: folder or web address; optional "args".
"block_windows_action": only meaningful for keys Windows handles itself (volume, media, browser, calculator, mail);
when true the built-in Windows action is suppressed while this program runs.
"""
import json
import logging
import os
import shutil
import time

from . import paths

log = logging.getLogger("igorskeys.config")

VALID_TYPES = ("none", "text", "keys", "open", "sequence", "delay")


class KeyDef:
    def __init__(self, d):
        self.id = d["id"]
        self.label = d["label"]
        self.group = d["group"]
        self.usage = d["usage"]
        self.press = bytes.fromhex(d["press"])
        self.release = bytes.fromhex(d["release"])
        self.native_vk = d.get("native_vk")
        self.native_vk_code = d.get("native_vk_code")
        self.windows_handles_it = bool(d.get("windows_handles_it"))
        self.cherry_name = d.get("cherry_name", "")
        self.ps2 = d.get("ps2", "")

    def __repr__(self):
        return "KeyDef(%s)" % self.id


class Keys:
    """The keyboard's extra keys, from the bundled keys.json."""

    def __init__(self, path=None):
        d = json.load(open(path or paths.keys_json_path(), encoding="utf-8"))
        self.device = d["device"]
        self.keys = [KeyDef(k) for k in d["keys"]]
        self.by_id = {k.id: k for k in self.keys}
        self.by_press = {k.press: k for k in self.keys}
        self.release_bytes = {k.release for k in self.keys}

    def groups(self):
        out = {}
        for k in self.keys:
            out.setdefault(k.group, []).append(k)
        return out


DEFAULT_CONFIG = {
    "version": 1,
    "comment": "Edit with the Igor's Keys editor (tray icon > Edit key assignments) or by hand. "
               "Keys that are not listed here do nothing (or keep their normal Windows function).",
    "mappings": {
        "XPress 6": {"action": {"type": "open", "target": "shell:Personal"}, "comment": "Documents folder (suggestion from the old KeyM@n setup)"},
        "XPress 7": {"action": {"type": "open", "target": "shell:My Video"}, "comment": "Videos folder (suggestion from the old KeyM@n setup)"},
    },
}


def validate_action(a, depth=0):
    """Return a list of problems (empty = OK)."""
    problems = []
    if not isinstance(a, dict):
        return ["action must be an object"]
    t = a.get("type", "none")
    if t not in VALID_TYPES:
        return ["unknown action type %r" % t]
    if t == "text" and not isinstance(a.get("text", ""), str):
        problems.append("text must be a string")
    if t == "keys" and not str(a.get("keys", "")).strip():
        problems.append("keys is empty")
    if t == "open" and not str(a.get("target", "")).strip():
        problems.append("open: target is empty")
    if t == "delay":
        try:
            ms = int(a.get("ms", 0))
            if ms < 0 or ms > 60000:
                problems.append("delay must be 0..60000 ms")
        except (TypeError, ValueError):
            problems.append("delay ms must be a number")
    if t == "sequence":
        if depth > 0:
            problems.append("a sequence cannot contain a sequence")
        steps = a.get("steps", [])
        if not isinstance(steps, list):
            problems.append("sequence steps must be a list")
        else:
            for i, s in enumerate(steps):
                problems += ["step %d: %s" % (i + 1, p) for p in validate_action(s, depth + 1)]
    return problems


def load_config(path=None):
    """Load config.json; create it with defaults on first run. Never raises: returns defaults on error."""
    path = path or paths.config_path()
    if not os.path.exists(path):
        save_config(DEFAULT_CONFIG, path)
        log.info("created default config at %s", path)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict) or not isinstance(cfg.get("mappings", {}), dict):
            raise ValueError("config root must be an object with a 'mappings' object")
        cfg.setdefault("mappings", {})
        return cfg
    except Exception as e:
        log.error("could not read %s (%s); using an empty configuration", path, e)
        return {"version": 1, "mappings": {}}


def config_is_readable(path=None):
    """True if config.json is missing (it will be created) or parses as a settings object."""
    path = path or paths.config_path()
    if not os.path.exists(path):
        return True
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        return isinstance(cfg, dict) and isinstance(cfg.get("mappings", {}), dict)
    except Exception:
        return False


def save_config(cfg, path=None):
    """Write config.json atomically. The previous version is kept in the backups folder (last 20)."""
    path = path or paths.config_path()
    if path == paths.config_path() and os.path.exists(path):
        try:
            backup_dir = paths.backup_dir()
            stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            shutil.copy2(path, os.path.join(backup_dir, "config_%s.json" % stamp))
            old = sorted(f for f in os.listdir(backup_dir) if f.startswith("config_") and f.endswith(".json"))
            for f in old[:-20]:
                os.remove(os.path.join(backup_dir, f))
        except Exception as e:
            log.warning("could not write automatic backup: %s", e)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def export_config(dest_path):
    """Copy the current settings to dest_path (a backup the user chooses)."""
    cfg = load_config()
    cfg["exported"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    log.info("settings exported to %s", dest_path)


def import_config(src_path):
    """Replace the current settings with the ones in src_path. Returns the number of mappings. Raises on bad files."""
    with open(src_path, encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict) or not isinstance(cfg.get("mappings"), dict):
        raise ValueError("not an Igor's Keys settings file (no 'mappings' object)")
    bad = []
    for kid, m in cfg["mappings"].items():
        if not isinstance(m, dict):
            bad.append(kid)
            continue
        bad += ["%s: %s" % (kid, p) for p in validate_action(m.get("action", {"type": "none"}))]
    if bad:
        raise ValueError("problems in the file: " + "; ".join(bad[:5]))
    cfg.pop("exported", None)
    save_config(cfg)
    log.info("settings restored from %s (%d mappings)", src_path, len(cfg["mappings"]))
    return len(cfg["mappings"])


def suggested_backup_name():
    return "IgorsKeys-settings-%s.json" % time.strftime("%Y-%m-%d")


def active_mappings(cfg, keys):
    """Return {KeyDef: mapping} for mappings that are enabled, refer to a known key and validate."""
    out = {}
    for kid, m in cfg.get("mappings", {}).items():
        k = keys.by_id.get(kid)
        if k is None:
            log.warning("config: unknown key %r ignored", kid)
            continue
        if not isinstance(m, dict) or m.get("enabled", True) is False:
            continue
        action = m.get("action", {"type": "none"})
        problems = validate_action(action)
        if problems:
            log.warning("config: mapping for %s ignored: %s", kid, "; ".join(problems))
            continue
        if action.get("type", "none") == "none":
            continue
        out[k] = m
    return out
