# 展厅触屏 · 关闭 TabTip 触控软键盘（仅当已显示时 Toggle，避免误开）
$ErrorActionPreference = "Stop"

if (-not ("TouchKbUtil.Ime" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace TouchKbUtil {
    public static class Native {
        [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=false)]
        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
        [DllImport("user32.dll", SetLastError=false)]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
        [StructLayout(LayoutKind.Sequential)] public struct RECT {
            public int Left; public int Top; public int Right; public int Bottom;
        }
    }

    public static class Ime {
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

        public static void HideIfVisible() {
            if (!Ime.IsTabTipVisible()) { return; }
            var host = (ITipInvocation)new UIHostNoLaunch();
            host.Toggle(GetDesktopWindow());
        }
    }
}
"@
}

[TouchKbUtil.TabTip]::HideIfVisible()
Write-Output "action=hide"
exit 0
