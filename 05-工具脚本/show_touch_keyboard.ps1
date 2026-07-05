# 展厅触屏 · 唤起中文输入 · 优先搜狗 IME + TabTip（搜狗软键盘无独立 exe）
param(
    [ValidateSet("auto", "tabtip", "sogou_hand")]
    [string]$Provider = "auto"
)

$ErrorActionPreference = "Stop"

function Find-SogouRoot {
    $hits = @(
        "C:\Program Files (x86)\SogouInput",
        "C:\Program Files\SogouInput"
    )
    foreach ($drive in (Get-PSDrive -PSProvider FileSystem).Name) {
        $root = Join-Path "${drive}:\" "SogouInput"
        if (Test-Path -LiteralPath $root) { $hits += $root }
        Get-ChildItem -LiteralPath "${drive}:\" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $nested = Join-Path $_.FullName "SogouInput"
            if (Test-Path -LiteralPath $nested) { $hits += $nested }
        }
    }
    foreach ($path in ($hits | Select-Object -Unique)) {
        if (Test-Path -LiteralPath (Join-Path $path "SogouExe\SogouExe.exe")) { return $path }
        if (Get-ChildItem -LiteralPath $path -Filter "SGTool.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1) {
            return $path
        }
    }
    return $null
}

function Ensure-SogouImeService {
    param([string]$Root)
    if (-not $Root) { return $false }
    $exe = Join-Path $Root "SogouExe\SogouExe.exe"
    if (-not (Test-Path -LiteralPath $exe)) { return $false }
    if (-not (Get-Process -Name "SogouExe" -ErrorAction SilentlyContinue)) {
        Start-Process -FilePath $exe -ErrorAction SilentlyContinue | Out-Null
        Start-Sleep -Milliseconds 250
    }
    return $true
}

function Show-SogouHandInput {
    param([string]$Root)
    if (-not $Root) { return $false }
    $hand = Get-ChildItem -LiteralPath (Join-Path $Root "Components\HandInput") -Filter "handinput.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $hand) { return $false }
    Start-Process -FilePath $hand.FullName
    return $true
}

if (-not ("TouchKbUtil.Ime" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

namespace TouchKbUtil {
    public static class Native {
        [DllImport("user32.dll", SetLastError=false)] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=false)]
        public static extern IntPtr LoadKeyboardLayout(string pwszKLID, uint Flags);
        [DllImport("user32.dll", SetLastError=false)]
        public static extern IntPtr ActivateKeyboardLayout(IntPtr hkl, uint Flags);
        [DllImport("user32.dll", SetLastError=false)]
        public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
        [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=false)]
        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
        [DllImport("user32.dll", SetLastError=false)]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
        [StructLayout(LayoutKind.Sequential)] public struct RECT {
            public int Left; public int Top; public int Right; public int Bottom;
        }
    }

    public static class Ime {
        public const uint WM_INPUTLANGCHANGEREQUEST = 0x0050;
        public const uint INPUTLANGCHANGE_FORWARD = 2;
        public const uint KLF_ACTIVATE = 1;

        public static bool SwitchForegroundToChinese() {
            IntPtr hwnd = Native.GetForegroundWindow();
            IntPtr hkl = Native.LoadKeyboardLayout("00000804", KLF_ACTIVATE);
            if (hkl == IntPtr.Zero) { return false; }
            Native.ActivateKeyboardLayout(hkl, 0);
            return Native.PostMessage(hwnd, WM_INPUTLANGCHANGEREQUEST,
                (IntPtr)INPUTLANGCHANGE_FORWARD, hkl);
        }

        public static bool IsTabTipVisible() {
            IntPtr hwnd = Native.FindWindow("IPTip_Main_Window", null);
            if (hwnd == IntPtr.Zero) { return false; }
            Native.RECT rect;
            Native.GetWindowRect(hwnd, out rect);
            return (rect.Bottom - rect.Top) > 80;
        }
    }

    [ComImport, Guid("4ce576fa-83dc-4F88-951c-9d0782b4e376")]
    public class UIHostNoLaunch { }

    [ComImport, Guid("37c994e7-432b-4834-a2f7-dce1f13b834b")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface ITipInvocation {
        void Toggle(IntPtr desktopWindow);
    }

    public static class TabTip {
        [DllImport("user32.dll", SetLastError=false)]
        public static extern IntPtr GetDesktopWindow();

        public static void ShowIfHidden() {
            if (Ime.IsTabTipVisible()) { return; }
            var host = (ITipInvocation)new UIHostNoLaunch();
            host.Toggle(GetDesktopWindow());
        }
    }
}
"@
}

$sogouRoot = Find-SogouRoot
$imeOk = [TouchKbUtil.Ime]::SwitchForegroundToChinese()
if ($sogouRoot) {
    Ensure-SogouImeService -Root $sogouRoot | Out-Null
    Start-Sleep -Milliseconds 120
}

if ($Provider -eq "sogou_hand") {
    if (Show-SogouHandInput -Root $sogouRoot) {
        Write-Output "provider=sogou_hand"
        exit 0
    }
}

$tabTip = Join-Path $env:CommonProgramFiles "Microsoft Shared\Ink\TabTip.exe"
if (-not (Test-Path -LiteralPath $tabTip)) {
    Write-Error "TabTip.exe not found"
    exit 1
}

if (-not (Get-Process -Name "TabTip" -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $tabTip
    Start-Sleep -Milliseconds 450
}

[TouchKbUtil.Ime]::SwitchForegroundToChinese() | Out-Null
[TouchKbUtil.TabTip]::ShowIfHidden()

Write-Output ("provider=tabtip;ime=" + $(if ($imeOk) { "zh-CN" } else { "fallback" }) + ";sogou=" + $(if ($sogouRoot) { "yes" } else { "no" }))
exit 0
