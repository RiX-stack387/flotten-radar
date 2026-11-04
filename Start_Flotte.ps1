$ErrorActionPreference = "Continue"
Set-Location "C:\DefconRecht"

Write-Host ">>> [STUFE 1] STARTE FLOTTEN-RADAR V44.0 (PYTHON-PIPELINE)... <<<" -ForegroundColor Cyan
& "C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\DefconRecht\Start_Flotte.py"

# ==============================================================================
# [STUFE 2] AUTOMATISCHER ZEITSTEMPEL-STEMPEL FÜR ALLE 3 MASTER-REFERENZEN
# ==============================================================================
Write-Host "`n>>> [STUFE 2] Synchronisiere Live-Zeitstempel aller Master-Referenzen... <<<" -ForegroundColor Cyan
$stampNow = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$deltaPaths = @(
    "C:\DefconRecht\Front_Delta_Compact.md",
    "C:\DefconRecht\SKILLS\asb-region-nordschwarzwald-neu\references\Front_Delta_Compact.md"
)
foreach ($p in $deltaPaths) {
    if (Test-Path $p) {
        $txt = Get-Content $p -Raw -Encoding UTF8
        $txt = $txt -replace "RADAR-DELTA COMPACT \([^\)]*\)", "RADAR-DELTA COMPACT ($stampNow)"
        [System.IO.File]::WriteAllText($p, $txt, $utf8NoBom)
    }
}

$asbPaths = @(
    "C:\DefconRecht\ASB_Knowledge_Base_2026.md",
    "C:\DefconRecht\SKILLS\asb-region-nordschwarzwald-neu\references\ASB_Knowledge_Base_2026.md"
)
foreach ($p in $asbPaths) {
    if (Test-Path $p) {
        $txt = Get-Content $p -Raw -Encoding UTF8
        $txt = $txt -replace "\*\*Stand:\*\*[^\r\n\|]*\|", "**Stand:** $stampNow |"
        [System.IO.File]::WriteAllText($p, $txt, $utf8NoBom)
    }
}
Write-Host "[OK] Alle Referenz-Header tragen nun exakt denselben Zeitstempel ($stampNow)!" -ForegroundColor Green

# ==============================================================================
# [STUFE 3] 3-WEGE-SYNC & TAG-X-TRESOR AKTUALISIEREN (VOR DEM STANDBY)
# ==============================================================================
if (Test-Path "C:\DefconRecht\Sync_DefconRecht.ps1") {
    Write-Host "`n>>> [STUFE 3a] Starte 3-Wege-Synchronisation (SSD -> Skills -> Drive -> Git)... <<<" -ForegroundColor Cyan
    & "C:\DefconRecht\Sync_DefconRecht.ps1"
}

Write-Host "`n>>> [STUFE 3b] Aktualisiere Tag-X-Tresor (Make_TagX_Backup.ps1)... <<<" -ForegroundColor Cyan
& "C:\DefconRecht\Make_TagX_Backup.ps1"

# ==============================================================================
# [STUFE 4] AUTOMATISCHER STANDBY NACH VOLLSTÄNDIGEM DURCHLAUF
# ==============================================================================
Write-Host "`n[FLOTTE BEENDET] Alle Radare, Stempel, Backups und der 3-Wege-Sync sind im Ziel." -ForegroundColor Green
Write-Host "[STANDBY] Rechner legt sich in 30 Sekunden schlafen (Sitzung mriex bleibt aktiv gesperrt)..." -ForegroundColor Yellow

Start-Sleep -Seconds 30

Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)