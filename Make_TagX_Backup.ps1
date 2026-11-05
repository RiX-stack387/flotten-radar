Write-Host ">>> STARTE TAG-X BACKUP (26 SKILLS: ANLEITUNGEN & REFERENCES + SEPARATES MASTER-ARCHIV)..." -ForegroundColor Yellow
python "C:\DefconRecht\tagx_step1.py"
python "C:\DefconRecht\tagx_step2.py"
Copy-Item "C:\DefconRecht\Master_Archiv_V23.4_EINSATZ-CHRONIK.md" "C:\DefconRecht\TAG_X_BACKUP\Master_Archiv_V23.4_EINSATZ-CHRONIK.md" -Force
$DriveBackupDir = "G:\Meine Ablage\DefconRecht\TAG_X_BACKUP"
if (Test-Path "G:\Meine Ablage\DefconRecht") {
    if (!(Test-Path $DriveBackupDir)) { New-Item -ItemType Directory -Path $DriveBackupDir | Out-Null }
    Copy-Item "C:\DefconRecht\TAG_X_BACKUP\*" "$DriveBackupDir\" -Force
    Write-Host "[OK] TAG_X_BACKUP (MD, JSON + separates Master-Archiv) nach G:\ gespiegelt!" -ForegroundColor Green
}
