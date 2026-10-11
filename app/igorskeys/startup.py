"""Start with Windows: a value under HKCU\\...\\Run (per user, no administrator rights needed)."""
import logging
import subprocess
import winreg

from . import paths

log = logging.getLogger("igorskeys.startup")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = paths.APP_NAME


def command_line():
    return subprocess.list2cmdline(paths.exe_command())


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            v, _ = winreg.QueryValueEx(k, VALUE)
            return bool(v)
    except OSError:
        return False


def enable():
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        winreg.SetValueEx(k, VALUE, 0, winreg.REG_SZ, command_line())
    log.info("autostart enabled: %s", command_line())


def disable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, VALUE)
        log.info("autostart disabled")
    except OSError:
        pass
