# memory/store.py
"""
SQLite 长期偏好存储。
与 checkpoints.sqlite 分开，专门存储用户偏好（如常用作者 ID、偏好语言等）。
"""
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent / "preferences.sqlite"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id    TEXT NOT NULL,
            key        TEXT NOT NULL,
            value      TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, key)
        )
    """)
    conn.commit()
    return conn


def save_preference(user_id: str, key: str, value: str) -> None:
    """保存或更新用户偏好。"""
    with _conn() as c:
        c.execute("""
            INSERT INTO preferences (user_id, key, value, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT (user_id, key) DO UPDATE SET
                value      = excluded.value,
                updated_at = excluded.updated_at
        """, (user_id, key, value))


def get_preferences(user_id: str) -> dict:
    """读取某用户的所有偏好，返回 {key: value} dict。"""
    c = _conn()
    rows = c.execute(
        "SELECT key, value FROM preferences WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    c.close()
    return {row[0]: row[1] for row in rows}


def delete_preference(user_id: str, key: str) -> None:
    """删除某个偏好键。"""
    with _conn() as c:
        c.execute(
            "DELETE FROM preferences WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
