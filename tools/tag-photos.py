#!/usr/bin/env python3
"""
Galerie-Werkzeug: Bilder aufnehmen, verschlagworten, Galerie bauen.

    python3 tools/tag-photos.py

Geht die Bilder aus photos.json der Reihe nach durch und laesst Datum, Ort,
Tags und die Beschreibungen ergaenzen. Die Vorschau kommt aus
images/gallery/thumb/, deshalb laedt auch eine 20-MB-Originaldatei sofort.

Oben eine Werkzeugleiste, damit kein Terminal noetig ist:
    Bilder hinzufuegen …   kopiert nach originals/ und baut die Galerie
    Galerie bauen          build-gallery.py + build-pages.py, danach neu laden
    Vorschau im Browser    startet tools/serve.py und oeffnet die Galerie
    KI-Einstellungen …     OpenRouter-Schluessel und Modell

KI-Vorschlaege (tools/ki_tags.py): die KI setzt passende Tags (markiert mit ✦)
und schlaegt neue vor — die erscheinen als Knopf und werden erst beim
Anklicken angelegt. Gespeichert wird wie immer nur auf Knopfdruck.

Tasten:  Bild-hoch/runter oder Alt+Links/Rechts  blaettern
         Strg+S  speichern      Strg+D  Ort, Tags und Beschreibung vom vorherigen Bild uebernehmen
                 (das Datum bleibt stehen, es stammt aus dem EXIF)
         Strg+K  KI-Vorschlag fuer das aktuelle Bild
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, filedialog

import ki_tags

try:
    from PIL import Image, ImageTk
except ImportError:
    sys.exit("Pillow fehlt.  Installieren mit:  pip install Pillow")

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA  = os.path.join(ROOT, "photos.json")
THUMB = os.path.join(ROOT, "images", "gallery", "thumb")
LARGE = os.path.join(ROOT, "images", "gallery", "large")
ORIG  = os.path.join(ROOT, "originals")
AUSGEBLENDET = "_ausgeblendet"
TOOLS = os.path.dirname(os.path.abspath(__file__))
BUILD_GALLERY = os.path.join(TOOLS, "build-gallery.py")
BUILD_PAGES   = os.path.join(TOOLS, "build-pages.py")
SERVE         = os.path.join(TOOLS, "serve.py")
PORT = 8000
BILDTYPEN = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")   # wie build-gallery.py

PAPER, PAPER_ALT, INK, INK_SOFT, LINE, BLUE = (
    "#edede6", "#e2e3da", "#191c1f", "#565b5e", "#c7cabf", "#2b4c7e")
VORSCHAU = 640
DATUM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def cent(usd, stellen=2):
    """0.00021 USD -> '0,021' (Cent, mit Dezimalkomma)"""
    return f"{usd * 100:.{stellen}f}".replace(".", ",")


class Tagger(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bilder verschlagworten")
        self.configure(bg=PAPER)
        self.minsize(1080, 720)

        with open(DATA, encoding="utf-8") as fh:
            self.daten = json.load(fh)
        self.tags_def = self.daten.setdefault("tags", {})
        self.alle = self.daten.get("photos", [])
        if not self.alle:
            messagebox.showerror("Keine Bilder",
                                 "photos.json ist leer.\n\n"
                                 "Zuerst:  python3 tools/build-gallery.py")
            self.destroy()
            return

        self.nur_offene = tk.BooleanVar(value=False)
        self.gesetzt    = []            # Tags des aktuellen Bildes, wie im Tag-Feld
        self.treffer    = []            # Eintraege der Vorschlagsliste: (kennung oder None, text)
        self.idx        = 0
        self.foto       = None          # haelt die Referenz aufs Bild
        self.schmutzig  = False
        self.ki         = {}            # datei -> letzter KI-Vorschlag
        self.ki_kosten  = 0.0
        self.ki_laeuft  = False
        self.laeuft     = False         # Build-Prozess aktiv
        self.server     = None          # von uns gestarteter Vorschau-Server
        self.protokoll  = None

        self._bauen()
        self._liste_aktualisieren()
        self._anzeigen()

        self.protocol("WM_DELETE_WINDOW", self._beenden)
        self.bind("<Control-s>", lambda e: self._speichern(sichtbar=True))
        self.bind("<Control-d>", lambda e: self._uebernehmen())
        self.bind("<Next>",      lambda e: self._blaettern(1))
        self.bind("<Prior>",     lambda e: self._blaettern(-1))
        self.bind("<Alt-Right>", lambda e: self._blaettern(1))
        self.bind("<Alt-Left>",  lambda e: self._blaettern(-1))
        self.bind("<Control-k>", lambda e: self._ki_vorschlag())

    # ------------------------------------------------------------ Aufbau ---
    def _bauen(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".",             background=PAPER, foreground=INK)
        st.configure("TFrame",        background=PAPER)
        st.configure("Card.TFrame",   background=PAPER_ALT)
        st.configure("TLabel",        background=PAPER, foreground=INK)
        st.configure("Hint.TLabel",   background=PAPER, foreground=INK_SOFT,
                     font=("TkDefaultFont", 9))
        st.configure("Head.TLabel",   background=PAPER, foreground=BLUE,
                     font=("TkDefaultFont", 9, "bold"))
        st.configure("Orig.TLabel",   background=PAPER, foreground=INK_SOFT,
                     font=("TkDefaultFont", 8))
        st.configure("Geaendert.TLabel", background=PAPER, foreground="#a03d18",
                     font=("TkDefaultFont", 8, "bold"))
        st.configure("Dirty.TLabel",  background=PAPER, foreground="#a03d18",
                     font=("TkDefaultFont", 9, "bold"))
        st.configure("TCheckbutton",  background=PAPER)
        st.configure("KI.TCheckbutton", background=PAPER, foreground=BLUE)
        st.configure("TButton",       padding=5)
        st.configure("Leiste.TFrame", background=PAPER_ALT)

        leiste = ttk.Frame(self, style="Leiste.TFrame", padding=(14, 8))
        leiste.pack(fill="x")
        ttk.Button(leiste, text="Bilder hinzufügen …", command=self._bilder_hinzufuegen).pack(side="left")
        ttk.Button(leiste, text="Galerie bauen", command=self._galerie_bauen).pack(side="left", padx=6)
        ttk.Button(leiste, text="Vorschau im Browser", command=self._vorschau).pack(side="left")
        ttk.Button(leiste, text="KI-Einstellungen …", command=self._ki_einstellungen).pack(side="right")
        ttk.Button(leiste, text="KI für alle ohne Tags …", command=self._ki_alle).pack(side="right", padx=6)

        kopf = ttk.Frame(self, padding=(14, 12, 14, 6))
        kopf.pack(fill="x")
        self.lbl_fortschritt = ttk.Label(kopf, text="", font=("TkDefaultFont", 11, "bold"))
        self.lbl_fortschritt.pack(side="left")
        ttk.Checkbutton(kopf, text="nur unvollständige", variable=self.nur_offene,
                        command=self._filter_umschalten).pack(side="right")
        self.lbl_status = ttk.Label(kopf, text="", style="Hint.TLabel")
        self.lbl_status.pack(side="right", padx=14)
        self.lbl_dirty = ttk.Label(kopf, text="", style="Dirty.TLabel")
        self.lbl_dirty.pack(side="right")

        koerper = ttk.Frame(self, padding=(14, 0, 14, 8))
        koerper.pack(fill="both", expand=True)

        # links: Vorschau
        links = ttk.Frame(koerper, style="Card.TFrame", padding=8)
        links.pack(side="left", fill="both")
        self.lbl_bild = tk.Label(links, bg=PAPER_ALT, bd=0)
        self.lbl_bild.pack()
        self.lbl_datei = ttk.Label(links, text="", style="Hint.TLabel",
                                   background=PAPER_ALT, wraplength=VORSCHAU)
        self.lbl_datei.pack(pady=(8, 0))
        self.lbl_exif = ttk.Label(links, text="", style="Hint.TLabel",
                                  background=PAPER_ALT, wraplength=VORSCHAU)
        self.lbl_exif.pack(pady=(2, 0))

        # rechts: Felder
        rechts = ttk.Frame(koerper, padding=(16, 0, 0, 0))
        rechts.pack(side="left", fill="both", expand=True)

        def kopfzeile(text, pady=(10, 2)):
            ttk.Label(rechts, text=text, style="Head.TLabel").pack(anchor="w", pady=pady)

        kopfzeile("DATUM  (JJJJ-MM-TT)", (0, 2))
        f_datum = ttk.Frame(rechts)
        f_datum.pack(anchor="w", fill="x")
        self.e_datum = ttk.Entry(f_datum, width=20)
        self.e_datum.pack(side="left")
        self.lbl_datum_orig = ttk.Label(f_datum, text="", style="Orig.TLabel")
        self.lbl_datum_orig.pack(side="left", padx=(8, 4))
        self.btn_datum_reset = ttk.Button(f_datum, text="↺", width=3,
                                          command=self._datum_zuruecksetzen)
        self.e_datum.bind("<KeyRelease>", lambda e: self._hinweise_aktualisieren())

        kopfzeile("ORT")
        self.cb_ort = ttk.Combobox(rechts, width=38, values=[])
        self.cb_ort.pack(anchor="w")

        kopfzeile("KAMERA  (aus EXIF, überschreibbar)")
        f_kamera = ttk.Frame(rechts)
        f_kamera.pack(anchor="w", fill="x")
        self.e_kamera = ttk.Entry(f_kamera, width=30)
        self.e_kamera.pack(side="left")
        self.lbl_kamera_orig = ttk.Label(f_kamera, text="", style="Orig.TLabel")
        self.lbl_kamera_orig.pack(side="left", padx=(8, 4))
        self.btn_kamera_reset = ttk.Button(f_kamera, text="↺", width=3,
                                           command=self._kamera_zuruecksetzen)
        self.e_kamera.bind("<KeyRelease>", lambda e: self._hinweise_aktualisieren())

        f_tagkopf = ttk.Frame(rechts)
        f_tagkopf.pack(anchor="w", fill="x", pady=(10, 2))
        ttk.Label(f_tagkopf, text="TAGS  (tippen · Tab/Enter übernimmt · ✦ = KI)",
                  style="Head.TLabel").pack(side="left")
        ttk.Button(f_tagkopf, text="Tags verwalten …", command=self._tags_verwalten).pack(side="right")
        self.btn_ki = ttk.Button(f_tagkopf, text="✦ KI-Vorschlag  (Strg+K)", command=self._ki_vorschlag)
        self.btn_ki.pack(side="right", padx=6)

        # Tag-Feld: gesetzte Tags als Kaestchen mit x, dahinter das Eingabefeld.
        # Ein Text-Widget bricht die eingebetteten Kaestchen von selbst um.
        self.t_tags = tk.Text(rechts, height=3, width=52, wrap="char", bg="white", fg=INK,
                              relief="solid", bd=1, highlightthickness=0, padx=4, pady=4,
                              cursor="xterm", spacing1=2, spacing3=2)
        self.t_tags.pack(anchor="w", fill="x")
        self.t_tags.bind("<Button-1>", lambda e: (self.e_tag.focus_set(), "break")[1])
        self.t_tags.bind("<Key>", lambda e: "break")
        self.e_tag = tk.Entry(self.t_tags, width=22, relief="flat", bd=0, bg="white", fg=INK,
                              insertbackground=INK, highlightthickness=0)
        self.t_tags.window_create("end", window=self.e_tag, padx=2)
        self.e_tag.bind("<KeyRelease>", self._tag_tippen)
        self.e_tag.bind("<Tab>",        self._tag_bestaetigen)
        self.e_tag.bind("<Return>",     self._tag_bestaetigen)
        self.e_tag.bind("<Down>",       lambda e: self._treffer_wandern(1))
        self.e_tag.bind("<Up>",         lambda e: self._treffer_wandern(-1))
        self.e_tag.bind("<Escape>",     lambda e: self._treffer_schliessen())
        self.e_tag.bind("<BackSpace>",  self._tag_ruecktaste)
        self.e_tag.bind("<FocusOut>",   lambda e: self.after(150, self._treffer_schliessen))

        # Vorschlagsliste schwebt unter dem Tag-Feld (place statt pack)
        self.lb_treffer = tk.Listbox(self, height=6, bg="white", fg=INK, relief="solid", bd=1,
                                     highlightthickness=0, activestyle="none", exportselection=False,
                                     selectbackground=BLUE, selectforeground=PAPER)
        self.lb_treffer.bind("<ButtonRelease-1>", lambda e: self._tag_bestaetigen())

        self.f_ki_neu = ttk.Frame(rechts)
        self.f_ki_neu.pack(anchor="w", fill="x")

        kopfzeile("BESCHREIBUNG DEUTSCH  (optional)")
        self.t_de = tk.Text(rechts, height=2, width=52, wrap="word",
                            bg="white", fg=INK, relief="solid", bd=1,
                            highlightthickness=0, insertbackground=INK)
        self.t_de.pack(anchor="w", fill="x")
        self.t_de.bind("<KeyRelease>", lambda e: self._rueckfall_anzeigen())

        kopfzeile("BESCHREIBUNG ENGLISCH  (optional)")
        self.t_en = tk.Text(rechts, height=2, width=52, wrap="word",
                            bg="white", fg=INK, relief="solid", bd=1,
                            highlightthickness=0, insertbackground=INK)
        self.t_en.pack(anchor="w", fill="x")

        self.lbl_rueckfall = ttk.Label(rechts, text="", style="Orig.TLabel", wraplength=430)
        self.lbl_rueckfall.pack(anchor="w", pady=(4, 0))

        fuss = ttk.Frame(self, padding=(14, 4, 14, 14))
        fuss.pack(fill="x")
        ttk.Button(fuss, text="‹ Zurück",  command=lambda: self._blaettern(-1)).pack(side="left")
        ttk.Button(fuss, text="Weiter ›",  command=lambda: self._blaettern(1)).pack(side="left", padx=6)
        ttk.Button(fuss, text="Ort, Tags, Text übernehmen  (Strg+D)",
                   command=self._uebernehmen).pack(side="left", padx=(18, 0))
        ttk.Button(fuss, text="Nächstes unvollständiges",
                   command=self._naechstes_offenes).pack(side="left", padx=6)
        ttk.Button(fuss, text="Bild entfernen …",
                   command=self._bild_entfernen).pack(side="left", padx=(18, 0))
        ttk.Button(fuss, text="Speichern  (Strg+S)",
                   command=lambda: self._speichern(sichtbar=True)).pack(side="right")

    # ------------------------------------------------------------- Daten ---
    def _unvollstaendig(self, p):
        return (not all(p.get(f) for f in ("datum", "ort"))
                or not p.get("tags")
                or not p.get("kamera"))

    def _liste_aktualisieren(self):
        self.liste = [p for p in self.alle
                      if not self.nur_offene.get() or self._unvollstaendig(p)]
        if not self.liste:
            self.liste = list(self.alle)
        self.idx = min(self.idx, len(self.liste) - 1)

    def _orte(self):
        return sorted({p.get("ort", "") for p in self.alle if p.get("ort")})

    def _tag_haeufigkeit(self):
        zahl = {}
        for p in self.alle:
            for t in p.get("tags", []):
                zahl[t] = zahl.get(t, 0) + 1
        for t in self.tags_def:
            zahl.setdefault(t, 0)
        # haeufigste zuerst, bei Gleichstand alphabetisch
        return sorted(zahl, key=lambda t: (-zahl[t], t)), zahl

    # ---------------------------------------------------------- Anzeigen ---
    def _anzeigen(self):
        p = self.liste[self.idx]
        self.lbl_fortschritt.config(
            text=f"Bild {self.idx + 1} von {len(self.liste)}"
                 + ("   ·   gefiltert" if self.nur_offene.get() else ""))

        pfad = os.path.join(THUMB, os.path.splitext(p["datei"])[0] + ".webp")
        if os.path.exists(pfad):
            im = Image.open(pfad)
            im.thumbnail((VORSCHAU, VORSCHAU), Image.LANCZOS)
            self.foto = ImageTk.PhotoImage(im)
            self.lbl_bild.config(image=self.foto, text="")
        else:
            self.foto = None
            self.lbl_bild.config(image="", text="(keine Vorschau —\nbuild-gallery.py laufen lassen)",
                                 width=60, height=20, fg=INK_SOFT)

        self.lbl_datei.config(text=p["datei"])
        ex = p.get("exif", {})
        teile = [ex.get(k, "") for k in ("objektiv", "brennweite", "blende", "belichtung")]
        if ex.get("iso"):
            teile.append("ISO " + ex["iso"])
        self.lbl_exif.config(text="  ·  ".join(t for t in teile if t) or "keine EXIF-Daten")

        self.e_datum.delete(0, "end");  self.e_datum.insert(0, p.get("datum", ""))
        self.cb_ort.config(values=self._orte())
        self.cb_ort.set(p.get("ort", ""))
        self.e_kamera.delete(0, "end"); self.e_kamera.insert(0, p.get("kamera", ""))

        self.t_de.delete("1.0", "end"); self.t_de.insert("1.0", p.get("de", ""))
        self.t_en.delete("1.0", "end"); self.t_en.insert("1.0", p.get("en", ""))
        self._tags_zeichnen(p)
        self._hinweise_aktualisieren()
        self._rueckfall_anzeigen()
        self.lbl_status.config(text="")

    def _rueckfall_anzeigen(self):
        """Zeigt, welcher Text ohne eigene Beschreibung verwendet wird."""
        if self.t_de.get("1.0", "end").strip():
            self.lbl_rueckfall.config(text="")
            return
        p = self.liste[self.idx]
        teile = [", ".join(self.tags_def.get(t, {}).get("de", t) for t in p.get("tags", []))]
        if p.get("ort"):
            teile.append(p["ort"])
        if self.e_datum.get().strip():
            j, m, t = (self.e_datum.get().strip().split("-") + ["", "", ""])[:3]
            if j and m and t:
                teile.append(f"{t}.{m}.{j}")
        text = " · ".join(x for x in teile if x)
        self.lbl_rueckfall.config(
            text=f"ohne Beschreibung wird verwendet:  {text}" if text else "")

    def _hinweise_aktualisieren(self):
        """Zeigt neben Datum und Kamera, was in der Datei steht, und ob es abweicht."""
        ex = self.liste[self.idx].get("exif", {})
        for feld, eingabe, label, knopf in (
                ("datum",  self.e_datum,  self.lbl_datum_orig,  self.btn_datum_reset),
                ("kamera", self.e_kamera, self.lbl_kamera_orig, self.btn_kamera_reset)):
            original = ex.get(feld, "")
            if not original:
                label.config(text="kein EXIF-Wert", style="Orig.TLabel")
                knopf.pack_forget()
            elif eingabe.get().strip() == original:
                label.config(text="= EXIF", style="Orig.TLabel")
                knopf.pack_forget()
            else:
                label.config(text=f"geändert · EXIF: {original}", style="Geaendert.TLabel")
                knopf.pack(side="left")

    def _datum_zuruecksetzen(self):
        original = self.liste[self.idx].get("exif", {}).get("datum", "")
        self.e_datum.delete(0, "end"); self.e_datum.insert(0, original)
        self._hinweise_aktualisieren()
        self.lbl_status.config(text="Datum auf EXIF-Wert zurückgesetzt")

    def _kamera_zuruecksetzen(self):
        original = self.liste[self.idx].get("exif", {}).get("kamera", "")
        self.e_kamera.delete(0, "end"); self.e_kamera.insert(0, original)
        self._hinweise_aktualisieren()
        self.lbl_status.config(text="Kamera auf EXIF-Wert zurückgesetzt")

    def _tags_zeichnen(self, p, gesetzt=None):
        """Tag-Feld neu fuellen. gesetzt: Kennungen (Standard: die des Bildes)."""
        self.gesetzt = list(p.get("tags", []) if gesetzt is None else gesetzt)
        self._chips_zeichnen()
        self.e_tag.delete(0, "end")
        self._treffer_schliessen()
        self._ki_neu_zeichnen(p)

    def _chips_zeichnen(self):
        # nur die Kaestchen vor dem Eingabefeld loeschen — das Feld selbst
        # wuerde Tk beim Loeschen aus dem Text-Widget mit zerstoeren
        self.t_tags.delete("1.0", str(self.e_tag))
        ki = set(self.ki.get(self.liste[self.idx]["datei"], {}).get("tags", []))
        for t in self.gesetzt:
            von_ki = t in ki
            chip = tk.Frame(self.t_tags, bg=PAPER_ALT, highlightthickness=1,
                            highlightbackground=BLUE if von_ki else LINE)
            name = self.tags_def.get(t, {}).get("de", t)
            tk.Label(chip, text=("✦ " if von_ki else "") + name, bg=PAPER_ALT,
                     fg=BLUE if von_ki else INK, padx=5, pady=1).pack(side="left")
            x = tk.Label(chip, text="×", bg=PAPER_ALT, fg=INK_SOFT, padx=4, cursor="hand2")
            x.pack(side="left")
            x.bind("<Button-1>", lambda e, t=t: self._tag_entfernen(t))
            self.t_tags.window_create(str(self.e_tag), window=chip, padx=2, pady=1)

    def _tag_setzen(self, t):
        if t not in self.gesetzt:
            self.gesetzt.append(t)
            self._chips_zeichnen()
        self.e_tag.delete(0, "end")
        self._treffer_schliessen()
        self.e_tag.focus_set()

    def _tag_entfernen(self, t):
        if t in self.gesetzt:
            self.gesetzt.remove(t)
            self._chips_zeichnen()
        self.e_tag.focus_set()

    # --- Vorschlagsliste beim Tippen
    def _tag_tippen(self, e):
        if e.keysym in ("Tab", "Return", "Up", "Down", "Escape", "BackSpace") and e.keysym != "BackSpace":
            return
        text = self.e_tag.get().strip()
        if not text:
            self._treffer_schliessen()
            return
        q = text.lower()
        _, zahl = self._tag_haeufigkeit()
        anfang, mitte = [], []
        for t, v in self.tags_def.items():
            if t in self.gesetzt:
                continue
            name = v.get("de", t)
            n, en = name.lower(), v.get("en", "").lower()
            if n.startswith(q):
                anfang.append(t)
            elif q in n or en.startswith(q):
                mitte.append(t)
        sortiert = lambda l: sorted(l, key=lambda t: (-zahl.get(t, 0), self.tags_def[t].get("de", t)))
        self.treffer = [(t, f"{self.tags_def[t].get('de', t)}   ({zahl.get(t, 0)})")
                        for t in (sortiert(anfang) + sortiert(mitte))[:8]]
        if not any(self.tags_def[t].get("de", t).lower() == q for t, _ in self.treffer) \
                and ki_tags.kennung(text) not in self.tags_def:
            self.treffer.append((None, f"+ neuen Tag „{text}“ anlegen"))
        self.lb_treffer.delete(0, "end")
        for _, zeile in self.treffer:
            self.lb_treffer.insert("end", zeile)
        self.lb_treffer.selection_clear(0, "end")
        self.lb_treffer.selection_set(0)
        self.lb_treffer.config(height=len(self.treffer))
        x = self.t_tags.winfo_rootx() - self.winfo_rootx()
        y = self.t_tags.winfo_rooty() - self.winfo_rooty() + self.t_tags.winfo_height()
        self.lb_treffer.place(x=x, y=y, width=self.t_tags.winfo_width())
        self.lb_treffer.lift()

    def _treffer_wandern(self, schritt):
        if not self.lb_treffer.winfo_ismapped():
            return "break"
        sel = self.lb_treffer.curselection()
        i = max(0, min(len(self.treffer) - 1, (sel[0] if sel else -1) + schritt))
        self.lb_treffer.selection_clear(0, "end")
        self.lb_treffer.selection_set(i)
        self.lb_treffer.see(i)
        return "break"

    def _treffer_schliessen(self):
        self.lb_treffer.place_forget()

    def _tag_bestaetigen(self, e=None):
        """Tab/Enter/Klick: markierten Vorschlag uebernehmen oder neuen Tag anlegen."""
        text = self.e_tag.get().strip()
        if not text:
            return None if e is not None and e.keysym == "Tab" else "break"   # leeres Feld: Tab springt weiter
        sel = self.lb_treffer.curselection() if self.lb_treffer.winfo_ismapped() else ()
        if sel and self.treffer[sel[0]][0]:
            self._tag_setzen(self.treffer[sel[0]][0])
            return "break"
        k = ki_tags.kennung(text)
        if k in self.tags_def:                       # exakt getippt
            self._tag_setzen(k)
            return "break"
        self._treffer_schliessen()
        self._tag_anlegen({"de": text[:1].upper() + text[1:], "en": ""})
        return "break"

    def _tag_ruecktaste(self, e):
        # Ruecktaste im leeren Feld entfernt das letzte Kaestchen
        if not self.e_tag.get() and self.gesetzt:
            self._tag_entfernen(self.gesetzt[-1])
            return "break"
        self.after(1, lambda: self._tag_tippen(e))
        return None

    def _ki_neu_zeichnen(self, p):
        """Neue Tags, die die KI vorschlaegt: als Knopf, angelegt erst beim Klick."""
        for w in self.f_ki_neu.winfo_children():
            w.destroy()
        offen = [n for n in self.ki.get(p["datei"], {}).get("neu", [])
                 if ki_tags.kennung(n["de"]) not in self.tags_def]
        if not offen:
            return
        ttk.Label(self.f_ki_neu, text="✦ neu vorgeschlagen:", style="Hint.TLabel").pack(
            side="left", pady=(6, 0))
        for n in offen:
            ttk.Button(self.f_ki_neu, text=f"+ {n['de']}",
                       command=lambda n=n: self._tag_anlegen(vorgabe=n)).pack(
                side="left", padx=(6, 0), pady=(6, 0))

    # --------------------------------------------------------- Bearbeiten --
    def _felder_uebernehmen(self):
        """Eingaben ins Datenmodell schreiben. Gibt False bei ungueltigem Datum."""
        p = self.liste[self.idx]
        datum = self.e_datum.get().strip()
        if datum and not DATUM_RE.match(datum):
            messagebox.showwarning("Datum ungültig",
                                   f"'{datum}' passt nicht ins Format JJJJ-MM-TT.\n"
                                   "Beispiel: 2026-08-15")
            return False
        neu = {
            "datum":  datum,
            "ort":    self.cb_ort.get().strip(),
            "tags":   sorted(self.gesetzt),
            "kamera": self.e_kamera.get().strip(),
            "de":     self.t_de.get("1.0", "end").strip(),
            "en":     self.t_en.get("1.0", "end").strip(),
        }
        if any(p.get(k) != v for k, v in neu.items()):
            p.update(neu)
            self.schmutzig = True
            self._dirty_anzeigen()
        return True

    def _dirty_anzeigen(self):
        self.lbl_dirty.config(text="● ungespeichert" if self.schmutzig else "")

    def _blaettern(self, schritt):
        # Aenderungen wandern ins Modell, auf die Platte erst beim Speichern
        if not self._felder_uebernehmen():
            return
        self.idx = (self.idx + schritt) % len(self.liste)
        self._anzeigen()

    def _naechstes_offenes(self):
        if not self._felder_uebernehmen():
            return
        for n in range(1, len(self.liste) + 1):
            k = (self.idx + n) % len(self.liste)
            if self._unvollstaendig(self.liste[k]):
                self.idx = k
                self._anzeigen()
                return
        messagebox.showinfo("Fertig", "Alle Bilder sind vollständig beschrieben.")

    def _uebernehmen(self):
        """Ort, Tags und Beschreibung vom vorher bearbeiteten Bild kopieren.

        Das Datum bleibt bewusst unangetastet — es kommt aus dem EXIF des
        jeweiligen Bildes und waere sonst mit dem des Vorgaengers ueberschrieben.
        """
        if self.idx == 0:
            self.lbl_status.config(text="kein vorheriges Bild")
            return
        vor = self.liste[self.idx - 1]
        self.cb_ort.set(vor.get("ort", ""))
        self.gesetzt = list(vor.get("tags", []))
        self._chips_zeichnen()
        self.t_de.delete("1.0", "end"); self.t_de.insert("1.0", vor.get("de", ""))
        self.t_en.delete("1.0", "end"); self.t_en.insert("1.0", vor.get("en", ""))
        self._rueckfall_anzeigen()
        self.lbl_status.config(text="Ort, Tags und Text übernommen — Datum bleibt")

    def _bild_entfernen(self):
        """Bild von der Seite nehmen — wahlweise auch das Original loeschen.

        Nur den Eintrag zu entfernen reicht nicht: build-gallery.py liest den
        Ordner originals/ und wuerde das Bild beim naechsten Lauf wieder
        aufnehmen. Deshalb wandert die Datei nach originals/_ausgeblendet/
        (Unterordner werden beim Bauen uebersprungen) oder wird geloescht.
        """
        p = self.liste[self.idx]
        datei = p["datei"]

        dlg = tk.Toplevel(self)
        dlg.title("Bild entfernen")
        dlg.configure(bg=PAPER)
        dlg.transient(self); dlg.grab_set()

        ttk.Label(dlg, text=datei, font=("TkDefaultFont", 10, "bold")).pack(
            padx=18, pady=(16, 4), anchor="w")
        ttk.Label(dlg, text="Was soll damit passieren?", style="Hint.TLabel").pack(
            padx=18, anchor="w")

        wahl = tk.StringVar(value="ausblenden")
        rahmen = ttk.Frame(dlg); rahmen.pack(padx=18, pady=(12, 4), anchor="w")
        ttk.Radiobutton(rahmen, variable=wahl, value="ausblenden",
                        text="Nur von der Seite nehmen").pack(anchor="w")
        ttk.Label(rahmen, text=f"Original wandert nach originals/{AUSGEBLENDET}/ und\n"
                               "kann jederzeit zurückgeholt werden.",
                  style="Hint.TLabel").pack(anchor="w", padx=(22, 0))
        ttk.Radiobutton(rahmen, variable=wahl, value="loeschen",
                        text="Endgültig löschen").pack(anchor="w", pady=(10, 0))
        ttk.Label(rahmen, text="Originaldatei wird von der Platte entfernt.\n"
                               "Das lässt sich nicht rückgängig machen.",
                  style="Geaendert.TLabel").pack(anchor="w", padx=(22, 0))

        def ausfuehren():
            endgueltig = wahl.get() == "loeschen"
            if endgueltig and not messagebox.askyesno(
                    "Endgültig löschen",
                    f"{datei} wirklich von der Platte löschen?\n\n"
                    "Es gibt kein Zurück.", parent=dlg):
                return
            dlg.destroy()
            self._entfernen_ausfuehren(p, endgueltig)

        knopf = ttk.Frame(dlg); knopf.pack(padx=18, pady=(14, 16), anchor="w")
        ttk.Button(knopf, text="Ausführen", command=ausfuehren).pack(side="left")
        ttk.Button(knopf, text="Abbrechen", command=dlg.destroy).pack(side="left", padx=6)

    def _entfernen_ausfuehren(self, p, endgueltig):
        datei = p["datei"]
        stamm = os.path.splitext(datei)[0]
        quelle = os.path.join(ORIG, datei)
        fehler = []

        try:
            if endgueltig:
                if os.path.exists(quelle):
                    os.remove(quelle)
            else:
                ziel_ordner = os.path.join(ORIG, AUSGEBLENDET)
                os.makedirs(ziel_ordner, exist_ok=True)
                if os.path.exists(quelle):
                    ziel = os.path.join(ziel_ordner, datei)
                    n = 1
                    while os.path.exists(ziel):     # Namenskollision vermeiden
                        ziel = os.path.join(ziel_ordner, f"{stamm}_{n}{os.path.splitext(datei)[1]}")
                        n += 1
                    os.replace(quelle, ziel)
        except OSError as e:
            fehler.append(str(e))

        for ordner in (THUMB, LARGE):               # Ableitungen immer weg
            pfad = os.path.join(ordner, stamm + ".webp")
            if os.path.exists(pfad):
                try:
                    os.remove(pfad)
                except OSError as e:
                    fehler.append(str(e))

        if fehler:
            messagebox.showerror("Fehler beim Entfernen", "\n".join(fehler))
            return

        self.alle.remove(p)
        if not self.alle:
            messagebox.showinfo("Leer", "Es sind keine Bilder mehr übrig.")
            self.schmutzig = True
            self._speichern()
            self.destroy()
            return

        self.schmutzig = True
        self._dirty_anzeigen()
        self._liste_aktualisieren()
        self.idx = min(self.idx, len(self.liste) - 1)
        self._anzeigen()
        self.lbl_status.config(
            text=f"{datei} " + ("gelöscht" if endgueltig else "ausgeblendet")
                 + " — noch nicht gespeichert")

    def _tags_verwalten(self):
        """Tags umbenennen, ihre Bezeichnungen aendern oder sie ganz loeschen."""
        self._felder_uebernehmen()

        dlg = tk.Toplevel(self)
        dlg.title("Tags verwalten")
        dlg.configure(bg=PAPER)
        dlg.transient(self)
        dlg.grab_set()
        dlg.minsize(560, 380)

        links = ttk.Frame(dlg, padding=(12, 12, 6, 12)); links.pack(side="left", fill="both", expand=True)
        ttk.Label(links, text="TAG WÄHLEN", style="Head.TLabel").pack(anchor="w")
        leiste = ttk.Frame(links); leiste.pack(fill="both", expand=True, pady=(4, 0))
        liste = tk.Listbox(leiste, width=32, height=16, exportselection=False,
                           bg="white", fg=INK, relief="solid", bd=1, highlightthickness=0)
        roller = ttk.Scrollbar(leiste, orient="vertical", command=liste.yview)
        liste.configure(yscrollcommand=roller.set)
        liste.pack(side="left", fill="both", expand=True); roller.pack(side="left", fill="y")

        rechts = ttk.Frame(dlg, padding=(6, 12, 12, 12)); rechts.pack(side="left", fill="both")
        ttk.Label(rechts, text="KENNUNG  (intern)", style="Head.TLabel").pack(anchor="w")
        e_id = ttk.Entry(rechts, width=28); e_id.pack(anchor="w")
        ttk.Label(rechts, text="BEZEICHNUNG DEUTSCH", style="Head.TLabel").pack(anchor="w", pady=(10, 0))
        e_de = ttk.Entry(rechts, width=28); e_de.pack(anchor="w")
        ttk.Label(rechts, text="BEZEICHNUNG ENGLISCH", style="Head.TLabel").pack(anchor="w", pady=(10, 0))
        e_en = ttk.Entry(rechts, width=28); e_en.pack(anchor="w")
        lbl_nutzung = ttk.Label(rechts, text="", style="Hint.TLabel"); lbl_nutzung.pack(anchor="w", pady=(10, 0))
        lbl_meldung = ttk.Label(rechts, text="", style="Hint.TLabel", wraplength=220)
        lbl_meldung.pack(anchor="w", pady=(6, 0))

        zustand = {"id": None}

        def fuellen(auswahl=None):
            reihen, zahl = self._tag_haeufigkeit()
            liste.delete(0, "end")
            for t in reihen:
                liste.insert("end", f"{self.tags_def.get(t, {}).get('de', t)}   ({zahl[t]})")
            zustand["ids"] = reihen
            if auswahl in reihen:
                i = reihen.index(auswahl)
                liste.selection_clear(0, "end"); liste.selection_set(i); liste.see(i)
                waehlen()
            else:
                zustand["id"] = None
                for e in (e_id, e_de, e_en): e.delete(0, "end")
                lbl_nutzung.config(text="")

        def waehlen(_=None):
            sel = liste.curselection()
            if not sel: return
            t = zustand["ids"][sel[0]]
            zustand["id"] = t
            _, zahl = self._tag_haeufigkeit()
            e_id.delete(0, "end"); e_id.insert(0, t)
            e_de.delete(0, "end"); e_de.insert(0, self.tags_def.get(t, {}).get("de", t))
            e_en.delete(0, "end"); e_en.insert(0, self.tags_def.get(t, {}).get("en", t))
            lbl_nutzung.config(text=f"verwendet bei {zahl[t]} Bild(ern)")
            lbl_meldung.config(text="")

        liste.bind("<<ListboxSelect>>", waehlen)

        def uebernehmen():
            alt = zustand["id"]
            if not alt: return
            neu = re.sub(r"[^a-z0-9]+", "", e_id.get().strip().lower()
                         .replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss"))
            if not neu:
                lbl_meldung.config(text="Kennung darf nicht leer sein."); return
            if neu != alt and neu in self.tags_def:
                lbl_meldung.config(text=f"'{neu}' gibt es bereits."); return

            self.tags_def[alt] = {"de": e_de.get().strip() or alt,
                                  "en": e_en.get().strip() or e_de.get().strip() or alt}
            if neu != alt:                      # Kennung umbenennen: ueberall nachziehen
                self.tags_def[neu] = self.tags_def.pop(alt)
                for p in self.alle:
                    p["tags"] = [neu if t == alt else t for t in p.get("tags", [])]
            self.schmutzig = True
            self._dirty_anzeigen()
            fuellen(neu)
            self._anzeigen()
            lbl_meldung.config(text="übernommen — noch nicht gespeichert")

        def loeschen():
            t = zustand["id"]
            if not t: return
            betroffen = [p for p in self.alle if t in p.get("tags", [])]
            name = self.tags_def.get(t, {}).get("de", t)
            if not messagebox.askyesno(
                    "Tag löschen",
                    f"'{name}' wirklich löschen?\n\n"
                    f"Der Tag wird bei {len(betroffen)} Bild(ern) entfernt.\n"
                    "Die Bilder selbst bleiben unverändert.",
                    parent=dlg):
                return
            self.tags_def.pop(t, None)
            for p in betroffen:
                p["tags"] = [x for x in p["tags"] if x != t]
            self.schmutzig = True
            self._dirty_anzeigen()
            fuellen()
            self._anzeigen()
            lbl_meldung.config(text=f"'{name}' gelöscht — noch nicht gespeichert")

        knoepfe = ttk.Frame(rechts); knoepfe.pack(anchor="w", pady=(16, 0))
        ttk.Button(knoepfe, text="Übernehmen", command=uebernehmen).pack(side="left")
        ttk.Button(knoepfe, text="Löschen", command=loeschen).pack(side="left", padx=6)
        ttk.Button(rechts, text="Schließen", command=dlg.destroy).pack(anchor="w", pady=(20, 0))

        fuellen()
        if zustand.get("ids"):
            liste.selection_set(0); waehlen()

    def _tag_anlegen(self, vorgabe):
        """Neuen Tag anlegen und setzen. vorgabe = {"de", "en"} — getippt oder von der KI."""
        roh = vorgabe["de"].strip()
        kennung = ki_tags.kennung(roh)
        if not kennung:
            return
        if kennung in self.tags_def:
            self._tag_setzen(kennung)
            return

        dlg = tk.Toplevel(self)
        dlg.title("Neuer Tag")
        dlg.configure(bg=PAPER)
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text=f"Kennung:  {kennung}").pack(padx=16, pady=(14, 8), anchor="w")
        ttk.Label(dlg, text="Bezeichnung deutsch:").pack(padx=16, anchor="w")
        e_de = ttk.Entry(dlg, width=34); e_de.pack(padx=16, pady=(0, 8))
        e_de.insert(0, roh)
        ttk.Label(dlg, text="Bezeichnung englisch:").pack(padx=16, anchor="w")
        e_en = ttk.Entry(dlg, width=34); e_en.pack(padx=16, pady=(0, 12))
        e_en.insert(0, vorgabe.get("en", ""))

        def anlegen():
            de = e_de.get().strip() or kennung
            en = e_en.get().strip() or de
            self.tags_def[kennung] = {"de": de, "en": en}
            if not self._felder_uebernehmen():
                dlg.destroy()
                return
            self.liste[self.idx].setdefault("tags", []).append(kennung)
            self.schmutzig = True
            self._dirty_anzeigen()
            dlg.destroy()
            self._anzeigen()
            self.lbl_status.config(text=f"Tag '{de}' angelegt und gesetzt")

        ttk.Button(dlg, text="Anlegen", command=anlegen).pack(pady=(0, 14))
        e_en.bind("<Return>", lambda e: anlegen())
        e_de.bind("<Return>", lambda e: e_en.focus_set())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        # Deutsch steht meist schon da (getippt oder von der KI) -> gleich Englisch
        (e_en if not vorgabe.get("en") else e_de).focus_set()

    # --------------------------------------------------------- Speichern ---
    def _speichern(self, sichtbar=False):
        if sichtbar and not self._felder_uebernehmen():
            return
        self.daten["tags"]   = self.tags_def
        self.daten["photos"] = self.alle
        tmp = DATA + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.daten, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, DATA)          # atomar: ein Absturz zerlegt die Datei nicht
        self.schmutzig = False
        self._dirty_anzeigen()
        if sichtbar:
            offen = sum(1 for p in self.alle if self._unvollstaendig(p))
            self.lbl_status.config(
                text=f"gespeichert — noch {offen} unvollständig" if offen
                     else "gespeichert — alles vollständig")

    def _filter_umschalten(self):
        if not self._felder_uebernehmen():
            self.nur_offene.set(not self.nur_offene.get())
            return
        self.idx = 0
        self._liste_aktualisieren()
        self._anzeigen()

    # ------------------------------------------------------- KI-Vorschlaege --
    def _ki_einstellungen(self):
        cfg = ki_tags.konfig_laden()
        dlg = tk.Toplevel(self)
        dlg.title("KI-Einstellungen")
        dlg.configure(bg=PAPER)
        dlg.transient(self); dlg.grab_set()

        ttk.Label(dlg, text="OPENROUTER-SCHLÜSSEL", style="Head.TLabel").pack(padx=16, pady=(14, 2), anchor="w")
        e_key = ttk.Entry(dlg, width=52, show="•"); e_key.pack(padx=16, anchor="w")
        e_key.insert(0, cfg.get("api_key", ""))
        ttk.Label(dlg, text="Anlegen unter  openrouter.ai/keys  ·  gespeichert in\n" + ki_tags.KONFIG,
                  style="Orig.TLabel").pack(padx=16, pady=(2, 0), anchor="w")
        if os.environ.get("OPENROUTER_API_KEY"):
            ttk.Label(dlg, text="Hinweis: OPENROUTER_API_KEY ist gesetzt und hat Vorrang.",
                      style="Geaendert.TLabel").pack(padx=16, anchor="w")

        ttk.Label(dlg, text="MODELL", style="Head.TLabel").pack(padx=16, pady=(12, 2), anchor="w")
        cb = ttk.Combobox(dlg, width=40, values=ki_tags.MODELLE); cb.pack(padx=16, anchor="w")
        cb.set(cfg.get("modell") or ki_tags.STANDARD_MODELL)
        ttk.Label(dlg, text="Jedes Modell von openrouter.ai/models mit Bildeingabe geht.\n"
                            f"Standard: {ki_tags.STANDARD_MODELL} (rund 0,02 Cent pro Bild)",
                  style="Orig.TLabel").pack(padx=16, pady=(2, 0), anchor="w")

        def speichern():
            cfg["api_key"] = e_key.get().strip()
            cfg["modell"] = cb.get().strip() or ki_tags.STANDARD_MODELL
            ki_tags.konfig_speichern(cfg)
            dlg.destroy()
            self.lbl_status.config(text=f"KI-Einstellungen gespeichert · {cfg['modell']}")

        f = ttk.Frame(dlg); f.pack(padx=16, pady=(14, 16), anchor="w")
        ttk.Button(f, text="Speichern", command=speichern).pack(side="left")
        ttk.Button(f, text="Abbrechen", command=dlg.destroy).pack(side="left", padx=6)
        e_key.focus_set()

    def _ki_anfrage(self, p):
        """Laeuft im Hintergrund-Thread — hier keine Tk-Aufrufe."""
        bild = os.path.join(THUMB, os.path.splitext(p["datei"])[0] + ".webp")
        return ki_tags.vorschlagen(bild, dict(self.tags_def), p.get("ort", ""), p.get("exif"))

    def _ki_vorschlag(self):
        """KI-Vorschlag fuer das aktuelle Bild."""
        if self.ki_laeuft:
            self.lbl_status.config(text="KI arbeitet noch …")
            return
        p = self.liste[self.idx]
        self.ki_laeuft = True
        self.btn_ki.state(["disabled"])
        self.lbl_status.config(text="KI schaut sich das Bild an …")

        def arbeit():
            try:
                res = self._ki_anfrage(p)
                self.after(0, lambda: self._ki_einzeln_fertig(p, res, None))
            except ki_tags.KIFehler as e:
                self.after(0, lambda e=e: self._ki_einzeln_fertig(p, None, str(e)))
            except Exception as e:                       # nie still im Thread sterben
                self.after(0, lambda e=e: self._ki_einzeln_fertig(p, None, repr(e)))
        threading.Thread(target=arbeit, daemon=True).start()

    def _ki_einzeln_fertig(self, p, res, fehler):
        self.ki_laeuft = False
        self.btn_ki.state(["!disabled"])
        if fehler:
            self.lbl_status.config(text="KI-Vorschlag fehlgeschlagen")
            messagebox.showerror("KI-Vorschlag", fehler)
            return
        self._ki_merken(p, res)
        if p is self.liste[self.idx]:
            # Vorschlaege zu den angehakten Tags dazu — nie etwas abwaehlen
            gesetzt = self.gesetzt + [t for t in res["tags"] if t not in self.gesetzt]
            self._tags_zeichnen(p, gesetzt)
        else:                                            # inzwischen weitergeblaettert
            neu = sorted(set(p.get("tags", [])) | set(res["tags"]))
            if neu != p.get("tags"):
                p["tags"] = neu
                self.schmutzig = True
                self._dirty_anzeigen()
        self.lbl_status.config(text=self._ki_zusammenfassung(res))

    def _ki_merken(self, p, res):
        self.ki[p["datei"]] = res
        if res.get("kosten"):
            self.ki_kosten += res["kosten"]

    def _ki_zusammenfassung(self, res):
        teile = [f"KI: {len(res['tags'])} Tags"]
        if res["neu"]:
            teile.append(f"{len(res['neu'])} neue vorgeschlagen")
        if res.get("kosten") is not None:
            teile.append(f"{cent(res['kosten'], 3)} Cent · Sitzung {cent(self.ki_kosten)} Cent")
        return "  ·  ".join(teile) + "  —  bitte prüfen"

    def _ki_alle(self, ziel=None):
        """KI-Vorschlaege fuer mehrere Bilder. Ohne Angabe: alle ohne Tags."""
        if self.ki_laeuft:
            self.lbl_status.config(text="KI arbeitet noch …")
            return
        if not self._felder_uebernehmen():
            return
        if ziel is None:
            ziel = [p for p in self.alle if not p.get("tags")]
            if not ziel:
                messagebox.showinfo("KI-Vorschläge", "Alle Bilder haben schon Tags.\n\n"
                                    "Für ein einzelnes Bild: „✦ KI-Vorschlag“ (Strg+K).")
                return
        modell = ki_tags.konfig_laden().get("modell")
        if not messagebox.askyesno(
                "KI-Vorschläge",
                f"{len(ziel)} Bild(er) an {modell} schicken?\n\n"
                "Die vorgeschlagenen Tags werden gesetzt und mit ✦ markiert.\n"
                "Bitte danach durchsehen — gespeichert wird erst mit „Speichern“."):
            return
        self.ki_laeuft = True
        self.btn_ki.state(["disabled"])

        def arbeit():
            for n, p in enumerate(ziel, 1):
                self.after(0, lambda n=n: self.lbl_status.config(
                    text=f"KI: Bild {n} von {len(ziel)} …"))
                try:
                    res = self._ki_anfrage(p)
                except ki_tags.KIFehler as e:
                    self.after(0, lambda e=e, n=n: self._ki_stapel_ende(n - 1, len(ziel), str(e)))
                    return
                except Exception as e:
                    self.after(0, lambda e=e, n=n: self._ki_stapel_ende(n - 1, len(ziel), repr(e)))
                    return
                self.after(0, lambda p=p, res=res: self._ki_stapel_ergebnis(p, res))
            self.after(0, lambda: self._ki_stapel_ende(len(ziel), len(ziel), None))
        threading.Thread(target=arbeit, daemon=True).start()

    def _ki_stapel_ergebnis(self, p, res):
        self._ki_merken(p, res)
        aktuell = p is self.liste[self.idx]
        if aktuell:
            self._felder_uebernehmen()
        # nur ergaenzen — eigene Tags bleiben immer stehen
        neu = sorted(set(p.get("tags", [])) | set(res["tags"]))
        if neu != p.get("tags"):
            p["tags"] = neu
            self.schmutzig = True
            self._dirty_anzeigen()
        if aktuell:
            self._anzeigen()

    def _ki_stapel_ende(self, fertig, gesamt, fehler):
        self.ki_laeuft = False
        self.btn_ki.state(["!disabled"])
        kosten = f" · {cent(self.ki_kosten)} Cent in dieser Sitzung" if self.ki_kosten else ""
        self.lbl_status.config(text=f"KI: {fertig} von {gesamt} Bildern{kosten} — bitte prüfen, dann speichern")
        if fehler:
            messagebox.showerror("KI-Vorschläge", f"Abgebrochen nach {fertig} von {gesamt} Bildern.\n\n{fehler}")

    # ----------------------------------------------------- Werkzeugleiste --
    def _protokoll_fenster(self):
        if self.protokoll and self.protokoll.winfo_exists():
            self.protokoll.deiconify(); self.protokoll.lift()
            return self.protokoll
        dlg = tk.Toplevel(self)
        dlg.title("Protokoll")
        dlg.configure(bg=PAPER)
        dlg.geometry("760x420")
        text = tk.Text(dlg, wrap="word", bg="white", fg=INK, relief="solid", bd=1,
                       font=("TkFixedFont", 9), highlightthickness=0)
        roller = ttk.Scrollbar(dlg, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=roller.set, state="disabled")
        roller.pack(side="right", fill="y", pady=10, padx=(0, 10))
        text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        dlg.text = text
        self.protokoll = dlg
        return dlg

    def _protokoll_schreiben(self, zeile):
        t = self._protokoll_fenster().text
        t.configure(state="normal"); t.insert("end", zeile); t.see("end"); t.configure(state="disabled")

    def _skripte_ausfuehren(self, titel, befehle, danach):
        """Skripte nacheinander im Hintergrund, Ausgabe ins Protokoll.

        Solange sie laufen, ist das Hauptfenster gesperrt: build-gallery.py
        schreibt photos.json, Eingaben in der Zwischenzeit gingen beim
        anschliessenden Neuladen verloren.
        """
        if self.laeuft:
            return
        self.laeuft = True
        dlg = self._protokoll_fenster()
        t = dlg.text
        t.configure(state="normal"); t.delete("1.0", "end"); t.configure(state="disabled")
        self._protokoll_schreiben(f"── {titel} ──\n")
        dlg.grab_set()
        umgebung = dict(os.environ, PYTHONUNBUFFERED="1")

        def arbeit():
            ok = True
            for befehl in befehle:
                self.after(0, self._protokoll_schreiben, f"\n$ python3 tools/{os.path.basename(befehl[-1])}\n")
                try:
                    proc = subprocess.Popen([sys.executable] + befehl, cwd=ROOT, env=umgebung,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for zeile in proc.stdout:
                        self.after(0, self._protokoll_schreiben, zeile)
                    ok = proc.wait() == 0
                except OSError as e:
                    self.after(0, self._protokoll_schreiben, f"{e}\n")
                    ok = False
                if not ok:
                    break
            self.after(0, fertig, ok)

        def fertig(ok):
            self.laeuft = False
            dlg.grab_release()
            self._protokoll_schreiben("\n✔ fertig\n" if ok else "\n✘ abgebrochen — siehe oben\n")
            danach(ok)
        threading.Thread(target=arbeit, daemon=True).start()

    def _galerie_bauen(self, danach=None):
        """build-gallery.py und build-pages.py. Ungespeichertes wird vorher gespeichert."""
        if self.laeuft or not self._felder_uebernehmen():
            return
        if self.ki_laeuft:
            messagebox.showinfo("Galerie bauen", "Die KI arbeitet noch — bitte kurz warten.")
            return
        gespeichert = self.schmutzig
        if self.schmutzig:
            self._speichern()

        def nach_bauen(ok):
            self._neu_laden()
            if gespeichert:
                self._protokoll_schreiben("(ungespeicherte Änderungen wurden vorher gespeichert)\n")
            if ok:
                self.lbl_status.config(text="Galerie gebaut — „Vorschau im Browser“ zeigt das Ergebnis")
            if danach:
                danach(ok)
        self._skripte_ausfuehren("Galerie bauen", [[BUILD_GALLERY], [BUILD_PAGES]], nach_bauen)

    def _neu_laden(self):
        """photos.json nach dem Bauen neu einlesen, beim selben Bild bleiben."""
        datei = self.liste[self.idx]["datei"] if self.liste else None
        with open(DATA, encoding="utf-8") as fh:
            self.daten = json.load(fh)
        self.tags_def = self.daten.setdefault("tags", {})
        self.alle = self.daten.get("photos", [])
        self.schmutzig = False
        self._dirty_anzeigen()
        if not self.alle:
            return
        self._liste_aktualisieren()
        for i, p in enumerate(self.liste):
            if p["datei"] == datei:
                self.idx = i
                break
        self._anzeigen()

    def _bilder_hinzufuegen(self):
        if self.laeuft:
            return
        wahl = filedialog.askopenfilenames(
            parent=self, title="Bilder für die Galerie auswählen",
            filetypes=[("Bilder", " ".join("*" + e + " *" + e.upper() for e in BILDTYPEN)),
                       ("Alle Dateien", "*")])
        if not wahl:
            return
        os.makedirs(ORIG, exist_ok=True)
        vorhanden = {os.path.splitext(f)[0] for f in os.listdir(ORIG)}
        kopiert, uebersprungen = [], []
        for quelle in wahl:
            name = os.path.basename(quelle)
            if not name.lower().endswith(BILDTYPEN):
                uebersprungen.append(f"{name}  (kein unterstütztes Format)")
            elif os.path.splitext(name)[0] in vorhanden:
                # gleicher Stamm hiesse fuer build-gallery.py: dieses Bild ersetzen
                uebersprungen.append(f"{name}  (gleichnamiges Bild gibt es schon)")
            else:
                shutil.copy2(quelle, os.path.join(ORIG, name))
                vorhanden.add(os.path.splitext(name)[0])
                kopiert.append(name)
        if uebersprungen:
            messagebox.showwarning("Nicht übernommen", "\n".join(uebersprungen))
        if not kopiert:
            return

        def danach(ok):
            if not ok:
                return
            neu = [p for p in self.alle if p["datei"] in kopiert]
            if neu:                                 # zum ersten neuen Bild springen
                self.nur_offene.set(False)
                self._liste_aktualisieren()
                self.idx = self.liste.index(neu[0])
                self._anzeigen()
                # KI erst auf Knopfdruck — nichts geht ungefragt raus
                self.lbl_status.config(text=f"{len(neu)} Bild(er) aufgenommen — "
                                            "KI-Vorschlag mit Strg+K oder „KI für alle ohne Tags …“")
        self._galerie_bauen(danach)

    def _vorschau(self):
        """Lokalen Server starten (falls noch keiner laeuft) und die Galerie oeffnen."""
        with socket.socket() as s:
            belegt = s.connect_ex(("127.0.0.1", PORT)) == 0
        if not belegt:
            self.server = subprocess.Popen([sys.executable, SERVE, str(PORT)], cwd=ROOT,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.after(0 if belegt else 600,
                   lambda: webbrowser.open(f"http://localhost:{PORT}/gallery.html"))
        self.lbl_status.config(text=f"Vorschau: http://localhost:{PORT}/gallery.html")

    def _beenden(self):
        self._felder_uebernehmen()
        if self.schmutzig:
            antwort = messagebox.askyesnocancel(
                "Ungespeicherte Änderungen",
                "Es gibt Änderungen, die noch nicht in photos.json stehen.\n\n"
                "Jetzt speichern?")
            if antwort is None:            # Abbrechen -> Fenster bleibt offen
                return
            if antwort:
                self._speichern()
            else:
                print("Änderungen verworfen.")
        offen = sum(1 for p in self.alle if self._unvollstaendig(p))
        print(f"Noch unvollständig: {offen}")
        if self.server and self.server.poll() is None:
            self.server.terminate()
        self.destroy()


if __name__ == "__main__":
    if not os.path.exists(DATA):
        sys.exit("photos.json fehlt. Zuerst:  python3 tools/build-gallery.py")
    Tagger().mainloop()
