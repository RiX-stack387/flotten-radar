#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import glob
import time
import shutil
import ctypes
import subprocess
from datetime import datetime

BASE_DIR = r"C:\DefconRecht"
DRIVE_BASE = r"G:\Meine Ablage\DefconRecht"
LOG_FILE = os.path.join(BASE_DIR, "Nightly_Run_Log.txt")

PY_EXE = r"C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not os.path.exists(PY_EXE):
    PY_EXE = sys.executable

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def set_awake(keep_awake=True):
    try:
        flags = (0x80000000 | 0x00000001 | 0x00000040) if keep_awake else 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
        if keep_awake:
            log("[INIT] Windows-Wachhalte-Sperre aktiviert (kein 30-Min-Standby).")
    except Exception as e:
        log(f"[WARNUNG] Wachhalte-Sperre Fehler: {e}")

def ensure_google_drive():
    log("[INIT] Pruefe Google Drive Status...")
    if not os.path.exists("G:\\"):
        matches = glob.glob(r"C:\Program Files\Google\Drive File Stream\*\GoogleDriveFS.exe")
        if matches:
            log(" -> Starte GoogleDriveFS.exe...")
            subprocess.Popen([matches[0]])
            time.sleep(5)
    for retry in range(15):
        if os.path.exists(DRIVE_BASE):
            log(f" -> [OK] Google Drive bereit unter: {DRIVE_BASE}")
            return True
        time.sleep(2)
    log(" -> [WARNUNG] Laufwerk G: im aktuellen Benutzerkontext nicht sichtbar!")
    return False

def rotate_logs(folder, max_days=2):
    if not os.path.exists(folder):
        return
    cutoff = time.time() - (max_days * 86400)
    for filepath in glob.glob(os.path.join(folder, "API_*.txt")):
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                log(f" -> Altes Log entfernt: {os.path.basename(filepath)}")
        except Exception:
            pass

def run_script(step_label, script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.exists(script_path):
        alt_path = os.path.join(BASE_DIR, "ASB", script_name)
        if os.path.exists(alt_path):
            script_path = alt_path
        else:
            log(f"[{step_label}] Ueberspringe {script_name} (nicht gefunden).")
            return
    log(f"[{step_label}] Starte {script_name} (100% Live-Ticker ohne Kuerzung)...")
    start_t = time.time()
    proc = subprocess.Popen(
        [PY_EXE, "-u", script_path],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )
    for line in proc.stdout:
        clean_line = line.rstrip("\r\n")
        if clean_line:
            log(f"    {clean_line}")
    proc.wait()
    dur = time.time() - start_t
    if proc.returncode == 0:
        log(f"[{step_label}] OK ({dur:.1f}s): {script_name}")
    else:
        log(f"[{step_label}] FEHLER (Code {proc.returncode} nach {dur:.1f}s) in {script_name}!")

def build_front_delta():
    log("[FRONT-SYNC] Komprimiere Tages-Deltas...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    delta_file = os.path.join(BASE_DIR, "Front_Delta_Compact.md")
    lines = [f"RADAR-DELTA COMPACT ({today_str})"]
    log_dir = os.path.join(BASE_DIR, "MasterLogs")
    pattern = re.compile(r"===\s*([^:]+:\s*[^=\r\n]+)\s*===.*?\[GE(?:Ä|Ä)NDERT/NEU\]\s*Norm/AZ:\s*([^|\r\n]+)\|\s*Wert:\s*([^(\r\n]+)", re.DOTALL)
    for lf in glob.glob(os.path.join(log_dir, f"*{today_str}*.txt")):
        try:
            with open(lf, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            if "AKUTER HANDLUNGSBEDARF" in raw:
                for m in pattern.finditer(raw):
                    lines.append(f"- [{m.group(1).strip()}] {m.group(2).strip()}: {m.group(3).strip()}")
        except Exception as e:
            log(f" -> Fehler beim Lesen von {lf}: {e}")
    if len(lines) == 1:
        lines.append("- Keine kritischen Rechtsaenderungen erfasst. Perimeter stabil.")
    with open(delta_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(" -> Front_Delta_Compact.md aktualisiert.")

def sync_in_place(src, dst):
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
        log(f" -> [SYNC-STREAM] {os.path.basename(src)} aktualisiert (Drive-ID behalten).")
    else:
        with open(dst, "wb") as fdst:
            fdst.write(data)
        log(f" -> [SYNC-CREATE] {os.path.basename(src)} neu angelegt.")

def main():
    os.chdir(BASE_DIR)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== M.E.R. FLOTTEN-RADAR RUN LOG ===\n")
    set_awake(True)
    try:
        ensure_google_drive()
        rotate_logs(os.path.join(BASE_DIR, "MasterLogs"), 2)

        run_script("1/6", "14_Slots_Radar_bereinigt.py")
        run_script("2/6", "Zusatz_Leben_Radar.py")
        run_script("3/6", "Zusatz_Leben_Radar_CW_FDS.py")
        run_script("4/6", "asb_nsw_radar.py")

        live_asb = os.path.join(BASE_DIR, "ASB", "ASB_Knowledge_Base_LIVE.md")
        legacy_asb = os.path.join(BASE_DIR, "ASB_Knowledge_Base_2026.md")
        if os.path.exists(live_asb):
            shutil.copy2(live_asb, legacy_asb)

        run_script("5/6", "build_knowledge.py")
        run_script("6/6", "build_enterprise_knowledge.py")

        build_front_delta()

        if ensure_google_drive():
            drive_logs = os.path.join(DRIVE_BASE, "MasterLogs")
            os.makedirs(drive_logs, exist_ok=True)
            rotate_logs(drive_logs, 2)

            sync_in_place(os.path.join(BASE_DIR, "DEFCON_RECHT_Enterprise_Base.md"), os.path.join(DRIVE_BASE, "DEFCON_RECHT_Enterprise_Base.md"))
            sync_in_place(os.path.join(BASE_DIR, "Front_Delta_Compact.md"), os.path.join(DRIVE_BASE, "Front_Delta_Compact.md"))
            sync_in_place(os.path.join(BASE_DIR, "ASB_Knowledge_Base_2026.md"), os.path.join(DRIVE_BASE, "ASB_Knowledge_Base_2026.md"))
            sync_in_place(os.path.join(BASE_DIR, "ASB", "ASB_Knowledge_Base_LIVE.md"), os.path.join(DRIVE_BASE, "ASB", "ASB_Knowledge_Base_LIVE.md"))
            sync_in_place(os.path.join(BASE_DIR, "quellen_registry.py"), os.path.join(DRIVE_BASE, "quellen_registry.py"))

            for lf in glob.glob(os.path.join(BASE_DIR, "MasterLogs", "*")):
                if os.path.isfile(lf):
                    shutil.copy2(lf, os.path.join(drive_logs, os.path.basename(lf)))
            log("[EXPORT] Alle Dateien und MasterLogs nach Google Drive synchronisiert.")
            time.sleep(10)
        else:
            log("[WARNUNG] Google Drive Export uebersprungen (G: nicht erreichbar).")

        sync_ps1 = os.path.join(BASE_DIR, "Sync_DefconRecht.ps1")
        if os.path.exists(sync_ps1):
            log("[SKILLS-SYNC] Starte Sync_DefconRecht.ps1...")
            subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", sync_ps1], cwd=BASE_DIR)

        log("[FERTIG] Gesamtflotten-Sweep vollstaendig abgeschlossen!")
    finally:
        set_awake(False)

if __name__ == "__main__":
    main()
