# 打包 GameForgeLabServer.exe · 教学机房服务器一键启动（0.0.0.0）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $PSScriptRoot "launch_lab_server.py"
$Dist = Join-Path $PSScriptRoot "dist"
$Build = Join-Path $PSScriptRoot "build\lab_server"
$ExeName = "GameForgeLabServer.exe"

Write-Host "Building GameForge lab server launcher v1.0 ..." 
python -m pip install --quiet pyinstaller

if (Test-Path $Build) { Remove-Item -Recurse -Force $Build -ErrorAction SilentlyContinue }

python -m PyInstaller `
  --onefile `
  --console `
  --name "GameForgeLabServer" `
  --distpath $Dist `
  --workpath $Build `
  --specpath $PSScriptRoot `
  --clean `
  $Script

$Exe = Join-Path $Dist $ExeName
if (-not (Test-Path $Exe)) {
  Write-Error "Build failed: $Exe not found"
}

$RootExe = Join-Path $Root $ExeName
Copy-Item -Force $Exe $RootExe

Write-Host ""
Write-Host "OK: $Exe"
Write-Host "OK: $RootExe  (仓库根目录副本)"
Write-Host ""
Write-Host "服务器用法（放在 E:\project\GameForge-K12\ 根目录）："
Write-Host "  .\GameForgeLabServer.exe"
Write-Host "  .\GameForgeLabServer.exe --server-ip 10.71.121.18"
Write-Host "  .\GameForgeLabServer.exe --open-browser"
Write-Host ""
Write-Host "对比：启动游戏工坊.exe 仅 127.0.0.1，勿用于机房服务器。"
