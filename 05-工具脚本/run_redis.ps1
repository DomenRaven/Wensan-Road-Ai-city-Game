# 启动 tools/redis/ 中的 Redis（需先 install_redis.ps1）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Server = Join-Path $Root "tools\redis\server\redis-server.exe"
$Conf = Join-Path $Root "tools\redis\redis.conf"

if (-not (Test-Path $Server)) {
    Write-Host "未找到 Redis，请先运行: .\05-工具脚本\install_redis.ps1"
    exit 1
}

$existing = Get-Process -Name "redis-server" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Redis 已在运行 (pid $($existing[0].Id))"
    exit 0
}

Start-Process -FilePath $Server -ArgumentList $Conf -WorkingDirectory (Join-Path $Root "tools\redis") -WindowStyle Hidden
Start-Sleep -Seconds 1
Write-Host "Redis 已启动 → redis://127.0.0.1:6379/0"
Write-Host "验证: curl http://127.0.0.1:8000/health  (需 backend 运行，session_backend 应为 redis)"
