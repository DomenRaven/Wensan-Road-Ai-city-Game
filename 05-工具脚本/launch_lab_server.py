"""GameForge K12 · 教学机房服务器一键启动（Redis 可选 · API + Kiosk · 0.0.0.0）。"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

LAUNCHER_VERSION: str = "1.0"
CREATE_NO_WINDOW: int = 0x08000000
API_PORT: int = 8000
KIOSK_PORT: int = 8080


def launcher_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "backend").is_dir() and (candidate / "kiosk").is_dir():
            return candidate
    raise RuntimeError(
        "未找到项目根目录（需含 backend/ 与 kiosk/）。"
        "请将 GameForgeLabServer.exe 放在 E:\\project\\GameForge-K12\\ 根目录。"
    )


def guess_lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def probe_url(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_url(url: str, timeout_sec: float = 90.0, interval_sec: float = 0.5) -> bool:
    deadline: float = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if probe_url(url):
            return True
        time.sleep(interval_sec)
    return False


def run_hidden(args: list[str], cwd: Path | None = None) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_backend_venv(backend_dir: Path) -> Path:
    venv_python: Path = backend_dir / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python

    print("[venv] 创建 backend/.venv 并安装依赖…")
    subprocess.run([sys.executable, "-m", "venv", str(backend_dir / ".venv")], check=True)
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=str(backend_dir),
        check=True,
    )
    return venv_python


def try_start_redis(repo_root: Path) -> None:
    redis_server: Path = repo_root / "tools" / "redis" / "server" / "redis-server.exe"
    redis_conf: Path = repo_root / "tools" / "redis" / "redis.conf"
    if not redis_server.is_file():
        print("[Redis] 未安装便携 Redis，跳过（会话可能 memory 降级）")
        return

    probe = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq redis-server.exe"],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    if "redis-server.exe" in probe.stdout:
        print("[Redis] 已在运行")
        return

    print("[Redis] 启动中…")
    run_hidden([str(redis_server), str(redis_conf)], cwd=repo_root / "tools" / "redis")
    time.sleep(1.0)


def fetch_health() -> dict[str, object]:
    with urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/health", timeout=5.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GameForge 教学机房服务器一键启动")
    parser.add_argument(
        "--server-ip",
        default="",
        help="展示用 LAN IP（默认自动探测，如 10.71.121.18）",
    )
    parser.add_argument("--no-redis", action="store_true", help="不尝试启动 Redis")
    parser.add_argument("--open-browser", action="store_true", help="启动后在服务器本机打开 Kiosk")
    return parser.parse_args()


def main() -> int:
    args: argparse.Namespace = parse_args()
    repo_root: Path = find_repo_root(launcher_dir())
    backend_dir: Path = repo_root / "backend"
    lan_ip: str = args.server_ip.strip() or guess_lan_ip()
    api_health: str = f"http://127.0.0.1:{API_PORT}/health"
    kiosk_probe: str = f"http://127.0.0.1:{KIOSK_PORT}/kiosk/edu/"
    kiosk_lan: str = f"http://{lan_ip}:{KIOSK_PORT}/kiosk/edu/"
    children: list[subprocess.Popen[bytes]] = []

    print("=" * 60)
    print(f"  GameForge 教学机房服务器 · 一键启动 v{LAUNCHER_VERSION}")
    print(f"  项目目录: {repo_root}")
    print(f"  绑定: 0.0.0.0:{API_PORT} · 0.0.0.0:{KIOSK_PORT}")
    print(f"  学生入口: {kiosk_lan}")
    print("=" * 60)

    try:
        if not args.no_redis:
            try_start_redis(repo_root)

        venv_python: Path = ensure_backend_venv(backend_dir)
        uvicorn: Path = backend_dir / ".venv" / "Scripts" / "uvicorn.exe"

        if probe_url(api_health):
            print(f"[API] :{API_PORT} 已在运行，跳过启动")
        else:
            print(f"[API] 启动 uvicorn → 0.0.0.0:{API_PORT}")
            children.append(
                run_hidden(
                    [
                        str(uvicorn),
                        "app.main:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        str(API_PORT),
                    ],
                    cwd=backend_dir,
                )
            )

        if probe_url(f"http://127.0.0.1:{KIOSK_PORT}/kiosk/"):
            print(f"[Kiosk] :{KIOSK_PORT} 已在运行，跳过启动")
        else:
            print(f"[Kiosk] 启动静态服务 → 0.0.0.0:{KIOSK_PORT}")
            children.append(
                run_hidden(
                    [
                        str(venv_python),
                        "-m",
                        "http.server",
                        str(KIOSK_PORT),
                        "--bind",
                        "0.0.0.0",
                    ],
                    cwd=repo_root,
                )
            )

        print("[等待] 服务就绪…")
        if not wait_url(api_health):
            print("错误：API 未在 90 秒内响应。请检查 backend/.env 与依赖。")
            return 1
        if not wait_url(kiosk_probe, timeout_sec=30.0):
            print("错误：Kiosk 未在 30 秒内响应。")
            return 1

        health = fetch_health()
        print()
        print("  服务已就绪：")
        print(f"    health      → http://127.0.0.1:{API_PORT}/health")
        print(f"    play_launch → {health.get('play_launch_mode', '?')}")
        print(f"    store_ok    → {health.get('store_ok', '?')}")
        print(f"    学生 Kiosk  → {kiosk_lan}")
        print()
        print("  勿用「启动游戏工坊.exe」（默认 127.0.0.1，学生机无法访问）。")
        print("  关闭本窗口或按 Enter 将停止由本启动器拉起的 API/Kiosk 进程。")
        print()

        if args.open_browser:
            webbrowser.open(kiosk_lan)

        input("按 Enter 停止服务并退出…")
        return 0
    except KeyboardInterrupt:
        print("\n收到中断，正在停止…")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"错误：子进程失败（exit {exc.returncode}）")
        return exc.returncode or 1
    except RuntimeError as exc:
        print(f"错误：{exc}")
        return 1
    finally:
        for proc in reversed(children):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
