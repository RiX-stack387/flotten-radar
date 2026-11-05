Write-Host ">>> STARTE TAG-X VOLL-ARSENAL GENERATOR (PYTHON TOP-DOWN KERN)..." -ForegroundColor Yellow
python "C:\DefconRecht\fix_and_build_tagx.py"
$DriveBackupDir = "G:\Meine Ablage\DefconRecht\TAG_X_BACKUP"
if (Test-Path "G:\Meine Ablage\DefconRecht") {
    if (!(Test-Path $DriveBackupDir)) { New-Item -ItemType Directory -Path $DriveBackupDir | Out-Null }
    Copy-Item "C:\DefconRecht\TAG_X_BACKUP\*" "$DriveBackupDir\" -Force
    Write-Host "[OK] Zwillings-Backup auf Google Drive (G:\) dynamisch gespiegelt!" -ForegroundColor Green
}
