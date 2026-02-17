from cryptography.fernet import Fernet
import os
import json
from typing import List, Optional


class EncryptionService:
    """API Key 加密服务（支持单个 Key 和 JSON 数组）"""

    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or os.getenv("LLM_ENCRYPTION_KEY", "") or ""
        if not self.secret_key:
            self.secret_key = Fernet.generate_key().decode()
            print(f"[WARNING] New encryption key generated: {self.secret_key}")
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        key = self.secret_key
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)

    def encrypt(self, data: str) -> str:
        """加密单个字符串"""
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密单个字符串"""
        return self._fernet.decrypt(encrypted_data.encode()).decode()

    def encrypt_keys(self, keys: List[str]) -> str:
        """
        加密 API Keys 列表

        Args:
            keys: API Key 列表

        Returns:
            加密后的 Base64 字符串
        """
        json_str = json.dumps(keys)
        return self.encrypt(json_str)

    def decrypt_keys(self, encrypted_data: str) -> List[str]:
        """
        解密 API Keys 列表

        Args:
            encrypted_data: 加密后的 Base64 字符串

        Returns:
            API Key 列表
        """
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)

    def encrypt_single_key(self, key: str) -> str:
        """加密单个 API Key（兼容旧方法）"""
        return self.encrypt(key)

    def decrypt_single_key(self, encrypted_data: str) -> str:
        """解密单个 API Key（兼容旧方法）"""
        return self.decrypt(encrypted_data)
