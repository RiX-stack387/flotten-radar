"""
Reiter 2: 3-Wege-Paritaet & Flotten-Ampel fuer alle 26 Einheiten
"""
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
import config

class ParityTab(ttk.Frame):
    def __init__(self, parent, log_callback):
        super().__init__(parent)
        self.log = log_callback
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self, bg=config.COLOR_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        header = tk.Frame(frame, bg=config.COLOR_BG)
        header.pack(fill="x", pady=(0, 8))

        lbl = tk.Label(header, text="🚦 3-WEGE-PARITÄT & FLOTTEN-AMPEL",
                       font=("Segoe UI", 11, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT)
        lbl.pack(side="left")

        btn_check = tk.Button(header, text="🔍 Jetzt pruefen", font=("Segoe UI", 9, "bold"),
                              bg=config.COLOR_ACCENT_GREEN, fg=config.COLOR_TEXT_BRIGHT, relief="flat",
                              command=self.check_parity)
        btn_check.pack(side="right", padx=4)

        btn_sync = tk.Button(header, text="⚡ Robocopy /MIR Sync", font=("Segoe UI", 9, "bold"),
                             bg=config.COLOR_ACCENT_BLUE, fg=config.COLOR_TEXT_BRIGHT, relief="flat",
                             command=self.run_sync)
        btn_sync.pack(side="right", padx=4)

        columns = ("unit", "local", "cloud", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree.heading("unit", text="Flotten-Einheit (26)")
        self.tree.heading("local", text="SSD (C:)")
        self.tree.heading("cloud", text="Drive (G:)")
        self.tree.heading("status", text="Paritaet")

        self.tree.column("unit", width=220)
        self.tree.column("local", width=80, anchor="center")
        self.tree.column("cloud", width=80, anchor="center")
        self.tree.column("status", width=90, anchor="center")
        self.tree.pack(fill="both", expand=True)

        for u in config.FLEET_UNITS:
            self.tree.insert("", "end", values=(u, "---", "---", "Ungeprueft"))

    def check_parity(self):
        threading.Thread(target=self._worker_check, daemon=True).start()

    def _worker_check(self):
        self.log("[AMPEL] Pruefe Vorhandensein aller 26 Einheiten auf SSD & G:...")
        for item in self.tree.get_children():
            self.tree.delete(item)

        for u in config.FLEET_UNITS:
            loc = os.path.exists(os.path.join(config.DIR_LOCAL_SKILLS, u, "SKILL.md"))
            cld = os.path.exists(os.path.join(config.DIR_CLOUD_SKILLS, u, "SKILL.md"))
            loc_txt = "✅ Da" if loc else "❌ Fehlt"
            cld_txt = "✅ Da" if cld else "❌ Fehlt"
            stat = "🟢 Synchron" if (loc and cld) else ("🟡 Lokal only" if loc else "🔴 Alarm")
            self.tree.insert("", "end", values=(u, loc_txt, cld_txt, stat))
        self.log("✅ Ampel-Pruefung abgeschlossen.")

    def run_sync(self):
        threading.Thread(target=self._worker_sync, daemon=True).start()

    def _worker_sync(self):
        self.log(f"[SYNC] Robocopy {config.DIR_LOCAL_SKILLS} -> {config.DIR_CLOUD_SKILLS}...")
        cmd = f'robocopy "{config.DIR_LOCAL_SKILLS}" "{config.DIR_CLOUD_SKILLS}" /MIR /R:2 /W:2 /NDL /NFL /XD ".git" "_backup"'
        res = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, text=True)
        self.log(f"[SYNC] Robocopy beendet mit Exit-Code {res.returncode}")
        self._worker_check()
