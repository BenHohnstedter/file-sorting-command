# -*- coding: utf-8 -*-
"""
Sortiert Fotos und Videos aus dem Ordner "Unsortierte Dateien"
nach dem echten Aufnahmedatum in Jahres- und Monatsordner.

Laeuft nativ unter Windows 10/11 (reines Python, keine Shell-Aufrufe).
Bedienung: Doppelklick auf "Sortieren starten.bat".
"""

import os
import re
import sys
import shutil
import traceback
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# EINSTELLUNGEN  -  hier darf gefahrlos angepasst werden
# ---------------------------------------------------------------------------

# Wenn in den Metadaten kein Aufnahmedatum steht: Datum aus dem Dateinamen
# lesen (IMG-20140703.jpg -> 03.07.2014). Betrifft vor allem Screenshots
# und WhatsApp-Bilder. Auf False setzen, um das abzuschalten.
DATUM_AUS_DATEINAMEN = True

# Diese Datei liegt im Unterordner ".dev". Alles, was die Anwenderin
# sieht, liegt eine Ebene darueber.
ORDNER_PROGRAMM = ".dev"

# Den Programmordner im Explorer verstecken, damit im Sortier-Ordner nur
# die Startdatei und die vier Sammelordner sichtbar sind.
PROGRAMMORDNER_VERSTECKEN = True

# Die drei Ordner, die die Anwenderin sieht (neben der Startdatei)
ORDNER_EINGANG = "Unsortierte Dateien"
ORDNER_BILDER = "Bilder"
ORDNER_VIDEOS = "Videos"

# Alles ohne Aufnahmedatum sammelt sich unter einem gemeinsamen Dach -
# da soll noch einmal ein Mensch draufschauen.
ORDNER_SAMMEL = "Zum Durchsehen"
ORDNER_OHNE_DATUM = "Ohne Datum"
ORDNER_GELOESCHT = "Gelöschte Dateien"
ORDNER_DOPPELT = "Doppelte Dateien"
ORDNER_SONSTIGES = "Sonstige Dateien"
# Das Protokoll liegt beim Programm, nicht im sichtbaren Ordner.
LOG_DATEI = "sortier-log.txt"

# Dateiendungen (immer klein schreiben, ohne Punkt)
BILD_ENDUNGEN = {
    "jpg", "jpeg", "png", "heic", "heif", "gif", "bmp", "tif", "tiff",
    "webp", "dng", "cr2", "nef", "arw", "raf", "orf", "rw2", "srw",
}
VIDEO_ENDUNGEN = {
    "mp4", "mov", "m4v", "avi", "mkv", "3gp", "mts", "m2ts",
    "wmv", "flv", "webm", "mpg", "mpeg",
}

# Erkennung geloeschter / in den Papierkorb verschobener Dateien
GELOESCHT_PRAEFIXE = (".trashed-", ".pending-")
GELOESCHT_TEILE = ("trashed", ".deleted")
GELOESCHT_ORDNER = {
    ".trash", "trash", "papierkorb", "$recycle.bin",
    "recently deleted", "zuletzt gelöscht", "zuletzt geloescht",
}

MONATSNAMEN = [
    "01-Januar", "02-Februar", "03-März", "04-April", "05-Mai", "06-Juni",
    "07-Juli", "08-August", "09-September", "10-Oktober", "11-November",
    "12-Dezember",
]

# Plausibilitaetsgrenze fuer erkannte Aufnahmedaten
JAHR_MINIMUM = 1990
# Windows-Pfadlaengenlimit (260 Zeichen); etwas Reserve eingeplant
MAX_PFADLAENGE = 255

# ---------------------------------------------------------------------------
# Konsolenausgabe (UTF-8-sicher)
# ---------------------------------------------------------------------------

_NUR_ASCII = False


def konsole_vorbereiten():
    """Konsole auf UTF-8 stellen. Klappt das nicht, wird auf reinen
    ASCII-Text ausgewichen, damit Umlaute keinen Absturz verursachen."""
    global _NUR_ASCII
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            _NUR_ASCII = True
    try:
        "ÄÖÜäöüß".encode(sys.stdout.encoding or "ascii")
    except Exception:
        _NUR_ASCII = True


def _ascii_ersatz(text):
    tabelle = {
        "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss", "–": "-", "→": "->",
    }
    for zeichen, ersatz in tabelle.items():
        text = text.replace(zeichen, ersatz)
    return text.encode("ascii", "replace").decode("ascii")


def sag(text="", ende="\n"):
    """Schreibt Text auf die Konsole, notfalls ohne Umlaute."""
    if _NUR_ASCII:
        text = _ascii_ersatz(text)
    try:
        sys.stdout.write(text + ende)
        sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.write(_ascii_ersatz(text) + ende)
            sys.stdout.flush()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Logdatei
# ---------------------------------------------------------------------------

class Protokoll:
    """Schreibt sortier-log.txt. Wird bei jedem Lauf angehaengt."""

    def __init__(self, pfad, testlauf):
        self.pfad = pfad
        self.testlauf = testlauf
        self.datei = None
        try:
            self.datei = open(pfad, "a", encoding="utf-8")
            self.zeile("")
            self.zeile("=" * 70)
            titel = "TESTLAUF (es wird nichts verschoben)" if testlauf else "Sortierlauf"
            self.zeile("%s  -  %s" % (
                titel, datetime.now().strftime("%d.%m.%Y %H:%M:%S")))
            self.zeile("=" * 70)
        except Exception:
            # Ohne Protokoll weiterarbeiten ist besser als abbrechen.
            self.datei = None

    def zeile(self, text):
        if self.datei is None:
            return
        try:
            self.datei.write(text + "\n")
            self.datei.flush()
        except Exception:
            pass

    def schliessen(self):
        if self.datei is not None:
            try:
                self.datei.close()
            except Exception:
                pass
            self.datei = None


# ---------------------------------------------------------------------------
# Aufnahmedatum aus Bildern (EXIF)
# ---------------------------------------------------------------------------

try:
    from PIL import Image
    PILLOW_DA = True
except Exception:
    PILLOW_DA = False

if PILLOW_DA:
    # Optional: ist pillow-heif installiert, koennen auch HEIC-Dateien gelesen
    # werden. Fehlt das Paket, laeuft alles unveraendert weiter.
    try:
        import pillow_heif  # type: ignore
        pillow_heif.register_heif_opener()
    except Exception:
        pass

EXIF_AUFNAHME = 36867       # DateTimeOriginal
EXIF_DIGITALISIERT = 36868  # DateTimeDigitized
EXIF_IFD_ZEIGER = 0x8769    # Zeiger auf die Exif-Unter-IFD


def _text_zu_datum(wert):
    """EXIF-Zeitstempel 'YYYY:MM:DD HH:MM:SS' in ein datetime wandeln."""
    if not wert:
        return None
    if isinstance(wert, bytes):
        wert = wert.decode("ascii", "ignore")
    wert = str(wert).strip().strip("\x00").strip()
    for muster, laenge in (("%Y:%m:%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19),
                           ("%Y:%m:%d", 10), ("%Y-%m-%d", 10)):
        try:
            return _pruefe_datum(datetime.strptime(wert[:laenge], muster))
        except Exception:
            continue
    return None


def datum_aus_exif(pfad):
    """Liest DateTimeOriginal, ersatzweise DateTimeDigitized."""
    if not PILLOW_DA:
        return None
    try:
        with Image.open(pfad) as bild:
            kandidaten = []
            try:
                exif = bild.getexif()
            except Exception:
                exif = None
            if exif:
                # Die Aufnahmezeit steht in der Exif-Unter-IFD, nicht in der
                # Haupt-IFD - deshalb zuerst dort nachsehen.
                try:
                    unter = exif.get_ifd(EXIF_IFD_ZEIGER) or {}
                except Exception:
                    unter = {}
                kandidaten.append(unter)
                kandidaten.append(exif)
            if hasattr(bild, "_getexif"):
                try:
                    alt = bild._getexif()
                    if alt:
                        kandidaten.append(alt)
                except Exception:
                    pass
            for quelle in kandidaten:
                for tag in (EXIF_AUFNAHME, EXIF_DIGITALISIERT):
                    try:
                        datum = _text_zu_datum(quelle.get(tag))
                    except Exception:
                        datum = None
                    if datum:
                        return datum
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Aufnahmedatum aus Videos (mvhd-Atom in MP4/MOV/M4V/3GP)
# ---------------------------------------------------------------------------

# MP4- und MOV-Dateien bestehen aus verschachtelten "Atomen" (Boxen).
# Jedes Atom beginnt mit 4 Byte Groesse (einschliesslich Kopf) und 4 Byte Typ.
# Sonderfaelle: Groesse 1 -> danach folgen 8 Byte "largesize";
#               Groesse 0 -> das Atom reicht bis zum Dateiende.
# Gesucht wird im Container "moov" das Atom "mvhd". Dort steht direkt hinter
# Version (1 Byte) und Flags (3 Byte) die Erstellzeit als Sekunden seit dem
# 01.01.1904 UTC - 4 Byte bei Version 0, 8 Byte bei Version 1.

MP4_EPOCHE = datetime(1904, 1, 1, tzinfo=timezone.utc)
VIDEO_MIT_MVHD = {"mp4", "mov", "m4v", "3gp", "3g2", "qt"}


def _atome_lesen(datei, start, ende):
    """Liefert (Typ, Datenanfang, Datenende) fuer alle Atome im Bereich."""
    position = start
    zaehler = 0
    while position + 8 <= ende and zaehler < 1000:
        zaehler += 1
        datei.seek(position)
        kopf = datei.read(8)
        if len(kopf) < 8:
            return
        groesse = int.from_bytes(kopf[0:4], "big")
        typ = kopf[4:8].decode("latin-1")
        datenanfang = position + 8
        if groesse == 1:
            gross = datei.read(8)
            if len(gross) < 8:
                return
            groesse = int.from_bytes(gross, "big")
            datenanfang = position + 16
        elif groesse == 0:
            groesse = ende - position
        if groesse < 8:
            return
        datenende = min(position + groesse, ende)
        yield typ, datenanfang, datenende
        position += groesse


def datum_aus_mvhd(pfad):
    """Erstellzeit aus dem mvhd-Atom lesen und in lokale Zeit umrechnen."""
    try:
        dateigroesse = pfad.stat().st_size
        if dateigroesse < 16:
            return None
        with open(pfad, "rb") as datei:
            for typ, anfang, schluss in _atome_lesen(datei, 0, dateigroesse):
                if typ != "moov":
                    continue
                for untertyp, u_anfang, u_schluss in _atome_lesen(datei, anfang, schluss):
                    if untertyp != "mvhd":
                        continue
                    datei.seek(u_anfang)
                    rohdaten = datei.read(min(32, u_schluss - u_anfang))
                    if len(rohdaten) < 8:
                        return None
                    version = rohdaten[0]
                    if version == 1:
                        if len(rohdaten) < 12:
                            return None
                        sekunden = int.from_bytes(rohdaten[4:12], "big")
                    else:
                        sekunden = int.from_bytes(rohdaten[4:8], "big")
                    # 0 bedeutet "nicht gesetzt" -> kein Datum
                    if sekunden <= 0:
                        return None
                    try:
                        # UTC seit 1904 -> lokale Zeit, danach ohne Zeitzone
                        utc = MP4_EPOCHE + timedelta(seconds=sekunden)
                        lokal = utc.astimezone()
                        return _pruefe_datum(lokal.replace(tzinfo=None))
                    except (OverflowError, OSError, ValueError):
                        return None
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Aufnahmedatum aus dem Dateinamen (nur wenn DATUM_AUS_DATEINAMEN = True)
# ---------------------------------------------------------------------------

# Getrennte Schreibweise: Screenshot_2021-05-03, WhatsApp Image 2019-07-12
_MUSTER_GETRENNT = re.compile(
    r"(?<!\d)(19\d{2}|20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})(?!\d)")

# Buchstaben, die auch im Hexadezimal-Alphabet vorkommen
_HEX_BUCHSTABEN = set("abcdefABCDEF")


def _sieht_hexadezimal_aus(wort):
    """Woerter wie "5f3a2b1c9d0e" oder "c20140703ab" sind Pruefsummen oder
    interne IDs - die Ziffern darin sind Zufall und kein Datum.

    Erkennungsmerkmal: das Wort ist lang genug UND alle Buchstaben darin
    stammen aus dem Hex-Alphabet a-f. "IMG20140703" faellt nicht darunter
    (I, M und G gibt es im Hexadezimalsystem nicht), "DSC20140703" auch
    nicht (S kommt dort nicht vor) - solche Namen werden also gelesen."""
    buchstaben = [z for z in wort if z.isalpha()]
    if not buchstaben or len(wort) < 8:
        return False
    return all(z in _HEX_BUCHSTABEN for z in buchstaben)


def _datum_aus_ziffernblock(block):
    """Deutet einen reinen Ziffernblock als YYYYMMDD.
    Erlaubt sind genau 8 Ziffern (20140703) oder 14 Ziffern, wenn noch
    eine Uhrzeit drankleht (20140703_120000 -> 20140703120000).
    Alles andere ist keine Datumsangabe und wird verworfen."""
    if len(block) not in (8, 14):
        return None
    try:
        return _pruefe_datum(datetime(int(block[0:4]), int(block[4:6]),
                                      int(block[6:8])))
    except Exception:
        return None


def datum_aus_dateiname(name):
    """Findet ein Datum im Dateinamen, z. B. IMG-20140703.jpg -> 03.07.2014.

    Gelesen wird nur das Dezimalsystem. Namen, die nach einer
    Hexadezimal-Pruefsumme aussehen, werden bewusst uebersprungen -
    dort waere jede gefundene Zahl reiner Zufall."""
    stamm = Path(name).stem

    # 1. Getrennte Schreibweise zuerst - die ist eindeutig.
    treffer = _MUSTER_GETRENNT.search(stamm)
    if treffer:
        try:
            datum = _pruefe_datum(datetime(int(treffer.group(1)),
                                           int(treffer.group(2)),
                                           int(treffer.group(3))))
        except Exception:
            datum = None
        if datum:
            return datum

    # 2. Zusammengeschriebene Form, Wort fuer Wort.
    for wort in re.split(r"[^0-9A-Za-z]+", stamm):
        if not wort or _sieht_hexadezimal_aus(wort):
            continue
        for block in re.findall(r"\d+", wort):
            datum = _datum_aus_ziffernblock(block)
            if datum:
                return datum
    return None


def _pruefe_datum(datum):
    """Unsinnige Werte (vor 1990 oder in der Zukunft) verwerfen."""
    if datum is None:
        return None
    if datum.year < JAHR_MINIMUM:
        return None
    if datum > datetime.now() + timedelta(days=1):
        return None
    return datum


def aufnahmedatum_ermitteln(pfad, endung, art):
    """art ist 'bild' oder 'video'. Liefert datetime oder None."""
    datum = None
    if art == "bild":
        datum = datum_aus_exif(pfad)
    elif art == "video" and endung in VIDEO_MIT_MVHD:
        datum = datum_aus_mvhd(pfad)
    if datum is None and DATUM_AUS_DATEINAMEN:
        datum = datum_aus_dateiname(pfad.name)
    return datum


# ---------------------------------------------------------------------------
# Einordnung
# ---------------------------------------------------------------------------

def ist_geloescht(pfad, eingang):
    """Papierkorb-Merkmale im Dateinamen oder in einem Ordner darueber."""
    name = pfad.name.lower()
    if name.startswith(GELOESCHT_PRAEFIXE):
        return True
    if any(teil in name for teil in GELOESCHT_TEILE):
        return True
    try:
        teile = pfad.relative_to(eingang).parts[:-1]
    except Exception:
        teile = pfad.parts[:-1]
    for ordner in teile:
        if ordner.lower() in GELOESCHT_ORDNER:
            return True
    return False


def endung_von(pfad):
    return pfad.suffix.lower().lstrip(".")


def dateiart(endung):
    if endung in BILD_ENDUNGEN:
        return "bild"
    if endung in VIDEO_ENDUNGEN:
        return "video"
    return "sonstiges"


def monatsordner(datum):
    return MONATSNAMEN[datum.month - 1]


def durchsehen(basis, name):
    """Pfad zu einem der vier Ordner unter dem Sammeldach."""
    return basis / ORDNER_SAMMEL / name


def zielordner_bestimmen(pfad, basis, eingang):
    """Liefert (Zielordner, Kategorie).
    Kategorien: geloescht, bild, video, ohne_datum, sonstiges"""
    # Regel 1: Papierkorb-Dateien
    if ist_geloescht(pfad, eingang):
        return durchsehen(basis, ORDNER_GELOESCHT), "geloescht"

    endung = endung_von(pfad)
    art = dateiart(endung)

    # Regel 3: Bilder und Videos
    if art in ("bild", "video"):
        datum = aufnahmedatum_ermitteln(pfad, endung, art)
        if datum is None:
            # Kein Aufnahmedatum in den Metadaten - nicht auf das
            # Dateisystem-Datum ausweichen.
            return durchsehen(basis, ORDNER_OHNE_DATUM), "ohne_datum"
        oberordner = ORDNER_BILDER if art == "bild" else ORDNER_VIDEOS
        return basis / oberordner / str(datum.year) / monatsordner(datum), art

    # Regel 4: alles andere
    return durchsehen(basis, ORDNER_SONSTIGES), "sonstiges"


def freier_dateiname(ordner, name):
    """Haengt _1, _2 ... vor der Endung an, bis der Name frei ist.
    Damit wird garantiert nie eine vorhandene Datei ueberschrieben."""
    ziel = ordner / name
    if not ziel.exists():
        return ziel
    stamm = Path(name).stem
    endung = Path(name).suffix
    nummer = 1
    while nummer < 10000:
        kandidat = ordner / ("%s_%d%s" % (stamm, nummer, endung))
        if not kandidat.exists():
            return kandidat
        nummer += 1
    # Notnagel: Zeitstempel anhaengen
    return ordner / ("%s_%s%s" % (
        stamm, datetime.now().strftime("%Y%m%d%H%M%S%f"), endung))


# ---------------------------------------------------------------------------
# Hauptlauf
# ---------------------------------------------------------------------------

def dateien_einsammeln(eingang):
    """Eingangsordner rekursiv durchlaufen, beliebig tief verschachtelt."""
    gefunden = []
    for wurzel, unterordner, dateien in os.walk(eingang):
        for name in dateien:
            gefunden.append(Path(wurzel) / name)
    gefunden.sort(key=lambda p: str(p).lower())
    return gefunden


def _enthaelt_startdatei(ordner):
    """Liegt in diesem Ordner eine .bat-Datei? Der genaue Name ist egal -
    die Startdatei darf umbenannt werden."""
    try:
        return any(ordner.glob("*.bat"))
    except Exception:
        return False


def basisordner_ermitteln(programmordner):
    """Findet den sichtbaren Ordner, in dem sortiert wird.

    Normalfall: sortierer.py liegt im Unterordner ".dev", der Basisordner
    ist also eine Ebene darueber. Liegt sortierer.py ausnahmsweise direkt
    im Basisordner, wird dieser genommen. Passt nichts davon, bleiben wir
    beim eigenen Ordner - lieber zu vorsichtig als eine Ebene zu hoch."""
    if programmordner.name.lower() == ORDNER_PROGRAMM.lower():
        return programmordner.parent
    # Flaches Layout: die Startdatei liegt neben sortierer.py.
    # (Im .dev-Ordner liegt zwar auch Testlauf.bat - der Fall ist aber
    # schon oben abgefangen.)
    if _enthaelt_startdatei(programmordner):
        return programmordner
    if _enthaelt_startdatei(programmordner.parent):
        return programmordner.parent
    return programmordner


def programmordner_verstecken(programmordner, basis):
    """Setzt unter Windows das Attribut "versteckt" auf den Programmordner.
    Nur dann sinnvoll, wenn er wirklich ein Unterordner der Basis ist."""
    if not PROGRAMMORDNER_VERSTECKEN or programmordner == basis:
        return
    try:
        import ctypes
        VERSTECKT = 0x02
        pfad = str(programmordner)
        vorher = ctypes.windll.kernel32.GetFileAttributesW(pfad)
        # -1 bedeutet "Fehler"; sonst das Attribut ergaenzen, nicht ersetzen.
        if vorher != -1 and not (vorher & VERSTECKT):
            ctypes.windll.kernel32.SetFileAttributesW(pfad, vorher | VERSTECKT)
    except Exception:
        pass  # z. B. kein Windows - dann bleibt der Ordner eben sichtbar


def grundordner_anlegen(basis, testlauf):
    """Fehlende Grundordner anlegen. Jahres- und Monatsordner entstehen
    erst dann, wenn es dafuer wirklich Dateien gibt.
    Liefert True zurueck, wenn der Eingangsordner neu angelegt wurde -
    dann ist das hier der allererste Start."""
    erster_start = not (basis / ORDNER_EINGANG).exists()
    if testlauf:
        return erster_start
    ordner = [basis / ORDNER_EINGANG, basis / ORDNER_BILDER,
              basis / ORDNER_VIDEOS]
    ordner += [durchsehen(basis, name) for name in
               (ORDNER_OHNE_DATUM, ORDNER_GELOESCHT, ORDNER_DOPPELT,
                ORDNER_SONSTIGES)]
    for pfad in ordner:
        try:
            pfad.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    return erster_start


def leere_ordner_entfernen(eingang, testlauf, protokoll):
    """Leere Unterordner im Eingang loeschen. Der Eingang selbst bleibt."""
    if testlauf:
        return
    for wurzel, unterordner, dateien in os.walk(eingang, topdown=False):
        pfad = Path(wurzel)
        if pfad == eingang:
            continue
        try:
            if not any(pfad.iterdir()):
                pfad.rmdir()
        except Exception as fehler:
            protokoll.zeile("  Ordner nicht entfernbar: %s (%s)" % (pfad, fehler))


def kurz(pfad, basis):
    """Pfad moeglichst kurz, relativ zum Basisordner, darstellen."""
    try:
        return str(pfad.relative_to(basis))
    except Exception:
        return str(pfad)


def sortiere(basis, testlauf, protokoll, erster_start=False):
    eingang = basis / ORDNER_EINGANG
    zaehler = {
        "bild": 0, "video": 0, "ohne_datum": 0, "geloescht": 0,
        "doppelt": 0, "sonstiges": 0, "fehler": 0,
    }

    if not eingang.exists():
        sag('  Der Ordner "%s" fehlt noch.' % ORDNER_EINGANG)
        sag("  Legen Sie Ihre Fotos und Videos hinein und starten Sie erneut.")
        sag("")
        protokoll.zeile("Eingangsordner nicht vorhanden.")
        return zaehler

    dateien = dateien_einsammeln(eingang)
    gesamt = len(dateien)

    if gesamt == 0:
        if erster_start:
            # Allererster Start: die Ordner wurden gerade erst angelegt.
            sag("  Die Ordner wurden angelegt.")
            sag("")
            sag('  Legen Sie Ihre Fotos und Videos jetzt in den Ordner "%s"'
                % ORDNER_EINGANG)
            sag("  und starten Sie das Programm noch einmal.")
            protokoll.zeile("Erster Start: Ordner angelegt.")
        else:
            sag('  Im Ordner "%s" liegt nichts zum Sortieren.' % ORDNER_EINGANG)
            sag("  Es ist bereits alles einsortiert.")
            protokoll.zeile("Keine Dateien gefunden.")
        sag("")
        return zaehler

    sag("  %d Dateien gefunden" % gesamt)
    sag("")

    # Set aus (kleingeschriebener Name, Groesse) - erkennt Doppelte,
    # die im selben Lauf schon einmal vorgekommen sind.
    gesehen = set()
    letzte_laenge = 0

    for nummer, quelle in enumerate(dateien, start=1):
        try:
            if not quelle.is_file():
                continue

            try:
                groesse = quelle.stat().st_size
            except Exception:
                groesse = -1

            zielordner, kategorie = zielordner_bestimmen(quelle, basis, eingang)

            # Regel 2: Doppelte ueber Dateiname + Groesse erkennen
            schluessel = (quelle.name.lower(), groesse)
            ist_doppelt = False
            if groesse >= 0:
                if schluessel in gesehen:
                    ist_doppelt = True
                else:
                    vorhanden = zielordner / quelle.name
                    try:
                        if vorhanden.is_file() and vorhanden.stat().st_size == groesse:
                            ist_doppelt = True
                    except Exception:
                        pass

            if ist_doppelt:
                zielordner = durchsehen(basis, ORDNER_DOPPELT)
                kategorie = "doppelt"
            elif groesse >= 0:
                gesehen.add(schluessel)

            # Gleicher Name, aber andere Groesse -> _1, _2 ... anhaengen,
            # damit nichts ueberschrieben wird.
            zielpfad = freier_dateiname(zielordner, quelle.name)

            # Windows-Pfadlaengenlimit abfangen statt abstuerzen
            if len(str(zielpfad)) > MAX_PFADLAENGE:
                zaehler["fehler"] += 1
                protokoll.zeile(
                    "  FEHLER (Pfad zu lang, Datei bleibt liegen): %s" % quelle)
                continue

            anzeige = "  [ %d / %d ]  %s  ->  %s" % (
                nummer, gesamt, quelle.name, kurz(zielpfad.parent, basis))

            if not testlauf:
                zielordner.mkdir(parents=True, exist_ok=True)
                shutil.move(str(quelle), str(zielpfad))
            protokoll.zeile("  %s -> %s" % (quelle, zielpfad))

            zaehler[kategorie] = zaehler.get(kategorie, 0) + 1

            # Fortschritt in einer sich ueberschreibenden Zeile
            sag("\r" + anzeige.ljust(letzte_laenge), ende="")
            letzte_laenge = len(anzeige)

        except PermissionError:
            zaehler["fehler"] += 1
            protokoll.zeile(
                "  FEHLER (kein Zugriff oder Datei in Benutzung): %s" % quelle)
        except Exception as fehler:
            zaehler["fehler"] += 1
            protokoll.zeile("  FEHLER (%s): %s" % (fehler, quelle))

    # Fortschrittszeile abraeumen und eine Leerzeile setzen
    sag("\r" + " " * max(letzte_laenge, 1), ende="\r")
    sag("")
    leere_ordner_entfernen(eingang, testlauf, protokoll)
    return zaehler


def zusammenfassung_ausgeben(zaehler, protokoll, testlauf, basis):
    zeilen = [
        ("Bilder einsortiert:", zaehler["bild"]),
        ("Videos einsortiert:", zaehler["video"]),
        ("Ohne Datum:", zaehler["ohne_datum"]),
        ("Gelöschte Dateien:", zaehler["geloescht"]),
        ("Doppelte Dateien:", zaehler["doppelt"]),
        ("Sonstige Dateien:", zaehler["sonstiges"]),
    ]
    if zaehler["fehler"]:
        zeilen.append(("Nicht verarbeitet:", zaehler["fehler"]))

    if testlauf:
        sag("Testlauf beendet - es wurde nichts verschoben.")
    else:
        sag("Fertig!")
    sag("")
    protokoll.zeile("")
    for text, wert in zeilen:
        ausgabe = "  %s %s" % (text.ljust(22), str(wert).rjust(4))
        sag(ausgabe)
        protokoll.zeile(ausgabe)
    sag("")
    sag("  Ein Protokoll liegt in %s" % kurz(protokoll.pfad, basis))
    sag("")


def main():
    konsole_vorbereiten()
    testlauf = "--test" in [a.lower() for a in sys.argv[1:]]
    programmordner = Path(__file__).resolve().parent
    basis = basisordner_ermitteln(programmordner)
    protokoll = Protokoll(programmordner / LOG_DATEI, testlauf)

    try:
        sag("")
        if testlauf:
            sag("*** TESTLAUF - es wird NICHTS verschoben und nichts angelegt ***")
            sag("")
            sag("So wuerde sortiert werden:")
        else:
            sag("Erinnerungen werden sortiert...")
        sag("")

        if not PILLOW_DA:
            sag("  Hinweis: Pillow ist nicht installiert. Fotos werden ohne")
            sag('  Aufnahmedatum in "%s" abgelegt.'
                % (ORDNER_SAMMEL + os.sep + ORDNER_OHNE_DATUM))
            sag("")
            protokoll.zeile("Hinweis: Pillow fehlt, kein EXIF-Datum lesbar.")

        erster_start = grundordner_anlegen(basis, testlauf)
        if not testlauf:
            programmordner_verstecken(programmordner, basis)
        zaehler = sortiere(basis, testlauf, protokoll, erster_start)
        # Beim allerersten Start gab es noch nichts zu sortieren -
        # dann waere eine Zusammenfassung aus lauter Nullen nur verwirrend.
        if not (erster_start and sum(zaehler.values()) == 0):
            zusammenfassung_ausgeben(zaehler, protokoll, testlauf, basis)
    finally:
        protokoll.schliessen()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            konsole_vorbereiten()
        except Exception:
            pass
        sag("")
        sag("Es ist ein unerwarteter Fehler aufgetreten.")
        sag("Es wurde nichts geloescht - Ihre Dateien sind unveraendert.")
        sag("")
        try:
            ordner = Path(__file__).resolve().parent
            with open(ordner / LOG_DATEI, "a", encoding="utf-8") as f:
                f.write("\nABBRUCH %s\n"
                        % datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
                f.write(traceback.format_exc())
            sag("  Einzelheiten stehen in %s" % LOG_DATEI)
            sag("")
        except Exception:
            pass
    # Fenster nach dem Doppelklick offen halten - auch im Fehlerfall.
    try:
        input("Zum Schliessen Enter druecken.")
    except Exception:
        pass
