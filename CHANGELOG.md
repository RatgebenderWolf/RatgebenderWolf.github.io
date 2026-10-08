# Changelog

Was an der Website geändert wurde und warum — neueste Einträge oben.
Gedacht als Einstieg für spätere Arbeitssitzungen (auch für Claude Code):
erst hier lesen, dann `README.md` für den Aufbau.

Grundregel aus der README: **nur `_src/` von Hand bearbeiten**, danach
`python3 tools/build-pages.py`. Die Dateien im Wurzelverzeichnis und in `en/`
sind Ausgabe. Wird doch einmal direkt in der Ausgabe geändert (z. B. schnell
im Browser getestet), die Änderung nach `_src/` übernehmen und neu bauen.

## 2026-10-08

### Hinweisbanner „Seite im Aufbau“ abgeschaltet
- Block `<div class="disclaimer" role="note">` aus allen 15 Quellen in
  `_src/` entfernt, Seiten neu gebaut
- CSS `.disclaimer` in `styles.css` bleibt (mit Kommentar), damit das Banner
  sich schnell wieder einschalten lässt. Markup zum Wiedereinsetzen, direkt
  nach dem Skip-Link:
  ```html
  <div class="disclaimer" role="note">
    <span class="lang-de" lang="de"><strong>Hinweis</strong> Diese Website befindet sich im Aufbau. Angaben können unvollständig, veraltet oder fehlerhaft sein.</span>
    <span class="lang-en" lang="en"><strong>Note</strong> This website is still under construction. Information may be incomplete, outdated or incorrect.</span>
  </div>
  ```

### Galerie-Werkzeug: Tag-Feld statt Ankreuzliste, KI nur auf Knopfdruck
Rückmeldung des Nutzers nach dem ersten Test.

- „Bilder hinzufügen …“ fragt die KI **nicht** mehr automatisch (vorher
  Rückfrage + Versand) — nur noch Hinweis in der Statuszeile
- Tag-Ankreuzliste (alle 27+ Tags) ersetzt durch ein **Tag-Feld**: gesetzte
  Tags als Kästchen mit ×, dahinter Eingabe mit Vorschlagsliste
  (Präfix-Treffer zuerst, nach Häufigkeit), Tab/Enter übernimmt, ↑/↓ wählt,
  Rücktaste im leeren Feld entfernt den letzten Tag, unbekannter Text →
  „+ neuen Tag anlegen“ (Dialog, Fokus gleich auf Englisch)
  Technik: `tk.Text` mit eingebetteten Frames (bricht von selbst um);
  beim Neuzeichnen nur bis zum Eingabefeld löschen, sonst zerstört Tk es.
  Zustand in `self.gesetzt` statt `self.tag_vars`
- Eingabezeile „Tag anlegen“ entfällt; „Tags verwalten …“ sitzt jetzt neben
  dem Tag-Feld
- `ki_tags.py`: Anweisung verlangt **mindestens 3 Tags** (`MIN_TAGS`),
  notfalls mit neuen ergänzt

### Galerie-Werkzeug: KI-Tags und Werkzeugleiste
Ziel: Tags per KI vorschlagen lassen und kein Terminal mehr für die Galerie.
Entscheidungen des Nutzers: Cloud erlaubt, Anbieter **OpenRouter**, KI darf
neue Tags vorschlagen (jeder Tag DE/EN), Oberfläche bleibt Tkinter, Commit
und Push bleiben **manuell** (nicht ins Werkzeug).

- `tools/ki_tags.py` (neu): OpenRouter-Aufruf nur mit Standardbibliothek
  (`urllib`). Schickt das 800-px-Vorschaubild + Tag-Liste + Ort + EXIF-Zeile,
  erwartet JSON `{"tags": [...], "neue_tags": [{"de","en"}]}`. Filtert
  unbekannte Kennungen, max. 3 neue Tags, liest `usage.cost`.
  Konfiguration: `~/.config/ralf-galerie/openrouter.json` (chmod 600) oder
  `OPENROUTER_API_KEY`. Standardmodell `google/gemini-2.5-flash-lite`
- `tools/tag-photos.py`: Werkzeugleiste (Bilder hinzufügen, Galerie bauen,
  Vorschau, KI für alle ohne Tags, KI-Einstellungen), Knopf „✦ KI-Vorschlag“
  (Strg+K), ✦-Markierung, Knöpfe für neue Tag-Vorschläge,
  Protokollfenster. KI und Skripte laufen in Threads; während eines Builds
  ist das Fenster gesperrt (`grab_set`), danach wird `photos.json` neu
  geladen. KI ergänzt Tags nur, wählt nie ab; gespeichert wird nur per Knopf
- `tools/serve.py` (neu): lokaler Server mit `Cache-Control: no-store`
- Startmenü-Eintrag `~/.local/share/applications/galerie-werkzeug.desktop`
  (außerhalb des Repos)
- Getestet: KI-Ablauf mit simulierter API-Antwort auf einer Kopie von
  `photos.json`, „Galerie bauen“ aus dem Fenster. **Noch nicht** gegen die
  echte OpenRouter-API getestet (Schlüssel lag nicht vor)

### Galerie: Seiten mit je 27 Bildern
Bei 75 Bildern wurden alle Vorschaubilder auf einmal geladen.

- `gallery.js`: nach Filter und Sortierung werden nur 27 Treffer je Seite
  angezeigt (`PER_PAGE`). Ausgeblendete Bilder haben `loading="lazy"` und
  werden deshalb gar nicht geladen
- Seite steht in der Adresse: `#seite-2` (DE) bzw. `#page-2` (EN) —
  Zurück-Taste, Neuladen und Links funktionieren; Seite 1 ohne Hash
- Filter/Suche/Sortierung ändern → zurück auf Seite 1; Zähler zeigt
  „75 Bilder · Seite 2 von 3“
- Lightbox blättert weiter durch **alle** Treffer, über Seitengrenzen
  hinweg; beim Schließen springt das Raster auf die Seite des letzten Bildes
- `_src/gallery.html`: `<nav class="pager" id="fPager">` nach der Bildliste
  (außerhalb der `GALLERY`-Marker, `build-gallery.py` überschreibt sie also
  nicht); ohne JavaScript bleibt sie leer und alle Bilder stehen untereinander
- `styles.css`: Abschnitt `gallery pages` (`.pager`, `.pager-btn`)

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
