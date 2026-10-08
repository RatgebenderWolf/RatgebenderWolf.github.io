# Changelog

Was an der Website geändert wurde und warum — neueste Einträge oben.
Gedacht als Einstieg für spätere Arbeitssitzungen (auch für Claude Code):
erst hier lesen, dann `README.md` für den Aufbau.

Grundregel aus der README: **nur `_src/` von Hand bearbeiten**, danach
`python3 tools/build-pages.py`. Die Dateien im Wurzelverzeichnis und in `en/`
sind Ausgabe. Wird doch einmal direkt in der Ausgabe geändert (z. B. schnell
im Browser getestet), die Änderung nach `_src/` übernehmen und neu bauen.

## 2026-10-08

### Startseite und 404 überarbeitet
Die Änderungen wurden zuerst direkt in `index.html` / `404.html` gemacht und
dann nach `_src/` übernommen, mit englischer Übersetzung.

- Rolle: „Masterstudent Interactive Technologies und Projekttechniker bei der
  Firma Doka“; Einleitung jetzt zur Arbeit bei Doka (Werkzeuge, Prozesse,
  Anlagen zum Thema Schalung)
- Master-Eintrag: „University of Applied Sciences St. Pölten“ (EN: „St. Pölten
  University of Applied Sciences“). Der Bachelor-Eintrag heißt noch
  „Fachhochschule St. Pölten“ — offen, ob angleichen
- Doka-Eintrag: „Projektmanagement“ → „Projektleitung“
- Skills: „Large Language Models (LLM)“, „Computer-Aided Design (CAD)“, neu
  „Projektmanagement“ / „Project management“
- Projekt-Previews: WER-Zahlen (ARCTA) und One-Class-Zusatz (Industrieöfen)
  entfernt
- Kontakt: Überschrift „Fragen?“, Anrede jetzt **Sie** („Schreiben Sie mir
  gerne eine E-Mail.“); Buttons GitHub und „Lebenslauf anfragen“ entfernt
  (GitHub bleibt im Fuß verlinkt)
- `404.html`: deutscher Block entfernt, die Seite ist jetzt nur englisch

### Projektseiten deaktiviert — außer ARCTA
Gewünscht: Seiten bleiben im Repo, sind aber nicht mehr verlinkt.

- `_src/projects.html`: alle Einträge außer ARCTA von `<a class="timeline-item">`
  zu `<div class="timeline-item">`, „→ Details ansehen“ entfernt
- `_src/index.html`: Preview-Karten Plywood und Industrieöfen von `<a>` zu `<div>`
- `_src/projects/arcta-funkprotokoll.html`: „Nächstes Projekt“ entfernt
  (zeigte auf Plywood)
- alle anderen `_src/projects/*.html` bekommen
  `<meta name="robots" content="noindex">` — `build-pages.py` lässt solche
  Seiten automatisch aus der `sitemap.xml` weg
- `styles.css`: Hover-Effekte nur noch für `a.preview-card` / `a.timeline-item`,
  damit nicht verlinkte Karten nicht klickbar wirken

**Wieder aktivieren:** `<div>` zurück zu `<a href="projects/….html">`,
„Details ansehen“-Zeile wieder einsetzen, `noindex` aus der Projektseite
entfernen, `detail-nav` der Nachbarseiten prüfen, neu bauen.

### Sonstiges
- Galerie: 12 weitere Bilder (`photos.json`, `_src/gallery.html`, `images/gallery/`)
- `projekte.md` gelöscht (vom Nutzer). Die README beschreibt sie noch als
  Quelle der Projektinhalte — Abschnitt *Projekte* dort ist damit veraltet
- `CHANGELOG.md` und `CLAUDE.md` angelegt und in `_config.yml` von der
  Veröffentlichung ausgenommen

## Frühere Stände (aus der Git-History)

- **2026-10-04** — Skills auf der Startseite zu einem Block zusammengefasst;
  Galerie +32 Bilder; Angabenliste der Projektseiten: Überlauf behoben,
  Beschriftung mit eigener Klasse
- **2026-08-24** — eigene Adressen je Sprache (`/en/` mit `hreflang`, Generator
  `build-pages.py`), Domain korrigiert; Projektseiten aus `projekte.md`,
  Aktualitätsstempel, Feinschliff für Handy; `CNAME`
- **2026-08-22** — Portfolio überarbeitet: Projekte, Galerie, Impressum/Datenschutz
- **2026-08-19** — erste Fassung
