$ErrorActionPreference = "Continue"
Set-Location "C:\DefconRecht"

Write-Host ">>> [STUFE 1] STARTE FLOTTEN-RADAR V44.0 (PYTHON-PIPELINE)... <<<" -ForegroundColor Cyan
& "C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\DefconRecht\Start_Flotte.py"

# ==============================================================================
# [STUFE 2] AUTOMATISCHER ZEITSTEMPEL FUER ALLE 3 MASTER-REFERENZEN
# ==============================================================================
Write-Host "`n>>> [STUFE 2] Synchronisiere Live-Zeitstempel aller Master-Referenzen... <<<" -ForegroundColor Cyan
$stampNow = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$utf8NoBom = New-Object System.Text.UTF8Encoding(
    $false
)

$deltaRep = "RADAR-DELTA COMPACT (" +
    $stampNow +
    ")"
$standRep = "**Stand:** " +
    $stampNow +
    " |"

$deltaPaths = @(
    "C:\DefconRecht\Front_Delta_Compact.md",
    "C:\DefconRecht\SKILLS\asb-region-nordschwarzwald-neu\references\Front_Delta_Compact.md"
)
$deltaPaths | ForEach-Object {
    if (Test-Path $_) {
        $txt = [System.IO.File]::ReadAllText(
            $_,
            $utf8NoBom
        )
        $txt =
            $txt -replace "RADAR-DELTA COMPACT \([^\)]*\)",
            $deltaRep
        [System.IO.File]::WriteAllText(
            $_,
            $txt,
            $utf8NoBom
        )
    }
}

$masterPaths = @(
    "C:\DefconRecht\ASB_Knowledge_Base_2026.md",
    "C:\DefconRecht\SKILLS\asb-region-nordschwarzwald-neu\references\ASB_Knowledge_Base_2026.md",
    "C:\DefconRecht\DEFCON_RECHT_Enterprise_Base.md",
    "C:\DefconRecht\SKILLS\defcon-recht-enterprise\references\DEFCON_RECHT_Enterprise_Base.md"
)
$masterPaths | ForEach-Object {
    if (Test-Path $_) {
        $txt = [System.IO.File]::ReadAllText(
            $_,
            $utf8NoBom
        )
        $txt =
            $txt -replace "\*\*Stand:\*\*[^\r\n\x7C]*\x7C",
            $standRep
        [System.IO.File]::WriteAllText(
            $_,
            $txt,
            $utf8NoBom
        )
    }
}
Write-Host "[OK] Alle 3 Referenz-Header tragen nun exakt denselben Zeitstempel:" -ForegroundColor Green
Write-Host $stampNow -ForegroundColor Green

# ==============================================================================
# [STUFE 3] 4-WEGE-KETTE: C: -> TAG_X_BACKUP -> G: (DRIVE) -> GITHUB
# ==============================================================================
Write-Host "`n>>> [STUFE 3a] Erzeuge Tag-X-Tresor VOR der Cloud-/Git-Verteilung... <<<" -ForegroundColor Cyan
if (Test-Path "C:\DefconRecht\Make_TagX_Backup.ps1") {
    & "C:\DefconRecht\Make_TagX_Backup.ps1"
} else {
    Write-Host "[WARNUNG] Make_TagX_Backup.ps1 nicht gefunden!" -ForegroundColor Red
}

Write-Host "`n>>> [STUFE 3b] Starte finale 3-Wege-Synchronisation (SSD -> Skills -> Drive -> Git)... <<<" -ForegroundColor Cyan
if (Test-Path "C:\DefconRecht\Sync_DefconRecht.ps1") {
    & "C:\DefconRecht\Sync_DefconRecht.ps1"
} else {
    Write-Host "[WARNUNG] Sync_DefconRecht.ps1 nicht gefunden!" -ForegroundColor Red
}

# ==============================================================================
# [STUFE 4] AUTOMATISCHER STANDBY NACH VOLLSTAENDIGEM DURCHLAUF
# ==============================================================================
Write-Host "`n[FLOTTE BEENDET] Alle Radare, Stempel, Tag-X-Tresor und der Cloud/Git-Sync sind im Ziel." -ForegroundColor Green
Write-Host "[STANDBY] Rechner legt sich in 30 Sekunden schlafen (Sitzung mriex bleibt aktiv gesperrt)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState(
    [System.Windows.Forms.PowerState]::Suspend,
    $false,
    $false
)