"""Translations.  English strings are the keys; tr() returns the Slovenian text when Slovenian is active.

Language selection: config.json "language": "auto" (default, follows the Windows display language),
"en" or "sl".  Key ids inside config.json never change, only what is shown.
"""
import ctypes
import logging
import os

log = logging.getLogger("igorskeys.i18n")

LANGUAGES = {"auto": "Automatic (Windows language)", "en": "English", "sl": "Slovenščina"}
_current = "en"


def windows_language():
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        return "sl" if lang_id == 0x24 else "en"
    except Exception:
        return "en"


def init(setting):
    """setting: 'auto', 'en' or 'sl'."""
    global _current
    setting = (os.environ.get("IGORSKEYS_LANG") or setting or "auto").lower()   # env var: testing override
    _current = windows_language() if setting == "auto" else ("sl" if setting == "sl" else "en")
    log.info("language: %s (setting %s)", _current, setting)
    return _current


def current():
    return _current


def tr(s):
    if _current == "sl":
        return SL.get(s, s)
    return s


def key_label(key):
    """Translated description of a KeyDef."""
    if _current == "sl":
        return KEY_LABELS_SL.get(key.id, key.label)
    return key.label


def group_label(group):
    return tr(group)


SL = {
    # editor window
    "Igor's Keys %s - key assignments": "Igor's Keys %s - dodelitve tipk",
    "Keys of the keyboard": "Tipke na tipkovnici",
    "Key": "Tipka",
    "Does": "Dejanje",
    "Import old KeyM@n file...": "Uvozi staro datoteko KeyM@n ...",
    "Clear all": "Počisti vse",
    "Back up settings...": "Varnostna kopija nastavitev ...",
    "Restore settings...": "Obnovi nastavitve ...",
    "Select a key on the left": "Izberi tipko na levi",
    "When this key is pressed:": "Ob pritisku te tipke:",
    "Do nothing": "Ne naredi ničesar",
    "Type a text": "Vnesi besedilo",
    "Press a key combination": "Pritisni kombinacijo tipk",
    "Open a program, file, folder or web address": "Odpri program, datoteko, mapo ali spletni naslov",
    "Run several steps in a row": "Izvedi več korakov zapored",
    "Text to type (Enter starts a new line):": "Besedilo za vnos (Enter začne novo vrstico):",
    "Key combination:": "Kombinacija tipk:",
    "Record...": "Posnemi ...",
    "Or pick a common action:": "Ali izberi pogosto dejanje:",
    "Examples: Ctrl+C    Ctrl+Shift+Esc    Win+E    Alt+F4    Enter    F5    PageDown\n"
    "Special names: VolumeUp, VolumeDown, Mute, PlayPause, MediaNext, MediaPrev, MediaStop,\n"
    "BrowserBack, BrowserHome, LaunchMail, Calculator, PrintScreen, Home, End, Tab, Esc":
        "Primeri: Ctrl+C    Ctrl+Shift+Esc    Win+E    Alt+F4    Enter    F5    PageDown\n"
        "Posebna imena: VolumeUp, VolumeDown, Mute, PlayPause, MediaNext, MediaPrev, MediaStop,\n"
        "BrowserBack, BrowserHome, LaunchMail, Calculator, PrintScreen, Home, End, Tab, Esc",
    "Program, file, folder or web address:": "Program, datoteka, mapa ali spletni naslov:",
    "Browse file...": "Poišči datoteko ...",
    "Browse folder...": "Poišči mapo ...",
    "Or pick a common place:": "Ali izberi pogosto mesto:",
    "Parameters (optional):": "Parametri (neobvezno):",
    "Examples: notepad.exe    C:\\Users\\Name\\Documents    https://www.google.com    shell:Personal (= Documents)":
        "Primeri: notepad.exe    C:\\Users\\Ime\\Documents    https://www.google.com    shell:Personal (= mapa Dokumenti)",
    "Steps:": "Koraki:",
    "One step per line:\n"
    "  keys: Ctrl+C          press a key combination\n"
    "  text: Hello there     type a text\n"
    "  wait: 500             wait 500 milliseconds\n"
    "  open: C:\\path\\x.exe   open a program, file, folder or web address":
        "En korak v vsaki vrstici:\n"
        "  keys: Ctrl+C          pritisni kombinacijo tipk\n"
        "  text: Pozdravljeni    vnesi besedilo\n"
        "  wait: 500             počakaj 500 milisekund\n"
        "  open: C:\\pot\\x.exe    odpri program, datoteko, mapo ali spletni naslov",
    "Also stop Windows' own function of this key": "Izklopi tudi vgrajeno funkcijo te tipke v sistemu Windows",
    "Apply to this key": "Uporabi za to tipko",
    "Test now": "Preizkusi zdaj",
    "Save and close": "Shrani in zapri",
    "Save": "Shrani",
    "nothing": "nič",
    "Windows already gives this key a function (%s). You can add your own; tick the box below to switch the Windows function off.":
        "Windows tej tipki že dodeljuje funkcijo (%s). Lahko ji dodaš svojo; označi polje spodaj, če želiš izklopiti funkcijo sistema Windows.",
    "Windows ignores this key, so it is free for your own use.": "Windows to tipko prezre, zato je prosta za tvojo uporabo.",
    "Choose a program or file": "Izberi program ali datoteko",
    "Choose a folder": "Izberi mapo",
    "Cannot apply": "Ni mogoče uporabiti",
    "Applied to %s (not saved yet)": "Uporabljeno za %s (še ni shranjeno)",
    "Cannot test": "Ni mogoče preizkusiti",
    "Test": "Preizkus",
    "The keystrokes will go to whatever window is active 2 seconds after you click OK. Click OK, then click into the window where they should land (e.g. Notepad).":
        "Tipke bodo poslane v okno, ki bo aktivno 2 sekundi po kliku na V redu. Klikni V redu in nato klikni v okno, kamor naj gredo (npr. Beležnica).",
    "Test done: %s": "Preizkus končan: %s",
    "Test failed": "Preizkus ni uspel",
    "Cannot save": "Ni mogoče shraniti",
    "Could not write %s:\n%s": "Zapis v %s ni uspel:\n%s",
    "Saved. The tray program picks the change up within a few seconds.":
        "Shranjeno. Program v opravilni vrstici spremembo prevzame v nekaj sekundah.",
    "Discard changes?": "Zavržem spremembe?",
    "You have unsaved changes. Close anyway?": "Imaš neshranjene spremembe. Vseeno zaprem?",
    "Remove every key assignment?": "Odstranim vse dodelitve tipk?",
    "Save a backup of the settings": "Shrani varnostno kopijo nastavitev",
    "Igor's Keys settings": "Nastavitve Igor's Keys",
    "Backup written to %s": "Varnostna kopija shranjena v %s",
    "Backup failed": "Varnostna kopija ni uspela",
    "Choose a settings backup to restore": "Izberi varnostno kopijo za obnovitev",
    "Restore": "Obnovitev",
    "Replace all current key assignments with the ones in\n%s ?": "Zamenjam vse trenutne dodelitve tipk s tistimi iz\n%s ?",
    "Restore failed": "Obnovitev ni uspela",
    "Restored %d assignment(s) from %s": "Obnovljenih dodelitev: %d iz %s",
    "All files": "Vse datoteke",
    "Choose the old KeyM@n configuration": "Izberi staro nastavitev KeyM@n",
    "Cherry shortcut file": "Datoteka bližnjic Cherry",
    "Import failed": "Uvoz ni uspel",
    "This does not look like a KeyM@n .csf file:\n%s": "To ni videti kot datoteka KeyM@n .csf:\n%s",
    "Import": "Uvoz",
    "%d key assignment(s) found. Add them (existing assignments for the same keys are replaced)?\n\n%s":
        "Najdenih dodelitev tipk: %d. Jih dodam (obstoječe dodelitve istih tipk bodo zamenjane)?\n\n%s",
    "Imported %d assignment(s) from %s (not saved yet)": "Uvoženih dodelitev: %d iz %s (še ni shranjeno)",
    "Record a key combination": "Snemanje kombinacije tipk",
    "Press the key combination now,\nfor example hold Ctrl and tap C.\n\nPress Esc to cancel.":
        "Zdaj pritisni kombinacijo tipk,\nnpr. drži Ctrl in pritisni C.\n\nEsc prekliče.",
    "Recorded: %s": "Posneto: %s",
    # key presets
    "Copy": "Kopiraj", "Cut": "Izreži", "Paste": "Prilepi", "Undo": "Razveljavi", "Redo": "Ponovi",
    "Select all": "Izberi vse", "Print": "Natisni", "Find": "Najdi",
    "New browser tab": "Nov zavihek v brskalniku", "Close tab / document": "Zapri zavihek / dokument",
    "Close window": "Zapri okno", "Zoom in": "Povečaj", "Zoom out": "Pomanjšaj", "Page up": "Stran gor",
    "Page down": "Stran dol", "Show desktop": "Pokaži namizje", "File Explorer": "Raziskovalec",
    "Windows Settings": "Nastavitve sistema Windows", "Screenshot (snip)": "Posnetek zaslona (izrez)",
    "Task view": "Pogled opravil", "Start menu": "Meni Start", "Volume up": "Glasnost gor",
    "Volume down": "Glasnost dol", "Mute": "Utišaj", "Play / pause": "Predvajaj / premor",
    "Next track": "Naslednja skladba", "Previous track": "Prejšnja skladba", "Stop media": "Ustavi predvajanje",
    "Open calculator (Windows key function)": "Odpri računalo (vgrajena funkcija Windows)",
    "Open e-mail program": "Odpri e-poštni program", "Browser home": "Domača stran brskalnika",
    "Browser back": "Brskalnik: nazaj", "Browser forward": "Brskalnik: naprej", "Browser refresh": "Brskalnik: osveži",
    "Browser search": "Brskalnik: iskanje",
    # open presets
    "Documents folder": "Mapa Dokumenti", "Downloads folder": "Mapa Prenosi", "Pictures folder": "Mapa Slike",
    "Videos folder": "Mapa Videoposnetki", "Music folder": "Mapa Glasba", "Desktop folder": "Mapa Namizje",
    "This PC": "Ta računalnik", "Recycle Bin": "Koš", "Control Panel": "Nadzorna plošča", "Notepad": "Beležnica",
    "Calculator": "Računalo", "Paint": "Slikar", "Snipping tool": "Orodje za izrezovanje",
    "Task Manager": "Upravitelj opravil", "Command prompt": "Ukazni poziv", "Lock the computer": "Zakleni računalnik",
    "Put the computer to sleep": "Preklopi računalnik v spanje", "Wikipedia": "Wikipedija",
    # key groups
    "Side keys (XPress)": "Stranske tipke (XPress)", "Multimedia keys": "Večpredstavnostne tipke",
    "Internet keys": "Internetne tipke", "Premium keys": "Tipke Premium",
    # tray
    "paused": "ustavljeno", "%d key(s) active": "aktivnih tipk: %d",
    "Edit key assignments...": "Uredi dodelitve tipk ...", "Reload assignments": "Znova naloži dodelitve",
    "Resume": "Nadaljuj", "Pause": "Ustavi", "Start with Windows": "Zaženi skupaj z Windows",
    "Language": "Jezik", "Automatic (Windows language)": "Samodejno (jezik sistema Windows)",
    "Open log file": "Odpri dnevniško datoteko", "Open settings folder": "Odpri mapo z nastavitvami", "Quit": "Izhod",
    "Igor's Keys could not start listening for the keyboard:\n%s": "Igor's Keys ne more začeti poslušati tipkovnice:\n%s",
    # command-line backup / restore dialogs
    "Save a backup of the Igor's Keys settings": "Shrani varnostno kopijo nastavitev Igor's Keys",
    "Choose an Igor's Keys settings backup to restore": "Izberi varnostno kopijo nastavitev Igor's Keys za obnovitev",
    "Restored %d key assignment(s). The tray program reloads them by itself.":
        "Obnovljenih dodelitev tipk: %d. Program v opravilni vrstici jih naloži sam.",
}

KEY_LABELS_SL = {
    "XPress 1": "Levi stolpec, 1. tipka (F1, ikona pomik gor)",
    "XPress 2": "Levi stolpec, 2. tipka (F2, ikona pomik dol)",
    "XPress 3": "Levi stolpec, 3. tipka (F3, škarje / izreži)",
    "XPress 4": "Levi stolpec, 4. tipka (F4, ikona prilepi)",
    "XPress 5": "Levi stolpec, 5. tipka (F5, ikona kopiraj)",
    "XPress 6": "Desni stolpec, 1. tipka (F6, dokument 1)",
    "XPress 7": "Desni stolpec, 2. tipka (F7, dokument 2)",
    "XPress 8": "Desni stolpec, 3. tipka (F8, dokument 3)",
    "XPress 9": "Desni stolpec, 4. tipka (F9, puščica ponovi)",
    "XPress 10": "Desni stolpec, 5. tipka (F10, puščica razveljavi)",
    "Calculator": "Tipka računalo",
    "E-Mail": "Tipka e-pošta",
    "WWW Home": "Tipka internet / domov",
    "Volume -": "Glasnost dol",
    "Volume +": "Glasnost gor",
    "Mute": "Utišaj",
    "Media player": "Tipka predvajalnik",
    "Internet Back": "Brskalnik: nazaj",
    "Internet Forward": "Brskalnik: naprej",
    "Internet Stop": "Brskalnik: ustavi",
    "Internet Refresh": "Brskalnik: osveži",
    "Internet Search": "Brskalnik: iskanje",
    "Media Play/Pause": "Predvajaj / premor",
    "Media Stop": "Ustavi predvajanje",
    "Media Previous": "Prejšnja skladba",
    "Media Next Track": "Naslednja skladba",
    "Media Eject": "Izvrzi",
}
