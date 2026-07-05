# 展馆实装配置同步 · 从 config/exhibition_server.json 写入 backend/.env 与 kiosk_edu_spec
# 用法（仓库根目录）：
#   Copy-Item config\exhibition_server.example.json config\exhibition_server.json
#   编辑 config\exhibition_server.json 填写 public_base
#   .\05-工具脚本\apply_exhibition_config.ps1
#   .\05-工具脚本\run_backend.ps1

param(
    [string]$ConfigPath = (Join-Path (Split-Path -Parent $PSScriptRoot) "config\exhibition_server.json")
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $Root "backend\.env"
$SpecPath = Join-Path $Root "config\kiosk_edu_spec.json"

if (-not (Test-Path $ConfigPath)) {
    Write-Host "未找到 $ConfigPath" -ForegroundColor Red
    Write-Host "请先复制: config\exhibition_server.example.json → config\exhibition_server.json" -ForegroundColor Yellow
    exit 1
}

$cfg = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$publicBase = [string]$cfg.api.public_base
$ttlHours = [int]($cfg.certificate.download_ttl_hours)
if ($ttlHours -le 0) { $ttlHours = 72 }
$ttlSec = $ttlHours * 3600
$certPublic = [string]$cfg.certificate.public_download_base
if (-not $certPublic) { $certPublic = $publicBase }
$apiBase = [string]$cfg.kiosk.api_base
if (-not $apiBase) { $apiBase = "http://127.0.0.1:8000" }

# --- backend/.env ---
$envLines = @()
if (Test-Path $EnvPath) {
    $envLines = Get-Content $EnvPath -Encoding UTF8
}
function Set-EnvLine([string]$Key, [string]$Value) {
    script:envLines = $script:envLines | Where-Object { $_ -notmatch "^\s*$Key\s*=" }
    $script:envLines += "$Key=$Value"
}
Set-EnvLine "PUBLIC_API_BASE" $publicBase
Set-EnvLine "CERTIFICATE_DOWNLOAD_TTL_SEC" $ttlSec
if (-not ($envLines -match "^\s*GODOT_PATH\s*=")) {
    Write-Host "提示: backend\.env 中 GODOT_PATH 请按本机填写" -ForegroundColor Yellow
}
Set-Content -Path $EnvPath -Value $envLines -Encoding UTF8
Write-Host "已更新 backend\.env · PUBLIC_API_BASE=$publicBase" -ForegroundColor Green

# --- kiosk_edu_spec.json ---
$spec = Get-Content $SpecPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $spec.certificate) {
    $spec | Add-Member -NotePropertyName certificate -NotePropertyValue (@{})
}
$spec.api_base = $apiBase
$spec.certificate.public_download_base = $certPublic
$spec.certificate.qr_download_host = $certPublic
$spec.certificate.download_ttl_sec = $ttlSec
$spec | ConvertTo-Json -Depth 20 | Set-Content $SpecPath -Encoding UTF8
Write-Host "已更新 config\kiosk_edu_spec.json · certificate.public_download_base=$certPublic" -ForegroundColor Green

Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "  1. 配置 nginx（见 05-工具脚本\nginx_exhibition.conf.example）" -ForegroundColor White
Write-Host "  2. 重启 backend: .\05-工具脚本\run_backend.ps1" -ForegroundColor White
Write-Host "  3. Kiosk 硬刷新 · 走通 B6 保存证书 → 扫码下载" -ForegroundColor White
