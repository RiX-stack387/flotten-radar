"""
M.E.R. FLOTTEN-DASHBOARD // HAUPTPROGRAMM (MODULAR)
Initialisiert das ttk.Notebook und bindet alle 5 Funktions-Module ein.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import config
from modules.tab_radar import RadarTab
from modules.tab_parity import ParityTab
from modules.tab_deadlines import DeadlinesTab
from modules.tab_git import GitTab
from modules.tab_dock import DockTab

class ModularFleetDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("M.E.R. Flotten-Dashboard // Hauptbruecke (Modular)")
        self.root.geometry("680x760")
        self.root.configure(bg=config.COLOR_BG)
        self.root.minsize(620, 700)

        self._apply_style()
        self._build_header()
        self._build_notebook()
        self._build_console()
        self._build_footer()

    def _apply_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=config.COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=config.COLOR_CARD, foreground=config.COLOR_TEXT, padding=[10, 5], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", config.COLOR_ACCENT_BLUE)], foreground=[("selected", "#FFFFFF")])
        style.configure("Treeview", background=config.COLOR_CARD, foreground=config.COLOR_TEXT, fieldbackground=config.COLOR_CARD, rowheight=24)
        style.configure("Treeview.Heading", background="#21262D", foreground=config.COLOR_TEXT_BRIGHT, font=("Segoe UI", 9, "bold"))

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=config.COLOR_BG, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🧑‍✈️ M.E.R. FLOTTEN-DASHBOARD // MODULAR V21.2",
                 font=("Segoe UI", 13, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT).pack()
        tk.Label(hdr, text="Hauptbruecken-Leitstand mit 5 integrierten Funktions-Reitern",
                 font=("Segoe UI", 8), bg=config.COLOR_BG, fg="#8B949E").pack()

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=4)

        self.tab_radar = RadarTab(self.notebook, self.log)
        self.tab_parity = ParityTab(self.notebook, self.log)
        self.tab_deadlines = DeadlinesTab(self.notebook, self.log)
        self.tab_git = GitTab(self.notebook, self.log)
        self.tab_dock = DockTab(self.notebook, self.log)

        self.notebook.add(self.tab_radar, text="🛰️ Radar")
        self.notebook.add(self.tab_parity, text="🚦 3-Wege-Ampel")
        self.notebook.add(self.tab_deadlines, text="⚖️ Fristen")
        self.notebook.add(self.tab_git, text="🐙 Git")
        self.notebook.add(self.tab_dock, text="🧭 Dock")

    def _build_console(self):
        con_frame = tk.Frame(self.root, bg=config.COLOR_BG, padx=12, pady=4)
        con_frame.pack(fill="both", expand=True)

        tk.Label(con_frame, text="ZENTRALES LOGBUCH:", font=("Segoe UI", 8, "bold"), bg=config.COLOR_BG, fg="#8B949E").pack(anchor="w")

        self.txt_console = scrolledtext.ScrolledText(
            con_frame, wrap=tk.WORD, height=8,
            bg=config.COLOR_CONSOLE_BG, fg=config.COLOR_CONSOLE_FG,
            insertbackground="white", font=("Consolas", 9), bd=1, relief="solid"
        )
        self.txt_console.pack(fill="both", expand=True, pady=2)
        self.log("[SYSTEM] Modulares Dashboard betriebsbereit. Alle 5 Module online.")

    def _build_footer(self):
        ft = tk.Frame(self.root, bg=config.COLOR_BG, pady=6, padx=12)
        ft.pack(fill="x")
        tk.Button(ft, text="Log leeren", font=("Segoe UI", 8), bg="#21262D", fg=config.COLOR_TEXT, relief="flat",
                  command=lambda: self.txt_console.delete("1.0", tk.END)).pack(side="left")
        tk.Button(ft, text="Beenden", font=("Segoe UI", 8), bg="#21262D", fg="#8B949E", relief="flat",
                  command=self.root.destroy).pack(side="right")

    def log(self, msg):
        self.txt_console.insert(tk.END, msg + "\n")
        self.txt_console.see(tk.END)

if __name__ == "__main__":
    app_root = tk.Tk()
    app = ModularFleetDashboard(app_root)
    app_root.mainloop()
