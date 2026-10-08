# Hinweise für Claude Code

- Zuerst `CHANGELOG.md` lesen (letzte Änderungen, offene Punkte), dann `README.md`.
- Nur `_src/` von Hand bearbeiten, danach `python3 tools/build-pages.py`.
  Wurzelverzeichnis und `en/` sind erzeugt.
- Immer beide Sprachen pflegen (`lang-de` / `lang-en`, `data-en`).
- Lokal ansehen: `python3 tools/serve.py` → http://localhost:8000 (ohne Browser-Cache)
- Nach jeder Änderung einen Eintrag in `CHANGELOG.md` ergänzen.
- Commit und Push macht der Nutzer selbst bzw. nur auf ausdrücklichen Wunsch — nicht ins Galerie-Werkzeug einbauen.
