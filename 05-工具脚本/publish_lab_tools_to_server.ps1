# 将开发机构建产物发布到教室服务器 workspace 共享 _tools（须能写入 UNC）
param(
  [string]$DevRoot = "E:\文三路AI馆\2.ai生成游戏",
  [string]$ServerIp = "10.71.121.18",
  [string]$ShareName = "GameForgeWorkspace"
)

$ErrorActionPreference = "Stop"
$HelperSrc = Join-Path $DevRoot "05-工具脚本\dist\GameForgeLabHelper.exe"
$LaunchSrc = Join-Path $DevRoot "05-工具脚本\launch-session-godot.ps1"
$ToolsUnc = "\\$ServerIp\$ShareName\_tools"
$HelperDest = Join-Path $ToolsUnc "GameForgeLabHelper.exe"
$LaunchDest = Join-Path $ToolsUnc "launch-session-godot.ps1"

if (-not (Test-Path $HelperSrc)) {
  Write-Error "未找到 $HelperSrc · 请先运行 05-工具脚本\build_lab_helper.ps1"
}

New-Item -ItemType Directory -Force -Path $ToolsUnc | Out-Null
Copy-Item $HelperSrc $HelperDest -Force
Copy-Item $LaunchSrc $LaunchDest -Force

Write-Host "已发布:"
Get-Item $HelperDest, $LaunchDest | Format-Table FullName, Length, LastWriteTime
