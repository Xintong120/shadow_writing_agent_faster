"""Search History Memory - 搜索历史管理"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from app.memory.base_memory import BaseMemory

class SearchHistoryMemory(BaseMemory):
    """搜索历史管理
    
    负责记录用户的搜索行为，用于分析和优化搜索体验
    """
    
    NAMESPACE_TYPE = "search_history"
    
    def add_search(
        self,
        user_id: str,
        original_query: str,
        optimized_query: str,
        alternative_queries: List[str],
        results_count: int,
        selected_url: Optional[str] = None,
        selected_title: Optional[str] = None,
        new_results: int = 0,
        filtered_seen: int = 0,
        search_duration_ms: int = 0
    ) -> str:
        """添加搜索历史记录
        
        Args:
            user_id: 用户ID
            original_query: 原始搜索词
            optimized_query: 优化后的搜索词
            alternative_queries: 备选搜索词列表
            results_count: 搜索结果数量
            selected_url: 用户选择的URL
            selected_title: 用户选择的标题
            new_results: 去重后的新结果数
            filtered_seen: 被过滤的已看过数量
            search_duration_ms: 搜索耗时（毫秒）
            
        Returns:
            记录ID（UUID）
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        key = str(uuid.uuid4())
        
        memory_data = {
            "original_query": original_query,
            "optimized_query": optimized_query,
            "alternative_queries": alternative_queries,
            "results_count": results_count,
            "selected_url": selected_url,
            "selected_title": selected_title,
            "searched_at": datetime.now().isoformat(),
            "search_duration_ms": search_duration_ms,
            "new_results": new_results,
            "filtered_seen": filtered_seen
        }
        
        self.store.put(namespace, key, memory_data)
        return key
    
    def get_recent_searches(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取最近的搜索历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            搜索历史列表（按时间倒序）
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        items = self.store.search(namespace)
        
        # 按时间倒序排序
        sorted_items = sorted(
            items, 
            key=lambda x: x.value.get("searched_at", ""),
            reverse=True
        )
        
        return [item.value for item in sorted_items[:limit]]
    
    def update_selected_url(
        self,
        user_id: str,
        search_id: str,
        selected_url: str,
        selected_title: str
    ) -> None:
        """更新搜索记录的选择结果
        
        Args:
            user_id: 用户ID
            search_id: 搜索记录ID
            selected_url: 用户选择的URL
            selected_title: 用户选择的标题
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        item = self.store.get(namespace, search_id)
        
        if item:
            search_data = item.value
            search_data["selected_url"] = selected_url
            search_data["selected_title"] = selected_title
            self.store.put(namespace, search_id, search_data)
