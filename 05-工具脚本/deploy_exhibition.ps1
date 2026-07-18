# GameForge K12 · 展厅一键部署脚本（给人 / 给 AI Agent）
# 用法（在仓库根目录）:
#   powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1
#   powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 -GodotPath "C:\Godot\Godot_v4.6.3-stable_win64.exe"
#   powershell -ExecutionPolicy Bypass -File .\05-工具脚本\deploy_exhibition.ps1 -NoBrowser -SkipRedis
param(
    [string]$GodotPath = "",
    [switch]$NoBrowser,
    [switch]$SkipRedis,
    [switch]$SkipLauncherBuild,
    [ValidateSet("edu", "fast")]
    [string]$Mode = "edu"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }

Write-Host "============================================================"
Write-Host "  GameForge K12 · 展厅一键部署 v1.2"
Write-Host "  Root: $Root"
Write-Host "============================================================"

# --- Preflight ---
Write-Step "检查 Python"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "未找到 python。请安装 Python 3.11+ 并勾选 Add to PATH。" }
python --version

Write-Step "检查目录结构"
foreach ($d in @("backend", "kiosk", "templates", "config", "assets")) {
    if (-not (Test-Path (Join-Path $Root $d))) { throw "缺少目录: $d" }
}

# --- .env ---
Write-Step "配置 backend/.env"
$envFile = Join-Path $Root "backend\.env"
$envExample = Join-Path $Root "backend\.env.example"
if (-not (Test-Path $envFile)) {
    if (-not (Test-Path $envExample)) { throw "缺少 backend/.env.example" }
    Copy-Item $envExample $envFile
    Write-Host "已从 .env.example 复制 backend/.env"
}

if ($GodotPath -ne "") {
    if (-not (Test-Path $GodotPath)) { throw "GODOT_PATH 不存在: $GodotPath" }
    $raw = Get-Content $envFile -Raw -Encoding UTF8
    if ($raw -match "(?m)^GODOT_PATH=.*$") {
        $raw = $raw -replace "(?m)^GODOT_PATH=.*$", "GODOT_PATH=$GodotPath"
    } else {
        $raw = $raw.TrimEnd() + "`r`nGODOT_PATH=$GodotPath`r`n"
    }
    Set-Content -Path $envFile -Value $raw -Encoding UTF8
    Write-Host "已写入 GODOT_PATH=$GodotPath"
} else {
    $line = (Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match "^GODOT_PATH=" } | Select-Object -First 1)
    if (-not $line -or $line -match "F:\\Godot\\" -or $line -match "TBD") {
        Write-Host "警告: 请用 -GodotPath 指定本机 Godot 4.6 Standard exe，否则试玩 launch 会失败。" -ForegroundColor Yellow
    }
}

# --- Redis ---
if (-not $SkipRedis) {
    Write-Step "安装/启动 Redis（可选）"
    $redisExe = Join-Path $Root "tools\redis\server\redis-server.exe"
    if (-not (Test-Path $redisExe)) {
        $install = Join-Path $PSScriptRoot "install_redis.ps1"
        if (Test-Path $install) {
            try { & $install } catch { Write-Host "Redis 安装失败，将使用内存会话降级: $_" -ForegroundColor Yellow }
        }
    }
    $runRedis = Join-Path $PSScriptRoot "run_redis.ps1"
    if ((Test-Path $redisExe) -and (Test-Path $runRedis)) {
        try { & $runRedis } catch { Write-Host "Redis 启动跳过: $_" -ForegroundColor Yellow }
    }
} else {
    Write-Host "已 SkipRedis · 会话将使用 memory 降级"
}

# --- Backend venv ---
Write-Step "准备 backend/.venv 依赖"
$venvPy = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Push-Location (Join-Path $Root "backend")
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
    Pop-Location
} else {
    Write-Host "已存在 backend/.venv"
}

# --- Launcher exe ---
if (-not $SkipLauncherBuild) {
    $exe = Join-Path $Root "启动游戏工坊.exe"
    if (-not (Test-Path $exe)) {
        Write-Step "打包一键启动 exe"
        & (Join-Path $PSScriptRoot "build_launcher.ps1")
    } else {
        Write-Host "已存在 启动游戏工坊.exe"
    }
}

# --- Start services via launch_workshop ---
Write-Step "启动服务 (API :8000 · Kiosk :8080)"
$launchArgs = @("--mode", $Mode)
if ($NoBrowser) { $launchArgs += "--no-browser" }

$launchPy = Join-Path $PSScriptRoot "launch_workshop.py"
if (Test-Path (Join-Path $Root "启动游戏工坊.exe")) {
    Write-Host "提示: 也可双击根目录「启动游戏工坊.exe」"
}

# Prefer python launch so this script stays in foreground control when needed
# For exhibition, start launch_workshop which blocks until Enter
Write-Host ""
Write-Host "端口一览:"
Write-Host "  8000  FastAPI 后端   http://127.0.0.1:8000/docs"
Write-Host "  8080  Kiosk 静态    http://127.0.0.1:8080/kiosk/edu/"
Write-Host "  6379  Redis（若已启）"
Write-Host ""
Write-Host "主入口: http://127.0.0.1:8080/kiosk/edu/"
Write-Host ""

& $venvPy $launchPy @launchArgs
