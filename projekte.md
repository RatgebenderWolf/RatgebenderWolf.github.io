# Projekte

---

## ARCTA – Automated Radio Communication Transcription & Analysis
**Zeitraum:** 03.2026 – 06.2026
**Typ:** Masterstudiengang Projekt 2

### Beschreibung
ARCTA ist eine Anwendung zur automatisierten Transkription, Strukturierung und Analyse von Feuerwehr- und BOS-Sprechfunk. Aus dialektbehafteten Audioaufnahmen wird ein normiertes, hochdeutsches Einsatzprotokoll erzeugt. Die Verarbeitung erfolgt in zwei Stufen: Zunächst wandelt ein Spracherkenner (Speech-to-Text, STT) das Audio in Rohtext um; anschließend korrigiert und strukturiert ein großes Sprachmodell (LLM) diesen Text (Dialektkorrektur, Erkennung von Sender und Empfänger, Klassifikation).

Für den Funkverkehr ist nicht nur die allgemeine Texttreue wichtig, sondern besonders die korrekte Erkennung von Zahlen, Koordinaten und Rufnamen. Die Evaluierung sollte daher beantworten, welches Korrektur-LLM die rohe STT-Ausgabe am stärksten verbessert, wie zuverlässig Zahlen erkannt werden und in welchem Verhältnis die erreichte Genauigkeit zu Kosten und Verarbeitungsgeschwindigkeit steht.

### Evaluierungswerkzeug: EvalARCTA
Die Auswertung erfolgte mit dem eigens entwickelten Werkzeug EvalARCTA. Es vergleicht jede Transkription (Hypothese) mit einer manuell erstellten, korrekten Referenz (Truth) auf Wortebene und berechnet daraus standardisierte Fehlerkennzahlen. Verglichen wird ausschließlich der Wortinhalt – Groß-/Kleinschreibung, Satzzeichen und Zeitstempel haben keinen Einfluss auf das Ergebnis. Die Berechnung stützt sich auf die etablierte Bibliothek jiwer und läuft vollständig lokal auf der CPU.

### Ergebnisse
Hauptergebnis im radio-Modus, sortiert nach WER (niedriger = besser):

| Serie (STT roh / + LLM) | WER % | CER % | Zahlen-Acc. % | Kosten USD | RTF |
|---|---|---|---|---|---|
| gemini-3.5-flash:nitro | 4,8 | 3,2 | 100,0 | 0,575 | 0,051 |
| gpt-5.5 | 6,1 | 4,1 | 100,0 | 0,430 | 0,678 |
| gemini-3.5-flash | 6,4 | 3,9 | 100,0 | 0,430 | 0,659 |
| qwen3.7-max | 7,0 | 4,7 | 98,4 | 0,540 | 0,375 |
| deepseek-v4-flash | 11,9 | 6,5 | 98,4 | 1,460 | 0,074 |
| STT roh (ohne LLM) | 18,5 | 7,1 | 98,4 | 1,000 | 0,110 |

**Kennzahlen-Definitionen:**
- **WER** (Word Error Rate) = (S + D + I) / N – Standardmetrik der Spracherkennung, niedriger ist besser. Kann theoretisch über 100 % steigen, wenn sehr viel zusätzlicher Text erzeugt wird.
- **CER** (Character Error Rate) = Zeichen-Editierdistanz / Referenzzeichen – feiner als WER und robuster bei deutschen Wortendungen und Komposita.
- **Zahlen-Accuracy** = korrekt erkannte Ziffern-Token / Ziffern-Token gesamt – missionskritisch für Koordinaten, nur im radio-Modus aussagekräftig.
- **RTF** (Real-Time-Factor) = Gesamtlaufzeit / Audiodauer – Werte unter 1 bedeuten schneller als Echtzeit.
- **Kosten** = STT-Kosten und LLM-Kosten in US-Dollar.

Der größte Qualitätssprung entsteht durch die LLM-Korrektur: Die rohe STT-Ausgabe liegt im radio-Modus bei 18,5 % WER, während das beste Modell die Fehlerrate auf 4,8 % senkt – eine Reduktion um rund drei Viertel. Selbst das schwächste Korrektur-LLM (deepseek-v4-flash, 11,9 %) verbessert die Rohausgabe noch spürbar. Zusätzlich zeigt der Vergleich der Modi, dass die radio-Normalisierung die gemessene WER durchgängig senkt, da unterschiedliche Sprechweisen derselben Zahl als inhaltlich gleich gewertet werden.

Die höchste Genauigkeit ist nicht automatisch die teuerste Option: gemini-3.5-flash:nitro verbindet die beste WER mit einem mittleren Preis (0,575 USD) und der gemeinsam mit gpt-5.5 schnellsten Verarbeitung (RTF 0,43, also gut doppelt so schnell wie Echtzeit). deepseek-v4-flash ist mit 0,074 USD am günstigsten, liefert aber die schwächste LLM-Qualität und arbeitet nur in Echtzeit (RTF 1,00). qwen3.7-max ist mit RTF 1,46 am langsamsten. Insgesamt bietet gemini-3.5-flash:nitro das beste Gesamtverhältnis aus Genauigkeit, Tempo und Kosten.

### Fazit
Für die automatische Transkription des untersuchten BOS-Sprechfunks empfiehlt sich auf Basis dieser ersten Evaluierung die Kombination aus dem STT-Modell microsoft/mai-transcribe-1.5 und dem Korrektur-LLM gemini-3.5-flash:nitro. Diese Kombination erreicht die niedrigste Wortfehlerrate (4,8 %), erkennt alle Zahlen-Token korrekt (100 % Zahlen-Accuracy) und arbeitet dabei zu moderaten Kosten schneller als Echtzeit.

Zwei grundsätzliche Erkenntnisse lassen sich festhalten: Die nachgelagerte LLM-Korrektur ist für eine brauchbare Transkriptionsqualität unverzichtbar, und für die Bewertung von Funktexten ist die radio-Normalisierung notwendig, um die fachlich entscheidende Zahlentreue korrekt zu messen. Der nächste sinnvolle Schritt ist die Ausweitung der Evaluierung auf einen größeren Korpus, um die gefundene Rangfolge statistisch abzusichern.

---

## AI Plywood Quality Assistant
**Zeitraum:** 02.2026 – laufend
**Typ:** Projekt
**Rolle:** Projektleitung & Requirements Engineer
**Bereich:** Künstliche Intelligenz, Qualitätssicherung, Bildverarbeitung
**Status:** Laufend

### Ziele
Entwicklung einer Anlage zur automatischen Qualitätserkennung von Oberflächen. Ziel ist ein System, das diese Bewertung bildbasiert und reproduzierbar durchführt und die Ergebnisse anzeigt.

### Rolle
Projektleitung und Requirements Engineering: Anforderungen erheben und strukturieren, den Projektablauf planen und die Abstimmung zwischen den Beteiligten führen.

*Genauere Details können nicht veröffentlicht werden.*

### Stand
Das Projekt befindet sich in Bearbeitung.

---

## Machbarkeitsstudie zur Anomalieerkennung bei Industrieöfen mit ML
**Zeitraum:** 09.2025 – 02.2026
**Typ:** Masterstudiengang Projekt 1

### Beschreibung
Im Rahmen dieses Masterklassenprojekts wurde die Machbarkeit einer Machine-Learning-basierten Anomalieerkennung für industrielle Stoßöfen untersucht. Ziel war die Entwicklung eines Analysesystems, das auf Basis historischer Prozessdaten auffällige Abweichungen im Ofenbetrieb automatisch erkennt und für Service-, Inbetriebnahme- und Analysezwecke nutzbar macht.

Als Datengrundlage dienten reale Prozessdaten aus einem Stoßofen, darunter Temperatur-Soll- und Istwerte sowie Reglerstellgrößen verschiedener Ofenzonen. Nach einer umfangreichen Datenaufbereitung und Segmentierung des Ofenbetriebs in einzelne Zyklen und Prozessphasen wurde ein Machine-Learning-Modell zur Erkennung von Abweichungen vom Normalbetrieb entwickelt.

Da keine gelabelten Fehlerdaten vorlagen, kam ein One-Class-Ansatz zum Einsatz, der das typische Betriebsverhalten erlernt und Auffälligkeiten über einen Anomalie-Score bewertet. Die Ergebnisse werden textbasiert und grafisch dargestellt, um technische Anwender bei der Analyse kritischer Betriebszustände zu unterstützen.

Die Arbeit ist als Machbarkeitsstudie für die Offline-Analyse historischer Daten ausgelegt. Die entwickelte Architektur ist modular aufgebaut und kann künftig um Funktionen wie eine grafische Benutzeroberfläche, Online-Analyse oder erweiterte Reportingmöglichkeiten ergänzt werden.

### Aufgabe im Projekt
- Planung und Durchführung von Tests zur Modellbewertung
- Bewertung von Ergebnissen
- Dokumentation und Ergebnisvisualisierung

### Fazit
Die Ergebnisse zeigen, dass eine Machine-Learning-basierte Anomalieerkennung für industrielle Stoßöfen grundsätzlich umsetzbar ist und großes Potenzial für den industriellen Einsatz besitzt.

---

## Automatisierung der Qualitätssicherung bei Mietschalungen durch Künstliche Intelligenz
**Abgabe:** 09.2025
**Typ:** Bachelorarbeit (Studiengang Smart Engineering)
**Untertitel:** Entwicklung und Evaluation von KI-Modellen zur Fehlererkennung auf Schalhautoberflächen

### Beschreibung
Diese Arbeit befasst sich mit der Datensammlung, Aufbereitung und Annotation sowie dem Training und der Evaluation von KI-Modellen. Grundlage bilden Bilddaten von Doka Xlife-Schalungsplatten, die von Baustellen zurückgeliefert und anschließend mit Hochdruck gereinigt wurden.

Ziel der Arbeit ist es, den Einsatz von Künstlicher Intelligenz zur automatisierten Oberflächenprüfung von Schalungselementen zu untersuchen. Der Fokus liegt dabei auf der Erfassung und Annotation von Bilddaten beschädigter Schalhaut. Aufbauend auf diesem Datensatz werden KI-Modelle trainiert und evaluiert, die in der Lage sein sollen, Fehler automatisch zu lokalisieren und zu klassifizieren. Die Arbeit soll damit die Grundlage für künftige Entwicklungen im Bereich der automatisierten Qualitätskontrolle sowie der automatisierten Sanierung von Schalungselementen schaffen.

*Geplante Veröffentlichung im Jahr 2031.*

---

## Proof of Concept: Qualitätserkennung von gebrauchter Schalhaut (Fortführung)
**DE:** Proof of Concept: Qualitätserkennung von gebrauchter Schalhaut
**EN:** Proof of concept: quality detection of used plywood
**Zeitraum:** 03.2025 – 07.2025
**Typ:** Bachelorstudienprojekt 4 (Fortführung von Projekt 2)

### Beschreibung
Im zweiten dualen Projekt des Studiengangs Smart Engineering wurde ein Konzept zur Sammlung von Daten für das Training einer KI entwickelt. Ziel ist es, die Qualität von gebrauchter Schalhaut automatisch zu überprüfen. Das Projekt dient als Proof of Concept und soll zeigen, was mit Bilddaten möglich ist.

### Zielstellung des Projekts
- Anwendung von Projektmanagement-Methoden
- Konzept für Datenverarbeitung und KI-Training erstellen
- Daten vorbereiten und mit Labeln beginnen

### Problem- bzw. Fragestellung
- Wie werden die Daten gelabelt?
- Welche neuronalen Netzarchitekturen werden verwendet?

---

## Automatisierung der Hochdruckreinigung von Elementrahmen: Positionserkennung und HMI-Entwicklung
**DE:** Automatisierung der Hochdruckreinigung von Elementrahmen: Positionserkennung und HMI-Entwicklung
**EN:** Automation of High-Pressure Cleaning of Element Frames: Position Detection and HMI
**Zeitraum:** 09.2024 – 02.2025
**Typ:** Bachelorstudienprojekt 3

### Beschreibung
Das Hauptziel des Projekts ist es, ein Lernvideo zu erstellen. Die Wissensvermittlung im Videoformat soll angewandt werden, um die im Projekt ausgearbeiteten Ergebnisse zu präsentieren. Im Projekt geht es allgemein um die Automatisierung der Hochdruckreinigung von Schalungselementen. Speziell geht es hier um die Positionserkennung von Schalungselementen in der Waschbox.

### Zielstellung des Projekts
- Methoden zur Positionserkennung aufzeigen und bewerten
- Anforderungen für ein Human-Machine-Interface (HMI) definieren
- Erstellung eines Lernvideos zur Wissensverbreitung der erarbeiteten Inhalte

### Problem- bzw. Fragestellung
- Wie kann die Position eines Elementpakets im Arbeitsbereich ermittelt werden?
- Wie könnte ein Interface für diese Anlage aussehen?

---

## Proof of Concept: Qualitätserkennung von gebrauchter Schalhaut
**DE:** Proof of Concept: Qualitätserkennung von gebrauchter Schalhaut
**EN:** Proof of concept: quality detection of used plywood
**Zeitraum:** 02.2024 – 07.2024
**Typ:** Bachelorstudienprojekt 2

### Beschreibung
Das Projekt zielt darauf ab, die Qualität von gebrauchter Schalhaut durch den Einsatz von Künstlicher Intelligenz und Bildverarbeitung zu verbessern. Dabei sollen automatische Systeme entwickelt werden, die Oberflächenfehler präzise erkennen und klassifizieren können. Das langfristige Ziel ist es, die Effizienz der Fehlererkennung zu steigern und die manuelle Nacharbeit zu reduzieren.

### Ziele
- Erstellung von Automatisierungsgraden der Wiederaufbereitung von Schalungselementen
- Technologien für die Qualitätserkennung finden und potenzielle Technologien aufzeigen
- Prototypen für das Sammeln von Daten aufbauen und Daten sammeln

### Ergebnisse
- Aufstellung von Automatisierungsgraden
- Qualitätserkennung: Evaluierung verschiedener Methoden zur Qualitätserkennung und Festlegung auf eine Methode
- Budget für Prototypen wurde freigegeben; eine Festlegung auf das spezifische Material ist noch ausstehend

---

## Diskrete Event Simulation einer Bearbeitungsstrecke von Schalungselementen
**Zeitraum:** 08.2023 – 02.2024
**Typ:** Bachelorstudienprojekt 1

### Beschreibung
Das Projekt konzentriert sich auf die gründliche Analyse einer neu installierten Reinigungsanlage. Verfolgt wird ein umfassender Ansatz, der die Aufzeichnung von Prozessdaten sowie die Erstellung einer Simulation umfasst. Diese Simulation wird ausgewertet, um potenzielle Verbesserungen zu identifizieren. Ein zentraler Aspekt besteht darin, die Leistung der Anlage zu optimieren, um sie effektiv mit anderen vergleichbaren Anlagen zu bewerten und eine effizientere Kapazitätssteuerung zu ermöglichen.

Die Hauptziele umfassen die Erfassung aktueller Daten wie Durchlaufzeit und Rüstzeiten der Anlage. Diese Daten dienen als Grundlage für eine eingehende Analyse der Prozesse, wobei gezielt nach Möglichkeiten zur Optimierung gesucht wird. Eine Diskrete Event Simulation (DES) der Anlage wird erstellt, um die Dynamik und Interaktionen der Prozessschritte zu modellieren. Die Ergebnisse dieser Simulation werden evaluiert, um Erkenntnisse zu gewinnen, die die Basis für konkrete Verbesserungsmaßnahmen bilden. Durch die Festlegung von fünf spezifischen Prozessschritten wird sichergestellt, dass die Simulation eine realitätsnahe Darstellung der Anlagenfunktionalität liefert.

### Ergebnisse
Am Ende des Projekts stehen eine umfassende Simulation der Anlage, konkrete Vorschläge zur Optimierung der Prozesse und eine Datensammlung, die einen Einblick in die Leistung und Effizienz der Anlage ermöglicht. Diese Ergebnisse bilden die Grundlage für zukünftige Entscheidungen zur Weiterentwicklung und Steigerung der Produktivität der Reinigungsanlage.

---

## Infinity 3D Printer – Entwicklung eines 3D-Druckers
**Zeitraum:** 06.2020 – 05.2021
**Typ:** Diplomarbeit (Abschlussarbeit HTL)
**Kooperationspartner:** Höhere Technische Bundeslehr- und Versuchsanstalt St. Pölten

### Beschreibung
In diesem Projekt wurde ein Belt-3D-Drucker konstruiert und gefertigt. Der 3D-Drucker kann in eine Richtung unendlich weit drucken und nach einem Druck gleich einen neuen Druck starten. Weiters besitzt der Drucker vier verschiedene Extruder, welche voll automatisiert gewechselt werden. Dadurch ist das Fertigen von sehr langen Prototypen wie zum Beispiel einer Frontstoßstange eines LKWs möglich. Zusätzlich können verschiedene Materialien in einem Druck verarbeitet werden. Das ermöglicht Teile, welche im Kern weich und außen hart sind.

### Ergebnisse
- Design des 3D-Druckers
- 3D-Konstruktion
- Fertigungsunterlagen
- Erzeugnis-Gliederung und Arbeitsplan
- Wirtschaftlichkeitsbetrachtung
- Visualisierung
- Prototypenbau begonnen

### Aufgabe im Projekt
- Projektmanagement
- Design
- Fertigung
- Einkauf
- Dokumentation
