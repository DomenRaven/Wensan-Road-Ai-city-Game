# 推送 gameforge-k12 → GitHub main + 标签 v1.0
# 用法：在可访问 GitHub 的网络下（必要时开 VPN）：
#   .\05-工具脚本\push_github.ps1
# 鉴权：HTTPS 用 Personal Access Token；或先配置 SSH 密钥后改下方 $UseSsh = $true

param(
    [switch]$Force,
    [switch]$UseSsh
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$HttpsUrl = "https://github.com/DomenRaven/Wensan-Road-Ai-city-Game.git"
$SshUrl = "git@github.com:DomenRaven/Wensan-Road-Ai-city-Game.git"

if (-not (git remote get-url github 2>$null)) {
    git remote add github $HttpsUrl
}

if ($UseSsh) {
    git remote set-url github $SshUrl
    $env:GIT_SSH_COMMAND = "ssh -o StrictHostKeyChecking=accept-new"
} else {
    git remote set-url github $HttpsUrl
}

Write-Host "==> 仓库: $RepoRoot"
Write-Host "==> 远程: github -> $(git remote get-url github)"
Write-Host "==> 本地提交: $(git log -1 --oneline)"
Write-Host ""

# 连通性粗检 · 443 不可达时尝试本机代理（Clash 等常见 7897/7890）
$GitProxyArgs = @()
foreach ($proxyPort in 7897, 7890, 10809) {
    try {
        $local = Test-NetConnection 127.0.0.1 -Port $proxyPort -WarningAction SilentlyContinue
        if ($local.TcpTestSucceeded) {
            $proxyUrl = "http://127.0.0.1:$proxyPort"
            $GitProxyArgs = @("-c", "http.proxy=$proxyUrl", "-c", "https.proxy=$proxyUrl")
            Write-Host "==> 使用本机代理: $proxyUrl"
            break
        }
    } catch { }
}
try {
    $tcp = Test-NetConnection github.com -Port 443 -WarningAction SilentlyContinue
    if (-not $tcp.TcpTestSucceeded -and -not $UseSsh -and $GitProxyArgs.Count -eq 0) {
        Write-Warning "github.com:443 不可达且无本机代理。请开 VPN/系统代理，或: .\05-工具脚本\push_github.ps1 -UseSsh"
    }
} catch { }

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    if ($GitProxyArgs.Count -gt 0) {
        & git @GitProxyArgs @Args
    } else {
        & git @Args
    }
}

Write-Host "==> git fetch github ..."
Invoke-Git fetch github

$pushArgs = @("push", "-u", "github", "gameforge-k12:main")
if ($Force) { $pushArgs += "--force" }

Write-Host "==> git $($pushArgs -join ' ') ..."
Invoke-Git @pushArgs
if ($LASTEXITCODE -ne 0) {
    Write-Warning "普通推送失败（远程可能有 GitHub 初始化 README）。使用 -Force 覆盖 stub 提交..."
    Invoke-Git push -u github gameforge-k12:main --force
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "==> git push github v1.0 ..."
Invoke-Git push github v1.0
if ($LASTEXITCODE -ne 0) {
    Write-Warning "标签推送失败，尝试强制推送标签..."
    git push github v1.0 --force
}

Write-Host ""
Write-Host "完成。查看: https://github.com/DomenRaven/Wensan-Road-Ai-city-Game"
Write-Host "回退锚点: git checkout v1.0  或  git reset --hard v1.0"
