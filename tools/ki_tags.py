#!/usr/bin/env python3
"""
KI-Vorschlaege fuer Tags ueber OpenRouter.

Wird von tag-photos.py benutzt, laesst sich zum Ausprobieren aber auch
direkt aufrufen:

    python3 tools/ki_tags.py images/gallery/thumb/IMG_8020.webp

Geschickt wird nur das Vorschaubild (800 px, ohne Metadaten — dieselbe
Datei, die ohnehin auf der Website liegt), dazu die Tag-Liste, der Ort und
die Aufnahmedaten. Zurueck kommen passende vorhandene Tags und hoechstens
drei neue, jeweils mit deutscher und englischer Bezeichnung — zusammen
mindestens drei.

Die KI schlaegt nur vor. Was davon uebernommen wird, entscheidet die
Oberflaeche bzw. der Mensch davor.

API-Schluessel und Modell stehen in  ~/.config/ralf-galerie/openrouter.json
(ausserhalb des Repos, damit der Schluessel nie in Git landet). Alternativ
gilt die Umgebungsvariable OPENROUTER_API_KEY.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

KONFIG = os.path.join(os.path.expanduser("~"), ".config", "ralf-galerie", "openrouter.json")
URL = "https://openrouter.ai/api/v1/chat/completions"

# Guenstig, kann Bilder lesen, gutes Deutsch. Rund 0,02 Cent pro Bild.
STANDARD_MODELL = "google/gemini-2.5-flash-lite"
MODELLE = (
    "google/gemini-2.5-flash-lite",
    "anthropic/claude-haiku-5.5",
    "openai/gpt-5-nano",
    "qwen/qwen3-vl-8b-instruct",
)
MAX_NEU = 3
MIN_TAGS = 3


class KIFehler(Exception):
    """Fehler mit einer Meldung, die man so in der Oberflaeche zeigen kann."""


# ------------------------------------------------------------- Konfiguration
def konfig_laden():
    try:
        with open(KONFIG, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        cfg = {}
    cfg.setdefault("modell", STANDARD_MODELL)
    cfg.setdefault("api_key", "")
    return cfg


def konfig_speichern(cfg):
    os.makedirs(os.path.dirname(KONFIG), exist_ok=True)
    tmp = KONFIG + ".tmp"
    # nur fuer den eigenen Benutzer lesbar — da steht ein Schluessel drin
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, KONFIG)


def schluessel(cfg):
    return os.environ.get("OPENROUTER_API_KEY") or cfg.get("api_key", "")


# ------------------------------------------------------------------ Helfer
def kennung(text):
    """Bezeichnung -> interne Kennung, wie beim Anlegen von Hand: 'Schiff/Boot' -> 'schiffboot'."""
    t = text.strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "", t)


def _aufnahmedaten(exif):
    teile = [exif.get(k, "") for k in ("belichtung", "brennweite", "blende")]
    if exif.get("iso"):
        teile.append("ISO " + exif["iso"])
    return " · ".join(t for t in teile if t)


def _anweisung(tags_def, ort, exif):
    liste = "\n".join(f"- {t}: {v.get('de', t)} / {v.get('en', t)}"
                      for t, v in sorted(tags_def.items()))
    kontext = []
    if ort:
        kontext.append(f"Aufnahmeort: {ort}")
    daten = _aufnahmedaten(exif or {})
    if daten:
        kontext.append(f"Aufnahmedaten: {daten}")
    return f"""Vorhandene Tags (Kennung: Deutsch / Englisch):
{liste}

{chr(10).join(kontext)}

Aufgabe:
1. Wähle aus den vorhandenen Tags alle, die eindeutig zum Bild passen. Nur
   Kennungen aus der Liste verwenden. Technik-Tags wie HDR oder
   Langzeitbelichtung nur, wenn es am Bild oder an den Aufnahmedaten
   erkennbar ist.
2. Schlage höchstens {MAX_NEU} neue Tags vor — für deutlich sichtbare,
   wichtige Motive, die kein vorhandener Tag abdeckt. Im Stil der
   vorhandenen: ein allgemeines Substantiv im Singular, kein Ortsname, keine
   Farbe, keine Stimmung.
3. Insgesamt (vorhandene + neue) mindestens {MIN_TAGS} Tags. Passen weniger
   vorhandene, ergänze passende neue, bis es mindestens {MIN_TAGS} sind.

Antworte nur mit JSON in genau dieser Form:
{{"tags": ["kennung", ...], "neue_tags": [{{"de": "...", "en": "..."}}]}}"""


def _json_aus(text):
    """Erstes JSON-Objekt aus der Antwort holen — manche Modelle packen es in ```json."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise KIFehler("Die Antwort der KI enthielt kein JSON:\n" + (text or "")[:300])
    try:
        return json.loads(m.group(0))
    except ValueError:
        raise KIFehler("Die Antwort der KI war kein gültiges JSON:\n" + m.group(0)[:300])


# ------------------------------------------------------------------- Abruf
def vorschlagen(bild, tags_def, ort="", exif=None, cfg=None, timeout=60):
    """Tags fuer ein Bild vorschlagen.

    Rueckgabe: {"tags": [kennung, ...],              nur vorhandene
                "neu":  [{"de": ..., "en": ...}],   noch nicht vorhandene
                "kosten": float oder None (USD),
                "modell": str}
    """
    cfg = cfg or konfig_laden()
    key = schluessel(cfg)
    if not key:
        raise KIFehler("Kein OpenRouter-Schlüssel hinterlegt.\n\n"
                       "In der Oberfläche unter „KI-Einstellungen …“ eintragen.")
    with open(bild, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    endung = os.path.splitext(bild)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg"}.get(endung, endung)

    koerper = {
        "model": cfg.get("modell") or STANDARD_MODELL,
        "messages": [
            {"role": "system",
             "content": "Du verschlagwortest Fotos für eine private Fotogalerie. "
                        "Antworte ausschließlich mit JSON."},
            {"role": "user", "content": [
                {"type": "text", "text": _anweisung(tags_def, ort, exif)},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
            ]},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }
    anfrage = urllib.request.Request(
        URL, data=json.dumps(koerper).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "X-Title": "Galerie-Werkzeug"})
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            daten = json.load(antwort)
    except urllib.error.HTTPError as e:
        try:
            meldung = json.load(e).get("error", {}).get("message", "")
        except ValueError:
            meldung = ""
        hinweis = {401: "Schlüssel ungültig.",
                   402: "Guthaben bei OpenRouter aufgebraucht.",
                   429: "Zu viele Anfragen — kurz warten."}.get(e.code, "")
        raise KIFehler(f"OpenRouter meldet Fehler {e.code}. {hinweis}\n{meldung}".strip())
    except (urllib.error.URLError, TimeoutError) as e:
        raise KIFehler(f"OpenRouter nicht erreichbar: {getattr(e, 'reason', e)}")

    if daten.get("error"):
        raise KIFehler("OpenRouter: " + str(daten["error"].get("message", daten["error"])))
    try:
        text = daten["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise KIFehler("Unerwartete Antwort von OpenRouter:\n" + json.dumps(daten)[:300])
    roh = _json_aus(text)

    tags, neu = [], []
    for t in roh.get("tags") or []:
        if isinstance(t, str) and t in tags_def and t not in tags:
            tags.append(t)
    for n in roh.get("neue_tags") or []:
        if not isinstance(n, dict):
            continue
        de = str(n.get("de", "")).strip()
        en = str(n.get("en", "")).strip() or de
        k = kennung(de)
        if not k:
            continue
        if k in tags_def:                    # gibt es doch schon -> normal setzen
            if k not in tags:
                tags.append(k)
        elif k not in {kennung(x["de"]) for x in neu}:
            neu.append({"de": de, "en": en})
    kosten = (daten.get("usage") or {}).get("cost")
    return {"tags": tags, "neu": neu[:MAX_NEU],
            "kosten": float(kosten) if isinstance(kosten, (int, float)) else None,
            "modell": daten.get("model", koerper["model"])}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf:  python3 tools/ki_tags.py <bilddatei>")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "photos.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    stamm = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    p = next((x for x in d["photos"] if os.path.splitext(x["datei"])[0] == stamm), {})
    try:
        print(json.dumps(vorschlagen(sys.argv[1], d["tags"], p.get("ort", ""), p.get("exif")),
                         ensure_ascii=False, indent=2))
    except KIFehler as e:
        sys.exit(str(e))
