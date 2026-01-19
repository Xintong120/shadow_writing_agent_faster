"""Memory Service - 统一Memory管理入口

使用Facade模式，协调各个子Memory服务
"""

from typing import Optional, List, Dict, Any, Set
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from app.memory.ted_history_memory import TEDHistoryMemory
from app.memory.search_history_memory import SearchHistoryMemory
from app.memory.learning_records_memory import LearningRecordsMemory

class MemoryService:
    """Memory统一管理服务（Facade模式）
    
    协调各个子Memory服务，提供统一接口
    """
    
    def __init__(self, store: Optional[BaseStore] = None):
        """初始化Memory Service
        
        Args:
            store: LangGraph Store实例，如果为None则使用InMemoryStore
        """
        if store is None:
            store = InMemoryStore()
        
        # 初始化子服务
        self.ted_history = TEDHistoryMemory(store)
        self.search_history = SearchHistoryMemory(store)
        self.learning_records = LearningRecordsMemory(store)
    
    # ========== TED观看历史 - 委托给ted_history子服务 ==========
    
    def get_seen_ted_urls(self, user_id: str) -> Set[str]:
        """获取用户看过的TED URL列表"""
        return self.ted_history.get_seen_urls(user_id)
    
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
        """添加TED观看记录"""
        return self.ted_history.add_seen_ted(
            user_id=user_id,
            url=url,
            title=title,
            speaker=speaker,
            search_topic=search_topic,
            chunks_processed=chunks_processed,
            shadow_writing_count=shadow_writing_count,
            metadata=metadata
        )
    
    def is_ted_seen(self, user_id: str, url: str) -> bool:
        """检查TED是否已观看"""
        return self.ted_history.is_seen(user_id, url)
    
    def get_ted_info(self, user_id: str, url: str) -> Optional[Dict[str, Any]]:
        """获取TED详细信息"""
        return self.ted_history.get_ted_info(user_id, url)
    
    def update_ted_processing_stats(
        self,
        user_id: str,
        url: str,
        chunks_processed: int,
        shadow_writing_count: int
    ) -> None:
        """更新TED处理统计"""
        return self.ted_history.update_processing_stats(
            user_id=user_id,
            url=url,
            chunks_processed=chunks_processed,
            shadow_writing_count=shadow_writing_count
        )
    
    # ========== 搜索历史 - 委托给search_history子服务 ==========
    
    def add_search_history(
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
        """添加搜索历史记录"""
        return self.search_history.add_search(
            user_id=user_id,
            original_query=original_query,
            optimized_query=optimized_query,
            alternative_queries=alternative_queries,
            results_count=results_count,
            selected_url=selected_url,
            selected_title=selected_title,
            new_results=new_results,
            filtered_seen=filtered_seen,
            search_duration_ms=search_duration_ms
        )
    
    def get_recent_searches(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的搜索历史"""
        return self.search_history.get_recent_searches(user_id, limit)
    
    def update_search_selected_url(
        self,
        user_id: str,
        search_id: str,
        selected_url: str,
        selected_title: str
    ) -> None:
        """更新搜索记录的选择结果"""
        return self.search_history.update_selected_url(
            user_id=user_id,
            search_id=search_id,
            selected_url=selected_url,
            selected_title=selected_title
        )
    
    # ========== 学习记录 - 委托给learning_records子服务 ==========
    
    def add_learning_record(
        self,
        user_id: str,
        ted_url: str,
        ted_title: str,
        ted_speaker: str,
        original: str,
        imitation: str,
        word_map: Dict[str, List[str]],
        paragraph: str,
        quality_score: float,
        tags: Optional[List[str]] = None
    ) -> str:
        """添加Shadow Writing学习记录"""
        return self.learning_records.add_record(
            user_id=user_id,
            ted_url=ted_url,
            ted_title=ted_title,
            ted_speaker=ted_speaker,
            original=original,
            imitation=imitation,
            word_map=word_map,
            paragraph=paragraph,
            quality_score=quality_score,
            tags=tags
        )
    
    def add_batch_learning_records(
        self,
        user_id: str,
        ted_url: str,
        ted_title: str,
        ted_speaker: str,
        shadow_writings: List[Dict[str, Any]],
        default_tags: Optional[List[str]] = None
    ) -> List[str]:
        """批量添加Shadow Writing学习记录
        
        Args:
            user_id: 用户ID
            ted_url: TED URL
            ted_title: TED标题
            ted_speaker: 演讲者
            shadow_writings: Shadow Writing列表
            default_tags: 默认标签（两级：[search_topic, ted_title]）
            
        Returns:
            记录ID列表
        """
        return self.learning_records.add_batch_records(
            user_id=user_id,
            ted_url=ted_url,
            ted_title=ted_title,
            ted_speaker=ted_speaker,
            shadow_writings=shadow_writings,
            default_tags=default_tags
        )
    
    def get_learning_records(
        self,
        user_id: str,
        limit: int = 50,
        ted_url: Optional[str] = None,
        min_quality: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """获取学习记录
        
        Args:
            user_id: 用户ID
            limit: 返回数量
            ted_url: 按TED URL过滤
            min_quality: 最小质量分数
            tags: 按标签过滤（支持一级/二级标签）
            
        Returns:
            学习记录列表
        """
        return self.learning_records.get_records(
            user_id=user_id,
            limit=limit,
            ted_url=ted_url,
            min_quality=min_quality,
            tags=tags
        )
    
    def get_learning_record_by_id(
        self,
        user_id: str,
        record_id: str
    ) -> Optional[Dict[str, Any]]:
        """根据ID获取单条学习记录"""
        return self.learning_records.get_record_by_id(user_id, record_id)
    
    def get_learning_stats(self, user_id: str) -> Dict[str, Any]:
        """获取学习统计"""
        return self.learning_records.get_stats(user_id)
    
    def delete_learning_record(self, user_id: str, record_id: str) -> bool:
        """删除学习记录"""
        return self.learning_records.delete_record(user_id, record_id)
