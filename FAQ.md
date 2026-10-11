# Igor's Keys – frequently asked questions

**Which keyboard is this for?**
Only the CHERRY CyMotion Master XPress, model G86-21050 (part numbers such as G86-21050PLAAAA or
G86-21050SLAAAA), connected by USB. Windows sees it as USB device 046A:0023, and Igor's Keys listens to that
device only, so other keyboards (other Cherry models included) are ignored.

**My keyboard is plugged in by PS/2. Does it work?**
No. Igor's Keys reads the keyboard's USB interface; on PS/2 the keyboard is not the USB device 046A:0023, so the
program never sees its extra keys. Plug it in by USB.

**Do I need to install a driver?**
No. Igor's Keys reads the keyboard through the Windows Raw Input API, which any program may use. No driver, no
administrator rights, nothing is written to the keyboard.

**Why did the side keys not work in Windows without Igor's Keys?**
The keyboard's USB description declares a smaller range of key codes than it actually sends. Windows' HID parser
trusts the description and throws away the codes above the limit (four of the side keys), and has no built-in
function for the other six. Cherry's old KeyM@n program worked around this with a kernel driver; Igor's Keys
reads the raw reports instead, which does not need a driver.

**Does it slow down typing or swallow keys?**
No. Igor's Keys does not register for the normal keyboard interface at all, and Raw Input is observation only: it
cannot block or alter anything. The only exception is the optional "Also stop Windows' own function of this key"
box, which blocks exactly one virtual key (for example Volume Up) when you have given that key a different job.

**What happens to the KeyM@n key?**
It is handled inside the keyboard: while you hold it, the ten side keys send the ordinary F1 to F10. Igor's Keys
cannot see the KeyM@n key itself and does not need to.

**Why does the Eject key do nothing?**
Windows has no built-in function for it. Give it a job in the editor if you want to use it.

**Where are my settings?**
`C:\Users\<your name>\AppData\Local\IgorsKeys\config.json`. Every time you save, the previous version is kept
in the `backups` folder next to it (the last 20). Use **Back up settings…** to write a copy anywhere you like and
**Restore settings…** to load one back.

**Can I copy my settings to another computer?**
Yes: back up on one machine, copy the file, restore on the other. Paths inside the settings (programs, folders)
must exist on the other machine too.

**Can I import my old KeyM@n setup?**
Yes, with **Import old KeyM@n file…** in the editor (`.csf` files). Text macros, key macros, programs, web
addresses and folders are converted. The KeyM@n+key layer is skipped (the keyboard does that itself) and keys
that Windows already handles, such as volume or play/pause, are left to Windows.

**A key does something twice.**
That happens when you give a key that Windows already handles (calculator, e-mail, media keys) a new job
without ticking "Also stop Windows' own function of this key".

**Pressing a side key types the wrong character / nothing in a game.**
Text is typed as Unicode and key combinations as virtual keys through SendInput. Some games and remote-desktop
sessions ignore synthetic input; there is no workaround for those.

**Does it start with Windows?**
Only if you tick **Start with Windows** in the tray menu. It adds an entry for your user account under
`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`; unticking removes it.

**How do I uninstall?**
Quit it from the tray menu, untick **Start with Windows** first if you had it on, delete the `IgorsKeys` folder,
and optionally delete `C:\Users\<your name>\AppData\Local\IgorsKeys`.

**Windows SmartScreen or my antivirus warns about it. Is it safe?**
The warning appears because the program is not code-signed and is packed with PyInstaller, and because it reads
the keyboard and sends keystrokes, which is also what malware does. It never sends anything over the network
and has no network code at all. The full source is in this repository, so you can read it or build the program
yourself. On the SmartScreen window click **More info → Run anyway**.

**Is this made by Cherry?**
No. It is an unofficial hobby project and is not affiliated with or supported by Cherry.

**Something is wrong, what do I send?**
The log file (tray menu > **Open log file**) and your settings backup. The log does not contain the texts your
keys type, only their length; the settings backup does, so look through it before you send it.
