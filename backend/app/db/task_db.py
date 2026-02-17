"""任务状态数据库操作模块"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    SEMANTIC_CHUNK = "semantic_chunk"
    SHADOW_WRITING = "shadow_writing"
    QUALITY_CHECK = "quality_check"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskDB:
    """任务状态数据库操作类"""

    def __init__(self, db_path: Union[str, Path, None] = None):
        if db_path is None:
            db_path = self._get_default_db_path()
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_default_db_path(self) -> Path:
        import platform
        home = Path.home()
        system = platform.system()
        if system == "Windows":
            data_dir = home / "AppData" / "Roaming" / "TED-Shadow-Writing"
        elif system == "Darwin":
            data_dir = home / "Library" / "Application Support" / "TED-Shadow-Writing"
        else:
            data_dir = home / ".config" / "TED-Shadow-Writing"
        return data_dir / "shadow_writing.db"

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_tasks (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_step TEXT,
                    current INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    current_url TEXT,
                    result TEXT,
                    error TEXT,
                    progress INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    completed_chunks INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def create(self, task_id: str, total: int = 0, url: Optional[str] = None) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO processing_tasks (id, status, current_step, total, current_url, progress)
                VALUES (?, 'pending', '等待开始', ?, ?, 0)
            """, (task_id, total, url))
            conn.commit()

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_tasks WHERE id = ?
            """, (task_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def update(self, task_id: str, data: Dict[str, Any]) -> bool:
        allowed_fields = {"status", "current_step", "current", "total", "current_url", "result", "error", "progress", "total_chunks", "completed_chunks"}
        data["updated_at"] = datetime.now().isoformat()
        data = {k: v for k, v in data.items() if k in allowed_fields}

        if not data:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [task_id]

        with self._get_connection() as conn:
            conn.execute(f"""
                UPDATE processing_tasks SET {set_clause} WHERE id = ?
            """, values)
            conn.commit()
            return conn.total_changes > 0

    def update_chunks_info(self, task_id: str, total_chunks: int, completed_chunks: int = 0) -> bool:
        """更新 chunks 总数和已完成数量，并计算进度"""
        # 进度计算：parsing(10%) + semantic_chunk(10%) + shadow_writing(60%) + quality_check(20%)
        progress = self._calculate_progress_from_chunks(total_chunks, completed_chunks)
        return self.update(task_id, {
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks,
            "status": TaskStatus.SHADOW_WRITING.value,
            "current_step": f"生成影子跟读 (0/{total_chunks})",
            "progress": progress
        })

    def increment_completed_chunk(self, task_id: str) -> int:
        """已完成 chunks 数量原子性加1，返回新的完成数量"""
        task = self.get(task_id)
        if not task:
            return 0

        current = task.get("completed_chunks", 0) + 1
        total = task.get("total_chunks", 1)

        # 进度计算
        progress = self._calculate_progress_from_chunks(total, current)

        # 原子性更新：使用 SQL 的 SET 表达式，而不是应用层计算
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE processing_tasks
                SET completed_chunks = completed_chunks + 1,
                    progress = ?,
                    current_step = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                progress,
                f"生成影子跟读 ({current}/{total})",
                datetime.now().isoformat(),
                task_id
            ))
            conn.commit()

        # 返回更新后的值（可能不是精确值，但至少不会丢失）
        updated_task = self.get(task_id)
        return updated_task.get("completed_chunks", 0) if updated_task else current

    def _calculate_progress_from_chunks(self, total_chunks: int, completed_chunks: int) -> int:
        """根据 chunks 完成数量计算进度 (0-100)"""
        if total_chunks <= 0:
            return 0

        chunk_progress = completed_chunks / total_chunks

        # 进度分配：
        # parsing: 0-10%
        # semantic_chunk: 10-20%
        # shadow_writing: 20-80%
        # quality_check: 80-100%

        shadow_progress = int(chunk_progress * 60)  # 占 60%
        return 20 + shadow_progress  # 从 20% 开始

    def update_progress(self, task_id: str, status: str, current: int, total: int, current_step: Optional[str] = None) -> bool:
        progress = self._calculate_progress(status, current, total)
        return self.update(task_id, {
            "status": status,
            "current": current,
            "total": total,
            "current_step": current_step or self._default_step_desc(status),
            "progress": progress
        })

    def _calculate_progress(self, status: str, current: int = 0, total: int = 0) -> int:
        """根据状态计算进度 (0-100)
        
        进度分配：
        - pending: 0%
        - parsing: 10%
        - semantic_chunk: 20%
        - shadow_writing: 20%-80% (由 update_chunks_info/increment_completed_chunk 计算)
        - quality_check: 80%-100%
        - completed: 100%
        - failed: 100%
        """
        if status == TaskStatus.SHADOW_WRITING.value:
            if total > 0 and current > 0:
                chunk_pct = current / total
                return int(20 + chunk_pct * 60)
            return 20

        base = {
            "pending": 0,
            "parsing": 10,
            "semantic_chunk": 20,
            "shadow_writing": 20,
            "quality_check": 80,
            "completed": 100,
            "failed": 100
        }.get(status, 0)

        return base

    def _default_step_desc(self, status: str) -> str:
        desc = {
            "pending": "等待开始",
            "parsing": "解析文件",
            "semantic_chunk": "语义分块",
            "shadow_writing": "生成影子跟读",
            "quality_check": "质量检查",
            "completed": "完成",
            "failed": "失败"
        }
        return desc.get(status, status)

    def delete(self, task_id: str) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM processing_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return conn.total_changes > 0

    def list_all(self, limit: int = 100) -> list:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_tasks ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_completed(self, older_than_hours: int = 24) -> int:
        import time
        threshold = time.time() - older_than_hours * 3600
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM processing_tasks
                WHERE status IN ('completed', 'failed')
                AND created_at < ?
            """, (datetime.fromtimestamp(threshold).isoformat(),))
            conn.commit()
            return cursor.rowcount


task_db = TaskDB()
