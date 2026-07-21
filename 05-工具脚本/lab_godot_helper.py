"""GameForge K12 · 教学机房本机助手（S2-路B）。

- ``deploy``：学生机一键部署（Z: 映射 · Godot · 配置文件）
- ``serve``（默认）：本机 HTTP 服务，供浏览器触发 Godot 启动并监测关窗

浏览器通过 ``POST /launch`` 传入服务器 ``project_path``；助手映射到 Z: 并启动 Godot。
关窗后浏览器轮询 ``GET /status``，结合 ``run_complete`` 触发今日榜单。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HELPER_VERSION: str = "1.0"
DEFAULT_PORT: int = 17890
DEFAULT_CONFIG_PATH: Path = Path(r"C:\GameForge\lab_helper.json")
CREATE_NO_WINDOW: int = 0x08000000


@dataclass
class HelperConfig:
    godot_path: Path
    workspace_prefix: str
    local_drive: str
    server_ip: str
    share_name: str
    port: int
    net_user: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> HelperConfig:
        return cls(
            godot_path=Path(str(raw.get("godot_path") or r"C:\Godot\Godot_v4.6.3-stable_win64.exe")),
            workspace_prefix=str(
                raw.get("workspace_prefix") or r"E:\project\GameForge-K12\workspace"
            ).rstrip("\\"),
            local_drive=str(raw.get("local_drive") or "Z:").rstrip("\\"),
            server_ip=str(raw.get("server_ip") or "10.71.121.18"),
            share_name=str(raw.get("share_name") or "GameForgeWorkspace"),
            port=int(raw.get("port") or DEFAULT_PORT),
            net_user=str(raw.get("net_user") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "godot_path": str(self.godot_path),
            "workspace_prefix": self.workspace_prefix,
            "local_drive": self.local_drive,
            "server_ip": self.server_ip,
            "share_name": self.share_name,
            "port": self.port,
            "net_user": self.net_user,
            "helper_version": HELPER_VERSION,
        }

    @property
    def share_unc(self) -> str:
        return rf"\\{self.server_ip}\{self.share_name}"

    @property
    def godot_share_path(self) -> Path:
        return Path(f"{self.local_drive}\\_tools\\Godot\\Godot_v4.6.3-stable_win64.exe")


@dataclass
class LaunchState:
    running: bool = False
    pid: int | None = None
    project_path: str = ""
    local_path: str = ""
    started_at: float = 0.0
    proc: subprocess.Popen[Any] | None = None


_state = LaunchState()
_state_lock = threading.Lock()
_config: HelperConfig | None = None


def load_config(path: Path) -> HelperConfig:
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return HelperConfig.from_dict(raw)
    return HelperConfig.from_dict({})


def save_config(path: Path, cfg: HelperConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def map_project_path(cfg: HelperConfig, project_path: str) -> Path:
    normalized = project_path.strip()
    prefix = cfg.workspace_prefix
    if normalized.lower().startswith(prefix.lower()):
        rel = normalized[len(prefix) :].lstrip("\\/")
        return Path(cfg.local_drive) / rel.replace("/", "\\")
    return Path(normalized)


def run_hidden(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )


def deploy_student(cfg: HelperConfig, config_path: Path, skip_net_use: bool) -> int:
    print("=" * 56)
    print(f"  GameForge 机房助手 · 学生机部署 v{HELPER_VERSION}")
    print("=" * 56)

    gameforge_dir = Path(r"C:\GameForge")
    gameforge_dir.mkdir(parents=True, exist_ok=True)
    cfg.godot_path.parent.mkdir(parents=True, exist_ok=True)

    if not skip_net_use:
        print(f"[1/4] 映射 {cfg.local_drive} → {cfg.share_unc}")
        run_hidden(["net", "use", f"{cfg.local_drive}", "/delete", "/y"])
        net_args = ["net", "use", cfg.local_drive, cfg.share_unc, "/persistent:yes"]
        if cfg.net_user.strip():
            net_args.extend(["/user:" + cfg.net_user.strip()])
        result = run_hidden(net_args)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            print("错误：映射 Z: 失败。请检查账号密码与服务器 SMB。")
            return 1
    else:
        print("[1/4] 跳过 net use（--skip-net-use）")

    if not Path(cfg.local_drive + "\\").exists():
        print(f"错误：{cfg.local_drive} 不可用")
        return 1
    print(f"  OK · {cfg.local_drive} 可用")

    print("[2/4] 安装 Godot 4.6.3")
    if not cfg.godot_path.is_file():
        if not cfg.godot_share_path.is_file():
            print(f"错误：共享盘无 Godot · 请先在服务器执行 §2.5")
            print(f"  期望: {cfg.godot_share_path}")
            return 1
        cfg.godot_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.godot_path.write_bytes(cfg.godot_share_path.read_bytes())
        print(f"  已从 Z: 复制 → {cfg.godot_path}")
    else:
        print(f"  已存在 · {cfg.godot_path}")

    version = run_hidden([str(cfg.godot_path), "--version"])
    if version.returncode != 0:
        print(version.stderr or version.stdout)
        print("错误：Godot --version 失败")
        return 1
    print(f"  {version.stdout.strip()}")

    print("[3/4] 写入配置")
    save_config(config_path, cfg)
    print(f"  OK · {config_path}")

    print("[4/4] 部署完成")
    print("")
    print("  下一步：双击「GameForgeLabHelper.exe」保持运行（或开机自启）")
    print("  浏览器试玩时将自动打开 Godot；关窗后自动弹今日榜单")
    print("")
    return 0


def _watch_process(proc: subprocess.Popen[Any]) -> None:
    proc.wait()
    with _state_lock:
        if _state.proc is proc:
            _state.running = False
            _state.pid = None
            _state.proc = None


def launch_godot(cfg: HelperConfig, project_path: str, force: bool) -> dict[str, Any]:
    local = map_project_path(cfg, project_path)
    project_godot = local / "project.godot"
    if not project_godot.is_file():
        return {
            "ok": False,
            "message": f"找不到 project.godot: {local}",
            "local_path": str(local),
        }

    with _state_lock:
        if _state.running and _state.proc is not None and _state.proc.poll() is None:
            if not force and _state.local_path.lower() == str(local).lower():
                return {
                    "ok": True,
                    "already_running": True,
                    "pid": _state.pid,
                    "local_path": str(local),
                    "project_path": project_path,
                }
            try:
                _state.proc.terminate()
                _state.proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    _state.proc.kill()
                except OSError:
                    pass
            _state.running = False
            _state.proc = None
            _state.pid = None

        if not cfg.godot_path.is_file():
            return {"ok": False, "message": f"Godot 不存在: {cfg.godot_path}"}

        proc = subprocess.Popen(
            [str(cfg.godot_path), "--path", str(local)],
            creationflags=CREATE_NO_WINDOW,
        )
        _state.running = True
        _state.pid = proc.pid
        _state.project_path = project_path
        _state.local_path = str(local)
        _state.started_at = time.time()
        _state.proc = proc
        threading.Thread(target=_watch_process, args=(proc,), daemon=True).start()

    return {
        "ok": True,
        "pid": proc.pid,
        "local_path": str(local),
        "project_path": project_path,
        "message": "Godot 已启动",
    }


def get_status() -> dict[str, Any]:
    with _state_lock:
        running = bool(_state.running and _state.proc is not None and _state.proc.poll() is None)
        if _state.proc is not None and _state.proc.poll() is not None:
            _state.running = False
            _state.pid = None
            _state.proc = None
            running = False
        return {
            "ok": True,
            "running": running,
            "pid": _state.pid,
            "project_path": _state.project_path,
            "local_path": _state.local_path,
            "started_at": _state.started_at,
            "helper_version": HELPER_VERSION,
        }


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    parsed = json.loads(raw.decode("utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _send_json(handler: BaseHTTPRequestHandler, code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class LabHelperHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/health":
            _send_json(
                self,
                200,
                {"ok": True, "service": "gameforge-lab-helper", "version": HELPER_VERSION},
            )
            return
        if path == "/status":
            _send_json(self, 200, get_status())
            return
        _send_json(self, 404, {"ok": False, "message": "not found"})

    def do_POST(self) -> None:
        if _config is None:
            _send_json(self, 500, {"ok": False, "message": "config not loaded"})
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path != "/launch":
            _send_json(self, 404, {"ok": False, "message": "not found"})
            return
        body = _read_json_body(self)
        project_path = str(body.get("project_path") or "").strip()
        force = bool(body.get("force"))
        if not project_path:
            _send_json(self, 400, {"ok": False, "message": "project_path required"})
            return
        result = launch_godot(_config, project_path, force)
        code = 200 if result.get("ok") else 400
        _send_json(self, code, result)


def serve(cfg: HelperConfig) -> int:
    global _config
    _config = cfg
    server = ThreadingHTTPServer(("127.0.0.1", cfg.port), LabHelperHandler)
    print("=" * 56)
    print(f"  GameForge 机房助手 v{HELPER_VERSION} · 本机服务")
    print(f"  http://127.0.0.1:{cfg.port}/health")
    print(f"  Godot: {cfg.godot_path}")
    print(f"  映射: {cfg.workspace_prefix} → {cfg.local_drive}\\")
    print("  保持本窗口运行；浏览器试玩时自动开 Godot")
    print("  按 Ctrl+C 退出")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        with _state_lock:
            if _state.proc is not None and _state.proc.poll() is None:
                _state.proc.terminate()
        return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GameForge 教学机房本机助手")
    sub = parser.add_subparsers(dest="command")
    sub.required = False

    deploy = sub.add_parser("deploy", help="学生机一键部署")
    deploy.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    deploy.add_argument("--server-ip", default="10.71.121.18")
    deploy.add_argument("--share-name", default="GameForgeWorkspace")
    deploy.add_argument("--local-drive", default="Z:")
    deploy.add_argument(
        "--workspace-prefix",
        default=r"E:\project\GameForge-K12\workspace",
    )
    deploy.add_argument("--godot-path", default=r"C:\Godot\Godot_v4.6.3-stable_win64.exe")
    deploy.add_argument("--net-user", default="", help=r"例: 10.71.121.18\TEST1")
    deploy.add_argument("--skip-net-use", action="store_true")

    serve_parser = sub.add_parser("serve", help="启动本机 HTTP 助手（默认）")
    serve_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    serve_parser.add_argument("--port", type=int, default=0)

    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    command = args.command or "serve"

    if command == "deploy":
        cfg = HelperConfig.from_dict(
            {
                "godot_path": args.godot_path,
                "workspace_prefix": args.workspace_prefix,
                "local_drive": args.local_drive,
                "server_ip": args.server_ip,
                "share_name": args.share_name,
                "net_user": args.net_user,
            }
        )
        return deploy_student(cfg, args.config, skip_net_use=bool(args.skip_net_use))

    config_path: Path = getattr(args, "config", DEFAULT_CONFIG_PATH)
    cfg = load_config(config_path)
    if getattr(args, "port", 0):
        cfg.port = int(args.port)
    return serve(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
