# 打包 GameForgeLabHelper.exe · 学生机部署 + 本机 Godot 助手服务
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $PSScriptRoot "lab_godot_helper.py"
$Dist = Join-Path $PSScriptRoot "dist"
$Build = Join-Path $PSScriptRoot "build\lab_helper"
$ExeName = "GameForgeLabHelper.exe"

Write-Host "Building GameForge lab helper exe v1.0 ..."
python -m pip install --quiet pyinstaller

if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist -ErrorAction SilentlyContinue }
if (Test-Path $Build) { Remove-Item -Recurse -Force $Build -ErrorAction SilentlyContinue }

python -m PyInstaller `
  --onefile `
  --console `
  --name "GameForgeLabHelper" `
  --distpath $Dist `
  --workpath $Build `
  --specpath $PSScriptRoot `
  --clean `
  $Script

$Exe = Join-Path $Dist $ExeName
if (-not (Test-Path $Exe)) {
  Write-Error "Build failed: $Exe not found"
}

Write-Host ""
Write-Host "OK: $Exe"
Write-Host ""
Write-Host "学生机部署:"
Write-Host "  .\GameForgeLabHelper.exe deploy --net-user `"10.71.121.18\TEST1`""
Write-Host ""
Write-Host "上课前启动助手（保持窗口）:"
Write-Host "  .\GameForgeLabHelper.exe"
Write-Host "  .\GameForgeLabHelper.exe serve"
Write-Host ""
Write-Host "Next: pack zip for server"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\05-工具脚本\pack_lab_helper_zip.ps1"
Write-Host "  -> 交付\GameForge-LabHelper-20260721.zip"
Write-Host ""
