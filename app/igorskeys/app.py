"""The tray application: logging, single instance, config, listener, executor, tray menu."""
import ctypes
import logging
import logging.handlers
import os
import subprocess
import sys
import threading
import time

from . import __version__, actions, config, hookblock, i18n, paths, rawinput, startup
from .i18n import tr

log = logging.getLogger("igorskeys")


def setup_logging(level="INFO", rotate=True):
    """rotate=False for the short-lived helper processes (editor, backup, import): only the tray process rotates
    the shared log file, because Windows cannot rename a file that another process has open."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    if rotate:
        fh = logging.handlers.RotatingFileHandler(paths.log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    else:
        fh = logging.FileHandler(paths.log_path(), encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if not getattr(sys, "frozen", False):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)


def single_instance():
    """Return True if this is the only running instance."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW(None, True, "Local\\IgorsKeys.SingleInstance")
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


class App:
    def __init__(self):
        self.keys = config.Keys()
        self.executor = actions.Executor()
        self.blocker = hookblock.Blocker()
        self.paused = False
        self.mappings = {}
        self.cfg = {}
        self._cfg_mtime = None
        self._last_press = {}
        self.listener = rawinput.Listener(self.keys.device["vid"], self.keys.device["pid"],
                                          self.keys.device["usage_page"], self.keys.device["usage"], self.on_report)
        self.icon = None

    # ---- configuration ----
    def load(self):
        self.cfg = config.load_config()
        i18n.init(self.cfg.get("language", "auto"))
        self.mappings = config.active_mappings(self.cfg, self.keys)
        try:
            self._cfg_mtime = os.path.getmtime(paths.config_path())
        except OSError:
            self._cfg_mtime = None
        for k, m in self.mappings.items():
            log.info("mapping: %-14s -> %s%s", k.id, actions.describe(m["action"], private=True),
                     "  (Windows' own action blocked)" if m.get("block_windows_action") and k.windows_handles_it else "")
        log.info("%d key(s) mapped", len(self.mappings))
        blocked = [k.native_vk_code for k, m in self.mappings.items()
                   if k.windows_handles_it and m.get("block_windows_action")]
        self.blocker.set_blocked(blocked)
        self.listener.run_on_thread(self._apply_blocker)
        self._update_menu()

    def _apply_blocker(self):
        self.blocker.remove()
        if self.blocker.blocked and not self.paused:
            self.blocker.install()

    def watch_config(self):
        """Reload config.json automatically when the editor (or the user) saves it."""
        while True:
            time.sleep(2)
            try:
                m = os.path.getmtime(paths.config_path())
            except OSError:
                continue
            if self._cfg_mtime is not None and m != self._cfg_mtime:
                log.info("config.json changed, reloading")
                try:
                    self.load()
                except Exception:
                    log.exception("reload failed")
                    self._cfg_mtime = m

    # ---- input ----
    def on_report(self, report):
        """Runs on the listener thread. Returns True when the report matched a mapped key."""
        if report in self.keys.release_bytes:
            return False
        k = self.keys.by_press.get(bytes(report))
        if k is None:
            log.debug("unknown report %s ignored", report.hex())
            return False
        now = time.monotonic()
        if now - self._last_press.get(k.id, 0) < 0.08:   # ignore electrical double reports
            return True
        self._last_press[k.id] = now
        if self.paused:
            log.debug("%s pressed while paused", k.id)
            return False
        m = self.mappings.get(k)
        if m is None:
            log.debug("%s pressed (no mapping)", k.id)
            return False
        log.info("%s pressed", k.id)
        self.executor.submit(k.id, m["action"])
        return True

    # ---- tray ----
    def _update_menu(self):
        if self.icon is not None:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def open_editor(self):
        subprocess.Popen(paths.exe_command() + ["--edit"], close_fds=True)

    def run_tool(self, arg):
        subprocess.Popen(paths.exe_command() + [arg], close_fds=True)

    def toggle_pause(self):
        self.paused = not self.paused
        log.info("paused" if self.paused else "resumed")
        self.listener.run_on_thread(self._apply_blocker)
        self._update_menu()

    def set_language(self, code):
        self.cfg["language"] = code
        try:
            # Save on top of what is on disk now, not the in-memory copy: the editor may have saved since the last
            # reload, and a file that cannot be read must not be replaced by an empty configuration.
            if config.config_is_readable():
                cfg = config.load_config()
                cfg["language"] = code
                config.save_config(cfg)
            else:
                log.warning("config.json cannot be read; language %s used for this session only", code)
        except Exception:
            log.exception("could not save language setting")
        i18n.init(code)
        self._update_menu()

    def toggle_autostart(self):
        if startup.is_enabled():
            startup.disable()
        else:
            startup.enable()
        self._update_menu()

    def quit(self):
        log.info("quit")
        self.listener.run_on_thread(self.blocker.remove)
        self.listener.stop()
        if self.icon:
            self.icon.stop()

    def run_tray(self):
        import pystray
        from PIL import Image
        try:
            image = Image.open(paths.icon_path())
        except Exception:
            image = Image.new("RGB", (64, 64), (74, 128, 200))
        def lang_item(code):
            return pystray.MenuItem(lambda item: tr(i18n.LANGUAGES[code]), lambda: self.set_language(code),
                                    checked=lambda item: self.cfg.get("language", "auto") == code, radio=True)

        menu = pystray.Menu(
            pystray.MenuItem(lambda item: "Igor's Keys %s - %s" % (__version__, tr("paused") if self.paused else
                                                                 tr("%d key(s) active") % len(self.mappings)),
                             None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: tr("Edit key assignments..."), lambda: self.open_editor(), default=True),
            pystray.MenuItem(lambda item: tr("Reload assignments"), lambda: self.load()),
            pystray.MenuItem(lambda item: tr("Resume") if self.paused else tr("Pause"), lambda: self.toggle_pause()),
            pystray.MenuItem(lambda item: tr("Start with Windows"), lambda: self.toggle_autostart(),
                             checked=lambda item: startup.is_enabled()),
            pystray.MenuItem(lambda item: tr("Language"),
                             pystray.Menu(lang_item("auto"), lang_item("en"), lang_item("sl"))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: tr("Back up settings..."), lambda: self.run_tool("--backup")),
            pystray.MenuItem(lambda item: tr("Restore settings..."), lambda: self.run_tool("--restore")),
            pystray.MenuItem(lambda item: tr("Open log file"), lambda: os.startfile(paths.log_path())),
            pystray.MenuItem(lambda item: tr("Open settings folder"), lambda: os.startfile(paths.data_dir())),
            pystray.MenuItem(lambda item: tr("Quit"), lambda: self.quit()),
        )
        self.icon = pystray.Icon("IgorsKeys", image, "Igor's Keys", menu)
        self.icon.run()


def main(argv):
    level = "DEBUG" if "--debug" in argv else "INFO"
    setup_logging(level)
    log.info("Igor's Keys %s starting (%s)", __version__, "frozen" if getattr(sys, "frozen", False) else "source")
    if not single_instance():
        log.info("another instance is already running; exiting")
        return 0
    app = App()
    try:
        app.listener.start()
    except Exception as e:
        log.error("could not start the Raw Input listener: %s", e)
        i18n.init(config.load_config().get("language", "auto"))
        ctypes.windll.user32.MessageBoxW(None, tr("Igor's Keys could not start listening for the keyboard:\n%s") % e,
                                         "Igor's Keys", 0x10)
        return 1
    app.load()
    if "--first-run" in argv and not startup.is_enabled():
        startup.enable()
    threading.Thread(target=app.watch_config, name="configwatch", daemon=True).start()
    app.run_tray()
    return 0
