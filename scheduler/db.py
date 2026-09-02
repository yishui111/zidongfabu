"""SQLite 任务与发布记录。"""

import json
import os
import sqlite3
import time


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class DB:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT,
                media_md5 TEXT,
                platform TEXT,
                account TEXT,
                status TEXT,
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                info_json TEXT,
                result_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_md5 ON tasks(media_md5)"
        )
        self.conn.commit()

    def find_folder_by_md5(self, md5):
        """按视频 md5 查找最近一次任务级记录（platform='*'）。"""
        cur = self.conn.execute(
            "SELECT * FROM tasks WHERE media_md5=? AND platform='*' "
            "ORDER BY id DESC LIMIT 1",
            (md5,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def record_task(self, folder_name, md5, info, status, results=None, error=None):
        """写入任务级记录与各平台明细。"""
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO tasks (folder_name, media_md5, platform, status, last_error, "
            "info_json, result_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                folder_name,
                md5,
                "*",
                status,
                error,
                json.dumps(info, ensure_ascii=False),
                json.dumps(results, ensure_ascii=False) if results is not None else None,
                now,
                now,
            ),
        )
        task_id = cur.lastrowid
        for r in results or []:
            self.conn.execute(
                "INSERT INTO tasks (folder_name, media_md5, platform, account, status, "
                "attempts, last_error, result_json, info_json, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    folder_name,
                    md5,
                    r.get("platform"),
                    r.get("account"),
                    "success" if r.get("success") else "failed",
                    r.get("attempts", 0),
                    r.get("error"),
                    json.dumps(r.get("detail"), ensure_ascii=False) if r.get("detail") else None,
                    json.dumps(info, ensure_ascii=False),
                    now,
                    now,
                ),
            )
        self.conn.commit()
        return task_id
