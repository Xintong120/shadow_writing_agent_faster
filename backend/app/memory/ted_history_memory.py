"""TED History Memory - TED观看历史管理"""

from typing import Dict, Any, Optional, Set
from datetime import datetime
from app.memory.base_memory import BaseMemory

class TEDHistoryMemory(BaseMemory):
    """TED观看历史管理
    
    负责记录用户看过的TED演讲，用于去重和个性化推荐
    """
    
    NAMESPACE_TYPE = "ted_history"
    
    def get_seen_urls(self, user_id: str) -> Set[str]:
        """获取用户看过的TED URL列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            URL集合
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        items = self.store.search(namespace)
        
        return {item.value.get("url") for item in items if item.value.get("url")}
    
    def add_seen_ted(
        self, 
        user_id: str, 
        url: str, 
        title: str,
        speaker: str,
        search_topic: str,
        chunks_processed: int = 0,
        shadow_writing_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加TED观看记录
        
        Args:
            user_id: 用户ID
            url: TED URL
            title: 演讲标题
            speaker: 演讲者
            search_topic: 搜索主题
            chunks_processed: 处理的语义块数量
            shadow_writing_count: 成功生成的Shadow Writing数量
            metadata: 额外元数据
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        
        # 使用URL的hash作为key（避免URL过长）
        key = self.hash_string(url)
        
        memory_data = {
            "url": url,
            "title": title,
            "speaker": speaker,
            "watched_at": datetime.now().isoformat(),
            "search_topic": search_topic,
            "chunks_processed": chunks_processed,
            "shadow_writing_count": shadow_writing_count,
            "metadata": metadata or {}
        }
        
        self.store.put(namespace, key, memory_data)
    
    def is_seen(self, user_id: str, url: str) -> bool:
        """检查TED是否已观看
        
        Args:
            user_id: 用户ID
            url: TED URL
            
        Returns:
            是否已观看
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        key = self.hash_string(url)
        
        item = self.store.get(namespace, key)
        return item is not None
    
    def get_ted_info(self, user_id: str, url: str) -> Optional[Dict[str, Any]]:
        """获取TED详细信息
        
        Args:
            user_id: 用户ID
            url: TED URL
            
        Returns:
            TED信息字典，如果不存在返回None
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        key = self.hash_string(url)
        
        item = self.store.get(namespace, key)
        return item.value if item else None
    
    def update_processing_stats(
        self,
        user_id: str,
        url: str,
        chunks_processed: int,
        shadow_writing_count: int
    ) -> None:
        """更新处理统计数据
        
        Args:
            user_id: 用户ID
            url: TED URL
            chunks_processed: 处理的语义块数量
            shadow_writing_count: 成功生成的数量
        """
        ted_info = self.get_ted_info(user_id, url)
        
        if ted_info:
            ted_info["chunks_processed"] = chunks_processed
            ted_info["shadow_writing_count"] = shadow_writing_count
            
            namespace = (user_id, self.NAMESPACE_TYPE)
            key = self.hash_string(url)
            self.store.put(namespace, key, ted_info)
