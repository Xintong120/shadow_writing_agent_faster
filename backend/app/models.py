# models.py
# 作用：Pydantic数据模型定义
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class TedTxt:
    """TED文本文件数据结构 / TED Transcript Data Structure"""
    title: str
    speaker: str
    url: str
    duration: str
    views: int
    transcript: str

class Ted_Shadows(BaseModel):
    """TED句子改写数据模型 / TED Sentence Shadow Writing Data Model"""
    original: str = Field(..., min_length=12, description="原始TED句子 / Original TED sentence")
    imitation: str = Field(..., min_length=12, description="话题迁移后的句子 / Topic-migrated sentence")
    map: dict = Field(..., description="词汇映射字典 / Vocabulary mapping dictionary")
    paragraph: str = Field(..., min_length=10, description="原始段落 / Original paragraph")
    quality_score: float = Field(default=6.0, ge=0, le=8, description="质量评分 / Quality score")

    @field_validator('original')
    @classmethod
    def validate_original(cls, v):
        word_count = len(v.split())
        if word_count < 8:
            raise ValueError("原始句子应包含至少8个单词")
        return v.strip()

    @field_validator('imitation')
    @classmethod
    def validate_imitation(cls, v):
        word_count = len(v.split())
        if word_count < 8:
            raise ValueError("迁移句子应包含至少8个单词")
        return v.strip()

    @field_validator('map')
    @classmethod
    def validate_map(cls, v):
        if not isinstance(v, dict):
            raise ValueError("映射必须是字典格式")
        if len(v) < 2:
            raise ValueError("至少需要2个词汇映射")
        for key, values in v.items():
            if not isinstance(values, list) or len(values) < 1:
                raise ValueError(f"词汇'{key}'的同义词列表至少包含1个词")
        return v

class Ted_Shadows_Result(BaseModel):
    """TED句子改写结果数据模型 / TED Sentence Shadow Writing Result Data Model"""
    original: str = Field(..., min_length=12, description="完整原句 / Complete original sentence")
    imitation: str = Field(..., min_length=12, description="话题迁移后的新句 / Topic-migrated new sentence")
    map: Dict[str, List[str]] = Field(..., description="词汇映射字典 / Vocabulary mapping dictionary")
    paragraph: str = Field(..., min_length=10, description="原始段落 / Original paragraph")
    quality_score: float = Field(default=6.0, ge=0, le=8, description="质量评分 / Quality score")

    @field_validator('original')
    @classmethod
    def validate_original(cls, v):
        if not v or len(v.strip()) < 12:
            raise ValueError("原句长度至少12个字符")
        word_count = len(v.split())
        if word_count < 8:
            raise ValueError("原句应包含至少8个单词")
        return v.strip()

    @field_validator('imitation')
    @classmethod
    def validate_imitation(cls, v):
        if not v or len(v.strip()) < 12:
            raise ValueError("迁移句长度至少12个字符")
        word_count = len(v.split())
        if word_count < 8:
            raise ValueError("迁移句应包含至少8个单词")
        return v.strip()

    @field_validator('map')
    @classmethod
    def validate_map(cls, v):
        if not isinstance(v, dict):
            raise ValueError("映射必须是字典格式")
        # 放宽验证：只要有映射即可，不强制要求每个词都有2个同义词
        for key, values in v.items():
            if not isinstance(values, list) or len(values) < 1:
                raise ValueError(f"词汇'{key}'的同义词列表至少包含1个词")
        return v


# ============ API请求/响应模型 ============

class SearchRequest(BaseModel):
    """搜索TED演讲请求 / Search TED Talks Request"""
    topic: str = Field(..., min_length=1, max_length=200, description="搜索主题 / Search topic")
    user_id: Optional[str] = Field(default="default", description="用户ID / User ID")


class TEDCandidate(BaseModel):
    """TED演讲候选 / TED Talk Candidate"""
    title: str = Field(..., description="演讲标题 / Talk title")
    speaker: str = Field(..., description="演讲者 / Speaker")
    url: str = Field(..., description="TED URL / TED URL")
    duration: str = Field(default="", description="时长 / Duration")
    views: Optional[str] = Field(default=None, description="观看次数 / View count")
    description: Optional[str] = Field(default="", description="简介 / Description")
    relevance_score: Optional[float] = Field(default=0.0, description="相关性评分 / Relevance score")


class SearchResponse(BaseModel):
    """搜索响应结果模型 / Search Response Model"""
    success: bool = Field(..., description="是否成功 / Success status")
    candidates: List[TEDCandidate] = Field(default_factory=list, description="候选列表 / Candidate list")
    search_context: Dict = Field(default_factory=dict, description="搜索上下文 / Search context")
    total: int = Field(default=0, description="结果总数 / Total results")


class BatchProcessRequest(BaseModel):
    """批量处理请求 / Batch Process Request"""
    urls: List[str] = Field(description="TED URL列表（1-10个） / TED URLs (1-10)")
    user_id: Optional[str] = Field(default="default", description="用户ID / User ID")


class BatchProcessResponse(BaseModel):
    """批量处理响应 / Batch Process Response"""
    success: bool = Field(..., description="是否成功 / Success status")
    task_id: str = Field(..., description="任务ID（第一个URL） / Task ID (first URL)")
    task_ids: List[str] = Field(..., description="所有URL的任务ID列表 / Task IDs for all URLs")
    total: int = Field(..., description="URL总数 / Total URLs")
    message: str = Field(..., description="提示信息 / Message")


class TaskStatusResponse(BaseModel):
    """任务状态响应 / Task Status Response (轮询方式)"""
    task_id: str
    status: str
    current_step: Optional[str] = None
    progress: int = 0
    total: int = 0
    current: int = 0
    current_url: Optional[str] = None
    result: Optional[List[Dict]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    total_chunks: int = 0
    completed_chunks: int = 0


class TaskCreateResponse(BaseModel):
    """任务创建响应 / Task Create Response"""
    success: bool
    task_id: str
    ted_info: Optional[Dict] = None
    message: str


class TaskDeleteResponse(BaseModel):
    """任务删除响应 / Task Delete Response"""
    success: bool
    message: str


class HistoryListResponse(BaseModel):
    """历史列表响应 / History List Response"""
    success: bool
    records: List[Dict]
    total: int


class HistoryDetailResponse(BaseModel):
    """历史详情响应 / History Detail Response"""
    success: bool
    record: Optional[Dict] = None


# ============ 生词本模型 ============

class VocabWord(BaseModel):
    """生词数据模型"""
    id: str = Field(..., description="唯一标识")
    word: str = Field(..., description="单词")
    definition: str = Field(..., description="释义")
    dictionary: str = Field(..., description="来源词典")
    added_at: float = Field(..., description="添加时间戳")


class AddVocabRequest(BaseModel):
    """批量添加生词请求"""
    words: List[VocabWord] = Field(..., description="生词列表")


class VocabResponse(BaseModel):
    """生词列表响应"""
    words: List[VocabWord]
    total: int
