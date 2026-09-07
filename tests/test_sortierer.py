# -*- coding: utf-8 -*-
"""Tests für den Sortierer.

Aufruf aus dem Projektordner:

    py -m unittest discover -s tests -v

Die Tests legen sich ihre Testdaten selbst in einem temporären Ordner an
und fassen nichts außerhalb davon an.
"""
import importlib.util
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
SORTIERER = PROJEKT / ".dev" / "sortierer.py"

try:
    from PIL import Image
    PILLOW_DA = True
except ImportError:
    PILLOW_DA = False


def modul_laden():
    """sortierer.py als Modul laden, ohne main() auszuführen."""
    spec = importlib.util.spec_from_file_location("sortierer", SORTIERER)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


s = modul_laden()

MP4_EPOCHE = datetime(1904, 1, 1, tzinfo=timezone.utc)


def jpeg(pfad, aufnahme=None, farbe=(10, 20, 30), groesse=(64, 48)):
    """Legt ein JPEG an, wahlweise mit EXIF-Aufnahmedatum."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    bild = Image.new("RGB", groesse, farbe)
    if aufnahme:
        exif = Image.Exif()
        exif[0x8769] = {36867: aufnahme}   # DateTimeOriginal
        bild.save(pfad, "JPEG", exif=exif)
    else:
        bild.save(pfad, "JPEG")


def mp4(pfad, wann_utc, version=0):
    """Baut ein minimales MP4 mit gültigem mvhd-Atom."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    sek = 0 if wann_utc is None else int((wann_utc - MP4_EPOCHE).total_seconds())
    if version == 1:
        koerper = b"\x01\x00\x00\x00" + struct.pack(">Q", sek) * 2
        koerper += struct.pack(">I", 1000) + struct.pack(">Q", 5000)
    else:
        koerper = b"\x00\x00\x00\x00" + struct.pack(">I", sek) * 2
        koerper += struct.pack(">I", 1000) + struct.pack(">I", 5000)
    koerper += b"\x00" * 80
    mvhd = struct.pack(">I", len(koerper) + 8) + b"mvhd" + koerper
    frei = struct.pack(">I", 16) + b"free" + b"\x00" * 8
    moov = struct.pack(">I", len(frei) + len(mvhd) + 8) + b"moov" + frei + mvhd
    ftyp = struct.pack(">I", 20) + b"ftyp" + b"isom\x00\x00\x02\x00isom"
    pfad.write_bytes(ftyp + moov)


class DatumAusDateiname(unittest.TestCase):
    """Nur Dezimalzahlen zählen - Hex-Prüfsummen werden ausgelassen."""

    def test_erkannte_namen(self):
        faelle = [
            ("IMG-20140703.jpg", "2014-07-03"),
            ("IMG_20180405_123456.jpg", "2018-04-05"),
            ("PXL_20220101_101112345.jpg", "2022-01-01"),
            ("VID-20190712-WA0001.mp4", "2019-07-12"),
            ("Screenshot_2021-05-03.png", "2021-05-03"),
            ("WhatsApp Image 2019-07-12 at 20.11.jpeg", "2019-07-12"),
            ("DSC20140703.JPG", "2014-07-03"),
            ("IMG20140703.jpg", "2014-07-03"),
            ("20140703.jpg", "2014-07-03"),
            ("20140703120000.mp4", "2014-07-03"),
            ("Urlaub 2019-07-12 Strand.jpg", "2019-07-12"),
        ]
        for name, erwartet in faelle:
            with self.subTest(name=name):
                datum = s.datum_aus_dateiname(name)
                self.assertIsNotNone(datum, "kein Datum gefunden")
                self.assertEqual(datum.strftime("%Y-%m-%d"), erwartet)

    def test_abgelehnte_namen(self):
        faelle = [
            "c20140703ab.jpg",        # Datum steckt in einer Hex-Prüfsumme
            "5f3a2b1c9d0e.jpg",
            "a3f5b20140703c.png",
            "deadbeef20140703.jpg",
            "IMG_1234.jpg",
            "urlaub.jpg",
            "IMG_18000101.jpg",       # vor JAHR_MINIMUM
            "IMG_20991231.jpg",       # in der Zukunft
            "IMG_20143299.jpg",       # 32. Monat gibt es nicht
            "rechnung_12345678.pdf",  # kein Jahr 19xx/20xx
            "1404345600.jpg",         # Unix-Zeitstempel, falsche Länge
            "DSC_0001.jpg",
        ]
        for name in faelle:
            with self.subTest(name=name):
                self.assertIsNone(s.datum_aus_dateiname(name))


class Papierkorberkennung(unittest.TestCase):

    def test_merkmale(self):
        eingang = Path("C:/X/Unsortierte Dateien")
        erkannt = [".trashed-1-a.jpg", "Trash/a.jpg", "tief/Recently Deleted/a.jpg",
                   "Zuletzt gelöscht/a.jpg", "urlaub/a.deleted.jpg",
                   ".pending-7-b.jpg", "tief/$RECYCLE.BIN/c.jpg"]
        for teil in erkannt:
            with self.subTest(teil=teil):
                self.assertTrue(s.ist_geloescht(eingang / teil, eingang))
        self.assertFalse(s.ist_geloescht(eingang / "normal/a.jpg", eingang))


class Basisordnererkennung(unittest.TestCase):
    """Das Skript darf niemals eine Ebene zu hoch sortieren."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_layouts(self):
        # a) flaches Layout: Startdatei liegt neben sortierer.py
        a = self.tmp / "A"
        a.mkdir()
        (a / "beliebiger name.bat").touch()
        self.assertEqual(s.basisordner_ermitteln(a), a)

        # b) irgendwo ohne Marker -> nicht nach oben ausbrechen
        b = self.tmp / "B" / "irgendwo"
        b.mkdir(parents=True)
        self.assertEqual(s.basisordner_ermitteln(b), b)

        # c) im Programmordner -> eine Ebene höher
        c = self.tmp / "C" / s.ORDNER_PROGRAMM
        c.mkdir(parents=True)
        self.assertEqual(s.basisordner_ermitteln(c), c.parent)


@unittest.skipUnless(PILLOW_DA, "Pillow wird für diesen Test gebraucht")
class Sortierlauf(unittest.TestCase):
    """Führt das Programm als eigenen Prozess aus, wie beim Doppelklick."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(PROJEKT / ".dev", self.tmp / ".dev")
        self.eingang = self.tmp / s.ORDNER_EINGANG
        self.eingang.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sortieren(self, *zusatz):
        ergebnis = subprocess.run(
            [sys.executable, str(Path(".dev") / "sortierer.py"), *zusatz],
            cwd=self.tmp, input="\n", capture_output=True,
            text=True, encoding="utf-8")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout)
        return ergebnis.stdout

    def dateien(self):
        return sorted(p.relative_to(self.tmp).as_posix()
                      for p in self.tmp.rglob("*")
                      if p.is_file() and ".dev" not in p.parts)

    def test_einsortieren_nach_datum(self):
        jpeg(self.eingang / "foto.jpg", "2019:03:04 12:30:00")
        mp4(self.eingang / "video.mp4", datetime(2019, 7, 12, 10, tzinfo=timezone.utc))
        jpeg(self.eingang / "IMG-20140703.jpg")          # Datum nur im Namen
        jpeg(self.eingang / "c20140703ab.jpg")           # Hex -> ohne Datum
        (self.eingang / "brief.pdf").write_bytes(b"%PDF")
        jpeg(self.eingang / ".trashed-9-weg.jpg")

        self.sortieren()
        vorhanden = self.dateien()

        self.assertIn("Bilder/2019/03-März/foto.jpg", vorhanden)
        self.assertIn("Videos/2019/07-Juli/video.mp4", vorhanden)
        self.assertIn("Bilder/2014/07-Juli/IMG-20140703.jpg", vorhanden)
        self.assertIn("Zum Durchsehen/Ohne Datum/c20140703ab.jpg", vorhanden)
        self.assertIn("Zum Durchsehen/Sonstige Dateien/brief.pdf", vorhanden)
        self.assertIn("Zum Durchsehen/Gelöschte Dateien/.trashed-9-weg.jpg", vorhanden)
        self.assertEqual(list(self.eingang.iterdir()), [], "Eingang muss leer sein")

    def test_exif_schlaegt_dateinamen(self):
        jpeg(self.eingang / "IMG-20140703.jpg", "2019:03:04 12:30:00")
        self.sortieren()
        self.assertIn("Bilder/2019/03-März/IMG-20140703.jpg", self.dateien())

    def test_nichts_wird_ueberschrieben(self):
        ziel = self.tmp / "Bilder" / "2019" / "03-März"
        jpeg(ziel / "foto.jpg", "2019:03:04 12:30:00")
        # gleicher Name, andere Größe -> darf das Original nicht ersetzen
        jpeg(self.eingang / "foto.jpg", "2019:03:04 12:30:00",
             farbe=(200, 5, 5), groesse=(128, 96))
        self.sortieren()
        vorhanden = self.dateien()
        self.assertIn("Bilder/2019/03-März/foto.jpg", vorhanden)
        self.assertIn("Bilder/2019/03-März/foto_1.jpg", vorhanden)

    def test_doppelte_werden_erkannt(self):
        jpeg(self.eingang / "a" / "foto.jpg", "2019:03:04 12:30:00")
        jpeg(self.eingang / "b" / "foto.jpg", "2019:03:04 12:30:00")
        self.sortieren()
        vorhanden = self.dateien()
        self.assertIn("Bilder/2019/03-März/foto.jpg", vorhanden)
        self.assertIn("Zum Durchsehen/Doppelte Dateien/foto.jpg", vorhanden)

    def test_bestehende_ordner_werden_benutzt(self):
        for name in ("Bilder/2019/03-März", "Zum Durchsehen/Ohne Datum"):
            (self.tmp / name).mkdir(parents=True)
        jpeg(self.tmp / "Bilder/2019/03-März/alt.jpg", "2019:03:04 12:30:00")
        jpeg(self.eingang / "neu.jpg", "2019:03:04 12:30:00")

        self.sortieren()
        vorhanden = self.dateien()
        self.assertIn("Bilder/2019/03-März/alt.jpg", vorhanden)
        self.assertIn("Bilder/2019/03-März/neu.jpg", vorhanden)

    def test_testlauf_verschiebt_nichts(self):
        jpeg(self.eingang / "foto.jpg", "2019:03:04 12:30:00")
        vorher = self.dateien()
        ausgabe = self.sortieren("--test")
        self.assertIn("TESTLAUF", ausgabe)
        self.assertEqual(vorher, self.dateien())

    def test_leerer_eingang_ist_kein_fehler(self):
        self.sortieren()
        self.sortieren()   # zweiter Lauf muss ebenfalls sauber durchgehen


if __name__ == "__main__":
    unittest.main(verbosity=2)
