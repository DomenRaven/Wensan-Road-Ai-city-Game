# 兼容旧调用 · 转发至 show_touch_keyboard.ps1
& (Join-Path $PSScriptRoot "show_touch_keyboard.ps1") -Provider "auto"
exit $LASTEXITCODE
