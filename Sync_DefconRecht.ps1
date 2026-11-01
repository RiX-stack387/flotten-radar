# =====================================================================
# INTEGRIERTER UNIVERSAL-SYNC (3-WEGE BRANDMAUER-WEICHE & GITHUB-PUSH)
# =====================================================================
$sourceDir   = "C:\DefconRecht"
$localSkills = "C:\DefconRecht\SKILLS"
$driveBase   = "G:\Meine Ablage\DefconRecht"
$driveSkills = "G:\Meine Ablage\DefconRecht\SKILLS"

$coreFiles = @(
    "ASB_Knowledge_Base_2026.md",
    "DEFCON_RECHT_Enterprise_Base.md",
    "Front_Delta_Compact.md"
)

# 1. Zivil-Front: NUR ASB + Delta (DEFCON_RECHT strikt fernhalten)
$zivilFrontSkills = @(
    "asb-region-nordschwarzwald-neu",
    "asb-core-leitstand",
    "pforzheim-enzkreis-heimat",
    "lebensassistent-lifestyle",
    "engel-ki-radar",
    "netzwerk-resilienz-anker"
)

# 2. Admiralitäts-Brücke: NUR Enterprise + Delta (ASB strikt fernhalten wegen DLP-Schutz)
$admiralSkills = @(
    "admiral-flotten-leitstand"
)

# 3. Alle uebrigen Skills (Rechte-Flotte & Fach-Anker): NUR Enterprise + Delta (ASB strikt fernhalten)

function Sync-SkillReferences ($skillsRootPath, $label) {
    if (Test-Path $skillsRootPath) {
        $skills = Get-ChildItem -Path $skillsRootPath -Directory
        $count = 0
        foreach ($skill in $skills) {
            $refDir = Join-Path $skill.FullName "references"
            if (-not (Test-Path $refDir)) {
                New-Item -ItemType Directory -Path $refDir -Force | Out-Null
            }

            if ($skill.Name -in $zivilFrontSkills) {
                # Gruppe 1: Zivil-Front (ASB + Delta)
                foreach ($file in @("ASB_Knowledge_Base_2026.md", "Front_Delta_Compact.md")) {
                    $src = Join-Path $sourceDir $file
                    if (Test-Path $src) { Copy-Item -Path $src -Destination (Join-Path $refDir $file) -Force }
                }
                $unwanted = Join-Path $refDir "DEFCON_RECHT_Enterprise_Base.md"
                if (Test-Path $unwanted) { Remove-Item $unwanted -Force }
            }
            elseif ($skill.Name -in $admiralSkills) {
                # Gruppe 2: Admiralitäts-Brücke (Enterprise + Delta, DLP & Groessen-Trigger strikt entfernen)
                foreach ($file in @("DEFCON_RECHT_Enterprise_Base.md", "Front_Delta_Compact.md")) {
                    $src = Join-Path $sourceDir $file
                    if (Test-Path $src) { Copy-Item -Path $src -Destination (Join-Path $refDir $file) -Force }
                }
                foreach ($del in @("ASB_Knowledge_Base_2026.md", "Handbuch_Admiral_V23.4.md", "Master_Archiv_V23.4_EINSATZ-CHRONIK.md")) {
                    $p = Join-Path $refDir $del
                    if (Test-Path $p) { Remove-Item $p -Force }
                }
            }
            else {
                # Gruppe 3: Rechte-Flotte & Fach-Anker (Enterprise + Delta, ASB strikt entfernen)
                foreach ($file in @("DEFCON_RECHT_Enterprise_Base.md", "Front_Delta_Compact.md")) {
                    $src = Join-Path $sourceDir $file
                    if (Test-Path $src) { Copy-Item -Path $src -Destination (Join-Path $refDir $file) -Force }
                }
                $unwanted = Join-Path $refDir "ASB_Knowledge_Base_2026.md"
                if (Test-Path $unwanted) { Remove-Item $unwanted -Force }
            }
            $count++
        }
        Write-Host "[OK] $count Skills ($label) zielgenau nach 3-Wege-Matrix munitioniert." -ForegroundColor Green
    }
}

Write-Host "`n>>> [UNIVERSAL-SYNC] STARTE SYSTEMWEITE 3-WEGE-SPIEGELUNG <<<" -ForegroundColor Cyan

# 1. Lokale Skills auf C:\ versorgen
Sync-SkillReferences -skillsRootPath $localSkills -label "Lokal SSD C:\"

# 2. Google Drive versorgen (Basis + Skills)
if (Test-Path $driveBase) {
    foreach ($file in $coreFiles) {
        $src = Join-Path $sourceDir $file
        if (Test-Path $src) {
            Copy-Item -Path $src -Destination (Join-Path $driveBase $file) -Force
        }
    }
    Write-Host "[OK] Google Drive Stammverzeichnis aktualisiert." -ForegroundColor Cyan
    Sync-SkillReferences -skillsRootPath $driveSkills -label "Google Drive G:\"
} else {
    Write-Host "[WARNUNG] Google Drive Pfad nicht erreichbar." -ForegroundColor Yellow
}

# 3. GitHub-Tresor: Automatischer Commit & Push
Set-Location -Path $sourceDir
if (Test-Path (Join-Path $sourceDir ".git")) {
    Write-Host "`n>>> [GIT-TRESOR] Sichere Aenderungen in GitHub... <<<" -ForegroundColor Yellow
    git add ASB_Knowledge_Base_2026.md DEFCON_RECHT_Enterprise_Base.md Front_Delta_Compact.md SKILLS/
    
    $status = git status --porcelain
    if ($status) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        git commit -m "auto(radar): 3-Wege-Universal-Sync Stand $timestamp [Zivil / Admiral / Recht]"
        git push origin main
        Write-Host "[ERFOLG] GitHub-Push erfolgreich abgeschlossen!" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Keine Git-Aenderungen zu committen." -ForegroundColor Gray
    }
}
Write-Host "`n=== [FERTIG] 3-WEGE-SYNC UEBERALL ERFOLGREICH VOLLZOGEN! ===" -ForegroundColor Green