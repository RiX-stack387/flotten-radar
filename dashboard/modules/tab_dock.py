"""
Reiter 5: System-Dock & Komfort (Verknuepfungen & Tools)
"""
import os
import subprocess
import tkinter as tk
from tkinter import ttk
import config

class DockTab(ttk.Frame):
    def __init__(self, parent, log_callback):
        super().__init__(parent)
        self.log = log_callback
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self, bg=config.COLOR_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        lbl = tk.Label(frame, text="🧭 SYSTEM-DOCK & SCHNELLSTARTER",
                       font=("Segoe UI", 11, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT)
        lbl.pack(anchor="w", pady=(0, 10))

        card = tk.Frame(frame, bg=config.COLOR_CARD, padx=10, pady=10)
        card.pack(fill="x", pady=4)

        tk.Label(card, text="Wichtige Verzeichnisse & Arbeitsbereiche:", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Button(card, text="📁 C:\DefconRecht im Explorer oeffnen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat", anchor="w", padx=8,
                  command=lambda: self.open_path(config.DIR_LOCAL_BASE)).pack(fill="x", pady=2)
        tk.Button(card, text="📁 C:\DefconRecht\SKILLS oeffnen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat", anchor="w", padx=8,
                  command=lambda: self.open_path(config.DIR_LOCAL_SKILLS)).pack(fill="x", pady=2)
        tk.Button(card, text="☁️ Google Drive (G:\) oeffnen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat", anchor="w", padx=8,
                  command=lambda: self.open_path(config.DIR_CLOUD_SKILLS)).pack(fill="x", pady=2)

        card2 = tk.Frame(frame, bg=config.COLOR_CARD, padx=10, pady=10)
        card2.pack(fill="x", pady=8)

        tk.Label(card2, text="Externe Werkzeuge:", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Button(card2, text="💻 PowerShell Terminal in C:\DefconRecht starten", bg="#21262D", fg=config.COLOR_TEXT, relief="flat", anchor="w", padx=8,
                  command=self.open_powershell).pack(fill="x", pady=2)
        tk.Button(card2, text="🌐 GitHub Repository im Browser aufrufen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat", anchor="w", padx=8,
                  command=self.open_github).pack(fill="x", pady=2)

    def open_path(self, path):
        if os.path.exists(path):
            os.startfile(path)
            self.log(f"[INFO] Ordner geoeffnet: {path}")
        else:
            self.log(f"⚠️ Pfad existiert nicht: {path}")

    def open_powershell(self):
        subprocess.Popen(["powershell.exe", "-NoExit", "-Command", f'Set-Location "{config.DIR_LOCAL_BASE}"'])
        self.log("[INFO] PowerShell-Konsole gestartet.")

    def open_github(self):
        import webbrowser
        webbrowser.open("https://github.com/RiX-stack387/flotten-radar")
        self.log("[INFO] GitHub aufgerufen.")
