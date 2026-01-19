"""Base Memory - Memory操作基类"""

from langgraph.store.base import BaseStore
import hashlib

class BaseMemory:
    """Memory操作基类
    
    提供通用的Store访问和工具方法
    """
    
    def __init__(self, store: BaseStore):
        """初始化Memory
        
        Args:
            store: LangGraph Store实例
        """
        self.store = store
    
    @staticmethod
    def hash_string(text: str, length: int = 16) -> str:
        """生成字符串的hash值
        
        Args:
            text: 需要hash的字符串
            length: hash长度（默认16位）
            
        Returns:
            SHA256 hash的前N位
        """
        return hashlib.sha256(text.encode()).hexdigest()[:length]
