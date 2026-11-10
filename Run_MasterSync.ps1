# ====================================================================
# M.E.R. FLOTTEN-RADAR // ALL-IN-ONE MEISTERSKRIPT (V23.4 / V21.2)
# 1. START_FLOTTE.PS1 (234 SLOTS & BUILDER)
# 2. 7-DATEIEN-BESTÜCKUNG ADMIRAL-FLOTTEN-LEITSTAND\REFERENCES
# 3. 0-BYTE-SCHUTZSCHILD & INTEGRITÄTS-CHECK
# 4. 4-WEGE-SYNC (C: ➔ TAG_X_BACKUP ➔ G:\ ➔ GITHUB origin/main)
# STAND: 10.11.2026 // DOKTRIN V2.5
# ====================================================================

$ErrorActionPreference = "Stop"
Set-Location -Path "C:\DefconRecht"

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "⚓ STUFE 1: ZÜNDE START_FLOTTE.PS1 (RADAR-PIPELINE) ⚓" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

if (Test-Path ".\Start_Flotte.ps1") {
    Write-Host "  -> Starte .\Start_Flotte.ps1 ..." -ForegroundColor Cyan
    & ".\Start_Flotte.ps1"
} elseif (Test-Path ".\Start_Flotte.py") {
    Write-Host "  -> Start_Flotte.ps1 nicht gefunden, starte .\Start_Flotte.py ..." -ForegroundColor Yellow
    python .\Start_Flotte.py
} else {
    Write-Host "  [FEHLER] Weder Start_Flotte.ps1 noch Start_Flotte.py in C:\DefconRecht gefunden!" -ForegroundColor Red
    exit 1
}

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "📂 STUFE 2: 7-DATEIEN-BESTÜCKUNG ADMIRAL-REFERENCES 📂" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$admiralRefDir = "C:\DefconRecht\SKILLS\admiral-flotten-leitstand\references"
if (-not (Test-Path $admiralRefDir)) {
    Write-Host "  -> Erstelle Verzeichnis: $admiralRefDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $admiralRefDir -Force | Out-Null
}

$admiralFiles = @(
    "DEFCON_RECHT_Enterprise_Base.md",
    "Front_Delta_Compact.md",
    "Master_Archiv_V23.4_EINSATZ-CHRONIK.md",
    "Handbuch_CORE_DACH_V23.4.md",
    "Handbuch_Admiral_V23.4.md",
    "Master_Archiv_V23.4_AKTIV_ab_4000.md",
    "Master_Archiv_V23.4_TEIL1_0001_3999.md"
)

foreach ($file in $admiralFiles) {
    $src = Join-Path "C:\DefconRecht" $file
    $dst = Join-Path $admiralRefDir $file
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
        Write-Host "  [KOPIERT] $file ➔ admiral-flotten-leitstand\references" -ForegroundColor Cyan
    } else {
        Write-Host "  [ALARM] Quelldatei fehlt in C:\DefconRecht: $file" -ForegroundColor Red
    }
}

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "🛡️ STUFE 3: 0-BYTE-SCHUTZSCHILD & VALIDIERUNG 🛡️" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$allValid =$true
foreach (\$file in $admiralFiles) {$dst = Join-Path $admiralRefDir$file
    if (Test-Path \$dst) {
        $item = Get-Item$dst
        $len =$item.Length
        $mod =$item.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        if (\$len -gt 0) {
            Write-Host "  [OK] \$file ($len Bytes \vert{} Stand:$mod)" -ForegroundColor Green
        } else {
            Write-Host "  [ALARM] 0-Byte-Datei erkannt: \$dst" -ForegroundColor Red
            $allValid =$false
        }
    } else {
        Write-Host "  [ALARM] Zieldatei fehlt: \$dst" -ForegroundColor Red
        $allValid =$false
    }
}

if (-not \$allValid) {
    Write-Host "`n[STOPP] 0-Byte-Schutzschild hat angeschlagen! Sync wird abgebrochen." -ForegroundColor Red
    exit 1
}

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "📦 STUFE 4: TAG_X_BACKUP SNAPSHOT GENERIEREN 📦" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

if (Test-Path ".\Make_TagX_Backup.ps1") {
    Write-Host "  -> Führe .\Make_TagX_Backup.ps1 aus..." -ForegroundColor Cyan
    & ".\Make_TagX_Backup.ps1"
    Write-Host "  [OK] TAG_X_BACKUP erfolgreich aktualisiert." -ForegroundColor Green
} else {
    Write-Host "  [WARNUNG] Make_TagX_Backup.ps1 nicht gefunden!" -ForegroundColor Yellow
}

Write-Host "`n====================================================" -ForegroundColor Cyan
Write-Host "☁️ STUFE 5: GOOGLE DRIVE (G:\) & GITHUB PUSH ☁️" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$driveBase = "G:\Meine Ablage\DefconRecht"
if (Test-Path $driveBase) {
    Write-Host "  -> Spiegle alle SKILLS (inkl. Admiral-References) nach G:\ ..." -ForegroundColor Cyan
    robocopy "C:\DefconRecht\SKILLS" "$driveBase\SKILLS" /MIR /FFT /R:2 /W:2 /NP /NDL /NJS

    if (Test-Path "C:\DefconRecht\TAG_X_BACKUP") {
        Write-Host "  -> Spiegle TAG_X_BACKUP nach G:\ ..." -ForegroundColor Cyan
        robocopy "C:\DefconRecht\TAG_X_BACKUP" "$driveBase\TAG_X_BACKUP" /MIR /FFT /R:2 /W:2 /NP /NDL /NJS
    }

    Write-Host "  -> Kopiere aktuelle Kern-Dateien auf Hauptebene G:\ ..." -ForegroundColor Cyan
    foreach ($file in $admiralFiles) {
        $src = Join-Path "C:\DefconRecht" $file
        if (Test-Path $src) {
            Copy-Item -Path $src -Destination $driveBase -Force
        }
    }
    Write-Host "  [OK] Google Drive (G:\) zu 100% synchron." -ForegroundColor Green
} else {
    Write-Host "  [HINWEIS] Laufwerk G:\ nicht verbunden. Fahre mit GitHub fort..." -ForegroundColor Yellow
}

Write-Host "  -> Führe finalen Git Commit & Push nach origin/main aus..." -ForegroundColor Cyan
git add -A
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$msg = "feat(master-sync): Start_Flotte + 7 Admiral-Refs + 4-Wege-Sync ($stamp)"
git commit -m $msg
git push origin main

Write-Host "`nAktueller Git-Status:" -ForegroundColor Cyan
git status -s -b

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "🏁 ALL-IN-ONE MEISTERSKRIPT ZU 100% ERFOLGREICH ABGESCHLOSSEN 🏁" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green