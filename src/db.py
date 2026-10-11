"""Database and state persistence layer for HowToLiveBetter-Motion."""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline.db")
DEFAULT_PROGRESS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progress.json")


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create and configure a SQLite connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize SQLite schema if not exists."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id VARCHAR(32) PRIMARY KEY,
                source_file VARCHAR(128) NOT NULL,
                chapter_index INTEGER NOT NULL,
                chapter_title VARCHAR(128) NOT NULL,
                item_index INTEGER NOT NULL,
                title VARCHAR(256) NOT NULL,
                cost_money VARCHAR(32),
                cost_time VARCHAR(32),
                cost_willpower VARCHAR(32),
                benefit_level VARCHAR(32),
                benefit_metric VARCHAR(64),
                cost_desc TEXT,
                plain_text TEXT,
                benefit_desc TEXT,
                evidence_grade VARCHAR(8),
                source_citations TEXT,
                notes TEXT,
                raw_content TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'Pending',
                script_json TEXT,
                raw_assets_dir VARCHAR(512),
                final_video_path VARCHAR(512),
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_chapter ON entries(chapter_index);")


def upsert_entry(conn: sqlite3.Connection, item: Dict[str, Any], force_reset_status: bool = False) -> str:
    """
    Insert or update an entry in the database.
    If the entry already exists, its parsed content is refreshed, but existing workflow state
    (status, script_json, raw_assets_dir, final_video_path) is preserved unless force_reset_status is True.
    """
    now = datetime.now().isoformat()
    existing = conn.execute("SELECT id, status, script_json, raw_assets_dir, final_video_path, retry_count FROM entries WHERE id = ?", (item["id"],)).fetchone()

    with conn:
        if existing:
            status = "Pending" if force_reset_status else existing["status"]
            script_json = None if force_reset_status else existing["script_json"]
            raw_assets_dir = None if force_reset_status else existing["raw_assets_dir"]
            final_video_path = None if force_reset_status else existing["final_video_path"]
            retry_count = 0 if force_reset_status else existing["retry_count"]

            conn.execute("""
                UPDATE entries SET
                    source_file = ?,
                    chapter_index = ?,
                    chapter_title = ?,
                    item_index = ?,
                    title = ?,
                    cost_money = ?,
                    cost_time = ?,
                    cost_willpower = ?,
                    benefit_level = ?,
                    benefit_metric = ?,
                    cost_desc = ?,
                    plain_text = ?,
                    benefit_desc = ?,
                    evidence_grade = ?,
                    source_citations = ?,
                    notes = ?,
                    raw_content = ?,
                    status = ?,
                    script_json = ?,
                    raw_assets_dir = ?,
                    final_video_path = ?,
                    retry_count = ?,
                    updated_at = ?
                WHERE id = ?;
            """, (
                item["source_file"],
                item["chapter_index"],
                item["chapter_title"],
                item["item_index"],
                item["title"],
                item.get("cost_money"),
                item.get("cost_time"),
                item.get("cost_willpower"),
                item.get("benefit_level"),
                item.get("benefit_metric"),
                item.get("cost_desc"),
                item.get("plain_text"),
                item.get("benefit_desc"),
                item.get("evidence_grade"),
                item.get("source_citations"),
                item.get("notes"),
                item.get("raw_content"),
                status,
                script_json,
                raw_assets_dir,
                final_video_path,
                retry_count,
                now,
                item["id"]
            ))
            return "updated"
        else:
            conn.execute("""
                INSERT INTO entries (
                    id, source_file, chapter_index, chapter_title, item_index,
                    title, cost_money, cost_time, cost_willpower, benefit_level, benefit_metric,
                    cost_desc, plain_text, benefit_desc, evidence_grade, source_citations, notes,
                    raw_content, status, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, 'Pending', ?, ?
                );
            """, (
                item["id"],
                item["source_file"],
                item["chapter_index"],
                item["chapter_title"],
                item["item_index"],
                item["title"],
                item.get("cost_money"),
                item.get("cost_time"),
                item.get("cost_willpower"),
                item.get("benefit_level"),
                item.get("benefit_metric"),
                item.get("cost_desc"),
                item.get("plain_text"),
                item.get("benefit_desc"),
                item.get("evidence_grade"),
                item.get("source_citations"),
                item.get("notes"),
                item.get("raw_content"),
                now,
                now
            ))
            return "inserted"


def update_status(
    conn: sqlite3.Connection,
    entry_id: str,
    status: str,
    script_json: Optional[str] = None,
    raw_assets_dir: Optional[str] = None,
    final_video_path: Optional[str] = None,
    error_message: Optional[str] = None,
    increment_retry: bool = False
) -> None:
    """Update progress status and associated fields for an entry."""
    now = datetime.now().isoformat()
    params = [status, now]
    updates = ["status = ?", "updated_at = ?"]

    if script_json is not None:
        updates.append("script_json = ?")
        params.append(script_json)

    if raw_assets_dir is not None:
        updates.append("raw_assets_dir = ?")
        params.append(raw_assets_dir)

    if final_video_path is not None:
        updates.append("final_video_path = ?")
        params.append(final_video_path)

    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if increment_retry:
        updates.append("retry_count = retry_count + 1")

    params.append(entry_id)
    query = f"UPDATE entries SET {', '.join(updates)} WHERE id = ?;"

    with conn:
        conn.execute(query, tuple(params))


def get_entry(conn: sqlite3.Connection, entry_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single entry by its ID."""
    row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    return dict(row) if row else None


def list_entries(
    conn: sqlite3.Connection,
    status: Optional[str] = None,
    chapter_index: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Query entries with optional filters."""
    query = "SELECT * FROM entries WHERE 1=1"
    params: List[Any] = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if chapter_index is not None:
        query += " AND chapter_index = ?"
        params.append(chapter_index)

    query += " ORDER BY chapter_index ASC, item_index ASC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def get_statistics(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Calculate summary statistics for dashboard and progress export."""
    total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]

    status_counts = {}
    rows = conn.execute("SELECT status, COUNT(*) FROM entries GROUP BY status").fetchall()
    for row in rows:
        status_counts[row[0]] = row[1]

    # Ensure all standard statuses exist in dictionary
    for s in ["Pending", "Script_Generated", "Media_Generated", "Video_Assembled", "Completed", "Failed"]:
        status_counts.setdefault(s, 0)

    chapter_counts = []
    ch_rows = conn.execute("""
        SELECT chapter_index, chapter_title, COUNT(*) as cnt,
               SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_cnt
        FROM entries
        GROUP BY chapter_index, chapter_title
        ORDER BY chapter_index ASC
    """).fetchall()

    for ch in ch_rows:
        chapter_counts.append({
            "chapter_index": ch["chapter_index"],
            "chapter_title": ch["chapter_title"],
            "total_items": ch["cnt"],
            "completed_items": ch["completed_cnt"]
        })

    return {
        "total_entries": total,
        "status_summary": status_counts,
        "chapters": chapter_counts
    }


def export_progress_json(conn: sqlite3.Connection, json_path: str = DEFAULT_PROGRESS_PATH) -> Dict[str, Any]:
    """Export current state to progress.json snapshot."""
    stats = get_statistics(conn)
    entries = list_entries(conn)

    snapshot_data = {
        "export_time": datetime.now().isoformat(),
        "total_entries": stats["total_entries"],
        "status_summary": stats["status_summary"],
        "chapters": stats["chapters"],
        "entries": [
            {
                "id": e["id"],
                "chapter_index": e["chapter_index"],
                "chapter_title": e["chapter_title"],
                "item_index": e["item_index"],
                "title": e["title"],
                "evidence_grade": e["evidence_grade"],
                "status": e["status"],
                "final_video_path": e["final_video_path"],
                "updated_at": e["updated_at"]
            }
            for e in entries
        ]
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

    return snapshot_data
