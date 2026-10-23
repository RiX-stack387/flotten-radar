# ==============================================================================
# Flotten-Deployer: Synchronisiert Radar- & ASB-Daten in die Skill-Referenzen
# ==============================================================================
$Root = "C:\DefconRecht"
$SkillsDir = Join-Path $Root "SKILLS"

$BaseFile  = Join-Path $Root "DEFCON_RECHT_Enterprise_Base.md"
$DeltaFile = Join-Path $Root "Front_Delta_Compact.md"
$AsbFile   = Join-Path $Root "ASB_Knowledge_Base_2026.md"

Write-Host "Starte Flotten-Synchronisation..." -ForegroundColor Cyan

Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object {
    $SkillName = $_.Name
    $TargetRef = Join-Path $_.FullName "references"

    if (Test-Path $TargetRef) {
        # 1. Allgemeine Radar-Dateien verteilen
        if (Test-Path $BaseFile) {
            Copy-Item -Path $BaseFile -Destination $TargetRef -Force
        }
        if (Test-Path $DeltaFile) {
            Copy-Item -Path $DeltaFile -Destination $TargetRef -Force
        }

        # 2. Brandmauer-Schutz: ASB-Wissen nur in ASB-relevante Skills spiegeln
        $TargetAsb = Join-Path $TargetRef "ASB_Knowledge_Base_2026.md"
        if (Test-Path $TargetAsb) {
            Copy-Item -Path $AsbFile -Destination $TargetRef -Force
            Write-Host "  -> ASB-Wissen aktualisiert in: $SkillName" -ForegroundColor Yellow
        }
    }
}

Write-Host "Flotten-Update erfolgreich abgeschlossen!" -ForegroundColor Green
