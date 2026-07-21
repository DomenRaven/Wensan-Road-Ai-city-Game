$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root ([char]0x4ea4 + [char]0x4ed8)
$Stamp = Get-Date -Format 'yyyyMMdd'
$ZipName = "GameForge-K12-v1.2-lab-classroom-$Stamp.zip"
$ZipPath = Join-Path $OutDir $ZipName
$Stage = Join-Path $OutDir '_lab_classroom_stage'
Write-Host 'Packing lab classroom delivery...'
if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $OutDir, $Stage | Out-Null

$asciiDirs = @('backend', 'kiosk', 'templates', 'config', 'assets', 'tools')
$excludeDirNames = @(
  '.venv', '__pycache__', '.godot', 'workspace', '_dev_archive',
  'build', 'dist', 'frozen', '.pytest_cache', '.clawhub',
  'node_modules', '.git', 'reports', 'experiences', 'snippets'
)
$excludeFileNames = @(
  'e2e_7_18_live_three_tasks.py',
  'e2e_7_19_live_three_tasks.py',
  'e2e_seven_genres_sandbox.py',
  'e2e_seven_genres_godot_smoke.py',
  'sandbox_llm_inject_probe.py',
  'generate_acceptance_doc.py',
  'pack_exhibition_delivery.ps1',
  'pack_lab_classroom_delivery.ps1',
  'pack_lab_helper_zip.ps1'
)

function Copy-Filtered([string]$src, [string]$dst) {
  if (-not (Test-Path -LiteralPath $src)) { return }
  if (-not (Get-Item -LiteralPath $src).PSIsContainer) {
    $p = Split-Path $dst -Parent
    if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    return
  }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Get-ChildItem -LiteralPath $src -Force | ForEach-Object {
    if ($_.PSIsContainer -and ($excludeDirNames -contains $_.Name)) { return }
    if ($_.Name -eq '.env') { return }
    if ($excludeFileNames -contains $_.Name) { return }
    if ($_.Extension -in @('.pyc', '.spec')) { return }
    $t = Join-Path $dst $_.Name
    if ($_.PSIsContainer) { Copy-Filtered $_.FullName $t } else { Copy-Item -LiteralPath $_.FullName -Destination $t -Force }
  }
}

foreach ($n in $asciiDirs) {
  $s = Join-Path $Root $n
  if (Test-Path -LiteralPath $s) {
    Write-Host ('  + ' + $n)
    Copy-Filtered $s (Join-Path $Stage $n)
  }
}

Get-ChildItem -LiteralPath $Root -Directory -Force | ForEach-Object {
  if ($_.Name -like '05-*') {
    Write-Host ('  + ' + $_.Name)
    Copy-Filtered $_.FullName (Join-Path $Stage $_.Name)
  }
}

$docDir = Join-Path $Root ([char]0x5f00 + [char]0x53d1 + [char]0x6587 + [char]0x6863)
if (Test-Path -LiteralPath $docDir) {
  Write-Host '  + dev docs'
  Copy-Filtered $docDir (Join-Path $Stage ([char]0x5f00 + [char]0x53d1 + [char]0x6587 + [char]0x6863))
}

$LabFieldDirName = -join @(
  [char]0x673a, [char]0x623f, [char]0x90e8, [char]0x7f72,
  [char]0x73b0, [char]0x573a, [char]0x8bb0, [char]0x5f55
)
$labFieldSrc = Join-Path $Root $LabFieldDirName
if (Test-Path -LiteralPath $labFieldSrc) {
  Write-Host '  + lab field records'
  Copy-Filtered $labFieldSrc (Join-Path $Stage $LabFieldDirName)
}

Get-ChildItem -LiteralPath $Root -File -Force | Where-Object {
  $_.Name -in @('VERSION', 'CHANGELOG.md', 'README.md') -or $_.Name -like '*请先读*'
} | ForEach-Object {
  Write-Host ('  + ' + $_.Name)
  Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Stage $_.Name) -Force
}

$skillSrc = Join-Path $Root '.cursor\skills\gameforge-lab-s2-deploy'
if (Test-Path -LiteralPath $skillSrc) {
  Write-Host '  + cursor skill gameforge-lab-s2-deploy'
  Copy-Filtered $skillSrc (Join-Path $Stage '.cursor\skills\gameforge-lab-s2-deploy')
}

$dataStage = Join-Path $Stage 'data'
New-Item -ItemType Directory -Force -Path $dataStage | Out-Null
$refSrc = Join-Path $Root 'data\reference_skills'
if (Test-Path -LiteralPath $refSrc) {
  Write-Host '  + data/reference_skills'
  Copy-Filtered $refSrc (Join-Path $dataStage 'reference_skills')
}
$lsStage = Join-Path $dataStage 'learned_skills'
New-Item -ItemType Directory -Force -Path $lsStage | Out-Null
Set-Content -LiteralPath (Join-Path $lsStage '.gitkeep') -Value '' -Encoding UTF8
Set-Content -LiteralPath (Join-Path $lsStage 'index.jsonl') -Value '' -Encoding UTF8

$ws = Join-Path $Stage 'workspace'
$toolsDir = Join-Path $ws '_tools'
$godotDir = Join-Path $toolsDir 'Godot'
New-Item -ItemType Directory -Force -Path $ws, $godotDir | Out-Null
Set-Content -LiteralPath (Join-Path $ws '.gitkeep') -Value '' -Encoding UTF8
$readmeLines = @(
  'Publish before class (server Agent section 2.5-2.6):',
  '  _tools\GameForgeLabHelper.exe  (v1.0.1+)',
  '  _tools\launch-session-godot.ps1',
  '  _tools\Godot\Godot_v4.6.3-stable_win64.exe'
)
Set-Content -LiteralPath (Join-Path $toolsDir 'README_tools.txt') -Value $readmeLines -Encoding UTF8
Write-Host '  + workspace skeleton'

$toolsScriptDir = Get-ChildItem -LiteralPath $Root -Directory | Where-Object { $_.Name -like '05-*' } | Select-Object -First 1
if ($toolsScriptDir) {
  $helperDist = Join-Path $toolsScriptDir.FullName 'dist\GameForgeLabHelper.exe'
  if (Test-Path -LiteralPath $helperDist) {
    Copy-Item -LiteralPath $helperDist -Destination (Join-Path $toolsDir 'GameForgeLabHelper.exe') -Force
    Write-Host '  + workspace/_tools/GameForgeLabHelper.exe'
  }
  $labServerPath = Join-Path $toolsScriptDir.FullName 'dist\GameForgeLabServer.exe'
  if (Test-Path -LiteralPath $labServerPath) {
    Copy-Item -LiteralPath $labServerPath -Destination (Join-Path $Stage 'GameForgeLabServer.exe') -Force
    Write-Host '  + GameForgeLabServer.exe'
  }
}

$exe = Get-ChildItem -LiteralPath $Root -File -Filter '*.exe' -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'GameForge|workshop' -or $_.Length -gt 1MB } |
  Sort-Object Length -Descending |
  Select-Object -First 1
if ($exe) {
  Copy-Item -LiteralPath $exe.FullName -Destination (Join-Path $Stage $exe.Name) -Force
  Write-Host ('  + exe ' + $exe.Name)
}

$cursorNames = '7.21_' + [char]0x6559 + [char]0x5b66 + [char]0x673a + [char]0x623f + '_' +
  [char]0x5b66 + [char]0x751f + [char]0x673a + [char]0x517c + [char]0x670d + [char]0x52a1 + [char]0x5668 + '_' +
  'Cursor' + [char]0x5f00 + [char]0x5de5 + [char]0x63d0 + [char]0x793a + [char]0x8bcd + '_2026-07-21.md'
$cursorPrompt = Join-Path $docDir $cursorNames
if (Test-Path -LiteralPath $cursorPrompt) {
  Copy-Item -LiteralPath $cursorPrompt -Destination (Join-Path $Stage 'CURSOR_START_server_on_student_pc.md') -Force
  Write-Host '  + CURSOR_START_server_on_student_pc.md'
}
$freezeNames = '7.21_' + [char]0x6559 + [char]0x5b66 + [char]0x673a + [char]0x623f + 'S2' + [char]0x8def + 'B_' +
  [char]0x51bb + [char]0x7ed3 + [char]0x5feb + [char]0x7167 + '_2026-07-21.md'
$freezeDoc = Join-Path $docDir $freezeNames
if (Test-Path -LiteralPath $freezeDoc) {
  Copy-Item -LiteralPath $freezeDoc -Destination (Join-Path $Stage 'FREEZE_SNAPSHOT_2026-07-21.md') -Force
  Write-Host '  + FREEZE_SNAPSHOT_2026-07-21.md'
}
$labReadmeName = [char]0x8bf7 + [char]0x5148 + [char]0x8bfb + '_' +
  [char]0x6559 + [char]0x5b66 + [char]0x673a + [char]0x623f + [char]0x89e3 + [char]0x538b + [char]0x540e + 'Cursor' +
  [char]0x5f00 + [char]0x5de5 + '.md'
$labReadme = Join-Path $Root $labReadmeName
if (Test-Path -LiteralPath $labReadme) {
  Copy-Item -LiteralPath $labReadme -Destination (Join-Path $Stage (Split-Path -Leaf $labReadme)) -Force
  Write-Host '  + lab unzip readme'
}
$aiDoc = Join-Path $docDir '服务器部署_AI智能体自动部署手册_v1.3.md'
if (Test-Path -LiteralPath $aiDoc) {
  Copy-Item -LiteralPath $aiDoc -Destination (Join-Path $Stage 'AI_DEPLOY_manual_v1.3.md') -Force
  Write-Host '  + AI_DEPLOY_manual_v1.3.md'
}

if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($Stage, $ZipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
$sizeMb = [math]::Round((Get-Item -LiteralPath $ZipPath).Length / 1MB, 1)
Write-Host ('OK: ' + $ZipPath + ' (' + $sizeMb + ' MB)')
Remove-Item -LiteralPath $Stage -Recurse -Force
