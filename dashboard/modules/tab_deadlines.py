"""
Reiter 3: Fristenwaechter & DEFCON-Lage (§ 37 SGB X / § 84 SGG)
"""
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import config

class DeadlinesTab(ttk.Frame):
    def __init__(self, parent, log_callback):
        super().__init__(parent)
        self.log = log_callback
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self, bg=config.COLOR_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        lbl = tk.Label(frame, text="⚖️ FRISTENWÄCHTER & TAKTISCHE DEFCON-LAGE",
                       font=("Segoe UI", 11, "bold"), bg=config.COLOR_BG, fg=config.COLOR_TEXT_BRIGHT)
        lbl.pack(anchor="w", pady=(0, 10))

        # Rechner Card
        calc_card = tk.Frame(frame, bg=config.COLOR_CARD, padx=10, pady=10)
        calc_card.pack(fill="x", pady=4)

        tk.Label(calc_card, text="Bescheiddatum (TT.MM.JJJJ):", bg=config.COLOR_CARD, fg=config.COLOR_TEXT).grid(row=0, column=0, sticky="w", pady=4)
        self.entry_date = tk.Entry(calc_card, width=15, font=("Consolas", 10))
        self.entry_date.insert(0, datetime.date.today().strftime("%d.%m.%Y"))
        self.entry_date.grid(row=0, column=1, padx=8, pady=4)

        btn_calc = tk.Button(calc_card, text="📅 Frist berechnen", bg=config.COLOR_ACCENT_BLUE, fg="white",
                             relief="flat", command=self.calculate_deadline)
        btn_calc.grid(row=0, column=2, padx=8, pady=4)

        self.lbl_result = tk.Label(calc_card, text="Ergebnis: Bitte Bescheiddatum eingeben.",
                                   font=("Segoe UI", 9, "bold"), bg=config.COLOR_CARD, fg="#58A6FF")
        self.lbl_result.grid(row=1, column=0, columnspan=3, sticky="w", pady=6)

        # DEFCON Schalter Card
        defcon_card = tk.Frame(frame, bg=config.COLOR_CARD, padx=10, pady=10)
        defcon_card.pack(fill="x", pady=10)

        tk.Label(defcon_card, text="DEFCON-STATUS DER FLOTTE:", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        btn_row = tk.Frame(defcon_card, bg=config.COLOR_CARD)
        btn_row.pack(fill="x", pady=6)

        tk.Button(btn_row, text="DEFCON 1 (Gefecht / Angriff)", bg="#DA3633", fg="white", relief="flat",
                  command=lambda: self.set_defcon("DEFCON 1 - Hohe Alarmstufe (Behoerden-Gegenschlag aktiv)")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_row, text="DEFCON 3 (Wachbetrieb)", bg="#D29922", fg="white", relief="flat",
                  command=lambda: self.set_defcon("DEFCON 3 - Normaler Wachbetrieb")).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_row, text="DEFCON ZIVIL (Frieden)", bg="#238636", fg="white", relief="flat",
                  command=lambda: self.set_defcon("DEFCON ZIVIL - Ziviler Friedens- und Lotsen-Fokus")).pack(side="left", expand=True, fill="x", padx=2)

    def calculate_deadline(self):
        raw = self.entry_date.get().strip()
        try:
            bescheid_dt = datetime.datetime.strptime(raw, "%d.%m.%Y").date()
            # 3-Tage-Fiktion nach § 37 Abs. 2 SGB X
            zugang_dt = bescheid_dt + datetime.timedelta(days=3)
            # 1 Monat Frist nach § 84 SGG / § 64 SGG
            # Vereinfachte Berechnung + 30 Tage / Folgemonat
            frist_ende = zugang_dt + datetime.timedelta(days=30)
            diff = (frist_ende - datetime.date.today()).days
            res_txt = f"Bekanntgabe (§ 37 SGB X): {zugang_dt.strftime('%d.%m.%Y')} | Fristablauf (§ 84 SGG): {frist_ende.strftime('%d.%m.%Y')} ({diff} Tage verbleibend)"
            self.lbl_result.config(text=res_txt, fg="#3FB950" if diff > 7 else "#DA3633")
            self.log(f"[FRIST] Berechnet fuer {raw}: Fristende ist der {frist_ende.strftime('%d.%m.%Y')} (Noch {diff} Tage)")
        except ValueError:
            messagebox.showerror("Fehler", "Ungueltiges Datumsformat! Bitte TT.MM.JJJJ verwenden.")

    def set_defcon(self, status_text):
        self.log(f"[DEFCON] Status geaendert auf: {status_text}")
