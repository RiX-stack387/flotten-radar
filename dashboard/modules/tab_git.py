"""
Reiter 4: Git- & Versions-Zentrale
"""
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import config

class GitTab(ttk.Frame):
    def __init__(self, parent, log_callback):
        super().__init__(parent)
        self.log = log_callback
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self, bg=config.COLOR_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        lbl = tk.Label(frame, text="🐙 GIT- & REPOSITORY-ZENTRALE",
                       font=("Segoe UI", 11, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT)
        lbl.pack(anchor="w", pady=(0, 10))

        # Commit Box
        commit_card = tk.Frame(frame, bg=config.COLOR_CARD, padx=10, pady=10)
        commit_card.pack(fill="x", pady=4)

        tk.Label(commit_card, text="Commit-Nachricht:", bg=config.COLOR_CARD, fg=config.COLOR_TEXT).pack(anchor="w")
        self.entry_msg = tk.Entry(commit_card, font=("Segoe UI", 10))
        self.entry_msg.pack(fill="x", pady=4)
        self.entry_msg.insert(0, "feat: Flotten-Update")

        btn_row = tk.Frame(commit_card, bg=config.COLOR_CARD)
        btn_row.pack(fill="x", pady=4)

        tk.Button(btn_row, text="1. Status pruefen", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=self.check_status).pack(side="left", padx=2)
        tk.Button(btn_row, text="2. Letzte 5 Commits", bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=self.show_log).pack(side="left", padx=2)
        tk.Button(btn_row, text="🚀 3. Add, Commit & Push", bg=config.COLOR_ACCENT_BLUE, fg="white", relief="flat",
                  command=self.push_changes).pack(side="right", padx=2)

    def check_status(self):
        threading.Thread(target=lambda: self._run_git("status --short", "Git Status")).start()

    def show_log(self):
        threading.Thread(target=lambda: self._run_git("log -n 5 --oneline", "Letzte 5 Commits")).start()

    def push_changes(self):
        msg = self.entry_msg.get().strip()
        if not msg:
            messagebox.showwarning("Warnung", "Bitte eine Commit-Nachricht eingeben!")
            return
        threading.Thread(target=lambda: self._worker_push(msg), daemon=True).start()

    def _worker_push(self, msg):
        self.log(f"[GIT] Fuehre Push mit Nachricht: '{msg}' aus...")
        self._run_git("add -A", "git add")
        self._run_git(f'commit -m "{msg}"', "git commit")
        self._run_git("push origin main", "git push")
        self.log("✅ Git Push abgeschlossen.")

    def _run_git(self, git_args, title=""):
        cmd = f'Set-Location "{config.DIR_LOCAL_BASE}"; git {git_args}'
        res = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, text=True)
        self.log(f"--- {title} ---")
        if res.stdout:
            self.log(res.stdout.strip())
        if res.stderr:
            self.log(f"[HINWEIS] {res.stderr.strip()}")
