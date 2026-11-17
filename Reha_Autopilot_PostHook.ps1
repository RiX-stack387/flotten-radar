$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$baseDir    = "C:\DefconRecht"
$skillsDir  = Join-Path $baseDir "SKILLS"
$tagXDir    = Join-Path $baseDir "TAG_X_BACKUP"
$archivFile = "Master_Archiv_V23.4_AKTIV_ab_4000.md"
$rootArchiv = Join-Path $baseDir $archivFile
$deltaFile  = Join-Path $baseDir "Front_Delta_Compact.md"
$tagXScript = Join-Path $baseDir "Make_TagX_Backup.ps1"

$nowDate = Get-Date -Format "dd.MM.yyyy"
$nowTime = Get-Date -Format "HH:mm"
$deltaSummary = "Keine inhaltlichen Aenderungen"
if (Test-Path $deltaFile) {
    $dLines = [System.IO.File]::ReadAllLines($deltaFile, $utf8NoBom) | Where-Object { $_ -match '^\-\s+\[' }
    if ($dLines.Count -gt 0) {
        $deltaSummary = ($dLines.Count.ToString() + " Delta-Eintraege aktiv: " + (($dLines | Select-Object -First 3) -join " | "))
    }
}

if (Test-Path $rootArchiv) {
    $archTxt = [System.IO.File]::ReadAllText($rootArchiv, $utf8NoBom).TrimStart([char]0xFEFF)
    $kbSize  = [math]::Round(((Get-Item $rootArchiv).Length / 1KB), 1)
    $autoEntry = "- [🤖 REHA-AUTOPILOT] | 📅 $nowDate | 🕒 $nowTime Uhr CET | Automatischer Nachtlauf abgeschlossen ($deltaSummary) | Archiv-Groesse: $kbSize KB / 400 KB."
    if ($archTxt -notmatch [regex]::Escape("📅 $nowDate") -or $archTxt -notmatch 'REHA-AUTOPILOT') {
        $sep = if ($archTxt.EndsWith("`n")) { "" } else { "`n" }
        $archTxt = $archTxt + $sep + $autoEntry + "`n"
        [System.IO.File]::WriteAllText($rootArchiv, $archTxt, $utf8NoBom)
    }
    Copy-Item -Path $rootArchiv -Destination (Join-Path $skillsDir "admiral-flotten-leitstand\references\$archivFile") -Force
    if (Test-Path $tagXDir) {
        Copy-Item -Path $rootArchiv -Destination (Join-Path $tagXDir $archivFile) -Force
    }
}

if (Test-Path $tagXScript) {
    & $tagXScript
}