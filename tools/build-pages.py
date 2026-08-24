#!/usr/bin/env python3
"""
Seiten bauen — aus je einer zweisprachigen Quelle zwei einsprachige Seiten.

    python3 tools/build-pages.py

Aus  _src/projects.html  entstehen:

    projects.html        nur Deutsch    https://ralfhoerhager.com/projects.html
    en/projects.html     nur Englisch   https://ralfhoerhager.com/en/projects.html

Beide verweisen per hreflang aufeinander, damit Suchmaschinen sie als
Uebersetzungen derselben Seite erkennen und die englische Fassung eine eigene
Adresse bekommt.

Was das Skript mit der Quelle macht
-----------------------------------
* <span class="lang-de">…</span> / <span class="lang-en">…</span>
  Die Huelle der Zielsprache faellt weg, ihr Inhalt bleibt; die andere Sprache
  wird samt Inhalt entfernt. Traegt die Huelle weitere Klassen
  ("tag mono lang-de"), bleibt das Element stehen und verliert nur lang-de.

* data-en="…"  auf <title> und <meta>
  Uebersetzung fuer Angaben, die kein Element umschliessen koennen. In der
  englischen Fassung ersetzt sie den deutschen Wert, danach faellt sie weg.

* data-alt-de / data-alt-en  und  data-ph-de / data-ph-en
  Werden zu  data-alt  bzw.  placeholder  zusammengezogen (bei <img> zusaetzlich
  zu alt). So braucht die Galerie zur Laufzeit keine Sprachlogik mehr.

* Interne Verweise werden absolut: aus "../fonts.css" wird "/fonts.css",
  aus "projects.html" wird "/projects.html" bzw. "/en/projects.html".
  Das erspart jede Tiefenrechnung, weil die englischen Seiten eine Ebene
  tiefer liegen. Dateien ausserhalb von _src (CSS, Bilder, PDF) sind gemeinsam
  und bekommen nie ein /en davor.

* Der Sprachumschalter wird aus Knoepfen zu Verweisen auf die andere Fassung.

* 404.html ist ein Sonderfall: GitHub Pages nutzt fuer die gesamte Website nur
  die eine Datei im Wurzelverzeichnis. Sie wird deshalb einmal gebaut und zeigt
  beide Sprachen untereinander.
"""

import html as _html
import os
import posixpath
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_src")
DOMAIN = "https://ralfhoerhager.com"

# Seiten, die es in beiden Sprachen gibt (404 siehe Modulkopf)
NUR_EINMAL = {"404.html"}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}

# data-<kurz>-de/-en  ->  Zielattribut
PAARE = {"alt": "data-alt", "ph": "placeholder"}

SPRACHE_HTML = {"de": "de", "en": "en"}
OG_LOCALE = {"de": "de_AT", "en": "en"}


def quellen():
    raus = []
    for wurzel, _, dateien in os.walk(SRC):
        for d in sorted(dateien):
            if d.endswith(".html"):
                raus.append(os.path.relpath(os.path.join(wurzel, d), SRC).replace(os.sep, "/"))
    return sorted(raus)


def url_pfad(rel, sprache):
    """Site-absoluter Pfad einer Seite:  projects.html -> /projects.html"""
    vorne = "/en/" if sprache == "en" else "/"
    if rel == "index.html":
        return vorne
    return vorne + rel


def voll_url(rel, sprache):
    return DOMAIN + url_pfad(rel, sprache)


class Umbau(HTMLParser):
    def __init__(self, sprache, quelle_rel, seiten):
        super().__init__(convert_charrefs=False)
        self.sprache = sprache
        self.andere = "en" if sprache == "de" else "de"
        self.dir = posixpath.dirname(quelle_rel)
        self.seiten = seiten
        self.out = []
        self.skip = 0          # Tiefe innerhalb der anderen Sprache
        self.unwrap = []       # offene Huellen, deren Tag entfaellt
        self.titel_skip = False

    # ---------------------------------------------------------------- Hilfen
    def schreib(self, s):
        if not self.skip:
            self.out.append(s)

    def _klassen(self, attrs):
        for k, v in attrs:
            if k == "class" and v:
                return v.split()
        return []

    def _verweis(self, wert):
        """Interner Verweis -> site-absoluter Pfad."""
        if not wert:
            return wert
        if re.match(r"^(https?:|mailto:|tel:|data:|//|#)", wert):
            return wert
        pfad, _, frag = wert.partition("#")
        frag = ("#" + frag) if frag else ""
        if not pfad:
            return wert
        if pfad.startswith("/"):
            ziel = pfad.lstrip("/")
        else:
            ziel = posixpath.normpath(posixpath.join(self.dir, pfad))
        if ziel in self.seiten:                       # eigene Seite -> Sprache
            return url_pfad(ziel, self.sprache) + frag
        return "/" + ziel + frag                      # gemeinsame Datei

    def _attrs_bauen(self, tag, attrs):
        d = {}
        reihenfolge = []
        for k, v in attrs:
            if k not in d:
                reihenfolge.append(k)
            d[k] = v

        # Sprachpaare zusammenziehen
        for kurz, ziel in PAARE.items():
            a, b = "data-%s-de" % kurz, "data-%s-en" % kurz
            if a in d or b in d:
                wert = d.get(a if self.sprache == "de" else b) or d.get(a) or d.get(b) or ""
                for weg in (a, b):
                    if weg in d:
                        d.pop(weg)
                        reihenfolge.remove(weg)
                if ziel not in d:
                    reihenfolge.append(ziel)
                d[ziel] = wert
                if tag == "img" and kurz == "alt":
                    if "alt" not in d:
                        reihenfolge.append("alt")
                    d["alt"] = wert

        # Uebersetzte Kopfangabe
        if "data-en" in d:
            if self.sprache == "en" and "content" in d:
                d["content"] = d["data-en"]
            d.pop("data-en")
            reihenfolge.remove("data-en")

        # Verweise absolut machen
        for k in ("href", "src", "data-large"):
            if k in d and d[k] is not None:
                d[k] = self._verweis(d[k])

        # lang-XX aus der Klassenliste nehmen
        if "class" in d and d["class"]:
            behalten = [c for c in d["class"].split() if c not in ("lang-de", "lang-en")]
            if behalten:
                d["class"] = " ".join(behalten)
            else:
                d.pop("class")
                reihenfolge.remove("class")

        teile = []
        for k in reihenfolge:
            v = d.get(k)
            if v is None:
                teile.append(k)
            else:
                teile.append('%s="%s"' % (k, _html.escape(v, quote=True)))
        return (" " + " ".join(teile)) if teile else ""

    # ------------------------------------------------------------- Ereignisse
    def handle_starttag(self, tag, attrs):
        klassen = self._klassen(attrs)

        if "lang-" + self.andere in klassen:
            self.skip += 1
            return
        if self.skip:
            if tag not in VOID:
                self.skip += 1
            return

        if "lang-" + self.sprache in klassen:
            # reine Huelle -> Tag faellt weg, Inhalt bleibt
            if tag == "span" and set(klassen) == {"lang-" + self.sprache}:
                self.unwrap.append(True)
                return
            self.unwrap.append(False)
            self.out.append("<%s%s>" % (tag, self._attrs_bauen(tag, attrs)))
            return

        if tag == "html":
            self.out.append('<html lang="%s">' % SPRACHE_HTML[self.sprache])
            return

        if tag == "title":
            for k, v in attrs:
                if k == "data-en" and self.sprache == "en":
                    self.out.append("<title>" + _html.escape(v) + "</title>")
                    self.titel_skip = True
                    return
            self.out.append("<title>")
            return

        self.out.append("<%s%s>" % (tag, self._attrs_bauen(tag, attrs)))

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in VOID:
                self.skip -= 1
            return
        if tag == "span" and self.unwrap:
            if self.unwrap.pop():
                return
        if tag == "title" and self.titel_skip:
            self.titel_skip = False
            return
        self.out.append("</%s>" % tag)

    def handle_startendtag(self, tag, attrs):
        if self.skip:
            return
        if "lang-" + self.andere in self._klassen(attrs):
            return
        self.out.append("<%s%s>" % (tag, self._attrs_bauen(tag, attrs)))

    def handle_data(self, data):
        if self.titel_skip:
            return
        self.schreib(data)

    def handle_comment(self, data):
        self.schreib("<!--%s-->" % data)

    def handle_decl(self, decl):
        self.schreib("<!%s>" % decl)

    def handle_entityref(self, name):
        self.schreib("&%s;" % name)

    def handle_charref(self, name):
        self.schreib("&#%s;" % name)


# ------------------------------------------------------------------ Kopfteil
def kopf_setzen(text, rel, sprache):
    """canonical, og:* und die hreflang-Verweise auf den Stand bringen."""
    de_url, en_url = voll_url(rel, "de"), voll_url(rel, "en")
    selbst = de_url if sprache == "de" else en_url

    text = re.sub(r'<link rel="canonical"[^>]*>',
                  '<link rel="canonical" href="%s">' % selbst, text)
    text = re.sub(r'<meta property="og:url"[^>]*>',
                  '<meta property="og:url" content="%s">' % selbst, text)
    text = re.sub(r'<meta property="og:locale"[^>]*>',
                  '<meta property="og:locale" content="%s">\n'
                  '<meta property="og:locale:alternate" content="%s">'
                  % (OG_LOCALE[sprache], OG_LOCALE["en" if sprache == "de" else "de"]), text)
    # verbliebene alte Adressen (og:image u. a.)
    text = text.replace("https://ratgebenderwolf.github.io", DOMAIN)

    if rel not in NUR_EINMAL:
        alt = ('<link rel="alternate" hreflang="de" href="%s">\n'
               '<link rel="alternate" hreflang="en" href="%s">\n'
               '<link rel="alternate" hreflang="x-default" href="%s">' % (de_url, en_url, de_url))
        text = text.replace('<link rel="canonical" href="%s">' % selbst,
                            '<link rel="canonical" href="%s">\n%s' % (selbst, alt), 1)
    return text


UMSCHALTER = {
    "de": '<div class="lang-toggle" aria-label="Sprache / Language">\n'
          '      <span aria-current="true">DE</span>\n'
          '      <a href="{en}" hreflang="en" lang="en" aria-label="English">EN</a>\n'
          '    </div>',
    "en": '<div class="lang-toggle" aria-label="Sprache / Language">\n'
          '      <a href="{de}" hreflang="de" lang="de" aria-label="Deutsch">DE</a>\n'
          '      <span aria-current="true">EN</span>\n'
          '    </div>',
}


def bauen(rel, sprache, seiten):
    with open(os.path.join(SRC, rel), encoding="utf-8") as fh:
        text = fh.read()

    # Sprachskript im Kopf entfaellt — die Sprache steht jetzt in der Adresse
    text = re.sub(r'<script>\(function\(\)\{var l="de";.*?</script>\n?', "", text, flags=re.S)

    # Umschalter: Knoepfe -> Verweise. Auf Seiten ohne Gegenstueck (404)
    # gaebe es nichts zu verlinken — dort faellt er weg.
    #
    # Erst Platzhalter, eingesetzt wird nach dem Parsen: der Verweis zeigt
    # bewusst auf die ANDERE Sprache, und der Verweis-Umbau im Parser wuerde
    # ihn sonst auf die Sprache der aktuellen Seite zurueckbiegen.
    PLATZ = "<!--LANG-TOGGLE-->"
    if rel in NUR_EINMAL:
        text = re.sub(r'\s*<div class="lang-toggle".*?</div>', "", text, flags=re.S)
    else:
        text = re.sub(r'<div class="lang-toggle".*?</div>', PLATZ, text, flags=re.S)

    p = Umbau(sprache, rel, seiten)
    p.feed(text)
    p.close()
    ergebnis = "".join(p.out)

    ergebnis = ergebnis.replace(
        PLATZ, UMSCHALTER[sprache].format(de=url_pfad(rel, "de"), en=url_pfad(rel, "en")))

    ergebnis = kopf_setzen(ergebnis, rel, sprache)
    ergebnis = re.sub(r"\n{3,}", "\n\n", ergebnis)
    return ergebnis


def schreiben(pfad, inhalt):
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(inhalt)


def sitemap(seiten):
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
              '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    rang = {"index.html": "1.0", "projects.html": "0.9", "gallery.html": "0.8"}
    for rel in seiten:
        if rel in NUR_EINMAL:
            continue
        # auf noindex gesetzte Seiten (Impressum, Datenschutz) gehoeren nicht
        # in die Sitemap — das waere ein Widerspruch fuer Suchmaschinen
        with open(os.path.join(SRC, rel), encoding="utf-8") as fh:
            if 'name="robots" content="noindex"' in fh.read():
                continue
        for sprache in ("de", "en"):
            zeilen.append("  <url>")
            zeilen.append("    <loc>%s</loc>" % voll_url(rel, sprache))
            for s2 in ("de", "en"):
                zeilen.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>'
                              % (s2, voll_url(rel, s2)))
            zeilen.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>'
                          % voll_url(rel, "de"))
            zeilen.append("    <priority>%s</priority>" % rang.get(rel, "0.7"))
            zeilen.append("  </url>")
    zeilen.append("</urlset>")
    return "\n".join(zeilen) + "\n"


def main():
    if not os.path.isdir(SRC):
        sys.exit("Ordner fehlt: %s" % SRC)
    seiten = quellen()
    if not seiten:
        sys.exit("Keine Quellen in %s" % SRC)

    n = 0
    for rel in seiten:
        schreiben(os.path.join(ROOT, rel), bauen(rel, "de", seiten))
        n += 1
        if rel not in NUR_EINMAL:
            schreiben(os.path.join(ROOT, "en", rel), bauen(rel, "en", seiten))
            n += 1

    schreiben(os.path.join(ROOT, "sitemap.xml"), sitemap(seiten))
    schreiben(os.path.join(ROOT, "robots.txt"),
              "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % DOMAIN)

    print("%d Seiten aus %d Quellen geschrieben." % (n, len(seiten)))
    print("sitemap.xml und robots.txt aktualisiert.")
    fehlt = [r for r in seiten
             if 'data-en' not in open(os.path.join(SRC, r), encoding="utf-8").read()
             and r not in NUR_EINMAL]
    if fehlt:
        print("\nHINWEIS — ohne englische Kopfangaben (data-en an <title>/<meta>):")
        for r in fehlt:
            print("   _src/%s" % r)


if __name__ == "__main__":
    main()
