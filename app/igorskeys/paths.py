"""Where Igor's Keys keeps its files.

Program folder (read-only, may be in Program Files):  keys.json, icon, defaults.
Data folder (%LOCALAPPDATA%\\IgorsKeys):                  config.json, igorskeys.log
"""
import os
import sys

APP_NAME = "IgorsKeys"


def program_dir():
    if getattr(sys, "frozen", False):          # PyInstaller one-folder build
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_dir():
    """Folder holding bundled read-only resources (keys.json, icon.ico)."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", program_dir()), "igorskeys")
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def config_path():
    return os.path.join(data_dir(), "config.json")


def backup_dir():
    d = os.path.join(data_dir(), "backups")
    os.makedirs(d, exist_ok=True)
    return d


def log_path():
    return os.path.join(data_dir(), "igorskeys.log")


def keys_json_path():
    return os.path.join(resource_dir(), "keys.json")


def icon_path():
    return os.path.join(resource_dir(), "icon.ico")


def exe_command():
    """Command line that starts this program (used for autostart and the editor sub-process)."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")   # no console window at login or for the editor
    if os.path.basename(exe).lower() == "python.exe" and os.path.exists(pythonw):
        exe = pythonw
    return [exe, os.path.join(program_dir(), "main.py")]
