param(
    [switch]$NoStandby
)

$ErrorActionPreference = "Continue"
Set-Location "C:\DefconRecht"

Write-Host ">>> [STUFE 1] STARTE FLOTTEN-RADAR V44.0 (PYTHON-PIPELINE)... <<<" -ForegroundColor Cyan
& "C:\Users\mriex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\DefconRecht\Start_Flotte.py"

# ==============================================================================
# [STUFE 2] ZEITSTEMPEL & AUTORISIERTE 7/20-VERTEILUNG DER 3 MASTER-REFERENZEN
# ==============================================================================
Write-Host "`n>>> [STUFE 2] Synchronisiere Zeitstempel & verteile Master-Referenzen (7/20-Matrix)... <<<" -ForegroundColor Cyan
$stampNow = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$deltaRep = "RADAR-DELTA COMPACT (" + $stampNow + ")"
$standRep = "**Stand:** " + $stampNow + " |"

$rootDelta = "C:\DefconRecht\Front_Delta_Compact.md"
if (Test-Path $rootDelta) {
    $txt = [System.IO.File]::ReadAllText($rootDelta, $utf8NoBom)
    $txt = $txt -replace "RADAR-DELTA COMPACT \([^\)]*\)", $deltaRep
    [System.IO.File]::WriteAllText($rootDelta, $txt, $utf8NoBom)
}

$rootMasters = @(
    "C:\DefconRecht\ASB_Knowledge_Base_2026.md",
    "C:\DefconRecht\DEFCON_RECHT_Enterprise_Base.md"
)
foreach ($rm in $rootMasters) {
    if (Test-Path $rm) {
        $txt = [System.IO.File]::ReadAllText($rm, $utf8NoBom)
        $txt = $txt -replace "\*\*Stand:\*\*[^\r\n\x7C]*\x7C", $standRep
        $txt = $txt -replace "> Stand: [^\r\n\x7C]*\x7C", ("> Stand: " + $stampNow + " |")
        [System.IO.File]::WriteAllText($rm, $txt, $utf8NoBom)
    }
}

$asbAuthorizedSkills = @(
    "asb-region-nordschwarzwald-neu",
    "asb-core-leitstand",
    "admiral-flotten-leitstand",
    "core-dach-rechenzentrum",
    "senioren-anker-vorsorge",
    "med-notfall-anker",
    "inklusion-anker"
)

$skillDirs = Get-ChildItem -Path "C:\DefconRecht\SKILLS" -Directory
$countAll = 0
$countAsb = 0

foreach ($dir in $skillDirs) {
    $refDir = Join-Path $dir.FullName "references"
    if (-not (Test-Path $refDir)) {
        New-Item -Path $refDir -ItemType Directory -Force | Out-Null
    }

    Copy-Item -Path "C:\DefconRecht\Front_Delta_Compact.md" -Destination (Join-Path $refDir "Front_Delta_Compact.md") -Force
    Copy-Item -Path "C:\DefconRecht\DEFCON_RECHT_Enterprise_Base.md" -Destination (Join-Path $refDir "DEFCON_RECHT_Enterprise_Base.md") -Force
    $countAll++

    $asbTarget = Join-Path $refDir "ASB_Knowledge_Base_2026.md"
    if ($asbAuthorizedSkills -contains $dir.Name) {
        Copy-Item -Path "C:\DefconRecht\ASB_Knowledge_Base_2026.md" -Destination $asbTarget -Force
        $countAsb++
    } elseif (Test-Path $asbTarget) {
        Remove-Item -Path $asbTarget -Force
        Write-Host " [BRANDMAUER] Unberechtigte ASB-Datei entfernt aus: $($dir.Name)" -ForegroundColor Yellow
    }
}

Write-Host "[OK] Zeitstempel ($stampNow) gesetzt!" -ForegroundColor Green
Write-Host "[OK] Front_Delta & Enterprise_Base in $countAll/27 Skills verteilt | ASB_Knowledge_Base exklusiv in $countAsb berechtigte Skills verteilt!" -ForegroundColor Green

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
# [STUFE 4] STANDBY-STEUERUNG (AUTOPILOT AB 17.11. VS. MANUELLER -NOSTANDBY MODUS)
# ==============================================================================
Write-Host "`n[FLOTTE BEENDET] Alle Radare, PDF-Scans, 7/20-Verteilung, Tag-X-Tresor und Cloud/Git-Sync sind im Ziel." -ForegroundColor Green
if ($NoStandby) {
    Write-Host "[MANUELL] Parameter -NoStandby aktiv: Rechner bleibt wach." -ForegroundColor Cyan
} else {
    Write-Host "[AUTOPILOT-STANDBY] Rechner legt sich in 30 Sekunden schlafen (Sitzung mriex bleibt aktiv gesperrt)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.Application]::SetSuspendState(
        [System.Windows.Forms.PowerState]::Suspend,
        $false,
        $false
    )
}