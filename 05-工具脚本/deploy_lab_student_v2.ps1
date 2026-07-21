# GameForge K12 · 教学机房 · 学生机一键部署 v2（S2-路B）
# 与 机房部署现场记录/学生机_巡检表.md 内联脚本等价 · 参数化 ServerIp / NetUser
# 用法（管理员 PowerShell）：
#   powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_lab_student_v2.ps1 `
#     -ServerIp "192.168.1.100" -NetUser "192.168.1.100\TEST1"
param(
  [Parameter(Mandatory = $true)]
  [string]$ServerIp,
  [Parameter(Mandatory = $true)]
  [string]$NetUser
)

$ErrorActionPreference = "Stop"
$ShareUnc    = "\\$ServerIp\GameForgeWorkspace"
$HelperLocal = "C:\GameForge\GameForgeLabHelper.exe"
$GodotLocal  = "C:\Godot\Godot_v4.6.3-stable_win64.exe"
$ToolsHelper = "Z:\_tools\GameForgeLabHelper.exe"
$ToolsPs1    = "Z:\_tools\launch-session-godot.ps1"
$ToolsGodot  = "Z:\_tools\Godot\Godot_v4.6.3-stable_win64.exe"

Write-Host "=== GameForge 学生机一键部署 v2 ===" -ForegroundColor Cyan
Write-Host "ServerIp=$ServerIp NetUser=$NetUser"

Enable-NetFirewallRule -DisplayGroup "文件和打印机共享" -ErrorAction SilentlyContinue | Out-Null

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
cmd /c "net use Z: /delete /y >nul 2>&1" | Out-Null
$ErrorActionPreference = $prevEap

Write-Host "[1/5] 正在映射 Z: -> $ShareUnc （请输入 SMB 密码）" -ForegroundColor Yellow
& net.exe use "Z:" $ShareUnc "/persistent:yes" "/user:$NetUser"
if ($LASTEXITCODE -ne 0) {
  throw "net use Z: 失败 exit=$LASTEXITCODE · 查: 445 通否 · 账号 $NetUser · 服务器 SMB 共享 GameForgeWorkspace"
}
if (-not (Test-Path "Z:\")) { throw "Z: 映射后仍不可用" }
Write-Host "[1/5] Z: OK" -ForegroundColor Green

foreach ($p in @($ToolsHelper, $ToolsPs1, $ToolsGodot)) {
  if (-not (Test-Path $p)) {
    throw "共享缺少: $p · 请在服务器发布 _tools（助手 v1.0.1 + §2.5 Godot）"
  }
}
Write-Host "[2/5] Z:\_tools 三件套 OK" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path "C:\GameForge" | Out-Null
Copy-Item $ToolsHelper $HelperLocal -Force
Copy-Item $ToolsPs1 "C:\GameForge\launch-session-godot.ps1" -Force
Write-Host "[3/5] 已复制到 C:\GameForge\" -ForegroundColor Green

& $HelperLocal deploy --skip-net-use
if ($LASTEXITCODE -ne 0) { throw "deploy 失败 exit=$LASTEXITCODE" }
Write-Host "[4/5] deploy OK" -ForegroundColor Green

$rows = @(
  [pscustomobject]@{ Check = "Z: 映射"; Pass = (Test-Path "Z:\") }
  [pscustomobject]@{ Check = "Godot exe"; Pass = (Test-Path $GodotLocal) }
  [pscustomobject]@{ Check = "lab_helper.json"; Pass = (Test-Path "C:\GameForge\lab_helper.json") }
  [pscustomobject]@{ Check = "启动脚本"; Pass = (Test-Path "C:\GameForge\launch-session-godot.ps1") }
  [pscustomobject]@{ Check = "助手 exe"; Pass = (Test-Path $HelperLocal) }
)
try {
  $k = Invoke-WebRequest "http://${ServerIp}:8080/kiosk/edu/" -UseBasicParsing -TimeoutSec 8
  $rows += [pscustomobject]@{ Check = "Kiosk 8080"; Pass = ($k.StatusCode -eq 200) }
} catch { $rows += [pscustomobject]@{ Check = "Kiosk 8080"; Pass = $false } }
try {
  $a = Invoke-RestMethod "http://${ServerIp}:8000/health" -TimeoutSec 8
  $rows += [pscustomobject]@{ Check = "API local_share"; Pass = ($a.play_launch_mode -eq "local_share") }
} catch { $rows += [pscustomobject]@{ Check = "API local_share"; Pass = $false } }
$rows | Format-Table Check, Pass -AutoSize
if ($rows.Pass -contains $false) { throw "§8 自检未全过 · 见上表" }

Get-Process GameForgeLabHelper -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Process $HelperLocal
Start-Sleep -Seconds 2
$h = Invoke-RestMethod http://127.0.0.1:17890/health -TimeoutSec 5
Write-Host "[5/5] 助手 health: ok=$($h.ok) version=$($h.version)" -ForegroundColor Green
if ($h.version -ne "1.0.1") { Write-Warning "期望 version=1.0.1 · 请更新服务器 _tools 后重跑 Copy-Item 段" }
Write-Host "部署完成 → http://${ServerIp}:8080/kiosk/edu/" -ForegroundColor Cyan
