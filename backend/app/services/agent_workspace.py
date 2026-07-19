"""会话工作区智能体写权限：可改「本局副本」，严禁碰 templates。

与旧 ai_sandbox 红线的关系：
- 默认/降级路径仍只写 core/ai_sandbox/**
- 智能体路径可改会话内 core/**、config/game_config.json、scenes/**
- 回主页 / release 仍整棵销毁 workspace

HF-12：分页 read / search_in_file / replace_text / 原子写 / 结构化 observation。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.services.workspace_guard import (
    assert_not_under_templates,
    assert_under_workspace,
)

# 危险 GDScript 片段（K12 / 展厅安全）
FORBIDDEN_GD_SNIPPETS: tuple[str, ...] = (
    "OS.execute",
    "OS.create_process",
    "OS.shell_open",
    "JavaScriptBridge",
    "ClassDB.instance",
    "DirAccess.remove",
    "IP.resolve_hostname",
    "HTTPRequest",
    "PacketPeer",
    "TCPServer",
    "UDPServer",
    "WebSocket",
)

_ALLOWED_SUFFIXES: frozenset[str] = frozenset(
    {".gd", ".tscn", ".json", ".svg", ".png", ".md", ".txt", ".tres", ".import"}
)

# 禁止智能体改动的相对路径前缀/文件（会话内）
_BLOCKED_EXACT: frozenset[str] = frozenset(
    {
        "project.godot",  # autoload 由 edu 注入，避免打坏启动
        ".env",
        "export_presets.cfg",
    }
)
_BLOCKED_PREFIXES: tuple[str, ...] = (
    ".git/",
    "addons/",
    ".godot/",
)

# HF-12：已有大文件默认走 replace_text，禁止整写
WRITE_FULL_MAX_CHARS: int = 6000
WRITE_FULL_MAX_LINES: int = 120
READ_DEFAULT_LIMIT: int = 8000
OBS_TOTAL_BUDGET: int = 14000
OBS_PER_ITEM_BUDGET: int = 7000
OBS_PRIORITY_TOOLS: tuple[str, ...] = (
    "read_file",
    "search_in_file",
    "replace_text",
    "write_file",
    "validate_gdscript",
    "self_check",
    "done",
)


class AgentWorkspaceError(ValueError):
    """智能体读写被拒绝。"""


def normalize_rel(rel_posix: str) -> str:
    rel = rel_posix.strip().replace("\\", "/").lstrip("/")
    parts = rel.split("/")
    if (
        not rel
        or "\x00" in rel
        or ".." in parts
        or "" in parts
    ):
        raise AgentWorkspaceError(f"非法路径: {rel_posix!r}")
    return rel


def assert_agent_path(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    *,
    for_write: bool,
) -> Path:
    """校验相对路径落在会话 workspace，且不在 templates。"""
    rel = normalize_rel(rel_posix)
    if rel in _BLOCKED_EXACT or any(rel.startswith(p) for p in _BLOCKED_PREFIXES):
        raise AgentWorkspaceError(f"路径不在会话可访问范围: {rel}")

    if for_write:
        suffix = Path(rel).suffix.lower()
        if suffix and suffix not in _ALLOWED_SUFFIXES:
            raise AgentWorkspaceError(f"文件类型不在会话可写白名单: {rel}")
        # 写范围：core/**、config/**、scenes/**、assets 下新建说明类
        if not (
            rel.startswith("core/")
            or rel.startswith("config/")
            or rel.startswith("scenes/")
            or rel.startswith("assets/")
        ):
            raise AgentWorkspaceError(
                f"智能体只能写会话 core/config/scenes/assets，拒绝: {rel}"
            )

    root = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())
    assert_not_under_templates(root, templates_dir.resolve())
    target = (root / rel).resolve()
    assert_under_workspace(target, workspace_dir.resolve())
    assert_not_under_templates(target, templates_dir.resolve())
    return target


def validate_gdscript_safe(content: str) -> None:
    for snip in FORBIDDEN_GD_SNIPPETS:
        if snip in content:
            raise AgentWorkspaceError(f"脚本 API 不在产品允许列表: {snip}")


def sha256_text(text: str) -> str:
    """内容 hash（按 UTF-8 字节，含原样换行）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text_raw(target: Path) -> str:
    """按磁盘字节解码，避免 Windows 文本模式把 CRLF 规范化成 LF。"""
    return target.read_bytes().decode("utf-8", errors="replace")


def list_workspace_tree_high_signal(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    *,
    recent_writes: list[str] | None = None,
    max_entries: int = 40,
) -> list[str]:
    """高信号文件树：优先 recent writes / core / scenes / config；过滤噪声。"""
    root = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())
    assert_not_under_templates(root, templates_dir.resolve())

    noise_suffixes = {
        ".import",
        ".ogg",
        ".wav",
        ".mp3",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".svg",
        ".ttf",
        ".otf",
    }
    noise_names = {
        ".session_ai_log.jsonl",
        "summary.json",
    }
    noise_dirs = (".agent/", ".godot/", ".git/", "addons/")

    def _is_noise(rp: str) -> bool:
        if any(rp.startswith(d) for d in noise_dirs):
            return True
        name = Path(rp).name
        if name in noise_names or name.startswith("."):
            return True
        if Path(rp).suffix.lower() in noise_suffixes:
            # 允许少量必要说明类 svg 在 assets 以外
            if rp.startswith("assets/"):
                return True
            if Path(rp).suffix.lower() in {".import", ".ogg", ".wav", ".mp3", ".png", ".jpg"}:
                return True
        if "footstep" in name.lower():
            return True
        return False

    buckets: dict[str, list[str]] = {
        "recent": [],
        "core": [],
        "scenes": [],
        "config": [],
        "sandbox": [],
        "other": [],
    }
    seen: set[str] = set()

    for rel in recent_writes or []:
        rp = str(rel).replace("\\", "/").lstrip("/")
        if not rp or rp in seen:
            continue
        p = root / rp
        if p.is_file() and not _is_noise(rp):
            buckets["recent"].append(rp)
            seen.add(rp)

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rp = p.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        if rp in seen or _is_noise(rp):
            continue
        if rp.startswith("core/ai_sandbox/"):
            buckets["sandbox"].append(rp)
        elif rp.startswith("core/"):
            buckets["core"].append(rp)
        elif rp.startswith("scenes/"):
            buckets["scenes"].append(rp)
        elif rp.startswith("config/"):
            buckets["config"].append(rp)
        else:
            buckets["other"].append(rp)
        seen.add(rp)

    for key in ("core", "scenes", "config", "sandbox", "other"):
        buckets[key].sort()

    out: list[str] = []
    per_cap = {
        "recent": 12,
        "core": 16,
        "scenes": 8,
        "config": 6,
        "sandbox": 6,
        "other": 4,
    }
    for key in ("recent", "core", "scenes", "config", "sandbox", "other"):
        for rp in buckets[key][: per_cap[key]]:
            out.append(rp)
            if len(out) >= max_entries:
                return out
    return out


def list_workspace_tree(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_dir: str = "",
    max_entries: int = 80,
) -> list[str]:
    """列出目录（相对路径），供 LLM 观察项目结构。"""
    rel = normalize_rel(rel_dir) if rel_dir.strip() else ""
    if rel:
        base = assert_agent_path(
            workspace_root, workspace_dir, templates_dir, rel, for_write=False
        )
        if not base.is_dir():
            raise AgentWorkspaceError(f"不是目录: {rel}")
    else:
        base = assert_under_workspace(workspace_root.resolve(), workspace_dir.resolve())

    out: list[str] = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        try:
            rp = p.resolve().relative_to(workspace_root.resolve()).as_posix()
        except ValueError:
            continue
        if any(rp.startswith(b) for b in _BLOCKED_PREFIXES):
            continue
        if rp in _BLOCKED_EXACT:
            continue
        out.append(rp)
        if len(out) >= max_entries:
            break
    return out


def read_workspace_file(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    max_chars: int | None = None,
) -> str:
    """读取全文（内部校验/门禁用）。max_chars 仅兼容旧调用；默认不截断。"""
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel_posix, for_write=False
    )
    if not target.is_file():
        raise AgentWorkspaceError(f"文件不存在: {rel_posix}")
    text = read_text_raw(target)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + f"\n\n…(截断，共 {len(text)} 字符)"
    return text


def read_workspace_file_page(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    *,
    offset: int = 0,
    limit: int = READ_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """分页读文件；返回 offset/limit/eof/sha256/next_offset 等元数据。"""
    rel = normalize_rel(rel_posix)
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel, for_write=False
    )
    if not target.is_file():
        raise AgentWorkspaceError(f"文件不存在: {rel}")
    text = read_text_raw(target)
    total = len(text)
    off = max(0, int(offset))
    lim = max(1, min(int(limit), 20000))
    # offset 已越过末尾：明确 eof，阻止 LLM 空转续读
    if total == 0 or off >= total:
        return {
            "path": rel,
            "offset": off,
            "limit": lim,
            "total_chars": total,
            "returned_chars": 0,
            "eof": True,
            "sha256": sha256_text(text),
            "content": "",
            "next_offset": None,
            "truncated": False,
            "note": (
                f"offset={off} 已达/超过文件末尾（total_chars={total}）；"
                "文件已完整，请停止续读并开始 replace_text 施工或 done"
            ),
        }
    chunk = text[off : off + lim]
    returned = len(chunk)
    eof = off + returned >= total
    next_off = off + returned if not eof else None
    return {
        "path": rel,
        "offset": off,
        "limit": lim,
        "total_chars": total,
        "returned_chars": returned,
        "eof": eof,
        "sha256": sha256_text(text),
        "content": chunk,
        "next_offset": next_off,
        "truncated": not eof and off == 0 and total > lim,
    }


def search_workspace_file(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    query: str,
    *,
    max_hits: int = 8,
    context_lines: int = 2,
) -> dict[str, Any]:
    """在文件中搜索 query，返回带上下文的命中行。"""
    rel = normalize_rel(rel_posix)
    q = (query or "").strip()
    if not q:
        raise AgentWorkspaceError("search_in_file 需要非空 query")
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel, for_write=False
    )
    if not target.is_file():
        raise AgentWorkspaceError(f"文件不存在: {rel}")
    text = read_text_raw(target)
    lines = text.splitlines()
    max_h = max(1, min(int(max_hits), 40))
    ctx = max(0, min(int(context_lines), 8))
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if q not in line:
            continue
        start = max(0, i - ctx)
        end = min(len(lines), i + ctx + 1)
        snippet_lines = []
        # 用原始文本估算 char_offset（兼容 \r\n）
        if "\r\n" in text:
            sep = "\r\n"
        elif "\r" in text and "\n" not in text:
            sep = "\r"
        else:
            sep = "\n"
        char_offset = sum(len(lines[j]) + len(sep) for j in range(0, start))
        for j in range(start, end):
            prefix = ">>" if j == i else "  "
            snippet_lines.append(f"{prefix}{j + 1}: {lines[j]}")
        hits.append(
            {
                "line": i + 1,
                "char_offset": char_offset,
                "match": line,
                "context": "\n".join(snippet_lines),
            }
        )
        if len(hits) >= max_h:
            break
    return {
        "path": rel,
        "query": q,
        "total_chars": len(text),
        "sha256": sha256_text(text),
        "hit_count": len(hits),
        "hits": hits,
        "truncated_hits": len(hits) >= max_h,
    }


def existing_file_requires_replace(
    path: str,
    existing_text: str | None,
    *,
    allow_full_rewrite: bool = False,
) -> bool:
    """已有且超过阈值的 .gd/.tscn 默认必须 replace_text。"""
    if allow_full_rewrite:
        return False
    if existing_text is None:
        return False
    rel = path.replace("\\", "/")
    suffix = Path(rel).suffix.lower()
    if suffix not in {".gd", ".tscn"}:
        return False
    if not existing_text:
        return False
    lines = existing_text.count("\n") + (0 if existing_text.endswith("\n") else 1)
    return len(existing_text) > WRITE_FULL_MAX_CHARS or lines > WRITE_FULL_MAX_LINES


def _deep_merge_dict(base: dict, overlay: dict) -> dict:
    """overlay 覆盖同名叶；base 独有键保留（防 LLM 整表覆盖丢字段）。"""
    out: dict = dict(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge_dict(out[key], val)
        else:
            out[key] = val
    return out


def atomic_write_text(target: Path, content: str) -> None:
    """同目录临时文件 + replace，保证原子写入。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp_path), str(target))
    except Exception:
        try:
            if tmp_path.is_file():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def write_workspace_file(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    content: str,
) -> str:
    """写入会话文件；返回相对路径。绝不写 templates。"""
    rel = normalize_rel(rel_posix)
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel, for_write=True
    )
    if rel.endswith(".gd"):
        validate_gdscript_safe(content)
    # game_config：合并写入，避免 LLM 只写局部 tuning 时丢掉 powerup_types 等
    if rel.replace("\\", "/") == "config/game_config.json" and target.is_file():
        try:
            incoming = json.loads(content)
            existing = json.loads(read_text_raw(target))
            if isinstance(incoming, dict) and isinstance(existing, dict):
                content = json.dumps(
                    _deep_merge_dict(existing, incoming),
                    ensure_ascii=False,
                    indent=2,
                ) + "\n"
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    atomic_write_text(target, content)
    return rel


def normalize_newlines(text: str) -> str:
    """统一为 \\n，便于跨 CRLF/LF 比较。"""
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def align_fragment_newlines(fragment: str, file_text: str) -> str:
    """把片段换行对齐到磁盘文件风格（Win 模板多为 CRLF，LLM 常给 LF）。"""
    body = normalize_newlines(fragment)
    if "\r\n" in (file_text or ""):
        return body.replace("\n", "\r\n")
    return body


def replace_workspace_text(
    workspace_root: Path,
    workspace_dir: Path,
    templates_dir: Path,
    rel_posix: str,
    old_text: str,
    new_text: str,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """唯一命中替换；零/多命中拒绝；换行自动对齐；唯一命中时 hash 可软忽略。"""
    rel = normalize_rel(rel_posix)
    if not old_text:
        raise AgentWorkspaceError("replace_text 需要非空 old_text")
    target = assert_agent_path(
        workspace_root, workspace_dir, templates_dir, rel, for_write=True
    )
    if not target.is_file():
        raise AgentWorkspaceError(f"文件不存在: {rel}")
    before = read_text_raw(target)
    before_hash = sha256_text(before)
    old_aligned = align_fragment_newlines(old_text, before)
    new_aligned = align_fragment_newlines(new_text, before)
    count = before.count(old_aligned)
    if count == 0:
        raise AgentWorkspaceError("replace_text 零命中: old_text 未在文件中找到")
    if count > 1:
        raise AgentWorkspaceError(
            f"replace_text 多命中({count}): old_text 须唯一；请扩大上下文"
        )
    hash_mismatch_ignored = False
    if expected_sha256 and expected_sha256.strip():
        want = expected_sha256.strip().lower()
        if before_hash.lower() != want:
            # 唯一命中时内容锚点已够安全；避免 LLM 陈旧/截断 hash 卡死整局
            hash_mismatch_ignored = True
    after = before.replace(old_aligned, new_aligned, 1)
    if rel.endswith(".gd"):
        validate_gdscript_safe(after)
    after_hash = sha256_text(after)
    # 行级 diff 预览
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    changed = abs(len(after_lines) - len(before_lines))
    # 粗算变更行：按最长公共前缀/后缀之外的区间
    i = 0
    while i < len(before_lines) and i < len(after_lines) and before_lines[i] == after_lines[i]:
        i += 1
    j = 0
    while (
        j < len(before_lines) - i
        and j < len(after_lines) - i
        and before_lines[-(j + 1)] == after_lines[-(j + 1)]
    ):
        j += 1
    old_hunk = before_lines[i : len(before_lines) - j if j else None]
    new_hunk = after_lines[i : len(after_lines) - j if j else None]
    if old_hunk is None:
        old_hunk = before_lines[i:]
    if new_hunk is None:
        new_hunk = after_lines[i:]
    changed_lines = max(len(old_hunk), len(new_hunk), 1 if before != after else 0)
    preview_old = "\n".join(old_hunk[:12])
    preview_new = "\n".join(new_hunk[:12])
    if len(old_hunk) > 12:
        preview_old += "\n…"
    if len(new_hunk) > 12:
        preview_new += "\n…"
    atomic_write_text(target, after)
    out: dict[str, Any] = {
        "path": rel,
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "changed_lines": changed_lines,
        "diff_preview": {
            "removed": preview_old,
            "added": preview_new,
        },
        "bytes": len(after.encode("utf-8")),
        "newline_aligned": old_aligned != old_text or new_aligned != new_text,
    }
    if hash_mismatch_ignored:
        out["hash_mismatch_ignored"] = True
        out["note"] = (
            "expected_sha256 与磁盘不一致，但 old_text 唯一命中，已按内容替换"
        )
    return out


def _trim_observation_item(
    obs: dict[str, Any],
    budget: int,
) -> dict[str, Any]:
    """单条 observation 结构化裁剪；保留 path/磁盘 eof/sha256/next_offset。

    HF-12 Live：prompt 预算截断 ≠ 磁盘未读完。
    不得把磁盘 eof=true 改成 false，否则 LLM 会对小文件空转续读。
    """
    raw = json.dumps(obs, ensure_ascii=False)
    if len(raw) <= budget:
        return dict(obs)

    out = dict(obs)
    out["truncated"] = True
    # 冻结磁盘读盘事实（裁剪前）
    disk_eof = out.get("eof")
    disk_next = out.get("next_offset")
    disk_returned = out.get("returned_chars")
    disk_total = out.get("total_chars")

    def _mark_prompt_trim(keep: int, *, key: str) -> None:
        """裁剪展示字段，但区分 prompt 截断与磁盘 eof。"""
        offset = int(out.get("offset") or 0)
        out["prompt_truncated"] = True
        out["content_resume_offset"] = offset + keep
        if disk_eof is True:
            # 磁盘已读完：保留 eof=true / next_offset=null，只提示查看未展示段
            out["eof"] = True
            out["next_offset"] = None
            out["note"] = (
                "prompt 展示截断；磁盘 eof=true 表示文件已读完。"
                "查看未展示段请 read_file(offset=content_resume_offset) 或 search_in_file，"
                "然后即可 replace_text 施工"
            )
        else:
            # 磁盘本身未读完：续读仍用磁盘 next_offset；另给 content_resume_offset
            out["eof"] = False
            if disk_next is not None:
                out["next_offset"] = disk_next
            elif "path" in out:
                out["next_offset"] = offset + keep
            out["note"] = (
                "prompt 展示截断且磁盘 eof=false；"
                "请按 next_offset 续读完整文件，或用 search_in_file 定位"
            )
        if key == "content":
            # returned_chars 保持磁盘本页真实长度，避免误导分页算术
            if disk_returned is not None:
                out["returned_chars"] = disk_returned
            if disk_total is not None:
                out["total_chars"] = disk_total

    # 优先裁 content / prompt / entries / hits / gate_errors 等大字段
    for key in ("content", "prompt", "detail", "summary"):
        val = out.get(key)
        if not isinstance(val, str) or not val:
            continue
        # 为元数据预留约 800 字符
        keep = max(200, budget - 800)
        if len(val) > keep:
            out[key] = val[:keep]
            out["truncated"] = True
            if key == "content" and "path" in out:
                _mark_prompt_trim(keep, key=key)
            elif key == "content":
                out["prompt_truncated"] = True

    if isinstance(out.get("entries"), list) and len(json.dumps(out, ensure_ascii=False)) > budget:
        entries = list(out["entries"])
        while entries and len(json.dumps(out, ensure_ascii=False)) > budget:
            entries.pop()
            out["entries"] = entries
        out["truncated"] = True
        out["entries_truncated"] = True

    if isinstance(out.get("hits"), list) and len(json.dumps(out, ensure_ascii=False)) > budget:
        hits = list(out["hits"])
        while hits and len(json.dumps(out, ensure_ascii=False)) > budget:
            hits.pop()
            out["hits"] = hits
        out["truncated"] = True
        out["truncated_hits"] = True

    if isinstance(out.get("gate_errors"), list) and len(json.dumps(out, ensure_ascii=False)) > budget:
        errs = [str(x)[:200] for x in out["gate_errors"][:8]]
        out["gate_errors"] = errs
        out["truncated"] = True

    # 仍超预算：丢掉低价值嵌套，保留工具名与路径 + 磁盘 eof 事实
    if len(json.dumps(out, ensure_ascii=False)) > budget:
        slim: dict[str, Any] = {
            "tool": out.get("tool"),
            "path": out.get("path"),
            "error": out.get("error"),
            "ok": out.get("ok"),
            "truncated": True,
            "prompt_truncated": True,
            "eof": disk_eof if disk_eof is not None else out.get("eof"),
            "sha256": out.get("sha256"),
            "next_offset": disk_next if disk_eof is not True else None,
            "offset": out.get("offset"),
            "total_chars": disk_total if disk_total is not None else out.get("total_chars"),
            "returned_chars": disk_returned,
            "note": (
                "observation 超预算，已保留路径与磁盘 eof/continuation；"
                "eof=true 勿无限续读；eof=false 按 next_offset 续读"
            ),
        }
        if isinstance(out.get("content"), str):
            keep = max(120, budget - 600)
            content_full = out["content"]
            # out["content"] 可能已被上一轮裁过；优先用原始 obs content 算 resume
            raw_content = obs.get("content") if isinstance(obs.get("content"), str) else content_full
            slim["content"] = content_full[:keep]
            off = int(out.get("offset") or 0)
            slim["content_resume_offset"] = off + keep
            if disk_eof is True:
                slim["eof"] = True
                slim["next_offset"] = None
                slim["note"] = (
                    "prompt 展示截断；磁盘 eof=true 文件已读完。"
                    "查看未展示段用 content_resume_offset 或 search_in_file"
                )
            else:
                slim["eof"] = False
                slim["next_offset"] = (
                    disk_next if disk_next is not None else off + len(raw_content)
                )
        out = slim

    return out


def serialize_observations_for_followup(
    observations: list[dict[str, Any]],
    *,
    total_budget: int = OBS_TOTAL_BUDGET,
    per_item_budget: int = OBS_PER_ITEM_BUDGET,
) -> str:
    """按工具优先级逐项结构化序列化；禁止对整个 JSON 裸硬切。"""
    if not observations:
        return "[]"

    # 优先级：read_file 等前置，其余保持相对顺序
    indexed = list(enumerate(observations))

    def _rank(item: tuple[int, dict[str, Any]]) -> tuple[int, int]:
        idx, obs = item
        tool = str(obs.get("tool") or "")
        try:
            pri = OBS_PRIORITY_TOOLS.index(tool)
        except ValueError:
            pri = len(OBS_PRIORITY_TOOLS)
        return (pri, idx)

    ordered = sorted(indexed, key=_rank)
    trimmed: list[tuple[int, dict[str, Any]]] = []
    used = 2  # []
    n = len(ordered)
    for pos, (orig_idx, obs) in enumerate(ordered):
        remaining_items = n - pos
        # 为后续条目预留最小槽位
        slot = max(
            400,
            min(
                per_item_budget,
                (total_budget - used - max(0, remaining_items - 1) * 120) // max(1, remaining_items),
            ),
        )
        item = _trim_observation_item(obs, slot)
        piece = json.dumps(item, ensure_ascii=False)
        # 逗号与括号
        extra = 1 if trimmed else 0
        if used + len(piece) + extra + 1 > total_budget and trimmed:
            # 塞一个占位，保留 path/磁盘 eof；勿把 eof=true 诱导成无限续读
            disk_eof = obs.get("eof")
            stub = {
                "tool": obs.get("tool"),
                "path": obs.get("path"),
                "truncated": True,
                "prompt_truncated": True,
                "eof": disk_eof,
                "sha256": obs.get("sha256"),
                "total_chars": obs.get("total_chars"),
                "offset": obs.get("offset"),
                "next_offset": None if disk_eof is True else obs.get("next_offset"),
                "note": (
                    "预算不足，本条已缩略；"
                    + (
                        "磁盘 eof=true，请 search_in_file 或对本文件 replace_text"
                        if disk_eof is True
                        else "请继续 read_file(path, offset=next_offset)"
                    )
                ),
            }
            if disk_eof is not True and isinstance(obs.get("content"), str) and obs.get("path"):
                stub["next_offset"] = obs.get("next_offset") or int(obs.get("offset") or 0)
            piece = json.dumps(stub, ensure_ascii=False)
            if used + len(piece) + extra + 1 > total_budget:
                break
            item = stub
        trimmed.append((orig_idx, item))
        used += len(piece) + extra

    # 恢复原始顺序
    trimmed.sort(key=lambda x: x[0])
    payload = [item for _, item in trimmed]
    text = json.dumps(payload, ensure_ascii=False)
    # 理论上不应再硬切；若极端超限，追加截断标记对象而非切断 JSON
    if len(text) > total_budget + 500:
        payload = payload[: max(1, len(payload) - 1)]
        payload.append(
            {
                "tool": "_observations_meta",
                "truncated": True,
                "note": "后续 observation 因预算省略；请按已有 path/next_offset 继续读盘",
            }
        )
        text = json.dumps(payload, ensure_ascii=False)
    return text


def assert_full_read_before_rewrite(
    path: str,
    content_to_write: str,
    read_eof_by_path: dict[str, bool],
    *,
    existing_text: str | None,
    allow_full_rewrite: bool = False,
) -> None:
    """未读到 EOF 时，不允许整写已有大文件。"""
    rel = path.replace("\\", "/")
    if existing_text is None:
        return
    if not existing_file_requires_replace(rel, existing_text, allow_full_rewrite=allow_full_rewrite):
        # 小文件仍建议读过，但不强制 EOF（兼容短配置）
        return
    if allow_full_rewrite:
        return
    if not read_eof_by_path.get(rel, False):
        raise AgentWorkspaceError(
            f"文件 {rel} 尚未完整读取（eof=false）；"
            "请继续 read_file(offset=next_offset)，或用 replace_text 做最小 patch"
        )
