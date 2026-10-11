"""Igor's Keys entry point.

  IgorsKeys.exe                 run the tray program
  IgorsKeys.exe --edit          open the key-assignment editor
  IgorsKeys.exe --import X.csf  convert an old KeyM@n file into config.json (command line)
  IgorsKeys.exe --debug         tray program with verbose logging
  IgorsKeys.exe --first-run     tray program; also switches "start with Windows" on
"""
import sys


def report(message, error=False):
    """Print to the console; in the windowed exe (no console) show a message box instead."""
    if sys.stdout is not None and not getattr(sys, "frozen", False):
        print(message, file=sys.stderr if error else sys.stdout)
    else:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Igor's Keys", 0x10 if error else 0x40)
    return 1 if error else 0


def main(argv):
    if "--edit" in argv:
        from igorskeys import app, editor
        app.setup_logging("INFO", rotate=False)
        return editor.main(argv)
    if "--backup" in argv or "--restore" in argv:
        from igorskeys import app, config, i18n
        from igorskeys.i18n import tr
        app.setup_logging("INFO", rotate=False)
        i18n.init(config.load_config().get("language", "auto"))
        import tkinter as tk
        from tkinter import filedialog, messagebox
        root = tk.Tk()
        root.withdraw()
        try:
            if "--backup" in argv:
                p = filedialog.asksaveasfilename(title=tr("Save a backup of the Igor's Keys settings"),
                                                 initialfile=config.suggested_backup_name(), defaultextension=".json",
                                                 filetypes=[(tr("Igor's Keys settings"), "*.json")])
                if p:
                    config.export_config(p)
                    messagebox.showinfo("Igor's Keys", tr("Backup written to %s") % ("\n" + p))
            else:
                p = filedialog.askopenfilename(title=tr("Choose an Igor's Keys settings backup to restore"),
                                               filetypes=[(tr("Igor's Keys settings"), "*.json"), (tr("All files"), "*.*")])
                if p and messagebox.askyesno("Igor's Keys", tr("Replace all current key assignments with the ones in\n%s ?") % p):
                    n = config.import_config(p)
                    messagebox.showinfo("Igor's Keys", tr("Restored %d key assignment(s). The tray program reloads them by itself.") % n)
        except Exception as e:
            messagebox.showerror("Igor's Keys", str(e))
        return 0
    if "--import" in argv:
        from igorskeys import app, config, importer, paths
        app.setup_logging("INFO", rotate=False)
        i = argv.index("--import")
        if i + 1 >= len(argv):
            return report("usage: IgorsKeys.exe --import <file.csf>", error=True)
        path = argv[i + 1]
        try:
            with open(path, "rb") as f:
                mappings, notes = importer.convert(f.read(), config.Keys())
        except Exception as e:
            return report("could not import %s:\n%s" % (path, e), error=True)
        if not config.config_is_readable():
            return report("config.json cannot be read; fix or delete it first:\n%s" % paths.config_path(),
                          error=True)
        cfg = config.load_config()
        cfg.setdefault("mappings", {}).update(mappings)
        config.save_config(cfg)
        return report("\n".join(notes + ["%d mapping(s) written to config.json" % len(mappings)]))
    from igorskeys import app
    return app.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
