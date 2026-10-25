@echo off
chcp 65001 >nul
title M.E.R. SOZIAL FLOTTE - NIGHTLY RUN

echo [INFO] Starte Flotten-Radar ueber Start_Flotte.ps1...
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "C:\DefconRecht\Start_Flotte.ps1"

echo [OK] Flotten-Durchlauf beendet.
exit /b 0
