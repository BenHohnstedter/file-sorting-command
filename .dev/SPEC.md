Baue mir ein Python-Programm, das Fotos und Videos automatisch nach Aufnahmedatum in Ordner einsortiert.

## Wichtigste Rahmenbedingung

Das Programm läuft **nativ unter Windows 10 und 11** — nicht in WSL, nicht unter Linux. Auch wenn du gerade in einer Linux-Umgebung arbeitest: nutze ausschließlich plattformunabhängigen Python-Code (`pathlib`, `shutil`, `os`), keine Linux-only-Befehle, keine Shell-Aufrufe, keine hartkodierten Pfade mit `/`. Getestet wird später mit Windows-Python aus der PowerShell.

Bedienerin ist eine nicht-technische Person. Sie macht **einen Doppelklick**, sonst nichts. Kein Terminal-Wissen, keine Parameter, keine Konfiguration.

## Ordnerstruktur

Das Programm liegt in einem Ordner (z. B. `C:\Erinnerungen`) und arbeitet **relativ zu seinem eigenen Speicherort** — leite den Basisordner aus `Path(__file__).resolve().parent` ab. Es gibt keine Konfigurationsdatei und keine Pfadeingabe.

```
Erinnerungen\
├── Sortieren starten.bat      <- die einzige Datei, die angeklickt wird
├── Testlauf.bat               <- zeigt nur an, verschiebt nichts
├── sortierer.py
├── Unsortierte Daten\         <- hier kommt alles rein
├── Bilder\
│   └── 2019\
│       ├── 01-Januar\
│       └── 03-März\
├── Videos\
│   └── 2019\
│       └── 07-Juli\
├── Ohne Datum\
├── Gelöschte Daten\
├── Doppelte Daten\
├── Sonstige Dateien\
└── sortier-log.txt
```

Fehlende Ordner legt das Programm beim Start selbst an. Jahres- und Monatsordner werden nur angelegt, wenn es dafür auch wirklich Dateien gibt. Monatsordner heißen `01-Januar`, `02-Februar`, `03-März`, `04-April`, `05-Mai`, `06-Juni`, `07-Juli`, `08-August`, `09-September`, `10-Oktober`, `11-November`, `12-Dezember`.

## Ablauf

1. `Unsortierte Daten` **rekursiv** durchlaufen — beliebig tief verschachtelte Unterordner müssen mit erfasst werden.
2. Jede Datei einzeln prüfen und verschieben (siehe Regeln unten).
3. Am Ende: leere Unterordner in `Unsortierte Daten` löschen. `Unsortierte Daten` selbst bleibt bestehen und ist danach leer.
4. Zusammenfassung ausgeben.

Dateien werden **nur verschoben, niemals gelöscht oder überschrieben.** Das ist die wichtigste Regel des ganzen Programms.

## Einsortier-Regeln (in dieser Reihenfolge geprüft)

**1. Gelöschte Daten**
Erkennungsmerkmale im Dateinamen: beginnt mit `.trashed-`, `.pending-`, enthält `trashed`, `.deleted`, oder die Datei liegt in einem Ordner namens `.trash`, `Trash`, `Papierkorb`, `$RECYCLE.BIN`, `Recently Deleted`, `Zuletzt gelöscht`. → flach nach `Gelöschte Daten`, Originalname bleibt.

**2. Doppelte Daten**
Erkennung über **Dateiname + Dateigröße in Bytes**. Zwei Fälle:
- Am Zielort liegt bereits eine Datei mit gleichem Namen *und* gleicher Größe → die neue Datei kommt nach `Doppelte Daten`.
- Gleicher Name, *andere* Größe → nicht doppelt. Zielname um `_1`, `_2` … vor der Endung erweitern (`IMG_1234_1.jpg`), damit nichts überschrieben wird.

Innerhalb eines Laufs mitzählen: ein Set aus `(kleingeschriebener Name, Größe)` reicht.

**3. Bilder und Videos**
Nach Endung (Groß-/Kleinschreibung egal):
- Bilder: `jpg jpeg png heic heif gif bmp tif tiff webp dng cr2 nef arw raf orf rw2 srw`
- Videos: `mp4 mov m4v avi mkv 3gp mts m2ts wmv flv webm mpg mpeg`

Ziel: `Bilder\<Jahr>\<MM-Monat>\` bzw. `Videos\<Jahr>\<MM-Monat>\`

**4. Alles andere** (PDFs, Dokumente, `.thumbnails`, unbekannte Endungen) → `Sonstige Dateien`, flach.

## Aufnahmedatum ermitteln

Es zählt ausschließlich das **echte Aufnahmedatum** aus den Metadaten — nicht Erstell-, Änderungs- oder Kopierdatum des Dateisystems.

**Bilder:** EXIF-Feld `DateTimeOriginal` (Tag 36867), ersatzweise `DateTimeDigitized` (36868). Über Pillow (`Image.getexif()` bzw. `_getexif()`). Format ist `YYYY:MM:DD HH:MM:SS`.

**Videos:** Bei MP4/MOV/M4V/3GP den `mvhd`-Atom direkt auslesen — dafür brauchst du keine externe Bibliothek. Schreib eine kleine Funktion, die die Atom-Struktur durchläuft (`moov` → `mvhd`) und das `creation_time`-Feld liest. Achtung: Epoche ist der 01.01.1904, Zeit ist UTC → in lokale Zeit umrechnen. Werte von 0 oder offensichtlich unsinnige Werte (vor 1990, in der Zukunft) gelten als „kein Datum". Für AVI/WMV/MKV gibt es meist nichts Auslesbares — das ist okay.

**Kein Datum gefunden → `Ohne Datum`** (flach, Originalname). Nicht auf das Dateisystem-Datum ausweichen.

Zusätzlich: Baue eine Funktion, die ein Datum aus dem Dateinamen liest (`IMG_20180405_123456`, `PXL_20220101_...`, `VID-20190712-WA0001`, `Screenshot_2021-05-03`, `WhatsApp Image 2019-07-12`), und steuere sie über eine Konstante ganz oben im Skript:

```python
DATUM_AUS_DATEINAMEN = False   # auf True setzen, wenn Screenshots/WhatsApp-Bilder auch einsortiert werden sollen
```

Standard bleibt `False` — sie soll nur bei Bedarf umgelegt werden können.

## Ausgabe im Fenster

Für eine nicht-technische Person lesbar, auf Deutsch, keine Tracebacks:

```
Erinnerungen werden sortiert...

  812 Dateien gefunden

  [ 34 / 812 ]  IMG_1234.jpg  ->  Bilder\2019\03-März

Fertig!

  Bilder einsortiert:    640
  Videos einsortiert:     97
  Ohne Datum:             41
  Gelöschte Daten:        12
  Doppelte Daten:         18
  Sonstige Dateien:        4

  Ein Protokoll liegt in sortier-log.txt

Zum Schliessen Enter druecken.
```

Fortschritt in einer sich überschreibenden Zeile (`\r`) ist okay, aber halte es simpel. Am Ende **`input()`**, damit sich das Fenster nach dem Doppelklick nicht sofort schliesst — auch im Fehlerfall.

## Robustheit

- Jede Datei in `try/except` verarbeiten. Eine kaputte Datei darf den Lauf nicht abbrechen — Fehler ins Log, weitermachen.
- Der komplette `main()` in `try/except`, Fehlermeldung auf Deutsch, dann `input()`.
- Windows-Umlaute: Konsolenausgabe UTF-8-sicher machen (`sys.stdout.reconfigure(encoding='utf-8')` mit Fallback auf ASCII-Text, falls das scheitert).
- Windows-Pfadlängenlimit (260 Zeichen) beachten — sehr lange Pfade abfangen und ins Log schreiben statt abstürzen.
- `shutil.move` benutzen (funktioniert auch über Laufwerksgrenzen).
- Dateien in Benutzung / ohne Rechte: abfangen, ins Log, weiter.
- Das Programm muss **mehrfach hintereinander** laufen können. Zweiter Lauf mit leerem Eingangsordner: freundliche Meldung, kein Fehler.

## Logdatei

`sortier-log.txt` im Basisordner, wird bei jedem Lauf **angehängt** (nicht überschrieben). Pro Lauf ein Kopf mit Zeitstempel, dann pro Datei eine Zeile `Quelle -> Ziel` bzw. die Fehlermeldung, am Ende die Zusammenfassung.

## Testlauf-Modus

Aufruf mit `--test`: alles wird berechnet und angezeigt, aber **nichts verschoben und nichts angelegt**. In der Ausgabe deutlich als Testlauf kennzeichnen.

## Die zwei .bat-Dateien

`Sortieren starten.bat`:
```bat
@echo off
cd /d "%~dp0"
py sortierer.py
```

`Testlauf.bat`: dasselbe mit `py sortierer.py --test`.

Falls `py` nicht existiert, soll die .bat auf `python` ausweichen und andernfalls eine verständliche Meldung ausgeben, dass Python fehlt.

## Abhängigkeiten

Nur `Pillow`. Sonst Standardbibliothek. Leg eine `requirements.txt` an.

## Lieferumfang

`sortierer.py`, `Sortieren starten.bat`, `Testlauf.bat`, `requirements.txt`, kurze `README.md`.

Schreib den Code in klar getrennten Funktionen mit deutschen Kommentaren an den nicht offensichtlichen Stellen (vor allem beim mvhd-Parser). Erklär mir am Ende kurz, was du gebaut hast — vor allem, wo ich Endungslisten und Ordnernamen anpassen kann.