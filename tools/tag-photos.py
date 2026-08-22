#!/usr/bin/env python3
"""
Bilder verschlagworten.

    python3 tools/tag-photos.py

Geht die Bilder aus photos.json der Reihe nach durch und laesst Datum, Ort,
Tags und die Beschreibungen ergaenzen. Die Vorschau kommt aus
images/gallery/thumb/, deshalb laedt auch eine 20-MB-Originaldatei sofort.

Voraussetzung: einmal  python3 tools/build-gallery.py  laufen lassen, damit
die Eintraege und die Vorschaubilder existieren.

Tasten:  Bild-hoch/runter oder Alt+Links/Rechts  blaettern
         Strg+S  speichern      Strg+D  Ort, Tags und Beschreibung vom vorherigen Bild uebernehmen
                 (das Datum bleibt stehen, es stammt aus dem EXIF)
"""

import json
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox

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

PAPER, PAPER_ALT, INK, INK_SOFT, LINE, BLUE = (
    "#edede6", "#e2e3da", "#191c1f", "#565b5e", "#c7cabf", "#2b4c7e")
VORSCHAU = 640
DATUM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
        self.tag_vars   = {}
        self.idx        = 0
        self.foto       = None          # haelt die Referenz aufs Bild
        self.schmutzig  = False

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
        st.configure("TButton",       padding=5)

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

        kopfzeile("TAGS  (häufigste zuerst)")
        self.f_tags = ttk.Frame(rechts)
        self.f_tags.pack(anchor="w", fill="x")

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

        f_neu = ttk.Frame(rechts)
        f_neu.pack(anchor="w", fill="x", pady=(6, 0))
        self.e_neuer_tag = ttk.Entry(f_neu, width=22)
        self.e_neuer_tag.pack(side="left")
        ttk.Button(f_neu, text="Tag anlegen", command=self._tag_anlegen).pack(side="left", padx=6)
        ttk.Button(f_neu, text="Tags verwalten …", command=self._tags_verwalten).pack(side="left")

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

    def _tags_zeichnen(self, p):
        for w in self.f_tags.winfo_children():
            w.destroy()
        self.tag_vars = {}
        reihenfolge, zahl = self._tag_haeufigkeit()
        gesetzt = set(p.get("tags", []))
        spalten = 3
        for i, t in enumerate(reihenfolge):
            v = tk.BooleanVar(value=t in gesetzt)
            self.tag_vars[t] = v
            beschriftung = self.tags_def.get(t, {}).get("de", t)
            if zahl[t]:
                beschriftung += f"  ({zahl[t]})"
            ttk.Checkbutton(self.f_tags, text=beschriftung, variable=v).grid(
                row=i // spalten, column=i % spalten, sticky="w", padx=(0, 14))

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
            "tags":   sorted(t for t, v in self.tag_vars.items() if v.get()),
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
        gesetzt = set(vor.get("tags", []))
        for t, v in self.tag_vars.items():
            v.set(t in gesetzt)
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

    def _tag_anlegen(self):
        roh = self.e_neuer_tag.get().strip().lower()
        kennung = re.sub(r"[^a-z0-9]+", "", roh.replace("ä", "ae").replace("ö", "oe")
                                              .replace("ü", "ue").replace("ß", "ss"))
        if not kennung:
            messagebox.showwarning("Kein Name", "Bitte einen Tag-Namen eingeben.")
            return
        if kennung in self.tags_def:
            self.tag_vars[kennung].set(True)
            self.e_neuer_tag.delete(0, "end")
            self.lbl_status.config(text=f"'{kennung}' gibt es schon — gesetzt")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Neuer Tag")
        dlg.configure(bg=PAPER)
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text=f"Kennung:  {kennung}").pack(padx=16, pady=(14, 8), anchor="w")
        ttk.Label(dlg, text="Bezeichnung deutsch:").pack(padx=16, anchor="w")
        e_de = ttk.Entry(dlg, width=34); e_de.pack(padx=16, pady=(0, 8)); e_de.insert(0, roh.capitalize())
        ttk.Label(dlg, text="Bezeichnung englisch:").pack(padx=16, anchor="w")
        e_en = ttk.Entry(dlg, width=34); e_en.pack(padx=16, pady=(0, 12))

        def anlegen():
            de = e_de.get().strip() or kennung
            en = e_en.get().strip() or de
            self.tags_def[kennung] = {"de": de, "en": en}
            if not self._felder_uebernehmen():
                dlg.destroy()
                return
            self.liste[self.idx].setdefault("tags", []).append(kennung)
            self.schmutzig = True
            self.e_neuer_tag.delete(0, "end")
            dlg.destroy()
            self._anzeigen()
            self.lbl_status.config(text=f"Tag '{de}' angelegt und gesetzt")

        ttk.Button(dlg, text="Anlegen", command=anlegen).pack(pady=(0, 14))
        e_en.bind("<Return>", lambda e: anlegen())
        e_de.focus_set()

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
        print("Weiter mit:  python3 tools/build-gallery.py")
        self.destroy()


if __name__ == "__main__":
    if not os.path.exists(DATA):
        sys.exit("photos.json fehlt. Zuerst:  python3 tools/build-gallery.py")
    Tagger().mainloop()
