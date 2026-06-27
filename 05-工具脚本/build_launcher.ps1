# 打包「启动游戏工坊.exe」一键启动器
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $PSScriptRoot "launch_workshop.py"
$Dist = Join-Path $PSScriptRoot "dist"
$Build = Join-Path $PSScriptRoot "build\launcher"
$Spec = Join-Path $PSScriptRoot "launch_workshop.spec"

Write-Host "Building launcher exe..."
python -m pip install --quiet pyinstaller

if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist }
if (Test-Path $Build) { Remove-Item -Recurse -Force $Build }

python -m PyInstaller `
    --onefile `
    --console `
    --name "启动游戏工坊" `
    --distpath $Dist `
    --workpath $Build `
    --specpath $PSScriptRoot `
    --clean `
    $Script

$Exe = Join-Path $Dist "启动游戏工坊.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "Build failed: $Exe not found"
}

$RootExe = Join-Path $Root "启动游戏工坊.exe"
Copy-Item -Force $Exe $RootExe
Write-Host ""
Write-Host "OK: $Exe"
Write-Host "OK: $RootExe  (仓库根目录副本，双击即可启动)"
Write-Host ""
Write-Host "用法: 双击 exe，或"
Write-Host "  .\启动游戏工坊.exe --mode fast   # A 链快玩"
Write-Host "  .\启动游戏工坊.exe --no-browser  # 不自动开浏览器"
