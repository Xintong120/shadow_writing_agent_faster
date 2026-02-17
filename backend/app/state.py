# state.py - 工作流状态定义

from typing import TypedDict, List, Optional, Annotated
import operator
from app.models import Ted_Shadows

class Shadow_Writing_State(TypedDict):
    """shadow writing工作流状态"""

    topic: Optional[str]                   # 用户输入的搜索主题
    user_id: Optional[str]                 # 用户ID（用于memory namespace）
    task_id: Optional[str]                 # 任务ID（用于SSE进度推送）
    
    # Communication结果
    ted_candidates: Optional[List[dict]]   # 搜索到的TED演讲候选列表
    selected_ted_url: Optional[str]        # 用户选择的TED URL
    awaiting_user_selection: Optional[bool] # 是否等待用户选择
    search_context: Optional[dict]         # 搜索上下文（原始topic、优化query等）
    file_path: Optional[str]               # 保存的TED文件路径
    
    # 输入
    text: str                              # 原始TED文本
    target_topic: Optional[str]
    ted_title: Optional[str]
    ted_speaker: Optional[str]
    ted_url: Optional[str]          
    
    # 语义分块结果
    semantic_chunks: List[str]             # 语义块列表
    
    # 并行处理：使用operator.add自动汇总所有chunk的结果
    final_shadow_chunks: Annotated[List[Ted_Shadows], operator.add]  # 自动合并结果
    
    # 元数据
    current_node: str                      # 当前节点名称
    processing_logs: Optional[List[str]]   # 处理日志
    errors: Optional[List[str]]            # 错误列表
    error_message: Optional[str]           # 错误信息


# 新增：单个Chunk的处理状态（用于子图）
class ChunkProcessState(TypedDict):
    """单个语义块的处理状态

    【重要】不要包含 task_id 等需要 SSE 推送的字段，避免并发写入冲突
    task_id 和 total_chunks 只在子图节点中作为局部变量使用
    """

    # 输入
    chunk_text: str                        # 当前语义块文本
    chunk_id: int                          # 块ID（用于日志追踪）

    # 处理流程中间状态
    raw_shadow: Optional[dict]             # Shadow Writing原始结果
    validated_shadow: Optional[Ted_Shadows] # 验证通过的结果
    quality_passed: bool                   # 质量检查是否通过
    quality_score: float                   # 质量分数
    quality_detail: Optional[dict]         # 质量评估详情
    corrected_shadow: Optional[Ted_Shadows] # 修正后的结果

    # 最终输出（会被operator.add合并到主State的final_shadow_chunks）
    final_shadow_chunks: Annotated[List[Ted_Shadows], operator.add]  # 与主State同名！

    # 错误处理
    error: Optional[str]                   # 错误信息
