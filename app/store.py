"""SQLite 持久化层。存储:小说项目、角色/世界观设定、章节正文、
上传文档的分块(用于续写检索)、以及对话消息(用于 agent 上下文)。

使用同步 sqlite3 (足够小说场景,避免 aiosqlite 额外依赖)。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Iterator, Optional

from .config import get_settings

_lock = threading.Lock()


def _now() -> float:
    return time.time()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    s = get_settings()
    os.makedirs(os.path.dirname(s.db_path), exist_ok=True)
    conn = sqlite3.connect(s.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                genre TEXT,
                premise TEXT,
                style TEXT,
                meta TEXT DEFAULT '{}',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                idx INTEGER NOT NULL,
                outline TEXT,
                content TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS elements (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,        -- character | location | lore | timeline
                name TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at REAL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source TEXT NOT NULL,      -- upload:filename | chapter:id
                idx INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding TEXT,            -- 预留向量字段 (当前用关键词检索)
                created_at REAL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,        -- user | assistant | tool
                content TEXT NOT NULL,
                tool_name TEXT,
                tool_call_id TEXT,
                created_at REAL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            -- 伏笔追踪 (跨章/跨卷)
            CREATE TABLE IF NOT EXISTS foreshadowings (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,           -- 伏笔名称/简述
                content TEXT NOT NULL,        -- 详细描述
                planted_chapter INTEGER,     -- 埋设章节号
                expected_recovery INTEGER,   -- 预期回收章节号
                actual_recovery INTEGER,     -- 实际回收章节号
                status TEXT DEFAULT 'planted', -- planted | recovered | abandoned
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            -- 时间线事件
            CREATE TABLE IF NOT EXISTS timeline_events (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                event TEXT NOT NULL,          -- 事件描述
                chapter_idx INTEGER,          -- 所属章节号
                time_in_story TEXT,           -- 故事内时间点 (自由格式)
                cause TEXT,                   -- 原因
                effect TEXT,                  -- 后果
                created_at REAL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            -- 角色状态快照 (随章节更新)
            CREATE TABLE IF NOT EXISTS character_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                character_name TEXT NOT NULL, -- 角色名
                current_state TEXT NOT NULL,  -- 当前状态描述 (身份/能力/关系/公众形象)
                latest_chapter INTEGER,       -- 最近一次更新的章节号
                change_log TEXT DEFAULT '[]',  -- JSON 数组: [{chapter, change, at}]
                updated_at REAL,
                UNIQUE(project_id, character_name),
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )


def _uuid() -> str:
    return uuid.uuid4().hex


# ---------- projects ----------
def create_project(name: str, genre: str = "", premise: str = "", style: str = "") -> str:
    pid = _uuid()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO projects(id,name,genre,premise,style,meta,created_at) VALUES(?,?,?,?,?,?,?)",
            (pid, name, genre, premise, style, "{}", _now()),
        )
    return pid


def list_projects() -> list[dict]:
    with get_conn() as c:
        rows = c.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_project(pid: str) -> Optional[dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None


def update_project(pid: str, **fields) -> None:
    if not fields:
        return
    sets = ",".join(f"{k}=?" for k in fields)
    with _lock, get_conn() as c:
        c.execute(f"UPDATE projects SET {sets} WHERE id=?", (*fields.values(), pid))


def delete_project(pid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM projects WHERE id=?", (pid,))


# ---------- chapters ----------
def add_chapter(pid: str, title: str, idx: int, outline: str = "", content: str = "") -> str:
    cid = _uuid()
    now = _now()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO chapters(id,project_id,title,idx,outline,content,status,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (cid, pid, title, idx, outline, content, "draft", now, now),
        )
    return cid


def list_chapters(pid: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM chapters WHERE project_id=? ORDER BY idx ASC", (pid,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_chapter(cid: str) -> Optional[dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM chapters WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None


def update_chapter(cid: str, **fields) -> None:
    fields = {**fields, "updated_at": _now()}
    if not fields:
        return
    sets = ",".join(f"{k}=?" for k in fields)
    with _lock, get_conn() as c:
        c.execute(f"UPDATE chapters SET {sets} WHERE id=?", (*fields.values(), cid))


def delete_chapter(cid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM chapters WHERE id=?", (cid,))


# ---------- elements ----------
def add_element(pid: str, kind: str, name: str, detail: str) -> str:
    eid = _uuid()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO elements(id,project_id,kind,name,detail,created_at) VALUES(?,?,?,?,?,?)",
            (eid, pid, kind, name, detail, _now()),
        )
    return eid


def list_elements(pid: str, kind: Optional[str] = None) -> list[dict]:
    with get_conn() as c:
        if kind:
            rows = c.execute(
                "SELECT * FROM elements WHERE project_id=? AND kind=? ORDER BY created_at",
                (pid, kind),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM elements WHERE project_id=? ORDER BY kind,created_at", (pid,)
            ).fetchall()
        return [dict(r) for r in rows]


def delete_element(eid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM elements WHERE id=?", (eid,))


# ---------- chunks (上传小说 / 章节分块) ----------
def add_chunk(pid: str, source: str, idx: int, text: str) -> str:
    cid = _uuid()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO chunks(id,project_id,source,idx,text,created_at) VALUES(?,?,?,?,?,?)",
            (cid, pid, source, idx, text, _now()),
        )
    return cid


def list_chunks(pid: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM chunks WHERE project_id=? ORDER BY source,idx", (pid,)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_chunks_by_source(pid: str, source: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM chunks WHERE project_id=? AND source=?", (pid, source))


# ---------- messages ----------
def add_message(
    pid: str,
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_call_id: Optional[str] = None,
) -> str:
    mid = _uuid()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO messages(id,project_id,role,content,tool_name,tool_call_id,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (mid, pid, role, content, tool_name, tool_call_id, _now()),
        )
    return mid


def list_messages(pid: str, limit: int = 50) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM messages WHERE project_id=? ORDER BY created_at ASC LIMIT ?",
            (pid, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def clear_messages(pid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM messages WHERE project_id=?", (pid,))


def stats(pid: str) -> dict:
    with get_conn() as c:
        ch = c.execute("SELECT COUNT(*) n FROM chapters WHERE project_id=?", (pid,)).fetchone()
        el = c.execute("SELECT COUNT(*) n FROM elements WHERE project_id=?", (pid,)).fetchone()
        ck = c.execute("SELECT COUNT(*) n FROM chunks WHERE project_id=?", (pid,)).fetchone()
        wc = c.execute(
            "SELECT COALESCE(SUM(LENGTH(content)),0) n FROM chapters WHERE project_id=?", (pid,)
        ).fetchone()
        fs = c.execute("SELECT COUNT(*) n FROM foreshadowings WHERE project_id=?", (pid,)).fetchone()
        tl = c.execute("SELECT COUNT(*) n FROM timeline_events WHERE project_id=?", (pid,)).fetchone()
        cs = c.execute("SELECT COUNT(*) n FROM character_states WHERE project_id=?", (pid,)).fetchone()
        return {
            "chapters": ch["n"],
            "elements": el["n"],
            "chunks": ck["n"],
            "total_chars": wc["n"],
            "foreshadowings": fs["n"],
            "timeline_events": tl["n"],
            "character_states": cs["n"],
        }


# ---------- foreshadowings (伏笔追踪) ----------
def add_foreshadowing(
    pid: str, name: str, content: str,
    planted_chapter: Optional[int] = None,
    expected_recovery: Optional[int] = None,
) -> str:
    fid = _uuid()
    now = _now()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO foreshadowings(id,project_id,name,content,"
            "planted_chapter,expected_recovery,actual_recovery,status,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,NULL,'planted',?,?)",
            (fid, pid, name, content, planted_chapter, expected_recovery, now, now),
        )
    return fid


def list_foreshadowings(pid: str, status: Optional[str] = None) -> list[dict]:
    with get_conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM foreshadowings WHERE project_id=? AND status=? "
                "ORDER BY planted_chapter ASC",
                (pid, status),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM foreshadowings WHERE project_id=? "
                "ORDER BY planted_chapter ASC",
                (pid,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_foreshadowing(fid: str) -> Optional[dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM foreshadowings WHERE id=?", (fid,)).fetchone()
        return dict(r) if r else None


def update_foreshadowing(fid: str, **fields) -> None:
    if not fields:
        return
    fields = {**fields, "updated_at": _now()}
    sets = ",".join(f"{k}=?" for k in fields)
    with _lock, get_conn() as c:
        c.execute(f"UPDATE foreshadowings SET {sets} WHERE id=?", (*fields.values(), fid))


def delete_foreshadowing(fid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM foreshadowings WHERE id=?", (fid,))


# ---------- timeline_events (时间线) ----------
def add_timeline_event(
    pid: str, event: str,
    chapter_idx: Optional[int] = None,
    time_in_story: Optional[str] = None,
    cause: Optional[str] = None,
    effect: Optional[str] = None,
) -> str:
    tid = _uuid()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT INTO timeline_events(id,project_id,event,chapter_idx,"
            "time_in_story,cause,effect,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (tid, pid, event, chapter_idx, time_in_story, cause, effect, _now()),
        )
    return tid


def list_timeline_events(
    pid: str, from_chapter: Optional[int] = None, to_chapter: Optional[int] = None
) -> list[dict]:
    with get_conn() as c:
        if from_chapter is not None and to_chapter is not None:
            rows = c.execute(
                "SELECT * FROM timeline_events WHERE project_id=? "
                "AND chapter_idx>=? AND chapter_idx<=? ORDER BY chapter_idx ASC, created_at ASC",
                (pid, from_chapter, to_chapter),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM timeline_events WHERE project_id=? "
                "ORDER BY chapter_idx ASC, created_at ASC",
                (pid,),
            ).fetchall()
        return [dict(r) for r in rows]


def delete_timeline_event(tid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM timeline_events WHERE id=?", (tid,))


# ---------- character_states (角色状态快照) ----------
def upsert_character_state(
    pid: str, character_name: str, current_state: str,
    latest_chapter: Optional[int] = None, change: Optional[str] = None,
) -> str:
    """新增或更新角色状态。若角色已存在,追加 change 到 change_log。"""
    now = _now()
    csid = _uuid()
    with _lock, get_conn() as c:
        existing = c.execute(
            "SELECT * FROM character_states WHERE project_id=? AND character_name=?",
            (pid, character_name),
        ).fetchone()
        if existing:
            log = json.loads(existing["change_log"] or "[]")
            if change:
                log.append({
                    "chapter": latest_chapter,
                    "change": change,
                    "at": now,
                })
            new_state = current_state or existing["current_state"]
            new_chapter = (latest_chapter if latest_chapter is not None
                           else existing["latest_chapter"])
            c.execute(
                "UPDATE character_states SET current_state=?, latest_chapter=?, "
                "change_log=?, updated_at=? WHERE id=?",
                (new_state, new_chapter, json.dumps(log, ensure_ascii=False), now, existing["id"]),
            )
            return existing["id"]
        else:
            log = [{"chapter": latest_chapter, "change": change, "at": now}] if change else []
            c.execute(
                "INSERT INTO character_states(id,project_id,character_name,"
                "current_state,latest_chapter,change_log,updated_at) VALUES(?,?,?,?,?,?,?)",
                (csid, pid, character_name, current_state, latest_chapter,
                 json.dumps(log, ensure_ascii=False), now),
            )
            return csid


def list_character_states(pid: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM character_states WHERE project_id=? "
            "ORDER BY character_name ASC",
            (pid,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_character_state(pid: str, name: str) -> Optional[dict]:
    with get_conn() as c:
        r = c.execute(
            "SELECT * FROM character_states WHERE project_id=? AND character_name=?",
            (pid, name),
        ).fetchone()
        return dict(r) if r else None


def delete_character_state(csid: str) -> None:
    with _lock, get_conn() as c:
        c.execute("DELETE FROM character_states WHERE id=?", (csid,))


# ---------- chapter outline (细纲蓝图,扩展 chapters.outline 字段) ----------
def set_chapter_outline(cid: str, outline_blueprint: str) -> None:
    """更新章节细纲蓝图 (oh-story 细纲格式 markdown)。"""
    update_chapter(cid, outline=outline_blueprint, status="outlined")


def get_chapter_outline(cid: str) -> Optional[str]:
    ch = get_chapter(cid)
    return ch.get("outline") if ch else None
