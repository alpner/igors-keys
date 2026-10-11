# Builds dist\IgorsKeys\ (a folder that needs no Python on the target machine).
# Run from the app folder:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python make_icon.py
python -m PyInstaller --noconfirm --clean --windowed --name IgorsKeys `
    --icon igorskeys\icon.ico `
    --add-data "igorskeys\keys.json;igorskeys" `
    --add-data "igorskeys\icon.ico;igorskeys" `
    --collect-submodules pystray `
    main.py
Copy-Item ..\README.md, ..\README.sl.md, ..\FAQ.md, ..\ABOUT.md, ..\CHANGELOG.md, ..\LICENSE dist\IgorsKeys\ -Force
Write-Host "Done: dist\IgorsKeys\IgorsKeys.exe"
