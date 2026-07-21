# GameForge K12 · 教学机房 · 学生机一键部署（S2-路B）
# 用法（管理员 PowerShell）：
#   powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_lab_student.ps1 `
#     -NetUser "10.71.121.18\TEST1"
# 或已打包 exe：
#   .\GameForgeLabHelper.exe deploy --net-user "10.71.121.18\TEST1"
param(
  [string]$ServerIp = "10.71.121.18",
  [string]$ShareName = "GameForgeWorkspace",
  [string]$LocalDrive = "Z:",
  [string]$WorkspacePrefix = "E:\project\GameForge-K12\workspace",
  [string]$GodotPath = "C:\Godot\Godot_v4.6.3-stable_win64.exe",
  [string]$NetUser = "",
  [switch]$SkipNetUse,
  [switch]$StartHelper
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$HelperPy = Join-Path $PSScriptRoot "lab_godot_helper.py"
$HelperExe = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "dist") -Filter "GameForge*.exe" | Select-Object -First 1
$VenvPy = Join-Path $Root "backend\.venv\Scripts\python.exe"

if ($HelperExe) {
  $deployArgs = @(
    "deploy",
    "--server-ip", $ServerIp,
    "--share-name", $ShareName,
    "--local-drive", $LocalDrive,
    "--workspace-prefix", $WorkspacePrefix,
    "--godot-path", $GodotPath
  )
  if ($NetUser) { $deployArgs += @("--net-user", $NetUser) }
  if ($SkipNetUse) { $deployArgs += "--skip-net-use" }
  & $HelperExe.FullName @deployArgs
} elseif (Test-Path $VenvPy) {
  $deployArgs = @(
    $HelperPy, "deploy",
    "--server-ip", $ServerIp,
    "--share-name", $ShareName,
    "--local-drive", $LocalDrive,
    "--workspace-prefix", $WorkspacePrefix,
    "--godot-path", $GodotPath
  )
  if ($NetUser) { $deployArgs += @("--net-user", $NetUser) }
  if ($SkipNetUse) { $deployArgs += "--skip-net-use" }
  & $VenvPy @deployArgs
} else {
  Write-Error "未找到 backend\.venv 或 dist\GameForge*.exe"
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($StartHelper) {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $shortcutTarget = if ($HelperExe) { $HelperExe.FullName } else { $VenvPy }
  $shortcutArgs = if ($HelperExe) { "" } else { "`"$HelperPy`" serve" }
  Write-Host "提示：请将助手加入开机启动，或桌面双击运行："
  Write-Host "  $shortcutTarget $shortcutArgs"
}
