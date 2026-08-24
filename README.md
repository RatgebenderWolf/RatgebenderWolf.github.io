# RatgebenderWolf.github.io

Portfolio-Website von Ralf Hörhager — <https://ratgebenderwolf.github.io/>

Statisches HTML/CSS/JS ohne Build-Schritt. Wird von GitHub Pages direkt aus `main` ausgeliefert.

## Struktur

```
index.html          Startseite: Hero, Lebenslauf, Projekt-Previews, Kontakt
projekte.md         Quelle aller Projektinhalte — siehe unten
projects.html       Zeitleiste aller Projekte
projects/           Detailseite je Projekt
gallery.html        Fotogalerie — wird aus photos.json gebaut, nicht von Hand
photos.json         Bilddaten: Datum, Ort, Tags, Beschreibungen
tools/build-gallery.py  Galerie bauen (Vorschaubilder + Bildliste)
impressum.html      Offenlegung nach § 25 Mediengesetz
datenschutz.html    Datenschutzerklärung (DSGVO)
404.html            Fehlerseite (GitHub Pages nutzt sie automatisch)
styles.css          gesamtes Layout
fonts.css           @font-face-Definitionen für die selbst gehosteten Schriften
fonts/              Archivo, Inter, IBM Plex Mono als woff2 (kein Google-CDN)
script.js           Sprachumschaltung DE/EN
gallery.js          Filter, Suche und Lightbox (nur auf gallery.html)
images/             profile.jpg
images/gallery/thumb/   800 px, für das Raster        (im Repo)
images/gallery/large/   1800 px, für die Lightbox     (im Repo)
originals/          Bild-Originale — NICHT im Repo, siehe .gitignore
tools/tag-photos.py Oberfläche zum Verschlagworten
cv-*.pdf            Lebenslauf — NICHT im Repo (enthält private Daten)
```

## Neue Fotos in die Galerie

```bash
cp ~/fotos/*.jpg originals/       # 1. Originale ablegen
python3 tools/build-gallery.py    # 2. Ableitungen + EXIF
python3 tools/tag-photos.py       # 3. Ort, Tags, Beschreibung ergänzen
python3 tools/build-gallery.py    # 4. Seite neu schreiben
```

### `originals/` liegt bewusst außerhalb von Git

Dort gehören die vollen Auflösungen hin (6000x4000, ~20 MB). `.gitignore`
schließt den Ordner aus, ins Repo kommen nur die Ableitungen unter
`images/gallery/thumb/` und `.../large/`. `build-gallery.py` bricht ab, falls
die Regel fehlt oder doch eine Originaldatei von Git erfasst wurde.

> **Backup nicht vergessen.** Bis jetzt war das Repo die zweite Kopie deiner
> Bilder. Das ist es nicht mehr — `originals/` existiert nur auf diesem Rechner
> und braucht eine eigene Sicherung (externe Platte oder Cloud).

### Welches Format für die Originale?

**Am besten die Kamera-JPEG oder ein TIFF, nicht PNG.** PNG transportiert die
EXIF-Daten unzuverlässig: ein Bild mit 9 EXIF-Feldern behält nach dem PNG-Export
oft **null** davon — damit fällt die automatische Übernahme von Aufnahmedatum
und Kameramodell aus. TIFF ist bei 6000x4000 nicht größer und behält alles.

Verarbeitet werden `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.png` und `.webp`. Fehlt
EXIF, bleiben die Felder leer und lassen sich in `tag-photos.py` eintragen.

### Was `build-gallery.py` erledigt

- erzeugt fehlende Vorschaubilder; vorhandene und aktuelle werden übersprungen
- korrigiert die Ausrichtung nach EXIF (Hochformat wird richtig gedreht)
- entfernt alle Metadaten aus den veröffentlichten Fassungen — Kameramodell,
  Aufnahmezeit und potenziell GPS bleiben in den Originalen und gehen nicht online
- liest Datum, Kamera, Objektiv, Brennweite, Blende, Belichtungszeit und ISO aus
  und trägt sie ein — **immer nur in leere Felder**, eigene Angaben bleiben stehen
- ordnet über den Dateistamm zu: ersetzt du `foo.webp` durch `foo.png`, behält
  das Bild seine Tags und Beschreibungen
- schreibt Kamera und Aufnahmedaten als `data-cam` / `data-exif` ins Markup —
  daraus baut die Lightbox ihre Unterschrift
- schreibt die Bildliste in `gallery.html` zwischen die `GALLERY`-Marker
- listet auf, wo noch Angaben fehlen

**Wichtig:** `gallery.html` zwischen den `GALLERY`-Markern nicht von Hand
bearbeiten, der nächste Lauf überschreibt das. Inhalte gehören in `photos.json`.

### Verschlagworten mit `tag-photos.py`

Öffnet ein Fenster und geht die Bilder der Reihe nach durch:

- Vorschau, darunter Dateiname und die EXIF-Zeile
- Gepflegt werden **Datum, Ort, Kamera und Tags**; die Beschreibung ist optional
- Datum mit Formatprüfung, Ort als Auswahlliste aller bisherigen Orte
- Tags als Ankreuzfelder, **die häufigsten zuerst**, mit Nennungszahl
- neue Tags anlegen — fragt die englische Bezeichnung ab
- **„Tags verwalten …"** — Kennung und Bezeichnungen ändern oder einen Tag
  löschen. Beim Umbenennen ziehen alle Bilder automatisch mit, beim Löschen
  wird vorher angezeigt, wie viele Bilder betroffen sind
- **„Bild entfernen …"** — siehe unten
- Kamera aus dem EXIF, überschreibbar; daneben steht, ob der Wert abweicht
- **„Ort + Tags übernehmen" (Strg+D)** kopiert Ort und Tags vom zuvor bearbeiteten Bild — spart bei einer Serie aus einem
  Shooting die meiste Arbeit. Das **Datum bleibt stehen**: es stammt aus dem EXIF
  des jeweiligen Bildes und wäre sonst überschrieben
- „Nächstes unvollständiges" springt gezielt zu den Lücken
- **Geschrieben wird nur auf Knopfdruck** (oder Strg+S). Blättern, Filtern und
  Tag-Änderungen bleiben bis dahin im Arbeitsspeicher; oben zeigt
  „● ungespeichert" an, dass etwas aussteht. Beim Schließen wird nachgefragt

Die Kamera erscheint danach in der Galerie am Ende der Tag-Zeile und ist über
die Freitextsuche auffindbar („canon", „55-250").

### Beschreibung ist optional

Die Felder `de` und `en` dürfen leer bleiben — ein Bild gilt auch ohne sie als
vollständig. Ist eine Beschreibung eingetragen, wird sie als Alt-Text und
Bildunterschrift verwendet. Ist sie leer, entsteht der Text beim Bauen aus Tags,
Ort und Datum:

```
mit Beschreibung:  alt="Blick über die Donau kurz nach Sonnenuntergang"
ohne:              alt="Donau, HDR, Landschaft, Sonnenuntergang · Ybbs · 22.08.2026"
```

Die Oberfläche zeigt unter den Feldern an, welcher Rückfalltext greifen würde.
Die Kamera steht nur in der sichtbaren Unterschrift, nicht im Alt-Text — sie
beschreibt nicht den Bildinhalt.

### Wo welcher Text erscheint

| | Raster | Lightbox |
|---|---|---|
| Datum und Ort | ✓ | — |
| Tags | ✓ | — |
| Kamera | ✓ | Zeile 1 |
| Blende, Zeit, Brennweite, ISO | — | Zeile 1 |
| Position (z. B. `6/31`) | — | Zeile 2 |
| Beschreibung | Alt-Text | Alt-Text |

Die Unterschrift im geöffneten Bild hat also zwei Zeilen:

```
Canon EOS 2000D · ƒ/5,6 · 1/400 · 194 mm · ISO 200
6/31
```

Aufbau der ersten Zeile wie im Info-Feld gängiger Foto-Programme: ƒ-Zeichen,
Belichtungszeit ohne Einheit, Dezimalkomma. Sie wird **nicht** übersetzt — sie
besteht nur aus Zahlen und Einheiten. Fehlt das EXIF (etwa bei einem
GIMP-PNG-Export), bleibt nur die Kamera stehen; fehlt auch die, entfällt die
Zeile ganz.

### Bilder entfernen

Über **„Bild entfernen …"** in der Oberfläche, mit zwei Möglichkeiten:

| | was passiert |
|---|---|
| **Nur von der Seite nehmen** | Original wandert nach `originals/_ausgeblendet/`, Eintrag und Vorschaubilder verschwinden. Zum Zurückholen die Datei eine Ebene hoch verschieben und neu bauen. |
| **Endgültig löschen** | Original wird von der Platte entfernt. Zweite Rückfrage, kein Zurück. |

Nur den Eintrag zu löschen würde nicht reichen: `build-gallery.py` liest den
Ordner `originals/` und nähme das Bild beim nächsten Lauf wieder auf. Deshalb
muss die Datei mit weg — Unterordner werden beim Bauen übersprungen.

### photos.json

Zwei Blöcke. Oben die **Tag-Tabelle** — jede Kennung einmal mit ihren
Bezeichnungen:

```json
"tags": {
  "motorsport": { "de": "Motorsport", "en": "Motorsport" },
  "naesse":     { "de": "Nässe",      "en": "Wet" }
}
```

Darunter die **Bilder**, die nur noch auf die Kennungen verweisen:

```json
{
  "datei":  "IMG_7224.JPG",
  "datum":  "2026-08-15",
  "ort":    "Melk",
  "kamera": "Canon EOS 2000D",
  "tags":   ["auto", "driften"],
  "de":     "",
  "en":     "",

  "exif": {
    "datum": "2026-08-15", "kamera": "Canon EOS 2000D",
    "objektiv": "EF-S55-250mm f/4-5.6 IS STM",
    "brennweite": "194 mm", "blende": "f/5.6",
    "belichtung": "1/400 s", "iso": "200"
  }
}
```

**Der Block `exif` gehört dem Skript, alles darüber dir.**

`exif` spiegelt, was in der Bilddatei steht, und wird bei jedem Lauf neu
geschrieben — Änderungen dort gehen verloren. `datum` und `kamera` daneben sind
das, was auf der Seite erscheint: beim ersten Lauf aus dem EXIF übernommen,
danach nie wieder angefasst.

Dadurch bleibt der Originalwert erhalten, und die Oberfläche zeigt neben beiden
Feldern an, ob du sie geändert hast:

```
DATUM   [2026-08-11]   geändert · EXIF: 2026-08-04   [↺]
KAMERA  [Canon EOS 2000D]   = EXIF
```

Der Knopf ↺ setzt das Feld auf den EXIF-Wert zurück. Hat die Datei keine
Metadaten, steht dort „kein EXIF-Wert".

`datum` und `ort` dürfen leer bleiben — die Filter zeigen solche Bilder dann
unter „ohne Datum" bzw. „ohne Ortsangabe". Die Jahres- und Orts-Auswahllisten
bauen sich selbst aus den vorhandenen Werten auf; neue Orte erscheinen also
automatisch im Filter.

Neue Tags brauchen einmalig eine Übersetzung im Block `"tags"` oben in der
Datei. Fehlt sie, warnt das Build-Skript und zeigt den Tag-Namen unübersetzt an.

## Zweisprachigkeit

Deutsche und englische Texte stehen beide im HTML, je in einem `<span>`:

```html
<span class="lang-de" lang="de">Projekte</span><span class="lang-en" lang="en">Projects</span>
```

`script.js` setzt das Attribut `data-lang` auf `<html>` und merkt sich die Wahl im
`localStorage`. Ein kleines Inline-Script im `<head>` jeder Seite setzt es bereits
vor dem ersten Rendern, damit nichts aufblitzt.

Bewusst ein Attribut und **keine** Klasse: die Regel `.lang-en { display:none }`
würde bei einer Klasse auch das `<html>`-Element selbst treffen und damit die
ganze Seite ausblenden.

**Beim Ergänzen von Inhalten immer beide Sprachen pflegen** — sonst ist der Text
in einer der beiden Sprachversionen unsichtbar.

## Projekte

`projekte.md` ist die Quelle der Projektinhalte. Die Regel dahinter:

> **Auf den Projektseiten steht nur, was in `projekte.md` steht.**

Damit gibt es genau eine Stelle, an der entschieden wird, was öffentlich ist —
gerade bei Arbeiten mit Sperrfrist oder Firmenbezug. Alles, was dort fehlt
(Zahlen, Werkzeuge, Firmennamen, Zeitpunkte), gehört auch nicht auf die Seite.
Anders als bei der Galerie gibt es dafür **kein Skript**: `projects/*.html` wird
von Hand gepflegt, `projekte.md` ist die inhaltliche Vorgabe, nicht der Input
eines Generators.

Reihenfolge auf der Zeitleiste = Reihenfolge in `projekte.md` (neueste zuerst).

### Neues Projekt hinzufügen

1. Abschnitt in `projekte.md` ergänzen — an der chronologisch richtigen Stelle.
2. Eine bestehende Datei in `projects/` als Vorlage kopieren.
3. `<title>`, `meta description`, `og:*` und `canonical` anpassen.
4. Eintrag in der Zeitleiste in `projects.html` ergänzen (neueste zuerst).
5. `detail-nav` (vorheriges/nächstes Projekt) der **beiden** Nachbarseiten anpassen.
6. Gegebenenfalls eine Preview-Karte in `index.html` ergänzen — dort stehen die
   drei neuesten Projekte.
7. URL in `sitemap.xml` eintragen.

Englische Texte sind Übersetzungen der deutschen Angaben aus `projekte.md` —
beim Ergänzen also immer beide Sprachen schreiben, siehe *Zweisprachigkeit*.

## Aktualitätsstempel

Jede Seite zeigt im Fuß, wann sie zuletzt aktualisiert wurde. Zusätzlich steht
das Datum dort, wo es am ehesten jemanden interessiert:

| Seite | zusätzlich |
|---|---|
| `index.html` | Zeile „Stand …" unter der Überschrift *Lebenslauf* |
| `projects.html` | Zeile „Stand …" unter *Zeitleiste* |
| `projects/*.html` | Zeile *Zuletzt aktualisiert* in der Angabenliste |
| `datenschutz.html` | „Stand …" am Ende des Textes |

Das Datum wird **von Hand** gepflegt — es gibt kein Skript dafür. Beim Ändern
einer Seite also das `<time datetime="JJJJ-MM-TT">` mitziehen; es steht in jeder
Datei einmal im Fuß und gegebenenfalls einmal im Inhalt. Alle Stellen finden:

```bash
grep -rn 'datetime="20' *.html projects/*.html
```

## Lokal ansehen

```bash
python3 -m http.server 8000
```

Dann <http://localhost:8000> öffnen.
