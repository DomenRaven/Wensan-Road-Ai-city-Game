from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.services.godot_window_layout import WindowRect, place_by_pid
from app.services.workspace_guard import (
    WorkspaceGuardError,
    validate_session_id,
    workspace_root_for_session,
)


@dataclass
class LaunchResult:
    ok: bool
    pid: int | None
    project_path: str
    genre: str
    godot_path: str
    message: str
    already_running: bool = False
    window_placed: bool = False
    placement_rect: WindowRect | None = None


class GodotLauncher:
    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        self._running: dict[str, int] = {}
        self._running_project: dict[str, str] = {}

    def resolve_godot_path(self) -> Path:
        env_path: str = os.environ.get("GODOT_PATH", self._settings.godot_path).strip()
        if not env_path:
            raise FileNotFoundError("GODOT_PATH 未配置")
        path: Path = Path(env_path)
        if path.is_dir():
            gui: Path = path / "Godot_v4.6.3-stable_win64.exe"
            if gui.is_file():
                return gui
            children: list[Path] = list(path.glob("Godot*.exe"))
            if children:
                return children[0]
        if not path.is_file():
            raise FileNotFoundError(f"Godot 不存在: {path}")
        if path.name.endswith("_console.exe"):
            gui_candidate: Path = path.with_name(path.name.replace("_console.exe", ".exe"))
            if gui_candidate.is_file():
                return gui_candidate
        return path

    def resolve_project_path(self, genre: str, session_id: str) -> Path:
        sid: str = validate_session_id(session_id)
        workspace: Path = workspace_root_for_session(self._settings.workspace_dir, sid)
        if (workspace / "project.godot").is_file():
            return workspace
        template: Path = self._settings.templates_dir / genre
        if not (template / "project.godot").is_file():
            raise FileNotFoundError(f"模板不存在: templates/{genre}/")
        return template.resolve()

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        if pid <= 0:
            return False
        if sys.platform == "win32":
            try:
                import ctypes

                PROCESS_QUERY_LIMITED_INFORMATION: int = 0x1000
                STILL_ACTIVE: int = 259
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, pid
                )
                if not handle:
                    return False
                exit_code = ctypes.c_uint32(0)
                ok: bool = bool(
                    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                )
                ctypes.windll.kernel32.CloseHandle(handle)
                if not ok:
                    return False
                return int(exit_code.value) == STILL_ACTIVE
            except Exception:
                return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def _clear_session_tracking(self, session_id: str) -> None:
        self._running.pop(session_id, None)
        self._running_project.pop(session_id, None)

    def _prune_stale(self, session_id: str) -> None:
        pid: int | None = self._running.get(session_id)
        if pid is None:
            return
        if not self._is_process_running(pid):
            self._clear_session_tracking(session_id)

    def clear_session(self, session_id: str) -> None:
        """Drop cached PID when session is reset/deleted."""
        self._clear_session_tracking(session_id)

    def _try_place_window(
        self,
        pid: int | None,
        layout_rect: WindowRect | None,
        *,
        wait_s: float = 0.0,
        timeout_s: float = 6.0,
    ) -> tuple[bool, WindowRect | None]:
        if pid is None or layout_rect is None:
            return False, None
        if wait_s > 0:
            time.sleep(wait_s)
        placed: bool = place_by_pid(pid, layout_rect, timeout_s=timeout_s, interval_s=0.25)
        return placed, layout_rect if placed else None

    def launch(
        self,
        session_id: str,
        genre: str,
        *,
        force: bool = False,
        layout_rect: WindowRect | None = None,
    ) -> LaunchResult:
        if not genre:
            raise ValueError("Session 尚未选择品类 (S1)")
        try:
            validate_session_id(session_id)
        except WorkspaceGuardError as exc:
            raise ValueError(str(exc)) from exc
        self._prune_stale(session_id)

        godot: Path = self.resolve_godot_path()
        project: Path = self.resolve_project_path(genre, session_id)
        project_key: str = str(project)

        old_pid: int | None = self._running.get(session_id)
        old_project: str | None = self._running_project.get(session_id)
        if (
            not force
            and old_pid is not None
            and self._is_process_running(old_pid)
            and old_project == project_key
        ):
            window_placed, placement_rect = self._try_place_window(
                old_pid,
                layout_rect,
                timeout_s=4.0,
            )
            return LaunchResult(
                ok=True,
                pid=old_pid,
                project_path=project_key,
                genre=genre,
                godot_path=str(godot),
                message="试玩窗口已在运行",
                already_running=True,
                window_placed=window_placed,
                placement_rect=placement_rect,
            )

        if old_pid is not None and self._is_process_running(old_pid) and old_project != project_key:
            self._clear_session_tracking(session_id)

        cmd: list[str] = [str(godot), "--path", str(project)]
        kwargs: dict[str, object] = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc: subprocess.Popen[bytes] = subprocess.Popen(cmd, **kwargs)  # noqa: S603
        time.sleep(0.35)
        if not self._is_process_running(proc.pid):
            raise RuntimeError(
                f"Godot 启动后立即退出，请检查 GODOT_PATH 或 templates/{genre}/ 项目完整性"
            )

        self._running[session_id] = proc.pid
        self._running_project[session_id] = project_key
        window_placed, placement_rect = self._try_place_window(
            proc.pid,
            layout_rect,
            wait_s=0.35,
            timeout_s=6.0,
        )
        message: str = "已重新启动 Godot 试玩窗口" if force or old_pid is not None else "已启动 Godot 试玩窗口"
        return LaunchResult(
            ok=True,
            pid=proc.pid,
            project_path=project_key,
            genre=genre,
            godot_path=str(godot),
            message=message,
            already_running=False,
            window_placed=window_placed,
            placement_rect=placement_rect,
        )

    def status(self, session_id: str) -> dict[str, object]:
        self._prune_stale(session_id)
        pid: int | None = self._running.get(session_id)
        running: bool = pid is not None and self._is_process_running(pid)
        if pid is not None and not running:
            self._clear_session_tracking(session_id)
            pid = None
        return {
            "session_id": session_id,
            "pid": pid,
            "running": running,
            "project_path": self._running_project.get(session_id),
        }


_launcher: GodotLauncher | None = None


def get_launcher(settings: Settings) -> GodotLauncher:
    global _launcher
    if _launcher is None:
        _launcher = GodotLauncher(settings)
    return _launcher
