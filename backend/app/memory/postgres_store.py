"""SQLite Store实现
用于Electron桌面应用的本地数据持久化
"""

import json
import sqlite3
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path
from langgraph.store.base import BaseStore, Item


class SQLiteStore(BaseStore):
    """SQLite本地存储Store
    
    适用场景：
    - Electron桌面应用
    - 单机应用
    - 需要数据持久化但不需要服务器
    
    优点：
    - 无需安装数据库服务
    - 单文件数据库（易于备份）
    - 跨平台支持
    - 轻量级（~1MB）
    """
    
    def __init__(self, db_path: str = None):
        """初始化SQLite Store
        
        Args:
            db_path: 数据库文件路径，默认为用户数据目录
        """
        if db_path is None:
            # 自动选择用户数据目录
            db_path = self._get_default_db_path()
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        print(f"[SQLiteStore] 数据库位置: {self.db_path}")
    
    def _get_default_db_path(self) -> Path:
        """获取默认数据库路径（用户数据目录）"""
        import platform
        
        system = platform.system()
        home = Path.home()
        
        if system == "Windows":
            data_dir = home / "AppData" / "Roaming" / "TED-Shadow-Writing"
        elif system == "Darwin":  # macOS
            data_dir = home / "Library" / "Application Support" / "TED-Shadow-Writing"
        else:  # Linux
            data_dir = home / ".config" / "TED-Shadow-Writing"
        
        return data_dir / "shadow_writing.db"
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            # 创建store表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS store (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (namespace, key)
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_namespace 
                ON store(namespace)
            """)
            
            conn.commit()
    
    def put(
        self,
        namespace: Tuple[str, ...],
        key: str,
        value: Dict[str, Any]
    ) -> None:
        """存储数据"""
        namespace_str = json.dumps(namespace)
        value_str = json.dumps(value, ensure_ascii=False)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO store (namespace, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (namespace_str, key, value_str))
            conn.commit()
    
    def get(
        self,
        namespace: Tuple[str, ...],
        key: str
    ) -> Optional[Item]:
        """获取单条数据"""
        namespace_str = json.dumps(namespace)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT namespace, key, value, created_at, updated_at
                FROM store
                WHERE namespace = ? AND key = ?
            """, (namespace_str, key))
            
            row = cursor.fetchone()
            
            if row:
                return Item(
                    value=json.loads(row['value']),
                    key=row['key'],
                    namespace=tuple(json.loads(row['namespace'])),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            
            return None
    
    def search(
        self,
        namespace_prefix: Tuple[str, ...]
    ) -> List[Item]:
        """搜索数据"""
        prefix_str = json.dumps(namespace_prefix)
        
        with self._get_connection() as conn:
            # 使用LIKE匹配namespace前缀
            cursor = conn.execute("""
                SELECT namespace, key, value, created_at, updated_at
                FROM store
                WHERE namespace LIKE ?
                ORDER BY updated_at DESC
            """, (f'{prefix_str[:-1]}%',))  # 去掉最后的]，用%匹配
            
            rows = cursor.fetchall()
            
            return [
                Item(
                    value=json.loads(row['value']),
                    key=row['key'],
                    namespace=tuple(json.loads(row['namespace'])),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]
    
    def delete(
        self,
        namespace: Tuple[str, ...],
        key: str
    ) -> None:
        """删除数据"""
        namespace_str = json.dumps(namespace)
        
        with self._get_connection() as conn:
            conn.execute("""
                DELETE FROM store
                WHERE namespace = ? AND key = ?
            """, (namespace_str, key))
            conn.commit()
    
    def list_namespaces(
        self,
        prefix: Optional[Tuple[str, ...]] = None
    ) -> List[Tuple[str, ...]]:
        """列出所有命名空间"""
        with self._get_connection() as conn:
            if prefix:
                prefix_str = json.dumps(prefix)
                cursor = conn.execute("""
                    SELECT DISTINCT namespace
                    FROM store
                    WHERE namespace LIKE ?
                """, (f'{prefix_str[:-1]}%',))
            else:
                cursor = conn.execute("""
                    SELECT DISTINCT namespace
                    FROM store
                """)
            
            rows = cursor.fetchall()
            return [tuple(json.loads(row['namespace'])) for row in rows]
    
    def backup(self, backup_path: str = None):
        """备份数据库
        
        Args:
            backup_path: 备份文件路径，默认为同目录_backup.db
        """
        if backup_path is None:
            backup_path = str(self.db_path).replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        print(f"[SQLiteStore] 备份完成: {backup_path}")
        return backup_path
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM store")
            total_records = cursor.fetchone()['count']
            
            cursor = conn.execute("SELECT COUNT(DISTINCT namespace) as count FROM store")
            total_namespaces = cursor.fetchone()['count']
            
            # 数据库文件大小
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return {
                "total_records": total_records,
                "total_namespaces": total_namespaces,
                "db_size_bytes": db_size,
                "db_size_mb": round(db_size / 1024 / 1024, 2),
                "db_path": str(self.db_path)
            }
