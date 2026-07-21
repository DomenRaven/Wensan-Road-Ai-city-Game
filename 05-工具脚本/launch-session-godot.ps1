param(
  [Parameter(Mandatory = $true)][string]$ProjectPath
)
$Godot = "C:\Godot\Godot_v4.6.3-stable_win64.exe"
$Prefix = "E:\project\GameForge-K12\workspace"
$Drive = "Z:"
if ($ProjectPath.StartsWith($Prefix)) {
  $rel = $ProjectPath.Substring($Prefix.Length).TrimStart('\')
  $local = Join-Path $Drive $rel
} else {
  $local = $ProjectPath
}
if (-not (Test-Path (Join-Path $local "project.godot"))) {
  Write-Error "找不到 project.godot: $local"
  exit 1
}
Start-Process -FilePath $Godot -ArgumentList @("--path", $local)
Write-Host "已启动 Godot: $local"
