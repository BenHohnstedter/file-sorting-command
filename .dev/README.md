# Erinnerungen sortieren

Sortiert Fotos und Videos automatisch nach ihrem **echten Aufnahmedatum** in
Jahres- und Monatsordner. Läuft nativ unter Windows 10 und 11.

## Aufbau

Kopiert werden nur zwei Dinge: die Startdatei und der Ordner `.dev`.
Alles andere legt das Programm selbst an.

```
KI Sortierung\
├── sortieren.bat              <- das Einzige, was angeklickt wird
├── Unsortierte Dateien\         <- hier kommen die Fotos rein
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
    ├── README.md
    ├── SPEC.md
    └── sortier-log.txt
```

Die Anwenderin sieht also genau **vier Ordner und eine Datei**. Der Ordner
`.dev` bekommt beim ersten echten Lauf automatisch das Windows-Attribut
*versteckt* und verschwindet aus dem Explorer.

**Wieder rankommen** (falls du selbst rein willst): oben in die Adresszeile
des Explorers `.dev` tippen und Enter drücken — das geht auch bei
ausgeblendetem Ordner. Oder *Ansicht → Einblenden → Ausgeblendete Elemente*.
Dauerhaft abschalten lässt es sich mit `PROGRAMMORDNER_VERSTECKEN = False`
in [sortierer.py](sortierer.py).

Die Startdatei darf beliebig heißen — das Programm erkennt den Basisordner
daran, dass es selbst in `.dev` liegt, nicht am Namen der `.bat`. Wenn du
dagegen den Ordner `.dev` umbenennst, musst du `ORDNER_PROGRAMM` in
[sortierer.py](sortierer.py) mit ändern.

## Bedienung

**Beim allerersten Mal:** Einen Ordner anlegen (z. B. `C:\KI Sortierung`),
`sortieren.bat` und den Ordner `.dev` hineinkopieren und einmal auf
**`sortieren.bat`** doppelklicken. Das Programm legt alle Ordner selbst an,
versteckt sich und sagt Bescheid, dass es jetzt losgehen kann.

**Danach immer:**

1. Fotos und Videos in den Ordner **`Unsortierte Dateien`** legen
   (Unterordner sind erlaubt, beliebig tief).
2. Doppelklick auf **`sortieren.bat`**.
3. Fertig. Das Fenster bleibt offen, bis Enter gedrückt wird.

Fehlt später einmal ein Ordner, weil er versehentlich gelöscht wurde, legt
ihn das Programm beim nächsten Start einfach wieder an.

Wer vorher nur schauen will, was passieren *würde*: **`Testlauf.bat`**
im Ordner `.dev`. Dabei wird nichts verschoben und nichts angelegt.
Die Datei liegt bewusst im versteckten Ordner — die Anwenderin soll
nur eine einzige Datei zum Anklicken vor sich haben.

Das Programm kann so oft laufen, wie man möchte. Läuft es mit leerem
Eingangsordner, kommt nur eine freundliche Meldung.

**Dateien werden ausschließlich verschoben — niemals gelöscht oder
überschrieben.**

## Einmalige Einrichtung

Python 3 muss installiert sein (<https://www.python.org/downloads/>, beim
Installieren den Haken bei *"Add Python to PATH"* setzen). Danach einmal in
der PowerShell im Ordner `.dev`:

```bash
py -m pip install -r requirements.txt
```

Ohne `Pillow` läuft das Programm trotzdem — Fotos landen dann aber alle in
`Zum Durchsehen\Ohne Datum`, weil kein EXIF gelesen werden kann.

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

Auf dem neuen Rechner muss außerdem Python installiert sein — siehe
*Einmalige Einrichtung*. `sortieren.bat` prüft das und sagt Bescheid, wenn
etwas fehlt.

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
* **AVI, WMV, MKV:** enthalten meist kein auslesbares Datum → `Zum Durchsehen\Ohne Datum`.
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

Metadaten haben immer Vorrang. Steht im EXIF ein anderes Datum als im
Namen, gewinnt das EXIF.

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
(`rechnung_12345678.pdf`, `1404345600.jpg`) und alles außerhalb von
1990 bis heute.

## Was du anpassen kannst

Alles Einstellbare steht ganz oben in [sortierer.py](sortierer.py) im Block
`EINSTELLUNGEN`:

| Stelle | Bedeutung |
|---|---|
| `DATUM_AUS_DATEINAMEN` ([sortierer.py:25](sortierer.py:25)) | Standard `True`: fehlt das Aufnahmedatum in den Metadaten, wird es aus dem Dateinamen gelesen. Auf `False` setzen, um ausschließlich Metadaten zu verwenden. |
| `ORDNER_PROGRAMM` ([sortierer.py:29](sortierer.py:29)) | Name des versteckten Programmordners (`.dev`). Beim Umbenennen des Ordners hier mit ändern. |
| `PROGRAMMORDNER_VERSTECKEN` ([sortierer.py:33](sortierer.py:33)) | Standard `True`. Auf `False` setzen, wenn `.dev` im Explorer sichtbar bleiben soll. |
| `ORDNER_EINGANG`, `ORDNER_BILDER`, `ORDNER_VIDEOS` ([sortierer.py:36](sortierer.py:36)) | Die drei Ordner, die die Anwenderin oben sieht. |
| `ORDNER_SAMMEL` ([sortierer.py:42](sortierer.py:42)) | Das Dach über den vier Sonderordnern (`Zum Durchsehen`). Darunter: `ORDNER_OHNE_DATUM`, `ORDNER_GELOESCHT`, `ORDNER_DOPPELT`, `ORDNER_SONSTIGES`. |
| `BILD_ENDUNGEN` / `VIDEO_ENDUNGEN` ([sortierer.py:51](sortierer.py:51)) | Endungslisten. Immer **klein** und **ohne Punkt** eintragen — Groß-/Kleinschreibung der echten Dateien ist egal. |
| `GELOESCHT_PRAEFIXE`, `GELOESCHT_TEILE`, `GELOESCHT_ORDNER` ([sortierer.py:61](sortierer.py:61)) | Erkennungsmerkmale für Papierkorb-Dateien. Alles klein schreiben. |
| `MONATSNAMEN` ([sortierer.py:68](sortierer.py:68)) | Die zwölf Monatsordner-Namen, in Reihenfolge Januar–Dezember. |
| `JAHR_MINIMUM` ([sortierer.py:75](sortierer.py:75)) | Ab welchem Jahr ein Datum als plausibel gilt. |

HEIC-Fotos vom iPhone brauchen zusätzlich `pillow-heif`
(`py -m pip install pillow-heif`). Ist es installiert, wird es automatisch
benutzt; fehlt es, landen HEIC-Dateien in `Zum Durchsehen`.

## Protokoll

`.dev\sortier-log.txt` (also im versteckten Ordner). Jeder Lauf hängt einen Abschnitt mit
Zeitstempel an (nichts wird überschrieben): pro Datei eine Zeile
`Quelle -> Ziel` bzw. die Fehlermeldung, am Ende die Zusammenfassung.

## Wenn etwas schiefgeht

Eine kaputte, gesperrte oder zu lang benannte Datei bricht den Lauf nicht ab:
sie bleibt liegen, der Fehler landet im Protokoll, es geht weiter. Am Ende
steht dann zusätzlich `Nicht verarbeitet: n` in der Zusammenfassung.

## Dateien

| Datei | Zweck |
|---|---|
| `sortieren.bat` | Doppelklick zum Sortieren — im sichtbaren Ordner |
| [Testlauf.bat](Testlauf.bat) | Doppelklick, zeigt nur an — in `.dev\` |
| [sortierer.py](sortierer.py) | das Programm |
| [requirements.txt](requirements.txt) | Abhängigkeit (`Pillow`) |
| [SPEC.md](SPEC.md) | die ursprüngliche Aufgabenstellung |
