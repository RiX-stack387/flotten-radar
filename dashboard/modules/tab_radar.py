"""
Reiter 1: Radar- & Sensorik-Steuerung (Komplette 8-Stufen-Pipeline)
Inklusive ASB-Radar, Enterprise-Kompilierung, Front-Delta, Drive-Stream & 3-Wege-Brandmauer-Sync
"""
import os
import re
import glob
import shutil
import subprocess
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import config

class RadarTab(ttk.Frame):
    def __init__(self, parent, log_callback):
        super().__init__(parent)
        self.log = log_callback
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self, bg=config.COLOR_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        lbl = tk.Label(frame, text="🛰️ RADAR-STEUERUNG & 8-STUFEN-WISSENS-PIPELINE",
                       font=("Segoe UI", 11, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT)
        lbl.pack(anchor="w", pady=(0, 8))

        # 1. Hauptbutton: Kompletter 8-Stufen-Durchlauf (Start_Flotte.py ohne Standby)
        btn_all = tk.Button(frame, text="🚀 Kompletten 8-Stufen-Flotten-Sweep starten (Start_Flotte.py)",
                            font=("Segoe UI", 10, "bold"), bg=config.COLOR_ACCENT_BLUE, fg=config.COLOR_TEXT_BRIGHT,
                            relief="flat", cursor="hand2", pady=4, command=self.run_full_fleet_pipeline)
        btn_all.pack(fill="x", pady=3)

        # 2. Turbo-Button: Direkt ab Stufe 4 (ASB + Wissens-Bau + 3-Wege-Verteilung in references/)
        btn_turbo = tk.Button(frame, text="⚡ Turbo-Pipeline ab Stufe 4: ASB + Wissens-Bau + 3-Wege-Sync (references/ & G:)",
                              font=("Segoe UI", 10, "bold"), bg=config.COLOR_ACCENT_GREEN, fg=config.COLOR_TEXT_BRIGHT,
                              relief="flat", cursor="hand2", pady=4, command=self.run_turbo_pipeline)
        btn_turbo.pack(fill="x", pady=3)

        # 3. Einzel-Steuerung (Zeile 1: Die 4 Radar-Sensoren)
        btn_grid1 = tk.Frame(frame, bg=config.COLOR_BG)
        btn_grid1.pack(fill="x", pady=(8, 3))

        tk.Button(btn_grid1, text="1. Master (30 Slots)", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_script("14_Slots_Radar_bereinigt.py")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid1, text="2. PF/ENZ (126 Slots)", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_script("Zusatz_Leben_Radar.py")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid1, text="3. CW/FDS (78 Slots)", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_script("Zusatz_Leben_Radar_CW_FDS.py")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid1, text="4. ASB-Radar", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_script("asb_nsw_radar.py")).pack(side="left", expand=True, fill="x", padx=2)

        # 4. Einzel-Steuerung (Zeile 2: Wissens-Bau & Brandmauer-Verteiler)
        btn_grid2 = tk.Frame(frame, bg=config.COLOR_BG)
        btn_grid2.pack(fill="x", pady=3)

        tk.Button(btn_grid2, text="5. Enterprise-Base bauen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_script("build_enterprise_knowledge.py")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid2, text="6. Front-Delta bauen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: threading.Thread(target=self._build_front_delta, daemon=True).start()).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid2, text="7. 3-Wege-Brandmauer-Sync (Sync_DefconRecht.ps1)", bg="#21262D", fg="#58A6FF", relief="flat",
                  command=lambda: threading.Thread(target=self._exec_ps1, args=("Sync_DefconRecht.ps1",), daemon=True).start()).pack(side="left", expand=True, fill="x", padx=2)

    def run_full_fleet_pipeline(self):
        threading.Thread(target=self._worker_full_fleet, daemon=True).start()

    def _worker_full_fleet(self):
        self.log("==========================================")
        self.log("🚀 START: KOMPLETTER 8-STUFEN-FLOTTEN-SWEEP (Start_Flotte.py)")
        self.log("==========================================")
        self._exec_script("Start_Flotte.py")
        self.log("✅ Kompletter 8-Stufen-Flotten-Sweep abgeschlossen!")

    def run_turbo_pipeline(self):
        threading.Thread(target=self._worker_turbo, daemon=True).start()

    def _worker_turbo(self):
        self.log("==========================================")
        self.log("⚡ START: TURBO-PIPELINE AB STUFE 4 (WISSENS-BAU & 3-WEGE-VERTEILUNG)")
        self.log("==========================================")

        # Stufe 4: ASB-Radar & Copy
        self._exec_script("asb_nsw_radar.py")
        live_asb = os.path.join(config.DIR_LOCAL_BASE, "ASB", "ASB_Knowledge_Base_LIVE.md")
        legacy_asb = os.path.join(config.DIR_LOCAL_BASE, "ASB_Knowledge_Base_2026.md")
        if os.path.exists(live_asb):
            shutil.copy2(live_asb, legacy_asb)
            self.log("[ASB-COPY] ASB_Knowledge_Base_LIVE.md -> ASB_Knowledge_Base_2026.md aktualisiert.")

        # Stufe 5: Enterprise Knowledge Base
        self._exec_script("build_enterprise_knowledge.py")

        # Stufe 6: Front Delta Compact
        self._build_front_delta()

        # Stufe 7: Drive-Stream (In-Place Sync fuer Stammdateien & MasterLogs)
        self._sync_drive_base()

        # Stufe 8: 3-Wege-Brandmauer-Verteilung in alle 26 references/ (C:\ & G:\) + Git-Push
        self._exec_ps1("Sync_DefconRecht.ps1")

        self.log("✅ TURBO-PIPELINE VOLLSTÄNDIG ABGESCHLOSSEN! Alle references/ auf C: und G: sind aktuell.")

    def run_single_script(self, script_name):
        threading.Thread(target=lambda: self._exec_script(script_name), daemon=True).start()

    def _build_front_delta(self):
        self.log("[FRONT-SYNC] Komprimiere Tages-Deltas fuer Front_Delta_Compact.md...")
        today_str = datetime.now().strftime("%Y-%m-%d")
        delta_file = os.path.join(config.DIR_LOCAL_BASE, "Front_Delta_Compact.md")
        lines = [f"RADAR-DELTA COMPACT ({today_str})"]
        log_dir = os.path.join(config.DIR_LOCAL_BASE, "MasterLogs")
        sec_pattern = re.compile(r"^===\s*([^=\r\n]+?)\s*===\s*$", re.MULTILINE)
        claim_pattern = re.compile(r"\[GE(?:Ä|A|Ã„|Ãƒâ€ž)NDERT/NEU\]\s*Norm/AZ:\s*([^|\r\n]+)\|\s*Wert:\s*([^\r\n(]+)")

        for lf in sorted(glob.glob(os.path.join(log_dir, f"*{today_str}*.txt"))):
            try:
                with open(lf, "r", encoding="utf-8", errors="replace") as f:
                    raw = f.read()
                active_part = re.split(r"\[(?:🟢|ðŸŸ¢)\s*SICHERER PERIMETER", raw)[0]
                matches = list(sec_pattern.finditer(active_part))
                for i, m in enumerate(matches):
                    sec_title = m.group(1).strip()
                    start_pos = m.end()
                    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(active_part)
                    block = active_part[start_pos:end_pos]
                    for cm in claim_pattern.finditer(block):
                        norm = cm.group(1).strip()
                        val = cm.group(2).strip()
                        lines.append(f"- [{sec_title}] {norm}: {val}")
            except Exception as e:
                self.log(f" -> Fehler beim Lesen von {lf}: {e}")

        if len(lines) == 1:
            lines.append("- Keine kritischen Rechtsaenderungen erfasst. Perimeter stabil.")

        with open(delta_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.log(f" -> Front_Delta_Compact.md sauber aktualisiert ({len(lines)-1} Eintraege).")

    def _sync_in_place(self, src, dst):
        if not os.path.exists(src):
            return
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "rb") as fsrc:
            data = fsrc.read()
        if os.path.exists(dst):
            with open(dst, "r+b") as fdst:
                fdst.seek(0)
                fdst.write(data)
                fdst.truncate()
            self.log(f" -> [SYNC-STREAM] {os.path.basename(src)} aktualisiert (Drive-ID behalten).")
        else:
            with open(dst, "wb") as fdst:
                fdst.write(data)
            self.log(f" -> [SYNC-CREATE] {os.path.basename(src)} neu angelegt.")

    def _sync_drive_base(self):
        drive_base = r"G:\Meine Ablage\DefconRecht"
        if not os.path.exists(drive_base):
            self.log("[WARNUNG] Google Drive Stammverzeichnis G: nicht erreichbar.")
            return

        self.log("[DRIVE-STREAM] Synchronisiere Stammdateien & MasterLogs nach G:...")
        drive_logs = os.path.join(drive_base, "MasterLogs")
        os.makedirs(drive_logs, exist_ok=True)

        files_to_stream = [
            ("DEFCON_RECHT_Enterprise_Base.md", "DEFCON_RECHT_Enterprise_Base.md"),
            ("Front_Delta_Compact.md", "Front_Delta_Compact.md"),
            ("ASB_Knowledge_Base_2026.md", "ASB_Knowledge_Base_2026.md"),
            (os.path.join("ASB", "ASB_Knowledge_Base_LIVE.md"), os.path.join("ASB", "ASB_Knowledge_Base_LIVE.md")),
            ("quellen_registry.py", "quellen_registry.py")
        ]
        for rel_src, rel_dst in files_to_stream:
            self._sync_in_place(
                os.path.join(config.DIR_LOCAL_BASE, rel_src),
                os.path.join(drive_base, rel_dst)
            )

        for lf in glob.glob(os.path.join(config.DIR_LOCAL_BASE, "MasterLogs", "*")):
            if os.path.isfile(lf):
                shutil.copy2(lf, os.path.join(drive_logs, os.path.basename(lf)))
        self.log("[EXPORT] Alle Stammdateien und MasterLogs nach Google Drive synchronisiert.")

    def _exec_script(self, script_name):
        path = os.path.join(config.DIR_LOCAL_BASE, script_name)
        if not os.path.exists(path):
            self.log(f"⚠️ Datei nicht gefunden: {path}")
            return
        self.log(f"[START] Fuehre {script_name} aus...")

        custom_env = os.environ.copy()
        custom_env["PYTHONIOENCODING"] = "utf-8"
        custom_env["PYTHONUTF8"] = "1"
        custom_env["PYTHONUNBUFFERED"] = "1"

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        proc = subprocess.Popen(
            ["python", "-u", path],
            cwd=config.DIR_LOCAL_BASE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=custom_env,
            creationflags=creation_flags
        )

        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                clean_line = line.rstrip()
                if clean_line:
                    self.log(clean_line)
            proc.stdout.close()

        return_code = proc.wait()
        self.log(f"[ENDE] {script_name} beendet mit Code {return_code}")

    def _exec_ps1(self, ps1_name):
        path = os.path.join(config.DIR_LOCAL_BASE, ps1_name)
        if not os.path.exists(path):
            self.log(f"⚠️ PowerShell-Skript nicht gefunden: {path}")
            return
        self.log(f"[START] Fuehre PowerShell-Pipeline {ps1_name} aus...")

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path],
            cwd=config.DIR_LOCAL_BASE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags
        )

        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                clean_line = line.rstrip()
                if clean_line:
                    self.log(clean_line)
            proc.stdout.close()

        return_code = proc.wait()
        self.log(f"[ENDE] {ps1_name} beendet mit Code {return_code}")