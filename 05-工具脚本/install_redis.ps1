# 安装便携 Redis 到 tools/redis/（项目内，不污染系统）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root "tools\redis"
$ZipUrl = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
$ZipFile = Join-Path $Tools "Redis-x64.zip"
$ServerDir = Join-Path $Tools "server"
$DataDir = Join-Path $Tools "data"
$ConfFile = Join-Path $Tools "redis.conf"

New-Item -ItemType Directory -Force -Path $Tools, $DataDir | Out-Null

if (-not (Test-Path (Join-Path $ServerDir "redis-server.exe"))) {
    Write-Host "下载 Redis 便携版 → $Tools"
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile -UseBasicParsing
    Expand-Archive -Path $ZipFile -DestinationPath $ServerDir -Force
    Remove-Item $ZipFile -Force
}

$confText = @"
port 6379
bind 127.0.0.1
dir ./data
appendonly no
maxmemory 64mb
"@
[System.IO.File]::WriteAllText($ConfFile, $confText, [System.Text.UTF8Encoding]::new($false))

Write-Host "Redis 已安装: $ServerDir"
Write-Host "数据目录: $DataDir"
Write-Host "启动: .\05-工具脚本\run_redis.ps1"
