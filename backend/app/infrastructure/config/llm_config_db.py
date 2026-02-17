import sqlite3
from typing import Optional, List
from app.infrastructure.config.llm_config import LLMConfig, LLMProvider
from app.infrastructure.config.encryption import EncryptionService
import json
import os


class LLMConfigDB:
    """SQLite 配置存储（支持多 Key 加密存储）"""

    def __init__(self, db_path: str = None, encryption_key: str = None):
        db_path = db_path or os.path.join(
            os.path.dirname(__file__), "../../../data/llm_config.db"
        )
        self.db_path = db_path
        self.encryption = EncryptionService(encryption_key)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL UNIQUE,
                model TEXT NOT NULL DEFAULT '',
                temperature REAL DEFAULT 0.1,
                max_tokens INTEGER DEFAULT 4096,
                top_p REAL DEFAULT 1.0,
                frequency_penalty REAL DEFAULT 0.0,
                response_format TEXT,
                api_keys_encrypted TEXT,
                api_key_env TEXT,
                rotation_enabled INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save_api_keys(self, provider: str, keys: List[str], rotation_enabled: bool = False) -> None:
        """保存多个 API Key（加密存储）"""
        encrypted = self.encryption.encrypt_keys(keys)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO llm_configs
            (provider, model, api_keys_encrypted, rotation_enabled, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(provider) DO UPDATE SET
                api_keys_encrypted = excluded.api_keys_encrypted,
                rotation_enabled = excluded.rotation_enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (provider, "", encrypted, int(rotation_enabled)))
        conn.commit()
        conn.close()

    def get_api_keys(self, provider: str) -> Optional[List[str]]:
        """获取指定 Provider 的 API Keys（解密）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT api_keys_encrypted FROM llm_configs WHERE provider = ?", (provider,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return self.encryption.decrypt_keys(row[0])
        return None

    def get_rotation_enabled(self, provider: str) -> bool:
        """获取指定 Provider 的轮换开关状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT rotation_enabled FROM llm_configs WHERE provider = ?", (provider,))
        row = cursor.fetchone()
        conn.close()
        return bool(row[0]) if row else False

    def is_rotation_enabled(self, provider: str) -> bool:
        """检查是否启用 API Key 轮换"""
        return self.get_rotation_enabled(provider)

    def save_config(self, config: LLMConfig, api_key: str = None):
        """保存配置（兼容旧方法 - 单个 Key）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        api_key_encrypted = None
        if api_key:
            api_key_encrypted = self.encryption.encrypt_single_key(api_key)

        cursor.execute("""
            INSERT OR REPLACE INTO llm_configs
            (provider, model, temperature, max_tokens, top_p,
             frequency_penalty, response_format, api_key_encrypted, api_key_env, enabled, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config.provider.value,
            config.model,
            config.temperature,
            config.max_tokens,
            config.top_p,
            config.frequency_penalty,
            json.dumps(config.response_format) if config.response_format else None,
            api_key_encrypted,
            config.api_key_env,
            int(config.enabled),
            int(config.is_default),
        ))
        conn.commit()
        conn.close()

    def get_config(self, provider: str) -> Optional[LLMConfig]:
        """获取指定 Provider 的配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM llm_configs WHERE provider = ? AND enabled = 1", (provider,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return LLMConfig(
                id=row[0],
                provider=LLMProvider(row[1]),
                model=row[2],
                temperature=row[3],
                max_tokens=row[4],
                top_p=row[5],
                frequency_penalty=row[6],
                response_format=json.loads(row[7]) if row[7] else None,
                api_key_env=row[9],
                enabled=bool(row[10]),
                is_default=bool(row[11]),
            )
        return None

    def get_api_key(self, provider: str) -> Optional[str]:
        """获取指定 Provider 的 API Key（兼容旧方法 - 解密单个 Key）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT api_key_encrypted FROM llm_configs WHERE provider = ?", (provider,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return self.encryption.decrypt_single_key(row[0])
        return None

    def set_api_key(self, provider: str, api_key: str):
        """设置指定 Provider 的 API Key（兼容旧方法 - 加密单个 Key）"""
        encrypted = self.encryption.encrypt_single_key(api_key)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE llm_configs SET api_key_encrypted = ? WHERE provider = ?", (encrypted, provider))
        conn.commit()
        conn.close()

    def list_all(self) -> List[LLMConfig]:
        """列出所有配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM llm_configs WHERE enabled = 1 ORDER BY provider")
        rows = cursor.fetchall()
        conn.close()

        return [
            LLMConfig(
                id=row[0],
                provider=LLMProvider(row[1]),
                model=row[2],
                temperature=row[3],
                max_tokens=row[4],
                top_p=row[5],
                frequency_penalty=row[6],
                response_format=json.loads(row[7]) if row[7] else None,
                api_key_env=row[9],
                enabled=bool(row[10]),
                is_default=bool(row[11]),
            )
            for row in rows
        ]


_llm_config_db: Optional[LLMConfigDB] = None


def get_llm_config_db() -> LLMConfigDB:
    """获取全局 LLMConfigDB 实例"""
    global _llm_config_db
    if _llm_config_db is None:
        _llm_config_db = LLMConfigDB()
    return _llm_config_db
