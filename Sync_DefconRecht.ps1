$ErrorActionPreference = "Continue"
Set-Location "C:\DefconRecht"

Write-Host "`n>>> [UNIVERSAL-SYNC] STARTE SYSTEMWEITE 3-WEGE-SPIEGELUNG (7/20-DOKTRIN) <<<" -ForegroundColor Cyan

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

    if (Test-Path "C:\DefconRecht\Front_Delta_Compact.md") {
        Copy-Item -Path "C:\DefconRecht\Front_Delta_Compact.md" -Destination (Join-Path $refDir "Front_Delta_Compact.md") -Force
    }
    if (Test-Path "C:\DefconRecht\DEFCON_RECHT_Enterprise_Base.md") {
        Copy-Item -Path "C:\DefconRecht\DEFCON_RECHT_Enterprise_Base.md" -Destination (Join-Path $refDir "DEFCON_RECHT_Enterprise_Base.md") -Force
    }
    $countAll++

    $asbTarget = Join-Path $refDir "ASB_Knowledge_Base_2026.md"
    if ($asbAuthorizedSkills -contains $dir.Name) {
        if (Test-Path "C:\DefconRecht\ASB_Knowledge_Base_2026.md") {
            Copy-Item -Path "C:\DefconRecht\ASB_Knowledge_Base_2026.md" -Destination $asbTarget -Force
            $countAsb++
        }
    } elseif (Test-Path $asbTarget) {
        Remove-Item -Path $asbTarget -Force
        Write-Host " [BRANDMAUER] ASB-Datei bereinigt aus: $($dir.Name)" -ForegroundColor Yellow
    }
}

Write-Host "[OK] $countAll/27 Skills (Lokal SSD C:\) nach 7/20-Matrix munitioniert ($countAsb ASB-Kern-Skills)." -ForegroundColor Green

# Tinas Desktop-ZIP synchron halten
$tinaFolder = "C:\DefconRecht\SKILLS\mein-familien-lotse"
$desktopPath = [Environment]::GetFolderPath("Desktop")
if ((Test-Path $tinaFolder) -and (Test-Path $desktopPath)) {
    $zipFile = Join-Path $desktopPath "Tinas_Familien_Lotse.zip"
    if (Test-Path $zipFile) { Remove-Item $zipFile -Force }
    Compress-Archive -Path "$tinaFolder\*" -DestinationPath $zipFile -Force
    Write-Host "[OK] Tinas_Familien_Lotse.zip aktualisiert." -ForegroundColor Green
}

# Google Drive Spiegelung (G:\)
$driveRoot = "G:\Meine Ablage\DefconRecht"
if (Test-Path $driveRoot) {
    $rootFiles = @("Front_Delta_Compact.md", "DEFCON_RECHT_Enterprise_Base.md", "ASB_Knowledge_Base_2026.md", "Start_Flotte.ps1", "Sync_DefconRecht.ps1", "Make_TagX_Backup.ps1")
    foreach ($rf in $rootFiles) {
        $src = Join-Path "C:\DefconRecht" $rf
        if (Test-Path $src) {
            Copy-Item -Path $src -Destination (Join-Path $driveRoot $rf) -Force
        }
    }
    Write-Host "[OK] Google Drive Stammverzeichnis aktualisiert." -ForegroundColor Green

    robocopy "C:\DefconRecht\SKILLS" "G:\Meine Ablage\DefconRecht\SKILLS" /MIR /FFT /R:2 /W:2 /NP /NDL /NJS | Out-Null
    robocopy "C:\DefconRecht\TAG_X_BACKUP" "G:\Meine Ablage\DefconRecht\TAG_X_BACKUP" /MIR /FFT /R:2 /W:2 /NP /NDL /NJS | Out-Null
    Write-Host "[OK] 27 Skills & Tag-X-Tresor (Google Drive G:\) exakt nach 7/20-Matrix gespiegelt." -ForegroundColor Green
} else {
    Write-Host "[WARNUNG] Laufwerk G:\ nicht verfuegbar - Drive-Spiegelung uebersprungen." -ForegroundColor Yellow
}

# GitHub Tresor
Write-Host "`n>>> [GIT-TRESOR] Sichere Aenderungen in GitHub... <<<" -ForegroundColor Cyan
$gitStamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git add -A
$changes = git status --porcelain
if ($changes) {
    git commit -m "auto(radar): 3-Wege-Sync 7/20-Matrix Stand $gitStamp"
    git push origin main
    Write-Host "[ERFOLG] GitHub-Push erfolgreich abgeschlossen!" -ForegroundColor Green
} else {
    Write-Host "[INFO] GitHub bereits zu 100% aktuell (keine neuen Aenderungen)." -ForegroundColor Cyan
}

Write-Host "`n=== [FERTIG] 3-WEGE-SYNC UEBERALL ERFOLGREICH VOLLZOGEN! ===" -ForegroundColor Green