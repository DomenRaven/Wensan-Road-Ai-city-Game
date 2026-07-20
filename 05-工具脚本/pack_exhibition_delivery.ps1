$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "交付"
$Stamp = Get-Date -Format "yyyyMMdd"
$ZipName = "GameForge-K12-v1.2-server-$Stamp.zip"
$ZipPath = Join-Path $OutDir $ZipName
$Stage = Join-Path $OutDir "_stage_v1.2"
Write-Host "Packing server delivery..."
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Force -Path $OutDir, $Stage | Out-Null

$includeDirs = @(
  "backend", "kiosk", "templates", "config", "assets",
  "05-工具脚本", "开发文档", "tools"
)
$includeFiles = @(
  "VERSION", "CHANGELOG.md", "README.md", "文档目录说明.md",
  "请先读_展厅部署与操作.md"
)
$excludeDirNames = @(
  ".venv", "__pycache__", ".godot", "workspace", "_dev_archive",
  "build", "dist", "frozen", ".pytest_cache", ".clawhub",
  "node_modules", ".git", ".cursor", "reports", "experiences", "snippets"
)
# 开发探针 / 一次性脚本：即使未归档也不打进交付包
$excludeFileNames = @(
  "e2e_7_18_live_three_tasks.py",
  "e2e_7_19_live_three_tasks.py",
  "e2e_seven_genres_sandbox.py",
  "e2e_seven_genres_godot_smoke.py",
  "sandbox_llm_inject_probe.py",
  "generate_acceptance_doc.py",
  "pack_exhibition_delivery.ps1"
)

function Copy-Filtered([string]$src, [string]$dst) {
  if (-not (Test-Path $src)) { return }
  if (-not (Get-Item $src).PSIsContainer) {
    $p = Split-Path $dst -Parent
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
    Copy-Item -Force $src $dst
    return
  }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Get-ChildItem $src -Force | ForEach-Object {
    if ($_.PSIsContainer -and ($excludeDirNames -contains $_.Name)) { return }
    if ($_.Name -eq ".env") { return }
    if ($excludeFileNames -contains $_.Name) { return }
    if ($_.Extension -in @(".pyc", ".spec")) { return }
    $t = Join-Path $dst $_.Name
    if ($_.PSIsContainer) { Copy-Filtered $_.FullName $t } else { Copy-Item -Force $_.FullName $t }
  }
}

foreach ($n in $includeDirs) {
  $s = Join-Path $Root $n
  if (Test-Path $s) { Write-Host "  + $n"; Copy-Filtered $s (Join-Path $Stage $n) }
}
foreach ($n in $includeFiles) {
  $s = Join-Path $Root $n
  if (Test-Path $s) {
    Write-Host "  + $n"
    Copy-Item -Force $s (Join-Path $Stage $n)
  } else { Write-Host "  skip $n" }
}

# data：只带策展 Reference Skill + 空 learned_skills 骨架（不带运行时 experiences）
$dataStage = Join-Path $Stage "data"
New-Item -ItemType Directory -Force -Path $dataStage | Out-Null
$refSrc = Join-Path $Root "data\reference_skills"
if (Test-Path $refSrc) {
  Write-Host "  + data/reference_skills"
  Copy-Filtered $refSrc (Join-Path $dataStage "reference_skills")
}
$lsStage = Join-Path $dataStage "learned_skills"
New-Item -ItemType Directory -Force -Path $lsStage | Out-Null
Set-Content (Join-Path $lsStage ".gitkeep") ""
Set-Content (Join-Path $lsStage "index.jsonl") ""
Write-Host "  + data/learned_skills (empty)"

# 空 workspace
$ws = Join-Path $Stage "workspace"
New-Item -ItemType Directory -Force -Path $ws | Out-Null
Set-Content (Join-Path $ws ".gitkeep") ""
Write-Host "  + workspace (empty)"

# Discover launcher exe
$exe = Get-ChildItem -Path $Root -File -Filter "*.exe" |
  Where-Object { $_.Name -match "启动|工坊|GameForge|workshop" -or $_.Length -gt 1MB } |
  Sort-Object Length -Descending |
  Select-Object -First 1
if ($exe) {
  $destExe = Join-Path $Stage "启动游戏工坊.exe"
  Copy-Item -Force $exe.FullName $destExe
  Write-Host "  + EXE from $($exe.Name) -> 启动游戏工坊.exe"
} else {
  Write-Host "WARNING: no launcher exe" -ForegroundColor Yellow
}

# 包内醒目：AI 部署入口副本（根目录快捷）
$aiDoc = Join-Path $Root "开发文档\服务器部署_AI智能体自动部署手册_v1.3.md"
if (Test-Path $aiDoc) {
  Copy-Item -Force $aiDoc (Join-Path $Stage "AI智能体自动部署手册_请先读.md")
  Write-Host "  + AI智能体自动部署手册_请先读.md (root shortcut)"
}

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
  $Stage, $ZipPath,
  [System.IO.Compression.CompressionLevel]::Optimal,
  $false
)
Write-Host ("OK: {0} ({1} MB)" -f $ZipPath, [math]::Round((Get-Item $ZipPath).Length / 1MB, 1))
Remove-Item -Recurse -Force $Stage
