"""Learning Records Memory - Shadow Writing学习记录管理"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from app.memory.base_memory import BaseMemory

class LearningRecordsMemory(BaseMemory):
    """Shadow Writing学习记录管理
    
    负责记录用户的Shadow Writing学习成果
    
    数据结构：
    {
        "record_id": "uuid",
        "ted_url": "https://ted.com/talks/...",
        "ted_title": "演讲标题",
        "ted_speaker": "演讲者",
        "original": "原始句子",
        "imitation": "改写句子",
        "map": {"category": ["word1", "word2"]},
        "paragraph": "原始段落",
        "quality_score": 7.5,
        "learned_at": "2025-10-10T09:00:00",
        "tags": [
            "leadership",              # 一级标签：search_topic
            "How to be a great leader" # 二级标签：ted_title
        ]
    }
    """
    
    NAMESPACE_TYPE = "shadow_writing_records"
    
    def add_record(
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
        """添加Shadow Writing学习记录
        
        Args:
            user_id: 用户ID
            ted_url: TED演讲URL
            ted_title: TED演讲标题
            ted_speaker: 演讲者
            original: 原始句子
            imitation: 改写后的句子
            word_map: 词汇映射字典
            paragraph: 原始段落
            quality_score: 质量评分（0-8）
            tags: 两级标签列表 [search_topic, ted_title]
            
        Returns:
            记录ID（UUID）
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        record_id = str(uuid.uuid4())
        
        record_data = {
            "record_id": record_id,
            "ted_url": ted_url,
            "ted_title": ted_title,
            "ted_speaker": ted_speaker,
            "original": original,
            "imitation": imitation,
            "map": word_map,
            "paragraph": paragraph,
            "quality_score": quality_score,
            "learned_at": datetime.now().isoformat(),
            "tags": tags or []
        }
        
        self.store.put(namespace, record_id, record_data)
        return record_id
    
    def add_batch_records(
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
            ted_url: TED演讲URL
            ted_title: TED演讲标题
            ted_speaker: 演讲者
            shadow_writings: Shadow Writing列表
            default_tags: 默认标签（两级：[search_topic, ted_title]）
            
        Returns:
            记录ID列表
        """
        record_ids = []
        base_tags = default_tags or []
        
        for sw in shadow_writings:
            # 合并默认标签和shadow_writing自带的标签（如果有）
            sw_tags = sw.get("tags", [])
            final_tags = list(set(base_tags + sw_tags))  # 去重
            
            record_id = self.add_record(
                user_id=user_id,
                ted_url=ted_url,
                ted_title=ted_title,
                ted_speaker=ted_speaker,
                original=sw.get("original", ""),
                imitation=sw.get("imitation", ""),
                word_map=sw.get("map", {}),
                paragraph=sw.get("paragraph", ""),
                quality_score=sw.get("quality_score", 6.0),
                tags=final_tags
            )
            record_ids.append(record_id)
        
        return record_ids
    
    def get_records(
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
            limit: 返回数量限制（默认50）
            ted_url: 按TED URL过滤（可选）
            min_quality: 最小质量分数过滤（可选）
            tags: 按标签过滤（可选，支持一级或二级标签）
            
        Returns:
            学习记录列表（按时间倒序）
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        items = self.store.search(namespace)
        
        # 提取所有记录
        records = [item.value for item in items]
        
        # 应用过滤条件
        if ted_url:
            records = [r for r in records if r.get("ted_url") == ted_url]
        
        if min_quality is not None:
            records = [r for r in records if r.get("quality_score", 0) >= min_quality]
        
        if tags:
            # 支持按一级标签（search_topic）或二级标签（ted_title）过滤
            records = [
                r for r in records 
                if any(tag in r.get("tags", []) for tag in tags)
            ]
        
        # 按时间倒序排序
        records.sort(key=lambda x: x.get("learned_at", ""), reverse=True)
        
        return records[:limit]
    
    def get_record_by_id(
        self,
        user_id: str,
        record_id: str
    ) -> Optional[Dict[str, Any]]:
        """根据ID获取单条学习记录
        
        Args:
            user_id: 用户ID
            record_id: 记录ID
            
        Returns:
            学习记录字典，如果不存在返回None
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        item = self.store.get(namespace, record_id)
        return item.value if item else None
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取学习统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计数据字典
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        items = self.store.search(namespace)
        
        records = [item.value for item in items]
        
        if not records:
            return {
                "total_records": 0,
                "avg_quality_score": 0.0,
                "top_tags": [],
                "records_by_ted": {},
                "recent_activity": None,
                "quality_trend": []
            }
        
        # 计算统计数据
        total_records = len(records)
        avg_quality = sum(r.get("quality_score", 0) for r in records) / total_records
        
        # 标签统计
        from collections import Counter
        all_tags = []
        for r in records:
            all_tags.extend(r.get("tags", []))
        tag_counts = Counter(all_tags)
        top_tags = [tag for tag, count in tag_counts.most_common(10)]
        
        # 按TED分组统计
        ted_counts = Counter(r.get("ted_url") for r in records)
        records_by_ted = {
            url: {
                "count": count,
                "title": next((r.get("ted_title") for r in records if r.get("ted_url") == url), "")
            }
            for url, count in ted_counts.most_common(10)
        }
        
        # 最近活动
        records.sort(key=lambda x: x.get("learned_at", ""), reverse=True)
        recent_activity = records[0].get("learned_at") if records else None
        
        # 质量趋势（最近20条）
        recent_records = records[:20]
        quality_trend = [
            {
                "learned_at": r.get("learned_at"),
                "quality_score": r.get("quality_score")
            }
            for r in reversed(recent_records)  # 从旧到新
        ]
        
        return {
            "total_records": total_records,
            "avg_quality_score": round(avg_quality, 2),
            "top_tags": top_tags,
            "records_by_ted": records_by_ted,
            "recent_activity": recent_activity,
            "quality_trend": quality_trend
        }
    
    def delete_record(
        self,
        user_id: str,
        record_id: str
    ) -> bool:
        """删除学习记录
        
        Args:
            user_id: 用户ID
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        namespace = (user_id, self.NAMESPACE_TYPE)
        try:
            # LangGraph Store的delete方法
            # 注意：InMemoryStore可能不支持delete，需要验证
            # 这里假设有delete方法，如果没有则需要其他方式实现
            self.store.delete(namespace, record_id)
            return True
        except Exception as e:
            print(f"删除记录失败: {e}")
            return False
    
