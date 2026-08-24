#!/usr/bin/env python3
"""
Galerie bauen.

    python3 tools/build-gallery.py

Ablauf:
  1. Liest die Originale aus  originals/  (nicht im Git-Repo!)
  2. Erzeugt fehlende Ableitungen:
        images/gallery/thumb/<stamm>.webp   800 px
        images/gallery/large/<stamm>.webp  1800 px
     Dabei wird die Ausrichtung nach EXIF korrigiert und saemtliche
     Metadaten (Kamera, Zeit, evtl. GPS) aus den veroeffentlichten
     Fassungen entfernt.
  3. Liest Aufnahmedatum und Kameradaten aus dem EXIF des Originals und
     traegt sie in photos.json ein — es werden nur LEERE Felder gefuellt,
     eigene Eintraege bleiben immer erhalten.
  4. Schreibt die Bildliste in _src/gallery.html zwischen die GALLERY-Marker.
     Danach  python3 tools/build-pages.py  laufen lassen.
  5. Listet auf, wo noch Angaben fehlen.

Neues Bild aufnehmen:
    cp meinbild.jpg originals/
    python3 tools/build-gallery.py
    python3 tools/tag-photos.py      # Datum, Ort, Tags, Beschreibung ergaenzen
    python3 tools/build-gallery.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from fractions import Fraction

try:
    from PIL import Image, ImageOps, ExifTags
except ImportError:
    sys.exit("Pillow fehlt.  Installieren mit:  pip install Pillow")

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC    = os.path.join(ROOT, "originals")
OUT    = os.path.join(ROOT, "images", "gallery")
PAGE   = os.path.join(ROOT, "_src", "gallery.html")
DATA   = os.path.join(ROOT, "photos.json")
IGNORE = os.path.join(ROOT, ".gitignore")

EXT    = (".webp", ".jpg", ".jpeg", ".png", ".tif", ".tiff")
SIZES  = (("thumb", 800, 76), ("large", 1800, 82))
START  = "<!-- GALLERY:START -->"
END    = "<!-- GALLERY:END -->"

# Felder, die der Benutzer pflegt (nie automatisch ueberschrieben)
PFLICHT = ("datum", "ort", "kamera")     # 'de'/'en' sind bewusst NICHT dabei
AUSGEBLENDET = "_ausgeblendet"           # Unterordner fuer aussortierte Bilder


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;").replace('"', "&quot;"))


def stamm(name):
    return os.path.splitext(name)[0]


def einstellungen(ex):
    """Aufnahmedaten als eine Zeile:  ƒ/5,6 · 1/400 · 194 mm · ISO 200

    Schreibweise wie im Info-Feld gaengiger Foto-Programme: Blende mit dem
    ƒ-Zeichen, Belichtungszeit ohne Einheit. Die Zeile wird nicht uebersetzt —
    sie besteht nur aus Zahlen und Einheiten. Fehlt ein Wert, faellt er weg;
    ohne EXIF bleibt die Zeile leer und die Lightbox zeigt nur die Kamera.
    """
    teile = []
    blende = (ex.get("blende") or "").strip()
    if blende:
        teile.append("ƒ/" + blende.replace("f/", "").replace(".", ","))
    zeit = (ex.get("belichtung") or "").strip()
    if zeit:
        teile.append(zeit[:-2] if zeit.endswith(" s") else zeit)
    weite = (ex.get("brennweite") or "").strip()
    if weite:
        teile.append(weite.replace(".", ","))
    iso = (ex.get("iso") or "").strip()
    if iso:
        teile.append("ISO " + iso)
    return " · ".join(teile)


def beschriftung(p, tags_def, sprache):
    """Alt-Text und Bildunterschrift.

    Steht eine eigene Beschreibung im Feld 'de' bzw. 'en', gilt die. Sonst
    entsteht der Text aus Tags, Ort und Datum — ein Bild ohne Beschreibung
    bleibt damit trotzdem fuer Screenreader nutzbar.
    """
    eigen = (p.get(sprache) or "").strip()
    if eigen:
        return eigen
    teile = []
    labels = [tags_def.get(t, {}).get(sprache, t) for t in p.get("tags", [])]
    if labels:
        teile.append(", ".join(labels))
    if p.get("ort"):
        teile.append(p["ort"])
    if p.get("datum"):
        j, m, t = p["datum"].split("-")
        teile.append(f"{t}.{m}.{j}")
    if not teile:
        teile.append(stamm(p["datei"]))
    return " · ".join(teile)


# ---------------------------------------------------------------- Schutz ----

def originale_schuetzen():
    """Verhindert, dass die 20-MB-Dateien versehentlich im Repo landen."""
    regel = False
    if os.path.exists(IGNORE):
        with open(IGNORE, encoding="utf-8") as fh:
            regel = any(z.strip().rstrip("/") == "originals"
                        for z in fh if not z.lstrip().startswith("#"))
    if not regel:
        sys.exit("ABBRUCH: 'originals/' fehlt in .gitignore.\n"
                 "         Sonst landen die Originale im Repo. Zeile ergaenzen:\n"
                 "             echo 'originals/' >> .gitignore")
    try:
        getrackt = subprocess.run(["git", "ls-files", "originals/"], cwd=ROOT,
                                  capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return                                   # kein Git verfuegbar -> egal
    if getrackt:
        sys.exit("ABBRUCH: diese Originale sind bereits von Git erfasst:\n  "
                 + "\n  ".join(getrackt.splitlines()[:10])
                 + "\n\nEntfernen mit:  git rm --cached -r originals/")


# ----------------------------------------------------------------- EXIF -----

def exif_lesen(pfad):
    """Liest die Aufnahmedaten aus der Datei. Fehlende Werte kommen als '' zurueck.

    Das Ergebnis landet unveraendert im Block 'exif' eines Bildes und wird bei
    jedem Lauf neu geschrieben — es ist die Wahrheit der Datei. Was auf der Seite
    erscheint, steht daneben in 'datum' und 'kamera' und bleibt unangetastet.
    """
    leer = {"datum": "", "kamera": "", "objektiv": "", "brennweite": "",
            "blende": "", "belichtung": "", "iso": ""}
    try:
        roh = Image.open(pfad).getexif()
        if not roh:
            return leer
        d = {ExifTags.TAGS.get(k, k): v for k, v in roh.items()}
        d.update({ExifTags.TAGS.get(k, k): v for k, v in roh.get_ifd(0x8769).items()})
    except Exception:
        return leer

    datum = ""
    for feld in ("DateTimeOriginal", "DateTime"):
        if d.get(feld):
            try:
                datum = datetime.strptime(str(d[feld])[:10], "%Y:%m:%d").strftime("%Y-%m-%d")
                break
            except ValueError:
                pass

    # "Canon" + "Canon EOS 2000D" -> "Canon EOS 2000D"
    marke  = str(d.get("Make", "") or "").strip()
    modell = str(d.get("Model", "") or "").strip()
    if modell and marke and not modell.lower().startswith(marke.lower()):
        kamera = f"{marke} {modell}"
    else:
        kamera = modell or marke

    def zahl(v):
        try:
            return float(Fraction(v)) if not isinstance(v, float) else v
        except Exception:
            return None

    brennweite = zahl(d.get("FocalLength"))
    blende     = zahl(d.get("FNumber"))
    zeit       = zahl(d.get("ExposureTime"))
    iso        = d.get("ISOSpeedRatings") or d.get("PhotographicSensitivity") or ""

    if zeit is None:
        belichtung = ""
    elif zeit >= 1:
        belichtung = f"{zeit:g} s"
    else:
        belichtung = f"1/{round(1/zeit)} s"

    return {
        "datum":      datum,
        "kamera":     kamera,
        "objektiv":   str(d.get("LensModel", "") or "").strip(),
        "brennweite": f"{brennweite:g} mm" if brennweite else "",
        "blende":     f"f/{blende:g}"      if blende else "",
        "belichtung": belichtung,
        "iso":        str(iso) if iso else "",
    }


# ----------------------------------------------------------- Ableitungen ----

def ableitungen_bauen(dateien):
    gebaut = 0
    for sub, _, _ in SIZES:
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for name in dateien:
        quelle = os.path.join(SRC, name)
        fehlend = [(sub, b, q) for sub, b, q in SIZES
                   if not (os.path.exists(os.path.join(OUT, sub, stamm(name) + ".webp"))
                           and os.path.getmtime(os.path.join(OUT, sub, stamm(name) + ".webp"))
                               >= os.path.getmtime(quelle))]
        if not fehlend:
            continue
        with Image.open(quelle) as roh:
            # Ausrichtung nach EXIF drehen, danach RGB -> verwirft alle Metadaten
            basis = ImageOps.exif_transpose(roh).convert("RGB")
            for sub, breite, q in fehlend:
                im = basis.copy()
                im.thumbnail((breite, breite), Image.LANCZOS)
                im.save(os.path.join(OUT, sub, stamm(name) + ".webp"),
                        "WEBP", quality=q, method=6)
                gebaut += 1
    return gebaut


# ------------------------------------------------------------------ Main ----

def main():
    originale_schuetzen()

    if not os.path.isdir(SRC):
        sys.exit(f"Ordner fehlt: {SRC}\nDort die Originalbilder ablegen.")
    dateien = sorted(f for f in os.listdir(SRC)
                     if f.lower().endswith(EXT) and not f.startswith(".")
                     and os.path.isfile(os.path.join(SRC, f)))
    if not dateien:
        sys.exit(f"Keine Bilder in {SRC}")

    with open(DATA, encoding="utf-8") as fh:
        daten = json.load(fh)
    tags_def = daten.get("tags", {})
    photos   = daten.get("photos", [])

    print(f"Ableitungen erzeugt: {ableitungen_bauen(dateien)}")

    # Zuordnung ueber den Dateistamm: foo.webp -> foo.png behaelt seine Daten
    nach_stamm = {stamm(p["datei"]): p for p in photos}
    neu = []
    for name in dateien:
        eintrag = nach_stamm.get(stamm(name))
        if eintrag is None:
            eintrag = {"datei": name, "datum": "", "ort": "", "tags": [],
                       "kamera": "", "de": "", "en": "", "exif": {}}
            photos.append(eintrag)
            nach_stamm[stamm(name)] = eintrag
            neu.append(name)
        elif eintrag["datei"] != name:
            print(f"  Datei ersetzt: {eintrag['datei']}  ->  {name}  (Angaben bleiben)")
            eintrag["datei"] = name

        # Altbestand: frueher lag die Kamera im exif-Block und war dort
        # ueberschreibbar. Einmalig nach oben ziehen, damit eine eigene
        # Korrektur nicht vom naechsten Lauf ueberbuegelt wird.
        if "kamera" not in eintrag and eintrag.get("exif", {}).get("kamera"):
            eintrag["kamera"] = eintrag["exif"]["kamera"]

        # 'exif' spiegelt immer die Datei — daher komplett neu schreiben.
        ex = exif_lesen(os.path.join(SRC, name))
        eintrag["exif"] = ex

        # Anzeigefelder nur befuellen, solange sie leer sind
        for feld in ("datum", "kamera"):
            if ex.get(feld) and not eintrag.get(feld):
                eintrag[feld] = ex[feld]
        eintrag.setdefault("kamera", "")
        eintrag.setdefault("de", "")     # optional; leer -> Tags als Rueckfall
        eintrag.setdefault("en", "")

    verwaist = [p for p in photos if stamm(p["datei"]) not in {stamm(d) for d in dateien}]
    if verwaist:
        print("\nWARNUNG — Eintraege ohne Bilddatei, werden entfernt:")
        for p in verwaist:
            print("   ", p["datei"])
        photos = [p for p in photos if p not in verwaist]

    unbekannt = sorted({t for p in photos for t in p.get("tags", [])} - set(tags_def))
    if unbekannt:
        print("\nWARNUNG — Tags ohne Uebersetzung (in photos.json unter 'tags' ergaenzen):")
        for t in unbekannt:
            print("   ", t)

    photos.sort(key=lambda p: (p.get("datum") or "0000-00-00"), reverse=True)
    daten["photos"] = photos

    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, DATA)

    if neu:
        print(f"\nNeu aufgenommen: {len(neu)}")
        for x in neu:
            print("   ", x)

    # ------------------------------------------------------------- Markup ---
    zeilen = []
    for p in photos:
        bild  = stamm(p["datei"]) + ".webp"
        thumb = f"images/gallery/thumb/{bild}"
        tpfad = os.path.join(ROOT, thumb)
        w, h  = Image.open(tpfad).size if os.path.exists(tpfad) else (800, 533)

        datum = p.get("datum", "")
        ort   = p.get("ort", "")
        tags  = p.get("tags", [])
        ex    = p.get("exif", {})
        kamera = p.get("kamera", "")
        de = beschriftung(p, tags_def, "de")
        en = beschriftung(p, tags_def, "en")

        if datum:
            j, m, t = datum.split("-")
            zeit_html = f'<time datetime="{datum}" class="shot-date">{t}.{m}.{j}</time>'
        else:
            zeit_html = ('<span class="shot-date shot-date-none">'
                         '<span class="lang-de" lang="de">ohne Datum</span>'
                         '<span class="lang-en" lang="en">no date</span></span>')

        ort_html = f'<span class="shot-place">{esc(ort)}</span>' if ort else ""

        chips = "".join(
            f'<span class="shot-tag">'
            f'<span class="lang-de" lang="de">{esc(tags_def.get(t, {}).get("de", t))}</span>'
            f'<span class="lang-en" lang="en">{esc(tags_def.get(t, {}).get("en", t))}</span>'
            f'</span>'
            for t in tags
        )
        if kamera:
            chips += f'<span class="shot-cam">{esc(kamera)}</span>'

        aufnahme = einstellungen(ex)

        such = " ".join([de, en, ort, " ".join(tags),
                         " ".join(tags_def.get(t, {}).get("de", "") for t in tags),
                         " ".join(tags_def.get(t, {}).get("en", "") for t in tags),
                         kamera, ex.get("objektiv", ""), aufnahme, datum]).lower()

        zeilen.append(
f'''        <li class="shot-item" data-date="{esc(datum)}" data-year="{esc(datum[:4])}"
            data-place="{esc(ort)}" data-tags="{esc(' '.join(tags))}" data-search="{esc(such)}">
          <button type="button" class="shot" data-large="images/gallery/large/{bild}"
                  data-cam="{esc(kamera)}" data-exif="{esc(aufnahme)}"
                  data-alt-de="{esc(de)}" data-alt-en="{esc(en)}">
            <img src="{thumb}" width="{w}" height="{h}" loading="lazy" decoding="async"
                 alt="{esc(de)}" data-alt-de="{esc(de)}" data-alt-en="{esc(en)}">
          </button>
          <div class="shot-meta">
            {zeit_html}{ort_html}
          </div>
          <div class="shot-tags">{chips}</div>
        </li>''')

    markup = START + "\n" + "\n".join(zeilen) + "\n        " + END

    with open(PAGE, encoding="utf-8") as fh:
        seite = fh.read()
    if START not in seite or END not in seite:
        sys.exit(f"Marker {START} / {END} fehlen in gallery.html")
    seite = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: markup,
                   seite, flags=re.S)

    z = [0]
    def entlazy(m):
        z[0] += 1
        return "" if z[0] <= 3 else m.group(0)
    seite = re.sub(r' loading="lazy" decoding="async"', entlazy, seite)

    tmp = PAGE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(seite)
    os.replace(tmp, PAGE)
    print(f"\ngallery.html aktualisiert — {len(photos)} Bilder")
    versteckt = os.path.join(SRC, AUSGEBLENDET)
    if os.path.isdir(versteckt):
        n = len([f for f in os.listdir(versteckt) if f.lower().endswith(EXT)])
        if n:
            print(f"({n} Bild(er) in originals/{AUSGEBLENDET}/ — nicht auf der Seite. "
                  f"Zum Zurueckholen einfach eine Ebene hoch verschieben.)")

    # -------------------------------------------------------- offene Punkte -
    offen = []
    for p in photos:
        fehlt = [f for f in PFLICHT if not p.get(f)]
        if not p.get("tags"):
            fehlt.append("tags")
        if not p.get("kamera"):
            fehlt.append("kamera")
        if fehlt:
            offen.append((p["datei"], fehlt))
    if offen:
        print(f"\nNoch zu ergaenzen ({len(offen)} Bilder) — am schnellsten mit:")
        print("    python3 tools/tag-photos.py\n")
        for datei, fehlt in offen:
            print(f"    {datei:38} {', '.join(fehlt)}")
    else:
        print("\nAlle Bilder vollstaendig beschrieben.")


if __name__ == "__main__":
    main()
