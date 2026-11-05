"""
M.E.R. Flotten-Radar - Web-Skill Autopilot (Playwright)
Stand: 03.11.2026
Automatischer Upload aller Referenzdateien direkt in gemini.google.com/customize/skills
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(r"C:\DefconRecht")
SKILLS_DIR = BASE_DIR / "SKILLS"
CDP_URL = "http://localhost:9222"

ALL_SKILLS = [
    "admiral-flotten-leitstand",
    "asb-region-nordschwarzwald-neu",
    "asb-core-leitstand",
    "pforzheim-enzkreis-heimat",
    "rechte-flotte-os",
    "buergergeld-grundsicherung-navigator",
    "quartiersmeister-wohn-logistik",
    "wohn-miet-anker",
    "inklusion-anker",
    "familien-eltern-anker",
    "schulden-insolvenz-anker",
    "junior-anker-jugend",
    "verbraucherschutz-anker",
    "senioren-anker-vorsorge",
    "core-dach-rechenzentrum",
    "defcon-recht-enterprise",
    "ch-flotte-safehaven",
    "reise-navigator-global",
    "lebensassistent-lifestyle",
    "mer-sentinel-20",
    "mer-sentinel",
    "netzwerk-resilienz-anker",
    "engel-ki-radar",
    "med-notfall-anker",
    "rixi-flotte-koordination",
    "juristisches-front-office"
]

def sync_single_skill_references(page, skill_name: str):
    ref_dir = SKILLS_DIR / skill_name / "references"
    if not ref_dir.exists():
        print(f"  [SKIP] Kein references/-Ordner fuer {skill_name}")
        return

    target_files = [str(f.resolve()) for f in ref_dir.glob("*.md")]
    if not target_files:
        print(f"  [SKIP] Keine .md-Dateien in {ref_dir}")
        return

    print(f"  -> Uebertrage {len(target_files)} Referenzen: {[Path(p).name for p in target_files]}")

    file_input = page.locator('input[type="file"]')
    if file_input.count() == 0:
        add_btn = page.locator('button:has-text("Dateien hinzufügen"), [aria-label*="Datei"]')
        if add_btn.count() > 0:
            add_btn.first.click()
            time.sleep(0.5)

    if file_input.count() > 0:
        file_input.first.set_input_files(target_files)
        print(f"  [OK] Dateiupload via Playwright uebergeben.")
        time.sleep(1.5)

        save_btn = page.locator('button:has-text("Speichern"), button:has-text("Aktualisieren")')
        if save_btn.count() > 0 and save_btn.first.is_enabled():
            save_btn.first.click()
            print(f"  [SAVED] Gespeichert.")
            time.sleep(1.0)
        else:
            print("  [INFO] Entwurf gesichert oder Datei bereits identisch.")
    else:
        print("  [WARNUNG] Kein file-input Element im offenen Tab gefunden!")

def main():
    print("=== STARTE M.E.R. WEB-SKILL AUTOPILOT (DATEI-UPLOAD-MODUS) ===")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            print("[OK] Verbindung mit Chrome (Port 9222) steht.")
        except Exception as e:
            print(f"[FEHLER] Keine Verbindung zu Chrome: {e}")
            print("Chrome muss mit '--remote-debugging-port=9222' geoeffnet sein.")
            sys.exit(1)

        contexts = browser.contexts
        if not contexts or not contexts[0].pages:
            print("[FEHLER] Kein offener Tab gefunden.")
            sys.exit(1)

        pages = contexts[0].pages
        active_page = pages[0]
        for pg in pages:
            if "gemini.google.com" in pg.url:
                active_page = pg
                break

        print(f"[TAB] Aktive Web-Adresse: {active_page.url}")

        current_url = active_page.url
        matched_skill = None
        for skill in ALL_SKILLS:
            if skill in current_url:
                matched_skill = skill
                break

        if matched_skill:
            print(f"\n[FOKUS] Synchronisiere aktuell geoeffneten Skill: {matched_skill}")
            sync_single_skill_references(active_page, matched_skill)
        else:
            print("\n[BATCH-MODUS] Bearbeite sichtbare Einheiten in der Liste...")
            for idx, skill in enumerate(ALL_SKILLS, 1):
                ref_dir = SKILLS_DIR / skill / "references"
                if not ref_dir.exists():
                    continue

                skill_entry = active_page.locator(f'text="{skill}"')
                if skill_entry.count() > 0:
                    print(f"\n[{idx}/{len(ALL_SKILLS)}] Oeffne: {skill}")
                    skill_entry.first.click()
                    active_page.wait_for_load_state("domcontentloaded")
                    time.sleep(1.2)
                    sync_single_skill_references(active_page, skill)
                    back_btn = active_page.locator('button:has-text("Skills"), [aria-label*="Zurück"]')
                    if back_btn.count() > 0:
                        back_btn.first.click()
                        time.sleep(1.0)

    print("\n=== [FERTIG] Autopilot-Lauf beendet! ===")

if __name__ == "__main__":
    main()
