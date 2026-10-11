# Igor's Keys (slovenska navodila)

Igor's Keys poskrbi, da dodatne tipke tipkovnice **CHERRY CyMotion Master XPress** spet delujejo v sistemih
Windows 10 in 11. Nadomešča stari Cherryjev program KeyM@n, ki na sodobnih Windows ne deluje več.

> **Neuradno.** Igor's Keys je neodvisen ljubiteljski projekt in ni povezan s podjetjem Cherry, ga ne podpira in
> ni od njega odobren. CHERRY, CyMotion in KeyM@n so blagovne znamke njihovih lastnikov; tu so omenjene le zato,
> da je jasno, s katero tipkovnico in katerim starim programom deluje.

## Narejeno za eno tipkovnico

Igor's Keys je napisan in preizkušen za natanko eno tipkovnico:

| | |
|---|---|
| Tipkovnica | **CHERRY CyMotion Master XPress**, s po petimi tipkami XPress ob levem in desnem robu |
| Model | **G86-21050** (prodajne oznake na primer `G86-21050PLAAAA` in `G86-21050SLAAAA`; črke za številko se razlikujejo med različicami) |
| Priklop | USB + PS/2. **Igor's Keys deluje le, če je priklopljena prek USB.** |
| Windows jo vidi kot | napravo USB `046A:0023` |
| Prvotno podprto | Windows 98 SE / ME / 2000 / XP s Cherryjevim programom KeyM@n |

Opisi izdelka: [podatkovni list Icecat (G86-21050PLAAAA)](https://icecat.sg/p/cherry/g86-21050plaaaa/keyboards-cymotion+master+xpress-+g86-21050-779009.html#Specs),
[Melcomp (G86-21050SLAAAA)](https://www.melcomp.hr/CHERRY_G86-21050_SLAAAA_USB_PS2_CyMotion_Master_Xpress_-sreb).

Program posluša samo tipkovnico s to oznako USB, vse druge naprave prezre. Druge tipkovnice, tudi drugi modeli
Cherry, niso podprte.

Je majhen program, ki živi v opravilni vrstici (poleg ure) in čaka na dodatne tipke. Ko katero pritisnete,
naredi, kar ste mu naročili: vnese besedilo, pritisne kombinacijo tipk ali odpre program, mapo ali spletno stran.

## Namestitev

Prenesite datoteko `IgorsKeys-<različica>-win64.zip` s strani
[Releases](https://github.com/alpner/igors-keys/releases/latest) in jo razširite.

1. Celotno mapo `IgorsKeys` prekopirajte na stalno mesto, ki je vaše, na primer
   `C:\Users\<vaše ime>\IgorsKeys`. Pozneje je ne premikajte.
2. Dvokliknite `IgorsKeys.exe`. Poleg ure se pojavi ikona tipke (če je ne vidite, kliknite puščico `^`).
3. Z desno tipko miške kliknite ikono in označite **Zaženi skupaj z Windows**, da se program zažene ob vsaki prijavi.

Brez namestitve, brez skrbniških pravic, brez gonilnika. Tipkovnica za običajno tipkanje deluje natanko tako kot prej.

**Windows SmartScreen ali protivirusni program vas lahko opozori.** Program ni digitalno podpisan, zapakiran je s
PyInstallerjem ter spremlja tipkovnico in pošilja pritiske tipk – vse to varnostna orodja naredi previdna. V modrem
oknu SmartScreen kliknite **Več informacij → Vseeno zaženi**.

## Jezik

Program sam izbere slovenščino, če so Windows v slovenščini. Jezik lahko kadar koli zamenjate v meniju ikone:
**Jezik** → *Slovenščina*, *English* ali *Samodejno*.

## Katere tipke obvladuje?

| Tipke | Brez Igor's Keys | Z Igor's Keys |
|---|---|---|
| 5 tipk levo od črk (F1–F5 z ikonami) in 5 tipk desno od njih (F6–F10) | nič | kar jim dodelite |
| Izvrzi (Eject) | nič | kar ji dodelite |
| Glasnost −/+, Utišaj, Predvajalnik, Predvajaj/premor, Ustavi, Prejšnja, Naslednja | obvladuje Windows | še naprej Windows, razen če dodelite kaj svojega |
| Računalo, E-pošta, Internet/Domov, Nazaj, Naprej, Ustavi, Osveži, Iskanje | obvladuje Windows | še naprej Windows, razen če dodelite kaj svojega |

Če držite tipko **KeyM@n** in pritisnete eno od desetih stranskih tipk, dobite običajne tipke F1 … F10. To je
vgrajeno v tipkovnico in deluje z Igor's Keys ali brez njega.

Ob prvem zagonu sta nastavljeni le dve tipki: prva tipka desnega stolpca odpre mapo Dokumenti, druga pa mapo
Videoposnetki. Spremenite ali odstranite ju po želji.

## Dodeljevanje tipk

Z desno tipko miške kliknite ikono in izberite **Uredi dodelitve tipk …** (ali ikono dvokliknite).

1. Na levi kliknite tipko.
2. Izberite, kaj naj se zgodi:
   * **Vnesi besedilo** – na primer naslov ali podpis za e-pošto. Enter v besedilu pomeni novo vrstico.
   * **Pritisni kombinacijo tipk** – kliknite **Posnemi …** in pritisnite kombinacijo na tipkovnici, izberite
     katero s seznama **pogostih dejanj** (kopiraj, prilepi, glasnost, predvajaj …) ali jo vpišite, na primer
     `Ctrl+C`, `Alt+F4`, `Win+E`, `PageDown` ali `Enter`.
   * **Odpri program, datoteko, mapo ali spletni naslov** – izberite **pogosto mesto** (Dokumenti, Prenosi,
     Beležnica, Google, zakleni računalnik …), uporabite gumba za iskanje ali vpišite spletni naslov, na primer
     `https://www.google.com`. `shell:Personal` pomeni mapo Dokumenti.
   * **Izvedi več korakov zapored** – en korak v vsaki vrstici, na primer:
     ```
     keys: Win+R
     wait: 300
     text: notepad
     keys: Enter
     ```
3. Kliknite **Uporabi za to tipko** in nato **Shrani**. Program v opravilni vrstici spremembo prevzame sam v nekaj sekundah.

**Preizkusi zdaj** dejanje takoj izvede. Pri besedilu in kombinacijah tipk imate dve sekundi, da kliknete v okno,
kamor naj gredo tipke.

Pri tipkah, ki jih Windows že obvladuje (glasnost, računalo in podobno), je na voljo polje
**Izklopi tudi vgrajeno funkcijo te tipke v sistemu Windows**. Označite ga, če taki tipki dodelite novo nalogo in
nočete, da se zgodi še stara.

## Prenos starih nastavitev KeyM@n

V urejevalniku kliknite **Uvozi staro datoteko KeyM@n …** in izberite datoteko `.csf` (na primer
`CyMotionMasterXPress.csf`). Prikaže se seznam, kaj bo uvoženo; tipke, ki jih Windows obvladuje sam, ostanejo pri
miru, plast KeyM@n+tipka pa se preskoči, ker jo tipkovnica opravi sama.

## Varnostna kopija nastavitev

V urejevalniku (ali v meniju ikone) kliknite **Varnostna kopija nastavitev …** in izberite, kam shraniti datoteko,
na primer `IgorsKeys-settings-2026-10-11.json` na USB-ključ. **Obnovi nastavitve …** tako datoteko naloži nazaj in
zamenja vse dodelitve. Ob vsakem shranjevanju se prejšnja različica samodejno shrani tudi v
`C:\Users\<vaše ime>\AppData\Local\IgorsKeys\backups` (zadnjih 20).

## Meni v opravilni vrstici

* **Uredi dodelitve tipk …** – odpre urejevalnik.
* **Znova naloži dodelitve** – znova prebere datoteko z nastavitvami (običajno ni potrebno, zgodi se samodejno).
* **Ustavi / Nadaljuj** – Igor's Keys začasno izklopite, ne da bi ga zaprli.
* **Zaženi skupaj z Windows** – označite za samodejni zagon.
* **Jezik** – slovenščina, angleščina ali samodejno.
* **Varnostna kopija nastavitev … / Obnovi nastavitve …** – shranite dodelitve v datoteko ali jih naložite nazaj.
* **Odpri dnevniško datoteko** – pokaže, kaj je program počel; to datoteko pošljite, ko prosite za pomoč.
  Besedil, ki jih vnašajo vaše tipke, nikoli ne vsebuje, le njihovo dolžino.
* **Odpri mapo z nastavitvami** – kjer sta `config.json` (vaše dodelitve) in dnevnik:
  `C:\Users\<vaše ime>\AppData\Local\IgorsKeys`.
* **Izhod** – program ustavi, dokler ga znova ne zaženete.

## Če kaj ne deluje

* Ni ikone tipke? Kliknite puščico `^` poleg ure. Če je še vedno ni, znova zaženite `IgorsKeys.exe`; če že teče,
  se drugi zagon preprosto konča.
* Tipka ne naredi ničesar: v urejevalniku preverite, ali ima tipka dodelitev in ali Igor's Keys ni ustavljen.
  V dnevniški datoteki se ob vsakem pritisku stranske tipke pojavi vrstica, kot je `XPress 3 pressed`, in kaj je sledilo.
* Program se ob nenavadnem pritisku tipke nikoli ne sesuje; vse nepričakovano zapiše v dnevnik in prezre.
* Tipke za glasnost, predvajanje in brskalnik ne delujejo več: pri teh tipkah odznačite
  **Izklopi tudi vgrajeno funkcijo te tipke v sistemu Windows**.

## Odstranitev

V meniju ikone izberite **Izhod** (prej odznačite **Zaženi skupaj z Windows**, če ste ga vklopili), izbrišite mapo
`IgorsKeys` in po želji še `C:\Users\<vaše ime>\AppData\Local\IgorsKeys`.

Tehnične podrobnosti so v angleškem `README.md`.
