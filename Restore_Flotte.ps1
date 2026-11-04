param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$targetBase = "C:\DefconRecht"
$backupDir = Join-Path $targetBase "TAG_X_BACKUP"
$backupSource = Join-Path $backupDir "TAG_X_FLOTTE_KOMPLETT.json"
$preRestoreDir = Join-Path $backupDir "PRE_RESTORE\STAND_$timestamp"

Write-Host "`n>>> STARTE TAG-X FLOTTEN-REDEPLOYMENT (HARDENED V2.0)... <<<" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "[MODUS] TROCKENLAUF (-DryRun) AKTIV: Es werden keine Dateien ueberschrieben!" -ForegroundColor Yellow
}

# 1. Harter JSON-Integritaets-Check (Vor jedem Schreibzugriff)
if (-not (Test-Path $backupSource)) {
    Write-Host "[FEHLER] Tag-X-Tresor unter $backupSource nicht gefunden! Abbruch." -ForegroundColor Red
    return
}

$fileInfo = Get-Item $backupSource
if ($fileInfo.Length -eq 0) {
    Write-Host "[FEHLER] Die Tresor-Datei $backupSource ist leer (0 Bytes)! Abbruch." -ForegroundColor Red
    return
}

try {
    $jsonContent = Get-Content $backupSource -Raw -Encoding UTF8
    $fleetData = $jsonContent | ConvertFrom-Json
} catch {
    Write-Host "[FEHLER] JSON-Tresor ist beschaedigt oder ungueltig: $($_.Exception.Message)" -ForegroundColor Red
    return
}

if (-not $fleetData.skills -or $fleetData.skills.Count -eq 0) {
    Write-Host "[FEHLER] Keine Skill-Einheiten im JSON-Tresor gefunden! Abbruch." -ForegroundColor Red
    return
}

if ($null -eq $fleetData.handbuch_und_chronik) {
    Write-Host "[FEHLER] Sektion 'handbuch_und_chronik' fehlt im JSON-Tresor! Abbruch." -ForegroundColor Red
    return
}

Write-Host "[OK] Tresor-Integritaet geprueft: $($fleetData.skills.Count) Skills & $($fleetData.handbuch_und_chronik.Count) Kerndokumente bereit." -ForegroundColor Green

# 2. Automatisches Pre-Restore-Backup des Ist-Zustands
$skillsRoot = Join-Path $targetBase "SKILLS"
if (-not $DryRun) {
    if (Test-Path $skillsRoot) {
        Write-Host ">>> Erstelle Sicherheitskopie (Pre-Restore-Backup) unter: $preRestoreDir" -ForegroundColor Cyan
        New-Item -ItemType Directory -Path $preRestoreDir -Force | Out-Null
        
        Copy-Item -Path $skillsRoot -Destination (Join-Path $preRestoreDir "SKILLS") -Recurse -Force
        
        foreach ($doc in $fleetData.handbuch_und_chronik) {
            $safeDocName = Split-Path $doc.filename -Leaf
            $existingDoc = Join-Path $targetBase $safeDocName
            if (Test-Path $existingDoc) {
                Copy-Item -Path $existingDoc -Destination (Join-Path $preRestoreDir $safeDocName) -Force
            }
        }
        Write-Host "[OK] Ist-Zustand erfolgreich gesichert!" -ForegroundColor Green
    }
}

# 3. Ordnerstruktur aufbauen & alle Skills samt Referenzen rekonstruieren
if (-not $DryRun -and -not (Test-Path $skillsRoot)) {
    New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
}

foreach ($skill in $fleetData.skills) {
    $safeSkillId = Split-Path $skill.id -Leaf
    $skillDir = Join-Path $skillsRoot $safeSkillId
    $refDir = Join-Path $skillDir "references"
    $skillMdPath = Join-Path $skillDir "SKILL.md"

    if ($DryRun) {
        $refCount = if ($skill.references) { $skill.references.Count } else { 0 }
        Write-Host "[DRY-RUN] Bereit: Skill '$safeSkillId' (inkl. $refCount Referenzen)" -ForegroundColor Gray
        continue
    }

    if (-not (Test-Path $skillDir)) { New-Item -ItemType Directory -Path $skillDir -Force | Out-Null }
    if (-not (Test-Path $refDir)) { New-Item -ItemType Directory -Path $refDir -Force | Out-Null }

    [System.IO.File]::WriteAllText($skillMdPath, [string]$skill.skill_md, $utf8NoBom)

    foreach ($ref in $skill.references) {
        $safeRefName = Split-Path $ref.filename -Leaf
        $refPath = Join-Path $refDir $safeRefName
        [System.IO.File]::WriteAllText($refPath, [string]$ref.content, $utf8NoBom)
    }
    Write-Host "[WIEDERHERGESTELLT] Skill: $safeSkillId" -ForegroundColor Gray
}

# 4. Handbuch und Chronik wiederherstellen
foreach ($doc in $fleetData.handbuch_und_chronik) {
    $safeDocName = Split-Path $doc.filename -Leaf
    $docPath = Join-Path $targetBase $safeDocName

    if ($DryRun) {
        Write-Host "[DRY-RUN] Bereit: Kerndokument '$safeDocName'" -ForegroundColor Cyan
        continue
    }

    [System.IO.File]::WriteAllText($docPath, [string]$doc.content, $utf8NoBom)
    Write-Host "[WIEDERHERGESTELLT] Kerndokument: $safeDocName" -ForegroundColor Cyan
}

if ($DryRun) {
    Write-Host "`n=== [TROCKENLAUF BEENDET] Tresor ist 100% intakt. Keine Dateien wurden veraendert. ===`n" -ForegroundColor Yellow
} else {
    Write-Host "`n=== [ERFOLG] DIE KOMPLETTE FLOTTE IST VOLLSTAENDIG WIEDERHERGESTELLT! ===`n" -ForegroundColor Green
    Write-Host "Vorheriger Zustand liegt sicher unter: $preRestoreDir" -ForegroundColor Cyan
}