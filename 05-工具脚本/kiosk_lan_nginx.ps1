# GameForge K12 · 展厅 LAN 反代草案
# 用途：同一局域网终端通过 http://<本机IP>:9080/kiosk/ 访问 Kiosk，API 走 /api/ 反代到 backend :8000
# 前置：安装 nginx（Windows 可用 choco install nginx 或解压 nginx.org 发行版）
# 用法（PowerShell，仓库根目录）：
#   .\05-工具脚本\kiosk_lan_nginx.ps1
#   .\05-工具脚本\kiosk_lan_nginx.ps1 -Port 9080 -BackendPort 8000
# 停止：Ctrl+C 或 taskkill /IM nginx.exe

param(
    [int]$Port = 9080,
    [int]$BackendPort = 8000,
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$KioskRoot = Join-Path $RepoRoot "kiosk"
$ConfDir = Join-Path $env:TEMP "gameforge-kiosk-nginx"
$ConfPath = Join-Path $ConfDir "kiosk.conf"
$LogDir = Join-Path $ConfDir "logs"

New-Item -ItemType Directory -Force -Path $ConfDir, $LogDir | Out-Null

# 反斜杠 → nginx 正斜杠
$KioskRootNginx = ($KioskRoot -replace "\\", "/")

$conf = @"
worker_processes  1;
error_log  "$($LogDir -replace '\\','/')/error.log";
pid        "$($ConfDir -replace '\\','/')/nginx.pid";

events { worker_connections  1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout  65;

    server {
        listen       $Port;
        server_name  _;

        # Kiosk 静态页（仓库根 python -m http.server 8080 等价，但单端口合并 API）
        location /kiosk/ {
            alias $KioskRootNginx/;
            index index.html;
            try_files `$uri `$uri/ /kiosk/index.html;
        }

        location = / {
            return 302 /kiosk/;
        }

        # FastAPI 反代
        location /api/ {
            proxy_pass http://127.0.0.1:$BackendPort/;
            proxy_http_version 1.1;
            proxy_set_header Host `$host;
            proxy_set_header X-Real-IP `$remote_addr;
            proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        }

        # 静态 assets / config（Kiosk 引用 ../assets ../config）
        location /assets/ {
            alias $($RepoRoot -replace '\\','/')/assets/;
        }
        location /config/ {
            alias $($RepoRoot -replace '\\','/')/config/;
        }
    }
}
"@

Set-Content -Path $ConfPath -Value $conf -Encoding UTF8

$nginx = Get-Command nginx -ErrorAction SilentlyContinue
if (-not $nginx) {
    Write-Host "未找到 nginx。请安装后重试，或继续使用:" -ForegroundColor Yellow
    Write-Host "  cd `"$RepoRoot`"" -ForegroundColor Cyan
    Write-Host "  python -m http.server 8080" -ForegroundColor Cyan
    Write-Host "  .\05-工具脚本\run_backend.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "已生成配置草案: $ConfPath" -ForegroundColor Green
    exit 0
}

Write-Host "GameForge Kiosk LAN 反代" -ForegroundColor Cyan
Write-Host "  Kiosk:  http://127.0.0.1:$Port/kiosk/" -ForegroundColor Green
Write-Host "  LAN:    http://<本机IP>:$Port/kiosk/" -ForegroundColor Green
Write-Host "  API:    http://127.0.0.1:$Port/api/  → :$BackendPort" -ForegroundColor Green
Write-Host "  配置:   $ConfPath" -ForegroundColor Gray
Write-Host ""
Write-Host "注意: wizard.js 当前 API base 为 http://127.0.0.1:8000；" -ForegroundColor Yellow
Write-Host "LAN 终端需后续将 API 改为同源 /api/ 或本机 IP:8000（线 A3 后续项）。" -ForegroundColor Yellow
Write-Host ""

Push-Location $ConfDir
try {
    & nginx -p $ConfDir -c $ConfPath
    Write-Host "nginx 已启动。按 Ctrl+C 停止本脚本后执行: nginx -s stop -p $ConfDir" -ForegroundColor Cyan
    while ($true) { Start-Sleep -Seconds 3600 }
} finally {
    Pop-Location
}
