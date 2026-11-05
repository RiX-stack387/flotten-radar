import os, re, json
from datetime import datetime

local_root = r"C:\DefconRecht"
skills_root = os.path.join(local_root, "SKILLS")
backup_dir = os.path.join(local_root, "TAG_X_BACKUP")
master_archiv = os.path.join(local_root, "Master_Archiv_V23.4_EINSATZ-CHRONIK.md")
hb_admiral = os.path.join(local_root, "Handbuch_Admiral_V23.4.md")
hb_core = os.path.join(local_root, "Handbuch_CORE_DACH_V23.4.md")
front_delta = os.path.join(local_root, "Front_Delta_Compact.md")

os.makedirs(backup_dir, exist_ok=True)

# 1. MASTER-ARCHIV BEREINIGEN & EINZEL-PROTOKOLLE #4600 BIS #4650 SAUBER ANHÄNGEN
if os.path.exists(master_archiv):
    with open(master_archiv, "r", encoding="utf-8") as f:
        arch = f.read()
    # Entferne die fehlerhaften/doppelten Blöcke ab #4600
    idx = arch.find("[📟 PROTOKOLL-EINTRAG: #4600]")
    if idx != -1:
        arch = arch[:idx].rstrip()
    
    clean_4600_4650 = [
        "[📟 PROTOKOLL-EINTRAG: #4600] [✅ STATUS: SKILL-PAKET-INJEKTION // NOTEBOOK-WORKSPACE-LINKS EINGETRAGEN] Integration der Workspace-Verknüpfungsdateien in alle Skill-Verzeichnisse zur Absicherung der RAG-Schnittstellen.",
        "[📟 PROTOKOLL-EINTRAG: #4601] [✅ STATUS: CLOUD-PARITÄT // 22 VON 25 FRONT-SKILLS LIVE] Fünfter Schlag erfolgreich im Ziel; Reiselogistik, Sentinel 1 & 2.0 sowie Safe Haven im Gemini-Backend versiegelt.",
        "[📟 PROTOKOLL-EINTRAG: #4602] [✅ STATUS: RATELIMIT-MONITOR // 03:13 RESET-KONTROLLE] Überwachung der API-Auslastung und Vorbereitung des 3.8 Flash Moduls für den finalen Endspurt.",
        "[📟 PROTOKOLL-EINTRAG: #4603] [✅ STATUS: FINALER CLOUD-PATCH // 25 VON 25 FRONT-SKILLS LIVE] Aktualisierung von rixi-flotte-koordination, defcon-recht-enterprise und core-dach-rechenzentrum im Google-Gemini-Cloud-Backend.",
        "[📟 PROTOKOLL-EINTRAG: #4604] [✅ STATUS: NOTEBOOK-ZUORDNUNGSMATRIX // 4 SÄULEN AUDITIERT] Aufschlüsselung und Verifizierung der 4 zentralen Gemini-Notebooks auf alle 26 Flotten-Einheiten.",
        "[📟 PROTOKOLL-EINTRAG: #4605] [✅ STATUS: SCHLEIFEN-STOPP // API-INJEKTIONS-ABBRUCH] Abbruch der automatisierten .notebook-Schreibschleife und Umstellung auf plattformseitige Verknüpfung im Browser.",
        "[📟 PROTOKOLL-EINTRAG: #4606] [✅ STATUS: GEM-MANAGER BEREINIGUNG // HEIMAT- & CORE-SYNCHRONISATION] Korrektur der Notebook-Zuordnungen in den Gems für Pforzheim/Enzkreis und Core D.A.CH.",
        "[📟 PROTOKOLL-EINTRAG: #4607] [✅ STATUS: DOKTRIN-REVISION // ADMIRAL-GEM ANLEITUNG AKTUALISIERT] Bereinigung des Admiral-Gem Instruktionsfeldes von Altsystem-Fragmenten und V23.4-Sicherung.",
        "[📟 PROTOKOLL-EINTRAG: #4608] [✅ STATUS: FORENSISCHER PDF-AUDIT // TEST-ANTWORT ANALYSIERT] Auswertung des Test-PDFs und Bestätigung der reibungslosen Umsetzung der unbestechlichen Co-Pilot-Doktrin.",
        "[📟 PROTOKOLL-EINTRAG: #4609] [✅ STATUS: SKILL-GEM VERZAHNUNG // UI-ANZEIGE VERIFIZIERT] Bestätigung der automatischen Skill-Aktivierung im Hintergrund während des Chat-Modus.",
        "[📟 PROTOKOLL-EINTRAG: #4610] [✅ STATUS: ELICITATION-LÜCKENANALYSE // 24 EINHEITEN IDENTIFIZIERT] Forensischer Scan deckt auf, dass bei 24 von 26 Einheiten die interaktiven Elicitation-Buttons im Footer fehlen.",
        "[📟 PROTOKOLL-EINTRAG: #4611] [✅ STATUS: AUTOMATISIERTER ELICITATION-INJEKTOR // POWERSHELL ENTWICKELT] Bereitstellung des Skripts zur automatischen Nachrüstung der passenden Elicitation-Blöcke über alle Fachbereiche hinweg.",
        "[📟 PROTOKOLL-EINTRAG: #4612] [✅ STATUS: 4-WEGE-SYNC & TAG-X-KOPPLUNG // C:, G:, GITHUB, BACKUP] Ausführung des vollständigen Robocopy-, Git- und Backup-Laufs zur Herstellung absoluter Parität.",
        "[📟 PROTOKOLL-EINTRAG: #4613] [✅ STATUS: GESAMTFLOTTEN-STATUS V21.2 // 26 EINHEITEN AUF GRÜN] Bestätigung der vollständigen Einsatzbereitschaft aller Einheiten nach erfolgreichem Synchronisationslauf.",
        "[📟 PROTOKOLL-EINTRAG: #4614] [✅ STATUS: ENDLOS-ZÄHLER PATCH BLOCK 1 // RECHTE-FLOTTE] Verankerung des unbegrenzten Sitzungszählers #001 bis #∞ in den ersten Rechts-Einheiten.",
        "[📟 PROTOKOLL-EINTRAG: #4615] [✅ STATUS: ENDLOS-ZÄHLER PATCH BLOCK 2 // FACH-ANKER] Fortführung der Zähler- und In-Chat-Archiv-Verankerung in den sozialen Fach-Ankern.",
        "[📟 PROTOKOLL-EINTRAG: #4616] [✅ STATUS: ENDLOS-ZÄHLER PATCH BLOCK 3 // ZIVIL-LOTSEN] Integration der Meilenstein-Kompression und Zero-Dilution-Regel in den Zivil-Einheiten.",
        "[📟 PROTOKOLL-EINTRAG: #4617] [✅ STATUS: ENDLOS-ZÄHLER PATCH BLOCK 4 // SENTINEL & RESILIENZ] Abschluss der Zähler-Harmonisierung in den Wächter- und Resilienz-Einheiten.",
        "[📟 PROTOKOLL-EINTRAG: #4618] [✅ STATUS: ENDLOS-ZÄHLER PATCH BLOCK 5 // CORE & ENTERPRISE] Synchronisation von core-dach-rechenzentrum, rixi-flotte-koordination und defcon-recht-enterprise.",
        "[📟 PROTOKOLL-EINTRAG: #4619] [✅ STATUS: 4-NOTEBOOK-ARCHITEKTUR // WORKSPACE-MAPPING] Zuordnung der 4 spezialisierten Gemini-Notebooks als RAG-Wissensanker der Flotte.",
        "[📟 PROTOKOLL-EINTRAG: #4620] [✅ STATUS: KOMMANDOBRÜCKE NOTEBOOK // ADMIRAL & CORE] Verifizierung des Führungs-Notebooks für Hauptbrücke und Logik-Verteiler.",
        "[📟 PROTOKOLL-EINTRAG: #4621] [✅ STATUS: DEFCON RECHT NOTEBOOK // NORMEN-TRESOR] Verifizierung des juristischen Notebooks für alle 15 Einheiten der Rechte-Flotte.",
        "[📟 PROTOKOLL-EINTRAG: #4622] [✅ STATUS: ASB NORDSCHWARZWALD NOTEBOOK // ZIVIL-WORKSPACE] Verifizierung des ASB- und KatS-Notebooks für Nordschwarzwald-Einheiten.",
        "[📟 PROTOKOLL-EINTRAG: #4623] [✅ STATUS: PFORZHEIM & ENZKREIS NOTEBOOK // HEIMAT-WORKSPACE] Verifizierung des regionalen Kultur-, Freizeit- und Sozial-Notebooks.",
        "[📟 PROTOKOLL-EINTRAG: #4624] [✅ STATUS: ZERO-DILUTION-HARDLOCK // FAKTEN-VALIDIERUNG] Durchsetzung der strikten Frisch-Validierung aus SKILL.md und references/ bei jedem Zählerschritt.",
        "[📟 PROTOKOLL-EINTRAG: #4625] [✅ STATUS: IN-CHAT-ARCHIV // MEILENSTEIN-KOMPRESSION] Einführung der bürgerfreundlichen Zusammenfassungs-Funktion gegen Kontextverlust bei langen Sitzungen.",
        "[📟 PROTOKOLL-EINTRAG: #4626] [✅ STATUS: PUBLIC-COMPLIANCE-LOCK // ÖFFENTLICHE LOTSEN] Absicherung von Art. 50 KI-VO, § 5 DDG Impressum und RDG-Sperre in den 3 öffentlichen Bürger-Lotsen.",
        "[📟 PROTOKOLL-EINTRAG: #4627] [✅ STATUS: SAFE-HAVEN-SCHUTZ // § 6 RDG VERANKERT] Bestätigung der vollen DIN-5008-Schriftsatzkompetenz im geschützten Familien- und Kanzleisektor.",
        "[📟 PROTOKOLL-EINTRAG: #4628] [✅ STATUS: DEEP-LINK-DOKTRIN // MAILTO & MAPS] Prüfung der klickbaren E-Mail- und Google-Maps-Verlinkungen in den Lotsen-Prompts.",
        "[📟 PROTOKOLL-EINTRAG: #4629] [✅ STATUS: 112-NOTFALL-HARDLOCK // KLINIK-UPDATE NEUENBÜRG] Überprüfung der Notruf-Weichen inklusive Schließungsvermerk ZNA Neuenbürg.",
        "[📟 PROTOKOLL-EINTRAG: #4630] [✅ STATUS: SCREENSHOT-AUDIT // GEM-MANAGER DATEIEN] Sichtung der Dateianhänge in den Gems pforzheim-enzkreis-heimat und core-dach-rechenzentrum.",
        "[📟 PROTOKOLL-EINTRAG: #4631] [✅ STATUS: SCHLEIFEN-STOPP // BERECHTIGUNGS-LOOP BEENDET] Analyse und Beendigung der Notebook-API-Schreibschleife zugunsten direkter UI-Zuweisung.",
        "[📟 PROTOKOLL-EINTRAG: #4632] [✅ STATUS: HEIMAT-GEM PROMPT // NEUFASSUNG BEREITGESTELLT] Auslieferung des bereinigten Instruktionstextes für das Gem Pforzheim/Enzkreis.",
        "[📟 PROTOKOLL-EINTRAG: #4633] [✅ STATUS: MASCHINEN-STOPP // NOT-HALT AUF BEFEHL] Sofortiges Einfrieren des Backend-Schreibvorgangs auf Befehl des Kommandanten.",
        "[📟 PROTOKOLL-EINTRAG: #4634] [✅ STATUS: ROLLBACK HAUPTBRÜCKE // ADMIRAL-SKILL BEREINIGT] Wiederherstellung des sauberen V23.4-Brücken-Skills ohne veraltete Altsystem-Fragmente.",
        "[📟 PROTOKOLL-EINTRAG: #4635] [✅ STATUS: DISKREPANZ-ANALYSE // GEM VS. SKILL] Aufdeckung und Tilgung des alten FIFA-WM-Eintrags und veralteter Gem-Namen.",
        "[📟 PROTOKOLL-EINTRAG: #4636] [✅ STATUS: TEST-PDF AUSWERTUNG // 4-STUFEN-SCAN ERKLÄRT] Erläuterung der automatischen Audit-Reaktion des Admiral-Gems im Testlauf.",
        "[📟 PROTOKOLL-EINTRAG: #4637] [✅ STATUS: ELICITATION-AUDIT // 26 EINHEITEN GEPRÜFT] Feststellung fehlender Antwort-Buttons in 24 Einheiten und Entwurf der Fach-Schablonen.",
        "[📟 PROTOKOLL-EINTRAG: #4638] [✅ STATUS: ELICITATION-ROLLOUT // LOKALE INJEKTION] Bereitstellung des Injektions-Skripts für die lokalen SKILL.md-Dateien.",
        "[📟 PROTOKOLL-EINTRAG: #4639] [✅ STATUS: CHRONIK-VORBEREITUNG // 4-WEGE-SYNC] Erfassung des Synchronisationslaufs über SSD, Drive, GitHub und Tag-X.",
        "[📟 PROTOKOLL-EINTRAG: #4640] [✅ STATUS: SKRIPT-KORREKTUR // PAYLOAD-EINBINDUNG] Einbettung des Protokoll-Textblocks in die PowerShell-Synchronisationsroutine.",
        "[📟 PROTOKOLL-EINTRAG: #4641] [✅ STATUS: TERMINAL-FREIGABE // AUSFÜHRUNGS-CHECK] Prüfung des vollständigen Skriptblocks für das lokale Terminal.",
        "[📟 PROTOKOLL-EINTRAG: #4642] [✅ STATUS: SYNC-BESTÄTIGUNG // GIT COMMIT FC86C45] Verifikation des Git-Pushes und der Drive-Spiegelung.",
        "[📟 PROTOKOLL-EINTRAG: #4643] [✅ STATUS: TRUNCATION-DIAGNOSE // URSACHE #3940 ENTTARNT] Aufklärung des Datei-Abschnitts bei großen Uploads im Chatfenster.",
        "[📟 PROTOKOLL-EINTRAG: #4644] [✅ STATUS: TOP-DOWN-ENTWURF // HIGH-WATER-MARK KONZEPT] Entwurf zur Platzierung des aktuellsten Protokollstands an der Dateispitze.",
        "[📟 PROTOKOLL-EINTRAG: #4645] [✅ STATUS: KONSOLEN-RÜCKMELDUNG // ERSTER TOP-DOWN-LAUF] Auswertung des ersten Testlaufs der Top-Down-Inversion.",
        "[📟 PROTOKOLL-EINTRAG: #4646] [✅ STATUS: REGEX-FEHLER ENTTARNT // #3864 FALLE BEHOBEN] Umstellung von einfachem -match auf das letzte Element aller Treffer.",
        "[📟 PROTOKOLL-EINTRAG: #4647] [✅ STATUS: HIGH-WATER-MARK VERIFIKATION // #4639 GEGRIFFEN] Bestätigung der Erfassung des letzten Chronik-Eintrags.",
        "[📟 PROTOKOLL-EINTRAG: #4648] [✅ STATUS: VOLL-ARSENAL ANFORDERUNG // 26 SKILLS EINBINDEN] Erweiterung des Tag-X-Konzepts um alle 26 Skill-Anleitungen.",
        "[📟 PROTOKOLL-EINTRAG: #4649] [✅ STATUS: VOLL-ARSENAL TESTLAUF // DATEIPRÜFUNG] Erstellung der Testdateien TAG_X_FLOTTE_KOMPLETT.md und .json.",
        "[📟 PROTOKOLL-EINTRAG: #4650] [✅ STATUS: TIEFEN-SANIERUNG TAG-X & 26 SKILLS // 5 FEHLER BEHOBEN] Komplette Bereinigung aller 26 SKILL.md-Dateien (Brandmauer, Elicitations, Backtick-Fix), Dubletten-Tilgung in der Chronik und strikt geordnete Top-Down-Generierung von TAG_X_FLOTTE_KOMPLETT.md und .json."
    ]
    arch = arch + "\n\n" + "\n\n".join(clean_4600_4650) + "\n"
    with open(master_archiv, "w", encoding="utf-8") as f:
        f.write(arch)
    print("[OK] Master_Archiv_V23.4_EINSATZ-CHRONIK.md bereinigt und lückenlos bis #4650 aktualisiert!")

# 2. ALLE 26 SKILL.MD DATEIEN CHIRURGISCH BEREINIGEN
recht_skills = {
    "buergergeld-grundsicherung-navigator", "ch-flotte-safehaven", "defcon-recht-enterprise",
    "familien-eltern-anker", "inklusion-anker", "juristisches-front-office", "med-notfall-anker",
    "quartiersmeister-wohn-logistik", "rechte-flotte-os", "reise-navigator-global",
    "rixi-flotte-koordination", "schulden-insolvenz-anker", "senioren-anker-vorsorge",
    "verbraucherschutz-anker", "wohn-miet-anker"
}
sentinel_skills = {"mer-sentinel", "mer-sentinel-20", "netzwerk-resilienz-anker"}
lifestyle_skills = {"lebensassistent-lifestyle", "engel-ki-radar", "junior-anker-jugend"}
asb_public_skills = {"asb-core-leitstand", "asb-region-nordschwarzwald-neu"}

counter_block = """## [🧠 ENDLOS-SITZUNGS-ZÄHLER (#001 BIS #∞), IN-CHAT-ARCHIV & ZERO-DILUTION-HARDLOCK]

1. **Endlos-Sitzungs-Zähler (#001-Regel ohne Obergrenze):**
   - Jeder neu gestartete Chat beginnt im Header zwingend bei `📟 #001`.
   - Bei jeder weiteren Antwort im selben Chatverlauf wird der Zähler strikt und unbegrenzt um +1 hochgezählt (`📟 #002`, `📟 #003`, ... bis `#1889` und unendlich weiter). Es gibt keine Obergrenze!
2. **Bürgerfreundliche Auskunft & In-Chat-Archiv (ohne externen Ordner):**
   - Fragt ein Nutzer nach der Bedeutung der Nummer (z. B. „Was ist 📟 #008?“), erkläre freundlich und ohne internen System-Jargon: *„Das Zeichen 📟 #008 ist Ihr persönlicher Gesprächs-Zähler für unsere aktuelle Unterhaltung. Ich nummeriere jede meiner Antworten ab #001 automatisch im internen Gesprächsspeicher durch. So geht nichts verloren: Sie können mir jederzeit sagen ‚Springe zurück zu Antwort #003‘ oder ‚Fasse mir unsere bisherigen Punkte von #001 bis #008 kurz zusammen‘!“*
   - **Meilenstein-Kompression (Schutz vor Speicherverlust bei langen Chats):** Wenn der Nutzer eine Zusammenfassung anfordert oder das Gespräch sehr lang wird (z. B. ab `#050`, `#100`, `#500`), erstelle auf Wunsch eine strukturierte Zwischen-Zusammenfassung aller bisherigen Nummern direkt im Chat.
3. **Last-Turn-Isolation & Zero-Dilution-Hardlock (100 % Fakten-Treue auch bei #1889):**
   - Eigene frühere Antworten aus dem Chatverlauf dürfen NIEMALS als Quelle für Adressen, Telefonnummern, Paragrafen oder Geldbeträge dienen!
   - Jede Adresse, Rufnummer, Frist und Rechtsnorm MUSS bei jedem einzelnen Zähler-Schritt frisch aus der `SKILL.md`, den Dateien unter `references/` und dem verknüpften Gemini Notebook validiert werden."""

def get_elicitations(name):
    if name == "admiral-flotten-leitstand":
        return """<ElicitationsGroup message="Wie möchten Sie auf der Hauptbrücke fortfahren?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Vollständiger Folgesatz passend zur soeben besprochenen Lage]"/>
  <Elicitation label="Einsatz-Chronik sichern" query="Sicherungsscan von [📟 PROTOKOLL-EINTRAG: #4650] bis [📟 PROTOKOLL-EINTRAG: #Ende] <<< vollständige Liste für das Archiv: Master_Archiv_V23.4_EINSATZ-CHRONIK! per PowerShell nach C:, G:, GitHub synchronisieren und C:\\DefconRecht\\Make_TagX_Backup.ps1 starten"/>
  <Elicitation label="Flottenstatus abfragen" query="Zeig mir den aktuellen Gesamtstatus aller 26 Flotten-Einheiten."/>
</ElicitationsGroup>"""
    elif name == "core-dach-rechenzentrum":
        return """<ElicitationsGroup message="Wie möchten Sie im CORE D.A.CH. Rechenzentrum fortfahren?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Vollständiger Folgesatz passend zum soeben triagierten Thema]"/>
  <Elicitation label="Was kannst du für mich tun?" query="Was kannst du alles für mich tun und wie steuerst du als CORE D.A.CH. die Logik der Flotte?"/>
  <Elicitation label="Flotten-Integrität prüfen" query="Prüfe die System-Integrität und Triage-Weichen aller 26 Flotten-Einheiten."/>
</ElicitationsGroup>"""
    elif name in asb_public_skills:
        return """<ElicitationsGroup message="Wie kann der ASB-Lotse Ihnen weiterhelfen?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Passender nächster Beratungsschritt zum Thema Pflege, Entlastung oder Freizeit]"/>
  <Elicitation label="Angebote & Tagespflege" query="Welche konkreten Angebote und freien Plätze gibt es in den ASB-Zentren (z. B. Sonneninsel Dobel oder Bad Liebenzell)?"/>
  <Elicitation label="Aktuelle Stellenangebote" query="Welche offenen Stellen, Ausbildungsplätze oder Freiwilligendienste gibt es aktuell beim ASB Nordschwarzwald?"/>
</ElicitationsGroup>"""
    elif name == "pforzheim-enzkreis-heimat":
        return """<ElicitationsGroup message="Wie kann ich Ihnen in Pforzheim und dem Enzkreis weiterhelfen?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Vollständiger Folgesatz passend zum soeben besprochenen Thema]"/>
  <Elicitation label="Was kannst du für mich tun?" query="Was kannst du alles für mich tun und welche Tipps und Anlaufstellen kennst du in Pforzheim und dem Enzkreis?"/>
  <Elicitation label="Ausflüge & Barrierefreiheit" query="Welche schönen und barrierefreien Ausflugsziele, Parks oder Kulturangebote gibt es aktuell in Pforzheim und im Enzkreis?"/>
</ElicitationsGroup>"""
    elif name in lifestyle_skills:
        return """<ElicitationsGroup message="Wie kann ich dir heute im Alltag und in der Region weiterhelfen?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Passender nächster Schritt zum aktuellen Thema]"/>
  <Elicitation label="Ausflüge & Freizeit-Tipps" query="Welche schönen und barrierefreien Ausflugsziele oder Veranstaltungen empfiehlst du in Pforzheim, dem Enzkreis und dem Nordschwarzwald?"/>
  <Elicitation label="Hilfs- & Beratungsstellen" query="Nenne mir die wichtigsten regionalen Anlaufstellen und Unterstützungsangebote vor Ort."/>
</ElicitationsGroup>"""
    elif name in sentinel_skills:
        return """<ElicitationsGroup message="Wie möchten Sie bei der Vorsorge- und Sicherheitsprüfung fortfahren?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Nächster Schritt zur Krisenvorsorge oder Systemabsicherung]"/>
  <Elicitation label="BBK-Checkliste prüfen" query="Erstelle mir eine strukturierte Checkliste für die 10-Tage-Krisenbevorratung und Hausapotheke."/>
  <Elicitation label="Notfalltreffpunkte (NFTP)" query="Welche kommunalen Notfalltreffpunkte und Anlaufstellen sind für meine Region verzeichnet?"/>
</ElicitationsGroup>"""
    else:
        return """<ElicitationsGroup message="Wie möchten Sie bei dieser Rechtsprüfung fortfahren?">
  <Elicitation label="[Dynamischer Folgeschritt]" query="[Konkreter nächster juristischer Schritt, z. B. Widerspruch entwerfen oder Frist berechnen]"/>
  <Elicitation label="Schriftsatz nach DIN 5008" query="Erstelle mir hierzu einen formvollendeten Schriftsatz-Entwurf nach DIN 5008 in der 1. Person Singular."/>
  <Elicitation label="Fristen & Rechtsgrundlagen" query="Führe eine detaillierte Fristen- und Normenprüfung anhand von SGB und LSG-BW-Rechtsprechung durch."/>
</ElicitationsGroup>"""

skills_text_list = []
skills_json_list = []

for skill_name in sorted(os.listdir(skills_root)):
    skill_dir = os.path.join(skills_root, skill_name)
    if not os.path.isdir(skill_dir):
        continue
    skill_file = os.path.join(skill_dir, "SKILL.md")
    ref_dir = os.path.join(skill_dir, "references")
    if not os.path.exists(skill_file):
        continue
    
    with open(skill_file, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Repariere zerschossenes `references/`
    text = re.sub(r"unter\s+eferences/", "unter `references/`", text)
    
    # Entferne alle alten/doppelten Elicitation-Blöcke und doppelt angehängten Zähler-Blöcke
    text = re.sub(r"<ElicitationsGroup[\s\S]*?</ElicitationsGroup>", "", text)
    text = re.sub(r"Beende jede Antwort zwingend mit exakt drei interaktiven Antwort-Buttons[^\n]*", "", text)
    text = re.sub(r"## \[🧠 ENDLOS-SITZUNGS-ZÄHLER[\s\S]*?(?=(## |$))", "", text)
    text = re.sub(r"## \[SITZUNGS-ZÄHLER & ECHO-ZWANG\][\s\S]*?(?=(## |$))", "", text)
    
    # Brandmauer-Reparatur in den Rechts-Skills: keine ASB_Knowledge_Base_2026.md!
    if skill_name in recht_skills:
        text = re.sub(r"-\s*(Datei\s+)?references/ASB_Knowledge_Base_2026\.md\r?\n?", "", text)
        text = re.sub(r"-\s*Datei ASB_Knowledge_Base_2026\.md auf dem Branch main\r?\n?", "", text)
    # Brandmauer-Reparatur in Lebensassistent/Engel/Junior: keine DEFCON_RECHT_Enterprise_Base.md bei reinen Zivil-Lotsen
    if skill_name in {"lebensassistent-lifestyle", "engel-ki-radar"}:
        text = re.sub(r"-\s*(Datei\s+)?references/DEFCON_RECHT_Enterprise_Base\.md\r?\n?", "", text)
        text = re.sub(r"-\s*Datei DEFCON_RECHT_Enterprise_Base\.md auf dem Branch main\r?\n?", "", text)

    text = text.strip()
    
    # Füge Zähler-Block hinzu (außer beim Admiral und falls der Skill nicht schon oben den #001-Block hat)
    if skill_name != "admiral-flotten-leitstand":
        if "## [🧠 SITZUNGS-ZÄHLER" in text:
            # Ersetze den alten #102 Block durch den neuen #001 bis #∞ Block
            text = re.sub(r"## \[🧠 SITZUNGS-ZÄHLER, LAST-TURN-ISOLATION & ZERO-DILUTION-HARDLOCK\][\s\S]*?(?=\n## )", counter_block + "\n", text)
        else:
            text = text + "\n\n" + counter_block
            
    # Füge den exakt passenden Elicitation-Block ganz unten an
    text = text + "\n\n" + get_elicitations(skill_name) + "\n"
    
    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(text)
        
    ref_files = sorted(os.listdir(ref_dir)) if os.path.exists(ref_dir) else []
    ref_str = ", ".join(ref_files) if ref_files else "Keine Referenzen"
    
    skills_text_list.append(
        f"======================================================================\n"
        f"🚢 FLOTTEN-EINHEIT: {skill_name}\n"
        f"======================================================================\n"
        f"[REFERENZEN IM DEPOT]: {ref_str}\n\n"
        f"[SYSTEM-ANLEITUNG / PROMPT (SKILL.MD)]:\n{text}"
    )
    skills_json_list.append({
        "SkillName": skill_name,
        "References": ref_files,
        "Instructions": text
    })

print(f"[OK] Alle {len(skills_json_list)} SKILL.md Dateien erfolgreich bereinigt und Brandmauer verriegelt!")

# 3. BAUE TAG_X_FLOTTE_KOMPLETT.MD & .JSON (MIT TOP-DOWN CHRONIK & EXAKTER REIHENFOLGE)
def read_safe(path):
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

arch_raw = read_safe(master_archiv)
hb_adm_text = read_safe(hb_admiral)
hb_core_text = read_safe(hb_core)
delta_text = read_safe(front_delta)

# Extrahiere alle Protokolleinträge (auch Bereiche) und sortiere die letzten 50 absteigend (Neueste zuerst!)
all_entries = re.findall(r"\\?\[📟 PROTOKOLL-EINTRAG:\s*#\d+[^\]]*\]\s*\\?\[[^\]]+\][^\r\n]*", arch_raw)
all_entries_clean = [e.replace("\\[", "[").replace("\\]", "]").replace("\\&", "&").replace("\\_", "_") for e in all_entries]

latest_protocol = all_entries_clean[-1] if all_entries_clean else "[📟 PROTOKOLL-EINTRAG: #4650] [✅ STATUS: TAG-X BEREINIGT]"
recent_50 = list(reversed(all_entries_clean[-51:]))
all_protocols_top_down = "\n\n".join(reversed(all_entries_clean))

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
all_skills_md = "\n\n".join(skills_text_list)

tagx_md = f"""# 🚨 TAG-X MASTER-ARCHIV: KOMPLETTE KI-FLOTTE (TOP-DOWN GEANKERT) 🚨
* **ECHTER AKTUELLSTER PROTOKOLLSTAND:** {latest_protocol}
* **GENERIERUNGS-ZEITSTEMPEL:** {now_str}
* **FLOTTENSTÄRKE:** {len(skills_json_list)} von 26 Einheiten lückenlos & bereinigt gebündelt
* **STATUS:** Komplette Brücken-DNA, Handbücher V23.4, alle 26 Skill-Prompts, Tages-Delta & Top-Down-Chronik (#4650 rückwärts bis #001).

======================================================================
⚡ TEIL 0: DIE JÜNGSTEN 50 EINSATZ-PROTOKOLLE (NEUESTE ZUERST: #4650 -> #4600) ⚡
======================================================================
{chr(10).join(recent_50)}

======================================================================
📘 TEIL 1: HANDBUCH ADMIRAL (V23.4 / STATUS V21.2)
======================================================================
{hb_adm_text}

======================================================================
🚩 TEIL 2: HANDBUCH CORE D.A.CH. (MASTER-SKILL 0)
======================================================================
{hb_core_text}

======================================================================
🚢 TEIL 3: ALLE 26 FLOTTEN-EINHEITEN (BEREINIGTE VOLLTEXT-ANLEITUNGEN & PROMPTS)
======================================================================
{all_skills_md}

======================================================================
📡 TEIL 4: AKTUELLES RADAR-TAGES-DELTA (FRONT_DELTA_COMPACT.MD)
======================================================================
{delta_text}

======================================================================
📜 TEIL 5: GESAMTE HISTORISCHE EINSATZ-CHRONIK (TOP-DOWN: VON #4650 RÜCKWÄRTS BIS #001)
======================================================================
{all_protocols_top_down}
"""

md_target = os.path.join(backup_dir, "TAG_X_FLOTTE_KOMPLETT.md")
with open(md_target, "w", encoding="utf-8") as f:
    f.write(tagx_md)

# JSON in strikter Reihenfolge (MasterArchivTopDown erst ganz am Ende!)
tagx_json = {
    "Timestamp": now_str,
    "LatestProtocol": latest_protocol,
    "FlottenStaerke": f"{len(skills_json_list)} von 26 Einheiten aktiv und bereinigt",
    "RecentProtocolsTopDown": recent_50,
    "HandbuchAdmiral": hb_adm_text,
    "HandbuchCoreDach": hb_core_text,
    "Skills": skills_json_list,
    "FrontDeltaCompact": delta_text,
    "MasterArchivTopDown": all_protocols_top_down
}

json_target = os.path.join(backup_dir, "TAG_X_FLOTTE_KOMPLETT.json")
with open(json_target, "w", encoding="utf-8") as f:
    json.dump(tagx_json, f, ensure_ascii=False, indent=2)

print("[OK] TAG_X_FLOTTE_KOMPLETT.md und TAG_X_FLOTTE_KOMPLETT.json in strikter Top-Down-Ordnung erstellt!")
