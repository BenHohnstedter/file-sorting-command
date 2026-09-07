# Erinnerungen sortieren

Sortiert Fotos und Videos automatisch nach ihrem **echten Aufnahmedatum** in
Jahres- und Monatsordner — gelesen aus den Metadaten, nicht aus dem
Dateisystem-Datum. Läuft nativ unter Windows 10 und 11.

Gebaut für jemanden, der kein Terminal benutzt: Dateien in einen Ordner
werfen, einmal doppelklicken, fertig.

**Dateien werden ausschließlich verschoben — niemals gelöscht oder
überschrieben.** Das ist die wichtigste Regel des ganzen Programms.

## Aufbau

Kopiert werden nur zwei Dinge: `sortieren.bat` und der Ordner `.dev`.
Alles andere legt das Programm selbst an.

```
Erinnerungen\
├── sortieren.bat              <- das Einzige, was angeklickt wird
├── Unsortierte Dateien\       <- hier kommen die Fotos rein
├── Bilder\
│   └── 2019\03-März\
├── Videos\
│   └── 2019\07-Juli\
├── Zum Durchsehen\            <- alles ohne Aufnahmedatum
│   ├── Ohne Datum\
│   ├── Gelöschte Dateien\
│   ├── Doppelte Dateien\
│   └── Sonstige Dateien\
└── .dev\                      <- versteckt, hier steckt die Technik
    ├── sortierer.py
    ├── Testlauf.bat
    ├── requirements.txt
    ├── SPEC.md
    └── sortier-log.txt
```

Die Anwenderin sieht also genau **vier Ordner und eine Datei**. Der Ordner
`.dev` bekommt beim ersten echten Lauf automatisch das Windows-Attribut
*versteckt* und verschwindet aus dem Explorer.

**Wieder rankommen:** oben in die Adresszeile des Explorers `.dev` tippen und
Enter drücken — das geht auch bei ausgeblendetem Ordner. Oder
*Ansicht → Einblenden → Ausgeblendete Elemente*. Dauerhaft abschalten lässt
es sich mit `PROGRAMMORDNER_VERSTECKEN = False` in
[.dev/sortierer.py](.dev/sortierer.py).

Die Startdatei darf beliebig heißen — das Programm erkennt den Basisordner
daran, dass es selbst in `.dev` liegt, nicht am Namen der `.bat`. Wenn du
dagegen den Ordner `.dev` umbenennst, musst du `ORDNER_PROGRAMM` mit ändern.

## Bedienung

**Beim allerersten Mal:** Einen Ordner anlegen (z. B. `C:\Erinnerungen`),
`sortieren.bat` und den Ordner `.dev` hineinkopieren und einmal auf
**`sortieren.bat`** doppelklicken. Das Programm legt alle Ordner selbst an,
versteckt sich und sagt Bescheid, dass es jetzt losgehen kann.

**Danach immer:**

1. Fotos und Videos in den Ordner **`Unsortierte Dateien`** legen
   (Unterordner sind erlaubt, beliebig tief).
2. Doppelklick auf **`sortieren.bat`**.
3. Fertig. Das Fenster bleibt offen, bis Enter gedrückt wird.

Fehlt später einmal ein Ordner, weil er versehentlich gelöscht wurde, legt
ihn das Programm beim nächsten Start einfach wieder an. Bestehende Ordner
mit dem richtigen Namen werden benutzt, nicht ersetzt.

Wer vorher nur schauen will, was passieren *würde*: **`Testlauf.bat`** im
Ordner `.dev`. Dabei wird nichts verschoben und nichts angelegt. Die Datei
liegt bewusst im versteckten Ordner — die Anwenderin soll nur eine einzige
Datei zum Anklicken vor sich haben.

Das Programm kann so oft laufen, wie man möchte. Läuft es mit leerem
Eingangsordner, kommt nur eine freundliche Meldung.

## Einmalige Einrichtung

Python 3.8 oder neuer muss installiert sein
(<https://www.python.org/downloads/>, beim Installieren den Haken bei
*"Add python.exe to PATH"* setzen). Danach einmal in der PowerShell:

```bash
py -m pip install -r .dev/requirements.txt
```

Ohne `Pillow` läuft das Programm trotzdem — Fotos landen dann aber alle in
`Zum Durchsehen\Ohne Datum`, weil kein EXIF gelesen werden kann.

HEIC-Fotos vom iPhone brauchen zusätzlich `pillow-heif`
(`py -m pip install pillow-heif`). Ist es installiert, wird es automatisch
benutzt.

## Auf einen anderen Computer umziehen

Hier lauert die einzige echte Stolperfalle: **`.dev` ist versteckt.** Wer den
Sortier-Ordner öffnet und den Inhalt mit Strg+A markiert, erwischt `.dev`
nicht — auf dem Zielrechner blitzt dann nur kurz ein schwarzes Fenster auf.

Richtig geht es so:

1. Eine Ebene **höher** gehen, den Sortier-Ordner **selbst** anklicken und
   diesen kopieren. Dann kommt `.dev` automatisch mit.
2. Oder: Rechtsklick auf den Ordner → *Senden an* → *ZIP-komprimierter
   Ordner*, und die ZIP-Datei rüberkopieren.

Zur Kontrolle auf dem Zielrechner: *Ansicht → Einblenden → Ausgeblendete
Elemente*. Dann muss `.dev` dort auftauchen.

`sortieren.bat` prüft beides und sagt verständlich Bescheid, statt sich
wortlos zu schließen — auch wenn auf dem Zielrechner Python fehlt.

## Wohin welche Datei kommt

Die Regeln werden in dieser Reihenfolge geprüft:

| Reihenfolge | Merkmal | Ziel |
|---|---|---|
| 1 | Papierkorb-Merkmale (`.trashed-`, `.pending-`, `trashed`, `.deleted`, oder liegt in `.trash`, `Trash`, `Papierkorb`, `$RECYCLE.BIN`, `Recently Deleted`, `Zuletzt gelöscht`) | `Zum Durchsehen\Gelöschte Dateien` |
| 2 | Am Ziel liegt schon eine Datei mit **gleichem Namen und gleicher Größe** | `Zum Durchsehen\Doppelte Dateien` |
| 3 | Bild- oder Video-Endung **mit** Aufnahmedatum | `Bilder\2019\03-März` bzw. `Videos\2019\07-Juli` |
| 3b | Bild- oder Video-Endung **ohne** Aufnahmedatum | `Zum Durchsehen\Ohne Datum` |
| 4 | Alles andere (PDF, Dokumente, `.thumbnails`, Unbekanntes) | `Zum Durchsehen\Sonstige Dateien` |

Gleicher Name, aber **andere** Größe? Dann ist es kein Duplikat — die Datei
bekommt `_1`, `_2` … vor der Endung (`IMG_1234_1.jpg`), damit nichts
überschrieben wird.

Am Ende werden leere Unterordner in `Unsortierte Dateien` entfernt.
`Unsortierte Dateien` selbst bleibt bestehen.

## Woher das Aufnahmedatum kommt

Es zählt nur das echte Aufnahmedatum aus den Metadaten — **nicht** das
Erstell-, Änderungs- oder Kopierdatum vom Dateisystem.

* **Fotos:** EXIF-Feld `DateTimeOriginal`, ersatzweise `DateTimeDigitized`.
* **Videos (MP4/MOV/M4V/3GP):** das `mvhd`-Atom wird direkt aus der Datei
  gelesen (`moov` → `mvhd`, Zeitrechnung ab 01.01.1904 UTC, wird in lokale
  Zeit umgerechnet). Keine Zusatzbibliothek nötig.
* **AVI, WMV, MKV:** enthalten meist kein auslesbares Datum →
  `Zum Durchsehen\Ohne Datum`.
* Unplausible Werte (vor 1990 oder in der Zukunft) gelten als *kein Datum*.

**Wenn in den Metadaten nichts steht**, wird das Datum aus dem Dateinamen
gelesen — das betrifft vor allem Screenshots und WhatsApp-Bilder:

| Dateiname | erkannt als |
|---|---|
| `IMG-20140703.jpg` | 03.07.2014 |
| `IMG_20180405_123456.jpg` | 05.04.2018 |
| `PXL_20220101_101112.jpg` | 01.01.2022 |
| `VID-20190712-WA0001.mp4` | 12.07.2019 |
| `Screenshot_2021-05-03.png` | 03.05.2021 |
| `WhatsApp Image 2019-07-12 at 20.11.jpeg` | 12.07.2019 |
| `20140703120000.mp4` | 03.07.2014 |

Metadaten haben immer Vorrang. Steht im EXIF ein anderes Datum als im Namen,
gewinnt das EXIF.

**Absichtlich übersprungen werden Namen, die nach einer Hexadezimal-Prüfsumme
aussehen** — dort wäre jede gefundene Zahl reiner Zufall. Erkennungsmerkmal:
das Wort ist mindestens acht Zeichen lang und *alle* Buchstaben darin stammen
aus dem Hex-Alphabet `a`–`f`. Beispiele, die deshalb in
`Zum Durchsehen\Ohne Datum` landen: `c20140703ab.jpg`, `deadbeef20140703.jpg`,
`5f3a2b1c9d0e.jpg`.

Normale Kamera-Kürzel sind davon nicht betroffen: `IMG`, `DSC`, `PXL` und
`VID` enthalten Buchstaben, die es im Hexadezimalsystem nicht gibt — solche
Namen werden ganz normal gelesen.

Ebenfalls verworfen: Zahlen, die kein gültiges Datum ergeben
(`IMG_20143299.jpg`), Ziffernblöcke mit falscher Länge
(`rechnung_12345678.pdf`, `1404345600.jpg`) und alles außerhalb von 1990
bis heute.

## Alles bleibt lokal

Das Programm hat keinerlei Netzwerkcode — kein `urllib`, kein `requests`,
kein `socket`, kein `subprocess`. Es kann technisch gar nichts hochladen.
Fotos werden nur innerhalb des Ordners von A nach B verschoben.

Einzige Einschränkung, die nichts mit dem Programm zu tun hat: Wenn der
Sortier-Ordner *innerhalb* eines Sync-Ordners liegt (OneDrive, Google Drive,
Dropbox), lädt dieser Client die Dateien hoch. Windows 11 synchronisiert
„Bilder" und „Dokumente" oft standardmäßig nach OneDrive — den Ordner
deshalb besser direkt auf `C:\` anlegen.

## Was du anpassen kannst

Alles Einstellbare steht ganz oben in [.dev/sortierer.py](.dev/sortierer.py)
im Block `EINSTELLUNGEN`:

| Stelle | Bedeutung |
|---|---|
| `DATUM_AUS_DATEINAMEN` ([Zeile 25](.dev/sortierer.py#L25)) | Standard `True`: fehlt das Aufnahmedatum in den Metadaten, wird es aus dem Dateinamen gelesen. Auf `False` setzen, um ausschließlich Metadaten zu verwenden. |
| `ORDNER_PROGRAMM` ([Zeile 29](.dev/sortierer.py#L29)) | Name des versteckten Programmordners (`.dev`). Beim Umbenennen des Ordners hier mit ändern. |
| `PROGRAMMORDNER_VERSTECKEN` ([Zeile 33](.dev/sortierer.py#L33)) | Standard `True`. Auf `False` setzen, wenn `.dev` im Explorer sichtbar bleiben soll. |
| `ORDNER_EINGANG`, `ORDNER_BILDER`, `ORDNER_VIDEOS` ([Zeile 36](.dev/sortierer.py#L36)) | Die drei Ordner, die die Anwenderin oben sieht. |
| `ORDNER_SAMMEL` ([Zeile 42](.dev/sortierer.py#L42)) | Das Dach über den vier Sonderordnern (`Zum Durchsehen`). Darunter: `ORDNER_OHNE_DATUM`, `ORDNER_GELOESCHT`, `ORDNER_DOPPELT`, `ORDNER_SONSTIGES`. |
| `BILD_ENDUNGEN` / `VIDEO_ENDUNGEN` ([Zeile 51](.dev/sortierer.py#L51)) | Endungslisten. Immer **klein** und **ohne Punkt** eintragen — Groß-/Kleinschreibung der echten Dateien ist egal. |
| `GELOESCHT_PRAEFIXE`, `GELOESCHT_TEILE`, `GELOESCHT_ORDNER` ([Zeile 61](.dev/sortierer.py#L61)) | Erkennungsmerkmale für Papierkorb-Dateien. Alles klein schreiben. |
| `MONATSNAMEN` ([Zeile 68](.dev/sortierer.py#L68)) | Die zwölf Monatsordner-Namen, in Reihenfolge Januar–Dezember. |
| `JAHR_MINIMUM` ([Zeile 75](.dev/sortierer.py#L75)) | Ab welchem Jahr ein Datum als plausibel gilt. |

## Protokoll

`.dev\sortier-log.txt`, also im versteckten Ordner. Jeder Lauf hängt einen
Abschnitt mit Zeitstempel an (nichts wird überschrieben): pro Datei eine
Zeile `Quelle -> Ziel` bzw. die Fehlermeldung, am Ende die Zusammenfassung.

## Wenn etwas schiefgeht

Jede Datei wird einzeln in `try`/`except` verarbeitet: eine kaputte,
gesperrte oder zu lang benannte Datei bricht den Lauf nicht ab. Sie bleibt
liegen, der Fehler landet im Protokoll, es geht weiter. Am Ende steht dann
zusätzlich `Nicht verarbeitet: n` in der Zusammenfassung.

Die Konsolenausgabe ist deutsch und ohne Tracebacks, und das Fenster bleibt
am Ende offen — auch im Fehlerfall.

## Tests

```bash
py -m unittest discover -s tests -v
```

11 Tests: Dateinamen-Parser einschließlich der Hex-Fälle, Papierkorb-
Erkennung, Basisordner-Sicherung und komplette Sortierläufe in einem
temporären Ordner (Duplikate, Nicht-Überschreiben, EXIF-Vorrang, Testlauf,
leerer Eingang).

## Dateien im Repository

| Datei | Zweck |
|---|---|
| `sortieren.bat` | Startdatei — wird mit ausgeliefert |
| [.dev/sortierer.py](.dev/sortierer.py) | das Programm |
| [.dev/Testlauf.bat](.dev/Testlauf.bat) | zeigt nur an, verschiebt nichts |
| [.dev/requirements.txt](.dev/requirements.txt) | Abhängigkeit (`Pillow`) |
| [.dev/SPEC.md](.dev/SPEC.md) | die ursprüngliche Aufgabenstellung |
| [tests/test_sortierer.py](tests/test_sortierer.py) | die Testsuite |

Für die Auslieferung werden nur `sortieren.bat` und `.dev` gebraucht —
`README.md`, `LICENSE` und `tests/` bleiben im Repository.

## Lizenz

[MIT](LICENSE)
