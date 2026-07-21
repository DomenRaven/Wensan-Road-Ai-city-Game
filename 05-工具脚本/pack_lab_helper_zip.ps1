$ErrorActionPreference = 'Stop'
$DevRoot = Split-Path -Parent $PSScriptRoot
$Delivery = Join-Path $DevRoot ([char]0x4ea4 + [char]0x4ed8)
$Stage = Join-Path $Delivery '_lab_helper_stage'
$Zip = Join-Path $Delivery 'GameForge-LabHelper-20260721.zip'
$ExeSrc = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'dist') -Filter 'GameForge*.exe' | Select-Object -First 1
$LaunchPs1 = Join-Path $PSScriptRoot 'launch-session-godot.ps1'
$DocDir = Join-Path $DevRoot ([char]0x5f00 + [char]0x53d1 + [char]0x6587 + [char]0x6863)
$ExeName = 'GameForgeLabHelper.exe'

if (-not $ExeSrc) { throw 'Run build_lab_helper.ps1 first' }

Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Copy-Item -LiteralPath $ExeSrc.FullName -Destination (Join-Path $Stage $ExeName) -Force
Copy-Item -LiteralPath $LaunchPs1 -Destination $Stage -Force
if (Test-Path -LiteralPath $DocDir) {
  Get-ChildItem -LiteralPath $DocDir -Filter '7.21_*.md' -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Stage -Force
  }
}
if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $Zip -Force
Write-Output ('OK ' + $Zip)
Get-Item -LiteralPath $Zip, (Join-Path $Stage $ExeName) | Format-Table Name, Length
