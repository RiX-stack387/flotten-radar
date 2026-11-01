"""
Reiter 1: Radar- & Sensorik-Steuerung (30 / 126 / 78 Slots)
Gehaertet fuer Live-Streaming (Popen, unbuffered) & ohne schwarzes Fenster
"""
import os
import subprocess
import threading
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

        lbl = tk.Label(frame, text="🛰️ RADAR-STEUERUNG & SENSORIK (234 SLOTS)",
                       font=("Segoe UI", 11, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT)
        lbl.pack(anchor="w", pady=(0, 10))

        btn_all = tk.Button(frame, text="🚀 Alle 3 Radar-Scans nacheinander starten",
                            font=("Segoe UI", 10, "bold"), bg=config.COLOR_ACCENT_BLUE, fg=config.COLOR_TEXT_BRIGHT,
                            relief="flat", cursor="hand2", command=self.run_all_scans)
        btn_all.pack(fill="x", pady=4)

        btn_grid = tk.Frame(frame, bg=config.COLOR_BG)
        btn_grid.pack(fill="x", pady=6)

        tk.Button(btn_grid, text="1. Master-Radar (30 Slots)", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_scan("14_Slots_Radar_bereinigt.py")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid, text="2. Praxis PF/ENZ (126 Slots)", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_scan("Zusatz_Leben_Radar.py")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_grid, text="3. Praxis CW/FDS (78 Slots)", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.run_single_scan("Zusatz_Leben_Radar_CW_FDS.py")).pack(side="left", expand=True, fill="x", padx=2)

    def run_all_scans(self):
        threading.Thread(target=self._worker_all, daemon=True).start()

    def _worker_all(self):
        scripts = ["14_Slots_Radar_bereinigt.py", "Zusatz_Leben_Radar.py", "Zusatz_Leben_Radar_CW_FDS.py"]
        self.log("==========================================")
        self.log("🚀 START: TÄGLICHER GESAMT-RADAR-SWEEP")
        self.log("==========================================")
        for s in scripts:
            self._exec_script(s)
        self.log("✅ Gesamter Radar-Sweep vollstaendig abgeschlossen!")

    def run_single_scan(self, script_name):
        threading.Thread(target=lambda: self._exec_script(script_name), daemon=True).start()

    def _exec_script(self, script_name):
        path = os.path.join(config.DIR_LOCAL_BASE, script_name)
        if not os.path.exists(path):
            self.log(f"⚠️ Datei nicht gefunden: {path}")
            return
        self.log(f"[START] Fuehre {script_name} aus...")

        custom_env = os.environ.copy()
        custom_env["PYTHONIOENCODING"] = "utf-8"
        custom_env["PYTHONUTF8"] = "1"

        # Unterdrueckt das leere schwarze Konsolenfenster
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        # -u fuer ungepuffertes Echtzeit-Streaming
        proc = subprocess.Popen(
            ["python", "-u", path],
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