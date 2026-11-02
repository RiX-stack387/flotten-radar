#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M.E.R. Web-Skills Browser-Autopilot (Playwright + Smart-Assist)
Synchronisiert die lokalen references/-Dateien (C:\DefconRecht\SKILLS\*\references)
streng nach der 3-Wege-Brandmauer-Matrix in die Gemini Web-Oberflaeche.
"""
import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import ttk

BASE_DIR = r"C:\DefconRecht"
SKILLS_DIR = r"C:\DefconRecht\SKILLS"
PROFILE_DIR = r"C:\DefconRecht\BrowserProfile"

# 1. Zivil-Front: NUR ASB + Delta
ZIVIL_SKILLS = [
    "asb-region-nordschwarzwald-neu",
    "asb-core-leitstand",
    "pforzheim-enzkreis-heimat",
    "lebensassistent-lifestyle",
    "engel-ki-radar",
    "netzwerk-resilienz-anker"
]

# Alle 25 verbleibenden Einheiten (core-dach-rechenzentrum bereits haendisch erledigt)
TARGET_UNITS = [
    "admiral-flotten-leitstand",
    "pforzheim-enzkreis-heimat",
    "asb-region-nordschwarzwald-neu",
    "asb-core-leitstand",
    "rechte-flotte-os",
    "juristisches-front-office",
    "buergergeld-grundsicherung-navigator",
    "wohn-miet-anker",
    "ch-flotte-safehaven",
    "senioren-anker-vorsorge",
    "inklusion-anker",
    "quartiersmeister-wohn-logistik",
    "familien-eltern-anker",
    "med-notfall-anker",
    "schulden-insolvenz-anker",
    "engel-ki-radar",
    "rixi-flotte-koordination",
    "junior-anker-jugend",
    "netzwerk-resilienz-anker",
    "reise-navigator-global",
    "mer-sentinel",
    "lebensassistent-lifestyle",
    "mer-sentinel-20",
    "verbraucherschutz-anker",
    "defcon-recht-enterprise"
]

def get_files_for_skill(skill_name):
    ref_dir = os.path.join(SKILLS_DIR, skill_name, "references")
    if skill_name in ZIVIL_SKILLS:
        names = ["ASB_Knowledge_Base_2026.md", "Front_Delta_Compact.md"]
    else:
        names = ["DEFCON_RECHT_Enterprise_Base.md", "Front_Delta_Compact.md"]
    return [os.path.join(ref_dir, n) for n in names if os.path.exists(os.path.join(ref_dir, n))]

def launch_debug_browser():
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ]
    exe = next((p for p in chrome_paths if os.path.exists(p)), None)
    if not exe:
        print("[WARNUNG] Weder Chrome noch Edge im Standardpfad gefunden.", flush=True)
        return None
    os.makedirs(PROFILE_DIR, exist_ok=True)
    cmd = [
        exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_DIR}",
        "https://gemini.google.com/"
    ]
    subprocess.Popen(cmd)
    print(f"[BROWSER] Gestartet mit Debug-Port 9222 ({os.path.basename(exe)})", flush=True)
    time.sleep(3)
    return exe

class WebSyncPilotUI:
    def __init__(self):
        self.idx = 0
        self.pw = None
        self.browser = None
        self.page = None

        self.root = tk.Tk()
        self.root.title("🌐 M.E.R. Web-Skill Autopilot (25 Einheiten)")
        self.root.geometry("540x360")
        self.root.configure(bg="#0D1117")
        self.root.attributes("-topmost", True)

        self._build_ui()
        self.root.after(400, self._connect_playwright)
        self._load_current_skill()

    def _build_ui(self):
        f = tk.Frame(self.root, bg="#0D1117", padx=14, pady=12)
        f.pack(fill="both", expand=True)

        self.lbl_progress = tk.Label(f, text="Einheit 1 / 25", font=("Segoe UI", 10, "bold"),
                                     bg="#0D1117", fg="#58A6FF")
        self.lbl_progress.pack(anchor="w")

        self.lbl_skill = tk.Label(f, text="", font=("Segoe UI", 13, "bold"),
                                  bg="#0D1117", fg="#FFFFFF")
        self.lbl_skill.pack(anchor="w", pady=(2, 6))

        self.lbl_matrix = tk.Label(f, text="", font=("Segoe UI", 9, "bold"),
                                   bg="#161B22", fg="#3FB950", padx=8, pady=4)
        self.lbl_matrix.pack(anchor="w", fill="x", pady=4)

        self.lbl_status = tk.Label(f, text="Initialisiere Browser-Verbindung...", font=("Consolas", 9),
                                   bg="#090D13", fg="#C9D1D9", justify="left", anchor="w", padx=8, pady=6)
        self.lbl_status.pack(fill="x", pady=6)

        # Schnell-Buttons zum Kopieren in die Zwischenablage / Auto-Upload
        btn_row1 = tk.Frame(f, bg="#0D1117")
        btn_row1.pack(fill="x", pady=4)

        tk.Button(btn_row1, text="🤖 Auto-Upload (Playwright)", font=("Segoe UI", 9, "bold"),
                  bg="#1F6FEB", fg="#FFFFFF", relief="flat", pady=5,
                  command=self.try_playwright_upload).pack(side="left", expand=True, fill="x", padx=2)

        tk.Button(btn_row1, text="📋 Hauptdatei-Inhalt kopieren", font=("Segoe UI", 9, "bold"),
                  bg="#238636", fg="#FFFFFF", relief="flat", pady=5,
                  command=lambda: self.copy_file_content(0)).pack(side="left", expand=True, fill="x", padx=2)

        tk.Button(btn_row1, text="📋 Delta-Inhalt kopieren", font=("Segoe UI", 9),
                  bg="#21262D", fg="#C9D1D9", relief="flat", pady=5,
                  command=lambda: self.copy_file_content(1)).pack(side="left", expand=True, fill="x", padx=2)

        btn_row2 = tk.Frame(f, bg="#0D1117")
        btn_row2.pack(fill="x", pady=(10, 0))

        tk.Button(btn_row2, text="⏮️ Zurueck", bg="#21262D", fg="#C9D1D9", relief="flat",
                  command=self.prev_skill).pack(side="left", padx=2)

        tk.Button(btn_row2, text="📂 Ordner oeffnen (Drag & Drop)", bg="#21262D", fg="#58A6FF", relief="flat",
                  command=self.open_ref_folder).pack(side="left", expand=True, fill="x", padx=4)

        tk.Button(btn_row2, text="⏭️ Naechster Skill (Erledigt)", font=("Segoe UI", 9, "bold"),
                  bg="#238636", fg="#FFFFFF", relief="flat",
                  command=self.next_skill).pack(side="right", padx=2)

    def _connect_playwright(self):
        launch_debug_browser()
        try:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.connect_over_cdp("http://localhost:9222")
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            self.lbl_status.config(text="✅ Playwright via CDP Port 9222 verbunden!\nWaehle den Skill im Browser oder nutze Direkt-Kopie.")
            print("[OK] Playwright erfolgreich mit Browser verbunden.", flush=True)
        except Exception as e:
            self.lbl_status.config(text=f"ℹ️ Smart-Assist aktiv (Zwischenablage & Drag&Drop bereit).\nPlaywright-Info: {str(e)[:60]}")

    def _load_current_skill(self):
        skill = TARGET_UNITS[self.idx]
        files = get_files_for_skill(skill)
        is_zivil = skill in ZIVIL_SKILLS
        gruppe = "🛡️ ZIVIL-FRONT (NUR ASB + Delta)" if is_zivil else "⚖️ RECHT / ADMIRAL (Enterprise + Delta)"

        self.lbl_progress.config(text=f"Einheit {self.idx + 1} von {len(TARGET_UNITS)}")
        self.lbl_skill.config(text=skill)
        self.lbl_matrix.config(text=f"{gruppe}\nDateien: {', '.join(os.path.basename(p) for p in files)}")

        # Automatisch den Inhalt der ersten Hauptdatei in die Zwischenablage legen
        if files:
            self.copy_file_content(0, silent=True)
            print(f"[{self.idx+1}/{len(TARGET_UNITS)}] Bereit: {skill} -> Hauptdatei liegt bereits in der Zwischenablage (Strg+V)!", flush=True)

    def copy_file_content(self, file_idx, silent=False):
        skill = TARGET_UNITS[self.idx]
        files = get_files_for_skill(skill)
        if file_idx < len(files):
            target = files[file_idx]
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            self.root.update()
            if not silent:
                self.lbl_status.config(text=f"📋 IN ZWISCHENABLAGE KOPIERT:\n{os.path.basename(target)} ({len(data)} Zeichen) -> Jetzt Strg+V druecken!")

    def open_ref_folder(self):
        skill = TARGET_UNITS[self.idx]
        ref_dir = os.path.join(SKILLS_DIR, skill, "references")
        if os.path.exists(ref_dir):
            os.startfile(ref_dir)
            self.lbl_status.config(text=f"📂 Explorer geoeffnet:\n{ref_dir}")

    def try_playwright_upload(self):
        skill = TARGET_UNITS[self.idx]
        files = get_files_for_skill(skill)
        if not self.page:
            self.lbl_status.config(text="⚠️ Keine aktive Playwright-Page. Nutze 'Hauptdatei kopieren' (Strg+V)!")
            return
        try:
            # 1. Versuch: Direktes <input type="file"> im offenen Tab befuellen
            file_inputs = self.page.locator('input[type="file"]')
            if file_inputs.count() > 0:
                file_inputs.first.set_input_files(files)
                self.lbl_status.config(text=f"✅ {len(files)} Dateien per Playwright hochgeladen!\nBitte im Browser auf 'Speichern' klicken.")
                print(f"[AUTO-UPLOAD] {skill}: {len(files)} Dateien injiziert.", flush=True)
                return

            # 2. Versuch: Offenes Textfeld / Editor im Browser mit Hauptdatei-Inhalt fuellen
            editors = self.page.locator('textarea, [contenteditable="true"]')
            if editors.count() > 0 and files:
                with open(files[0], "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                editors.last.fill(content)
                self.lbl_status.config(text=f"✅ Textfeld im Browser automatisch mit {os.path.basename(files[0])} befuellt!")
                print(f"[AUTO-FILL] {skill}: Textfeld automatisch mit {os.path.basename(files[0])} befuellt.", flush=True)
                return

            self.lbl_status.config(text="ℹ️ Kein offenes Upload-/Textfeld im Tab erkannt.\nInhalt liegt in Zwischenablage -> Einfach Strg+V druecken!")
        except Exception as e:
            self.lbl_status.config(text=f"⚠️ Upload-Hinweis: {str(e)[:75]}\nNutze Strg+V (Inhalt ist bereits in Zwischenablage).")

    def next_skill(self):
        if self.idx < len(TARGET_UNITS) - 1:
            self.idx += 1
            self._load_current_skill()
        else:
            self.lbl_status.config(text="🎉 ALLE 25 EINHEITEN ABGESCHLOSSEN!")
            print("[FERTIG] Alle 25 verbleibenden Einheiten wurden synchronisiert!", flush=True)

    def prev_skill(self):
        if self.idx > 0:
            self.idx -= 1
            self._load_current_skill()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    print("=== STARTE M.E.R. WEB-SKILL AUTOPILOT ===", flush=True)
    app = WebSyncPilotUI()
    app.run()