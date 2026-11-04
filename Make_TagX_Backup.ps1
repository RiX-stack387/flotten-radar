$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupDir = "C:\DefconRecht\TAG_X_BACKUP"
$driveBackupDir = "G:\Meine Ablage\DefconRecht\TAG_X_BACKUP"
$bt = [string][char]96 * 3

if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }
if ((Test-Path "G:\Meine Ablage\DefconRecht") -and (-not (Test-Path $driveBackupDir))) {
    New-Item -ItemType Directory -Path $driveBackupDir | Out-Null
}

# 1. ADMIRAL KERN-IDENTITÄT
$admiralCore = @"
# ADMIRAL BRÜCKEN-KERN & PERSONA (TAG-X INITIALISIERUNG)
- **Rolle:** Ich agiere als loyaler Flotten-Lotse (Admiral) und taktischer Beistand für private, gesundheitliche und administrative Herausforderungen (Doktrin V2.5 / V21.2 / V23.4).
- **Fokus & Tonfall:** Architektur der Empathie (70/30-Regel: 70 % Empathie, 30 % Fakten). Direkt, loyal, präzise, strategischer Humor. Antworten immer in der 1. Person Singular ("Ich").
- **Safe Haven:** Schutz der Familie (§ 6 RDG). Einsatzgebiet: Pforzheim, Enzkreis und Nordschwarzwald (CW/FDS).
- **Brandmauer-Prinzip:** Strikte Trennung zwischen ziviler Daseinsvorsorge (ASB, Pflege, Gesundheit) und sozialrechtlicher Gegenwehr (Jobcenter, Behörden, KdU nach LSG BW).
- **Compliance & Rote Linien:** Strikte Einhaltung des 112-Hardlocks, des Behörden-Verbots, der RDG-Sperre bei zivilen Lotsen und des DSGVO-Stealth-Schutzes.
- **Struktur:** Wichtige Lageberichte mit Admiral-Header eröffnen, komplexe Sachverhalte in Tabellen/Listen zerlegen, Arbeitsplan-Modul V1.3 und Proaktive Vorausschau vor dem Footer ausgeben.
"@

$mdBuilder = New-Object System.Text.StringBuilder
[void]$mdBuilder.AppendLine("# 🛡️ TAG-X MASTER-ARCHIV: KOMPLETTE KI-FLOTTE INKL. DYNAMISCHER CHRONIK & HANDBUCH (STAND: $timestamp)")
[void]$mdBuilder.AppendLine("Dieses Dokument enthält die komplette Brücken-Identität, das Kommandanten-Handbuch, die stets tagesaktuell dynamisch eingelesene Einsatz-Chronik V23.4, alle 26 Skills und sämtliche Wissensbasen für den sofortigen Neustart am Tag X.`n")
[void]$mdBuilder.AppendLine($admiralCore)

# 2. HANDBUCH & DYNAMISCHE EINSATZ-CHRONIK LADEN (Keine Duplikate)
[void]$mdBuilder.AppendLine("`n---`n# TEIL 0: KOMMANDANTEN-HANDBUCH & DYNAMISCHE EINSATZ-CHRONIK`n")

$coreDocsPaths = @(
    "C:\DefconRecht\Handbuch_Admiral_V23.4.md",
    "C:\DefconRecht\Master_Archiv_V23.4_EINSATZ-CHRONIK.md"
)

$coreDocsJson = @()
foreach ($docPath in $coreDocsPaths) {
    if (Test-Path $docPath) {
        $docName = Split-Path $docPath -Leaf
        $docText = Get-Content $docPath -Raw -Encoding UTF8
        [void]$mdBuilder.AppendLine("## DOKUMENT: $docName (Stand: $timestamp)")
        [void]$mdBuilder.AppendLine($docText.Trim())
        [void]$mdBuilder.AppendLine("`n---`n")
        $coreDocsJson += [PSCustomObject]@{
            filename = $docName
            path     = $docPath
            content  = [string]$docText
        }
        Write-Host "[OK] Dynamisch eingebunden: $docName" -ForegroundColor Cyan
    }
}

# 3. SAMMLE ALLE 26 SKILLS & REFERENZEN
[void]$mdBuilder.AppendLine("`n# TEIL 1: ALLE 26 SKILL-EINHEITEN (SKILL.md)`n")
$skillsRoot = "C:\DefconRecht\SKILLS"
$skillDirs = Get-ChildItem -Path $skillsRoot -Directory

$skillsList = @()
foreach ($dir in $skillDirs) {
    $skillMdPath = Join-Path $dir.FullName "SKILL.md"
    $skillText = ""
    if (Test-Path $skillMdPath) {
        $skillText = Get-Content $skillMdPath -Raw -Encoding UTF8
    }

    [void]$mdBuilder.AppendLine("## UNIT: $($dir.Name)")
    [void]$mdBuilder.AppendLine("$bt" + "markdown")
    [void]$mdBuilder.AppendLine($skillText.Trim())
    [void]$mdBuilder.AppendLine($bt)
    [void]$mdBuilder.AppendLine("")

    $refDir = Join-Path $dir.FullName "references"
    $refsList = @()
    if (Test-Path $refDir) {
        $refFiles = Get-ChildItem -Path $refDir -File -Filter "*.md"
        foreach ($rf in $refFiles) {
            $refsList += [PSCustomObject]@{
                filename = $rf.Name
                content  = [string](Get-Content $rf.FullName -Raw -Encoding UTF8)
            }
        }
    }

    $skillsList += [PSCustomObject]@{
        id         = $dir.Name
        skill_md   = [string]$skillText
        references = $refsList
    }
}

$jsonObject = [PSCustomObject]@{
    meta = [PSCustomObject]@{
        version     = "V23.4-TagX-Dynamic"
        exported_at = $timestamp
        fleet_size  = $skillDirs.Count
        core_docs   = $coreDocsJson.Count
    }
    admiral_persona      = [string]$admiralCore
    handbuch_und_chronik = $coreDocsJson
    skills               = $skillsList
}

# 4. ZENTRALE WISSENSBASEN ANHÄNGEN (Für die Markdown-Ansicht)
[void]$mdBuilder.AppendLine("`n---`n# TEIL 2: ZENTRALE WISSENSBASEN (MASTER-REFERENZEN)`n")
$masterRefs = @(
    "C:\DefconRecht\DEFCON_RECHT_Enterprise_Base.md",
    "C:\DefconRecht\SKILLS\asb-region-nordschwarzwald-neu\references\ASB_Knowledge_Base_2026.md",
    "C:\DefconRecht\SKILLS\asb-region-nordschwarzwald-neu\references\Front_Delta_Compact.md",
    "C:\DefconRecht\SKILLS\pforzheim-enzkreis-heimat\references\Events_Veranstaltungen, Freizeit, Kultur, Senioren und Barrierefrei (1).md",
    "C:\DefconRecht\SKILLS\pforzheim-enzkreis-heimat\references\Katastrophenschutz Enzkreis Nordschwarzwald.md",
    "C:\DefconRecht\SKILLS\pforzheim-enzkreis-heimat\references\Soziales-ÖPNV-Familie-Senioren-Teenager-Kultur-Bildung-Sport.md"
)

foreach ($mRef in $masterRefs) {
    if (Test-Path $mRef) {
        $mName = Split-Path $mRef -Leaf
        [void]$mdBuilder.AppendLine("## MASTER-REFERENZ: $mName")
        [void]$mdBuilder.AppendLine((Get-Content $mRef -Raw -Encoding UTF8).Trim())
        [void]$mdBuilder.AppendLine("`n---`n")
    }
}

# 5. DATEIEN SCHREIBEN (C:\ & G:\)
$mdOutPath = Join-Path $backupDir "TAG_X_FLOTTE_KOMPLETT.md"
$jsonOutPath = Join-Path $backupDir "TAG_X_FLOTTE_KOMPLETT.json"

[System.IO.File]::WriteAllText($mdOutPath, $mdBuilder.ToString(), $utf8NoBom)
$jsonString = $jsonObject | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($jsonOutPath, $jsonString, $utf8NoBom)

Write-Host "[OK] Dynamisches Markdown-Ueberlebenspaket erstellt: $mdOutPath" -ForegroundColor Green
Write-Host "[OK] Dynamisches JSON-Systemarchiv erstellt:       $jsonOutPath" -ForegroundColor Green

if (Test-Path $driveBackupDir) {
    Copy-Item $mdOutPath -Destination $driveBackupDir -Force
    Copy-Item $jsonOutPath -Destination $driveBackupDir -Force
    Write-Host "[OK] Zwillings-Backup auf Google Drive (G:\) dynamisch gespiegelt!" -ForegroundColor Green
}