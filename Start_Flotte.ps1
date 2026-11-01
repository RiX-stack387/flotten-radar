Set-Location "C:\DefconRecht"

# 1. Haupt-Radar und Wissens-Pipeline zünden (ruft am Ende automatisch Sync_DefconRecht.ps1 auf)
& "C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\DefconRecht\Start_Flotte.py"

# 2. Automatischer Standby (Energie sparen) nach vollständigem Durchlauf aller Systeme
Write-Host "`n[FLOTTE BEENDET] Alle Radare, Drive-Streams und der 3-Wege-Sync sind im Ziel." -ForegroundColor Green
Write-Host "[STANDBY] Rechner legt sich in 30 Sekunden schlafen (Sitzung mriex bleibt aktiv gesperrt)..." -ForegroundColor Yellow

Start-Sleep -Seconds 30

# Versetzt den Rechner in den echten Standby (Suspend / Energie sparen)
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)