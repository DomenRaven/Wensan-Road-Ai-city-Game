$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "交付"
$Stamp = Get-Date -Format "yyyyMMdd"
$ZipName = "GameForge-K12-v1.2-exhibition-$Stamp.zip"
$ZipPath = Join-Path $OutDir $ZipName
$Stage = Join-Path $OutDir "_stage_v1.2"
Write-Host "Packing..."
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Force -Path $OutDir,$Stage | Out-Null
$includeDirs = @("backend","kiosk","templates","config","assets","05-工具脚本","开发文档","tools")
$includeFiles = @("VERSION","CHANGELOG.md","README.md","文档目录说明.md","请先读_展厅部署与操作.md")
$excludeDirNames = @(".venv","__pycache__",".godot","workspace","_dev_archive","build","dist","frozen",".pytest_cache",".clawhub","node_modules")
function Copy-Filtered([string]$src,[string]$dst) {
  if (-not (Test-Path $src)) { return }
  if (-not (Get-Item $src).PSIsContainer) {
    $p = Split-Path $dst -Parent
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
    Copy-Item -Force $src $dst; return
  }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Get-ChildItem $src -Force | ForEach-Object {
    if ($_.PSIsContainer -and ($excludeDirNames -contains $_.Name)) { return }
    if ($_.Name -eq ".env") { return }
    if ($_.Extension -in @(".pyc",".spec")) { return }
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
  if (Test-Path $s) { Write-Host "  + $n"; Copy-Item -Force $s (Join-Path $Stage $n) } else { Write-Host "  skip $n" }
}
# Discover launcher exe (Chinese filename)
$exe = Get-ChildItem -Path $Root -File -Filter "*.exe" | Where-Object { $_.Name -match "启动|工坊|GameForge|workshop" -or $_.Length -gt 1MB } | Sort-Object Length -Descending | Select-Object -First 1
if ($exe) {
  $destExe = Join-Path $Stage "启动游戏工坊.exe"
  Copy-Item -Force $exe.FullName $destExe
  Write-Host "  + EXE from $($exe.Name) -> 启动游戏工坊.exe"
} else { Write-Host "WARNING: no launcher exe" }
$ws = Join-Path $Stage "workspace"; New-Item -ItemType Directory -Force -Path $ws | Out-Null; Set-Content (Join-Path $ws ".gitkeep") ""
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($Stage, $ZipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
Write-Host ("OK: {0} ({1} MB)" -f $ZipPath, [math]::Round((Get-Item $ZipPath).Length/1MB,1))
Remove-Item -Recurse -Force $Stage