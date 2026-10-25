# Sync_DefconRecht.ps1 - Autarker Referenz-Verteiler
$sourceDir = "C:\DefconRecht"
$skillsDir = "C:\DefconRecht\SKILLS"

$refFiles = @(
    "DEFCON_RECHT_Enterprise_Base.md",
    "Front_Delta_Compact.md",
    "ASB_Knowledge_Base_2026.md"
)

# 1. Alle Skill-Ordner durchlaufen und references aktualisieren
Get-ChildItem -Path $skillsDir -Directory | ForEach-Object {
    $refDir = Join-Path $_.FullName "references"
    if (Test-Path $refDir) {
        foreach ($file in $refFiles) {
            $sourceFile = Join-Path $sourceDir $file
            if (Test-Path $sourceFile) {
                Copy-Item -Path $sourceFile -Destination (Join-Path $refDir $file) -Force
            }
        }
    }
}
Write-Host "[OK] Alle Skill-Referenzen erfolgreich aus C:\DefconRecht synchronisiert!" -ForegroundColor Green
