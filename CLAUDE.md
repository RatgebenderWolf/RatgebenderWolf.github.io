# Hinweise für Claude Code

- Zuerst `CHANGELOG.md` lesen (letzte Änderungen, offene Punkte), dann `README.md`.
- Nur `_src/` von Hand bearbeiten, danach `python3 tools/build-pages.py`.
  Wurzelverzeichnis und `en/` sind erzeugt.
- Immer beide Sprachen pflegen (`lang-de` / `lang-en`, `data-en`).
- Lokal ansehen: `python3 -m http.server 8000` → http://localhost:8000
- Nach jeder Änderung einen Eintrag in `CHANGELOG.md` ergänzen.
