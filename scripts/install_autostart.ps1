# Script PowerShell per configurare l'avvio automatico di AntigraCall in background
# Risolve la directory del progetto in modo robusto rispetto a dove viene eseguito lo script
if ($PSScriptRoot) {
    $projectDir = (Get-Item "$PSScriptRoot\..").FullName
    $scriptsDir = $PSScriptRoot
} else {
    $projectDir = (Get-Item ".").FullName
    if ($projectDir.EndsWith("\scripts") -or $projectDir.EndsWith("/scripts")) {
        $projectDir = Split-Path -Parent $projectDir
    }
    $scriptsDir = "$projectDir\scripts"
}

Write-Host "Configurazione autostart per AntigraCall in: $projectDir" -ForegroundColor Cyan

# 1. Crea lo start_bot.bat
$batContent = @"
@echo off
cd /d "$projectDir"
call .\.venv\Scripts\activate.bat
python.exe -m antigracall.main
"@
$batPath = "$projectDir\start_bot.bat"
$batContent | Out-File -FilePath $batPath -Encoding ascii -Force
Write-Host "Creato script batch di avvio: $batPath" -ForegroundColor Green

# 2. Crea il run_background.vbs (permette l'esecuzione completamente invisibile)
$vbsContent = @"
Dim WinScriptHost
Set WinScriptHost = CreateObject("WScript.Shell")
WinScriptHost.Run Chr(34) & "$projectDir\start_bot.bat" & Chr(34), 0
Set WinScriptHost = Nothing
"@
$vbsPath = "$scriptsDir\run_background.vbs"
$vbsContent | Out-File -FilePath $vbsPath -Encoding ascii -Force
Write-Host "Creato script VBS per l'esecuzione invisibile: $vbsPath" -ForegroundColor Green

# 3. Crea il collegamento nella cartella di Esecuzione Automatica (Startup) di Windows
$startupFolder = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup')
$shortcutPath = "$startupFolder\AntigraCall.lnk"

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $vbsPath
    $Shortcut.WorkingDirectory = $projectDir
    $Shortcut.Description = "Avvio automatico del bot Telegram AntigraCall"
    $Shortcut.Save()
    Write-Host "Collegamento creato con successo nella cartella Startup:" -ForegroundColor Green
    Write-Host "--> $shortcutPath" -ForegroundColor Yellow
} catch {
    Write-Error "Impossibile creare il collegamento in Startup: $_"
}

Write-Host "Installazione completata! Il bot si avvierà automaticamente ad ogni avvio di Windows in modo invisibile." -ForegroundColor Green
