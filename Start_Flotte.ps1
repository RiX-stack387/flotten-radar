Set-Location "C:\DefconRecht"
& "C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\DefconRecht\Start_Flotte.py"

# [DEAKTIVIERT DURCH ADMIRAL] # Automatischer Shutdown nach Radar
# [DEAKTIVIERT DURCH ADMIRAL] Start-Process shutdown.exe -ArgumentList '/s /f /t 60 /c "M.E.R. Flotten-Radar abgeschlossen. Rechner faehrt in 60 Sekunden herunter."'
