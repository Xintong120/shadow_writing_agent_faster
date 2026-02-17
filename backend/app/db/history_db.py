"""历史学习记录数据库操作模块"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union


class LearningStatus:
    """学习状态常量"""
    TODO = "todo"              # 待学习
    IN_PROGRESS = "in_progress"  # 学习中
    COMPLETED = "completed"    # 已完成


class HistoryDB:
    """历史学习记录数据库操作类"""

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
                CREATE TABLE IF NOT EXISTS learning_history (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    ted_title TEXT,
                    ted_speaker TEXT,
                    ted_url TEXT,
                    ted_duration TEXT,
                    ted_views TEXT,
                    result TEXT NOT NULL,
                    transcript TEXT,
                    status TEXT DEFAULT 'todo',
                    learned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_id ON learning_history(task_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_learned_at ON learning_history(learned_at DESC)
            """)
            conn.commit()
            
        self._migrate_add_status_column()
        self._create_status_index()
        self._migrate_add_core_arguments_column()

    def _migrate_add_status_column(self):
        """迁移：添加 status 列（如果不存在）"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    ALTER TABLE learning_history ADD COLUMN status TEXT DEFAULT 'todo'
                """)
                conn.commit()
        except sqlite3.OperationalError:
            pass

    def _create_status_index(self):
        """创建 status 索引（如果不存在）"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status ON learning_history(status)
                """)
                conn.commit()
        except sqlite3.OperationalError:
            pass

    def _migrate_add_core_arguments_column(self):
        """迁移：添加 core_arguments 列（如果不存在）"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    ALTER TABLE learning_history ADD COLUMN core_arguments TEXT
                """)
                conn.commit()
        except sqlite3.OperationalError:
            pass

    def create(
        self,
        record_id: str,
        task_id: str,
        ted_title: str,
        ted_speaker: str,
        ted_url: str,
        result: Dict[str, Any],
        ted_duration: Optional[str] = None,
        ted_views: Optional[str] = None,
        transcript: Optional[str] = None
    ) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO learning_history
                (id, task_id, ted_title, ted_speaker, ted_url, ted_duration, ted_views, result, transcript)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id, task_id, ted_title, ted_speaker, ted_url,
                ted_duration, ted_views,
                json.dumps(result, ensure_ascii=False),
                transcript
            ))
            conn.commit()

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM learning_history WHERE id = ?
            """, (record_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def get_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM learning_history WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def list_all(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取历史学习记录列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            status: 过滤状态 (todo/in_progress/completed)，None 表示全部
        """
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute("""
                    SELECT * FROM learning_history
                    WHERE status = ?
                    ORDER BY learned_at DESC
                    LIMIT ? OFFSET ?
                """, (status, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT * FROM learning_history
                    ORDER BY learned_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update_user_practice(self, task_id: str, user_practice: List[Dict[str, Any]]) -> bool:
        """更新用户练习内容"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT result FROM learning_history WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            result = json.loads(row['result']) if row['result'] else {}
            result['user_practice'] = user_practice
            
            conn.execute("""
                UPDATE learning_history 
                SET result = ? 
                WHERE task_id = ?
            """, (json.dumps(result, ensure_ascii=False), task_id))
            conn.commit()
            return True

    def get_user_practice(self, task_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取用户练习内容"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT result FROM learning_history WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            if row:
                result = json.loads(row['result']) if row['result'] else {}
                return result.get('user_practice')
            return None

    def count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM learning_history")
            return cursor.fetchone()["cnt"]

    def delete(self, record_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM learning_history WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_older_than(self, days: int = 30) -> int:
        threshold = datetime.now().timestamp() - days * 24 * 3600
        threshold_date = datetime.fromtimestamp(threshold).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM learning_history WHERE created_at < ?", (threshold_date,))
            conn.commit()
            return cursor.rowcount

    def update_status(self, task_id: str, status: str) -> bool:
        """更新学习状态
        
        Args:
            task_id: 任务ID
            status: 新状态 (todo/in_progress/completed)
        
        Returns:
            是否更新成功
        """
        if status not in [LearningStatus.TODO, LearningStatus.IN_PROGRESS, LearningStatus.COMPLETED]:
            return False
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE learning_history SET status = ? WHERE task_id = ?
            """, (status, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_status(self, task_id: str) -> Optional[str]:
        """获取学习状态"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT status FROM learning_history WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            return row["status"] if row else None

    def get_by_title(self, ted_title: str) -> Optional[Dict[str, Any]]:
        """根据标题查询学习记录"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM learning_history WHERE ted_title = ? LIMIT 1
            """, (ted_title,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def update_core_arguments(self, task_id: str, core_arguments: str) -> bool:
        """更新核心观点
        
        Args:
            task_id: 任务ID
            core_arguments: 提取的核心观点
            
        Returns:
            是否更新成功
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE learning_history SET core_arguments = ? WHERE task_id = ?
            """, (core_arguments, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_core_arguments(self, task_id: str) -> Optional[str]:
        """获取核心观点"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT core_arguments FROM learning_history WHERE task_id = ?
            """, (task_id,))
            row = cursor.fetchone()
            return row["core_arguments"] if row and row["core_arguments"] else None

    def _row_to_dict(self, row) -> Dict[str, Any]:
        result = dict(row)
        if result.get("result"):
            try:
                result["result"] = json.loads(result["result"])
            except json.JSONDecodeError:
                pass
        return result


history_db = HistoryDB()
