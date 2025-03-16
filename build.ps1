# lus4n local packaging script using PyInstaller
# Usage: .\build.ps1

Write-Host "Starting lus4n packaging process..." -ForegroundColor Cyan

# Create and activate virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
$envPath = ".venv"
if (Test-Path $envPath) {
    Remove-Item -Path $envPath -Recurse -Force
}
python -m venv $envPath

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$envPath\Scripts\Activate.ps1"

# Install necessary dependencies
Write-Host "Installing necessary dependencies..." -ForegroundColor Green
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Create a hook file for luaparser
Write-Host "Creating hook file for luaparser..." -ForegroundColor Yellow
$hookDir = ".\hooks"
if (!(Test-Path $hookDir)) {
    New-Item -Path $hookDir -ItemType Directory | Out-Null
}
$hookContent = @"
# PyInstaller hook for luaparser
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Make sure all submodules are included
hiddenimports = collect_submodules('luaparser')

# Include any data files
datas = collect_data_files('luaparser')
"@
Set-Content -Path "$hookDir\hook-luaparser.py" -Value $hookContent

# Clean up old output directories
Write-Host "Cleaning up old output directories..." -ForegroundColor Yellow
$outputDirs = @(".\dist", ".\build", ".\releases")
foreach ($dir in $outputDirs) {
    if (Test-Path $dir) {
        Remove-Item -Path $dir -Recurse -Force
    }
    New-Item -Path $dir -ItemType Directory | Out-Null
}

# Get CPU core count for parallel compilation
$cpuCores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors

# Package GUI application
Write-Host "Packaging GUI application (using $cpuCores CPU cores)..." -ForegroundColor Green
pyinstaller --clean --noconfirm --onedir --name "lus4n-gui" --windowed --additional-hooks-dir=hooks lus4n\gui.py

# Package command-line application
Write-Host "Packaging command-line application..." -ForegroundColor Green
pyinstaller --clean --noconfirm --onedir --name "lus4n-cli" --additional-hooks-dir=hooks lus4n\cli.py

# Check generated executable files
$guiExe = ".\dist\lus4n-gui\lus4n-gui.exe"
$cliExe = ".\dist\lus4n-cli\lus4n-cli.exe"

if (!(Test-Path $guiExe) -or !(Test-Path $cliExe)) {
    Write-Host "Packaging failed, cannot find generated executable files!" -ForegroundColor Red
    exit 1
}

# Create release archives
Write-Host "Creating release archives..." -ForegroundColor Yellow
Compress-Archive -Path ".\dist\lus4n-gui\*" -DestinationPath ".\releases\lus4n-gui-windows.zip" -Force
Compress-Archive -Path ".\dist\lus4n-cli\*" -DestinationPath ".\releases\lus4n-cli-windows.zip" -Force

# Clean up virtual environment
Write-Host "Cleaning up virtual environment..." -ForegroundColor Yellow
deactivate
Remove-Item -Path $envPath -Recurse -Force

Write-Host "Packaging complete!" -ForegroundColor Green
Write-Host "Generated files are located in the releases directory:" -ForegroundColor Cyan
Write-Host "- GUI version: releases\lus4n-gui-windows.zip" -ForegroundColor White
Write-Host "- Command-line version: releases\lus4n-cli-windows.zip" -ForegroundColor White