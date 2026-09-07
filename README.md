# file-sorting-command

Sorts photos and videos into folders by the date they were **actually taken** —
read from EXIF and MP4 metadata, not from the file system timestamp.

Built for someone who does not use a terminal. She drops her files into one
folder, double-clicks one file, and that is the whole interaction.

> 🇩🇪 Die Oberfläche ist auf Deutsch. Ausführliche Anleitung:
> **[.dev/README.md](.dev/README.md)**

---

## What it does

```
Erinnerungen\
├── sortieren.bat            <- the only thing that gets clicked
├── Unsortierte Dateien\     <- drop everything in here
├── Bilder\
│   └── 2019\03-März\
├── Videos\
│   └── 2019\07-Juli\
├── Zum Durchsehen\          <- anything without a capture date
│   ├── Ohne Datum\
│   ├── Gelöschte Dateien\
│   ├── Doppelte Dateien\
│   └── Sonstige Dateien\
└── .dev\                    <- hidden; the program lives here
```

The person using it sees **four folders and one file.** Everything technical is
in `.dev`, which sets itself hidden on the first run.

**Files are only ever moved — never deleted, never overwritten.** That is the
one rule the whole program is built around.

## Where the date comes from

| Type | Source |
|---|---|
| Photos | EXIF `DateTimeOriginal`, falling back to `DateTimeDigitized` |
| MP4 / MOV / M4V / 3GP | the `mvhd` atom, parsed by hand — no extra library needed |
| AVI / WMV / MKV | usually carry nothing readable → `Ohne Datum` |
| Fallback | the filename, if it holds a plain decimal date |

Metadata always wins. The filename is only consulted when the metadata is
silent — which is the normal case for screenshots and WhatsApp images.

### Filename dates

`IMG-20140703.jpg` → 3 July 2014. Also handled: `IMG_20180405_123456`,
`PXL_20220101_...`, `VID-20190712-WA0001`, `Screenshot_2021-05-03`,
`WhatsApp Image 2019-07-12`, and 14-digit stamps like `20140703120000`.

Names that look like a **hexadecimal checksum are deliberately skipped** — any
number found inside one is a coincidence, not a date. A word is treated as hex
when it is at least eight characters long and *every* letter in it is `a`–`f`:
`c20140703ab.jpg` and `deadbeef20140703.jpg` are ignored. Ordinary camera
prefixes survive this test on their own, because `IMG`, `DSC`, `PXL` and `VID`
all contain letters that do not exist in hexadecimal.

## Sorting rules, in order

1. **Trash markers** (`.trashed-`, `.pending-`, `.deleted`, or sitting in
   `.trash` / `Papierkorb` / `$RECYCLE.BIN` / `Recently Deleted`)
   → `Zum Durchsehen\Gelöschte Dateien`
2. **Duplicate** — same filename *and* same byte size already at the target
   → `Zum Durchsehen\Doppelte Dateien`.
   Same name but a *different* size is not a duplicate: it gets `_1`, `_2` …
   appended so nothing is overwritten.
3. **Image or video** → `Bilder\<year>\<MM-Month>\` or `Videos\<year>\<MM-Month>\`,
   or `Zum Durchsehen\Ohne Datum` when no date could be read.
4. **Everything else** → `Zum Durchsehen\Sonstige Dateien`

Empty subfolders in the input folder are removed afterwards. The input folder
itself stays.

## Requirements

- Windows 10 or 11, running natively (not WSL)
- Python 3.8 or newer — [python.org](https://www.python.org/downloads/),
  with *"Add python.exe to PATH"* ticked during setup
- [Pillow](https://pypi.org/project/Pillow/) for reading EXIF:
  `py -m pip install -r .dev/requirements.txt`

Without Pillow the program still runs, but every photo lands in
`Zum Durchsehen\Ohne Datum`. Optionally, `pillow-heif` adds HEIC support; it is
picked up automatically when installed.

## Install

Copy **`sortieren.bat`** and the folder **`.dev`** into an empty folder, then
double-click `sortieren.bat`. It creates the rest and tells you what to do next.

`.dev` is hidden, so when copying to another machine, copy the *containing
folder* rather than its contents — otherwise `.dev` is left behind. The batch
file detects that case and says so instead of failing silently.

## Robustness

Every file is handled inside its own `try`/`except`: a locked, broken or
over-long path is logged and skipped, and the run continues. The console output
is plain German with no tracebacks, and the window stays open at the end — also
on failure. Runs are repeatable; a second run on an empty input folder just
says so.

A log is appended to `.dev/sortier-log.txt` on every run: one line per file,
plus a summary.

## Configuration

Everything adjustable sits in the `EINSTELLUNGEN` block at the top of
[.dev/sortierer.py](.dev/sortierer.py) — folder names, month names, file
extension lists, trash markers, and whether filename dates are used at all.

## Tests

```bash
py -m unittest discover -s tests -v
```

11 tests covering filename parsing, trash detection, base-folder resolution,
and full sorting runs in a temporary folder.

## License

[MIT](LICENSE)
