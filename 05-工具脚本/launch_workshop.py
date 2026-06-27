"""GameForge K12 · 展厅一键启动器（Redis + API + Kiosk + 浏览器）。"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

CREATE_NO_WINDOW: int = 0x08000000
API_HEALTH_URL: str = "http://127.0.0.1:8000/health"
KIOSK_PROBE_URL: str = "http://127.0.0.1:8080/kiosk/"
EDU_URL: str = "http://127.0.0.1:8080/kiosk/edu/"
FAST_URL: str = "http://127.0.0.1:8080/kiosk/"


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
        "请将启动器放在仓库内，或从仓库根目录运行。"
    )


def wait_url(url: str, timeout_sec: float = 90.0, interval_sec: float = 0.5) -> bool:
    deadline: float = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if 200 <= response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
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

    print("[1/4] 创建后端虚拟环境并安装依赖…")
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
        print("[Redis] 未安装便携 Redis，跳过（会话将使用内存降级）")
        print("        可选：运行 .\\05-工具脚本\\install_redis.ps1")
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
    run_hidden(
        [str(redis_server), str(redis_conf)],
        cwd=repo_root / "tools" / "redis",
    )
    time.sleep(1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GameForge K12 展厅一键启动")
    parser.add_argument(
        "--mode",
        choices=("edu", "fast"),
        default="edu",
        help="edu=教育创作链 / fast=A 链快玩（默认 edu）",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器",
    )
    return parser.parse_args()


def main() -> int:
    args: argparse.Namespace = parse_args()
    repo_root: Path = find_repo_root(launcher_dir())
    backend_dir: Path = repo_root / "backend"
    kiosk_url: str = EDU_URL if args.mode == "edu" else FAST_URL
    children: list[subprocess.Popen[bytes]] = []

    print("=" * 56)
    print("  文三路 AI 游戏创作工坊 · 一键启动")
    print(f"  项目目录: {repo_root}")
    print("=" * 56)

    try:
        try_start_redis(repo_root)

        venv_python: Path = ensure_backend_venv(backend_dir)
        uvicorn: Path = backend_dir / ".venv" / "Scripts" / "uvicorn.exe"

        print("[2/4] 启动后端 API :8000 …")
        backend_proc: subprocess.Popen[bytes] = run_hidden(
            [str(uvicorn), "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=backend_dir,
        )
        children.append(backend_proc)

        print("[3/4] 启动 Kiosk 静态服务 :8080 …")
        http_proc: subprocess.Popen[bytes] = run_hidden(
            [str(venv_python), "-m", "http.server", "8080"],
            cwd=repo_root,
        )
        children.append(http_proc)

        print("[4/4] 等待服务就绪…")
        if not wait_url(API_HEALTH_URL):
            print("错误：后端 API 未在 90 秒内响应，请检查 backend/.env 与依赖。")
            return 1
        if not wait_url(KIOSK_PROBE_URL):
            print("错误：Kiosk 静态服务未在 90 秒内响应。")
            return 1

        print()
        print("  服务已就绪：")
        print(f"    API   → http://127.0.0.1:8000/docs")
        print(f"    Kiosk → {kiosk_url}")
        print()
        print("  提示：请确认 backend/.env 中 GODOT_PATH 已配置（试玩必需）。")
        print("  关闭本窗口或按 Enter 将停止全部后台服务。")
        print()

        if not args.no_browser:
            webbrowser.open(kiosk_url)

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
