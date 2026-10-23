@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP UNATTENDSLEEP 0
powercfg /setactive SCHEME_CURRENT
cd /d C:\DefconRecht
"C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\DefconRecht\Start_Flotte.py"
REM 1. Frische Radar-Daten in alle Skills spiegeln
powershell.exe -ExecutionPolicy Bypass -File "C:\DefconRecht\deploy_radar_to_skills.ps1"

REM 2. 30 Sekunden warten, dann Standby ausfuehren
timeout /t 30 /nobreak
REM Standby entfernt

REM Automatischer Shutdown nach Radar
shutdown.exe /s /f /t 60 /c "M.E.R. Flotten-Radar abgeschlossen. Rechner faehrt in 60 Sekunden herunter."