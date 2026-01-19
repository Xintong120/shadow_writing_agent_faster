# 作用：定义所有LangGraph工作流

from langgraph.graph import StateGraph, END, START
from langgraph.types import Send
from app.state import Shadow_Writing_State, ChunkProcessState
# 共用组件
from app.agents.shared.semantic_chunking import Semantic_Chunking_Agent
""" ----------------------------------------------------------- """
# 串行工作流agents（已弃用，保留以备回退）
from app.agents.serial.sentence_shadow_writing import TED_shadow_writing_agent
from app.agents.serial.validation import validation_agent
from app.agents.serial.quality import quality_agent
from app.agents.serial.correction import correction_agent
from app.agents.serial.finalize import finalize_agent
from app.agents.serial.communication import communication_agent


def create_search_workflow():
    """
    创建搜索工作流
    
    功能：搜索TED演讲，返回候选列表
    
    流程：
    START → communication_agent → END
    
    Returns:
        编译后的工作流
    """
    builder = StateGraph(Shadow_Writing_State)
    
    # 添加communication节点
    builder.add_node("communication", communication_agent)
    
    # 设置路径
    builder.add_edge(START, "communication")
    builder.add_edge("communication", END)
    
    return builder.compile()


def create_shadow_writing_workflow():
    """
    创建Shadow Writing工作流
    
    功能：处理单个TED文本，生成shadow writing结果
    
    流程：
    START → semantic_chunking → sentence_shadow_writing 
          → validation → quality → [correction] → finalize → END
    
    Returns:
        编译后的工作流
    """
    builder = StateGraph(Shadow_Writing_State)
    
    # 添加所有处理节点
    builder.add_node("semantic_chunking", Semantic_Chunking_Agent())
    builder.add_node("sentence_shadow_writing", TED_shadow_writing_agent)
    builder.add_node("validation", validation_agent)
    builder.add_node("quality", quality_agent)
    builder.add_node("correction", correction_agent)
    builder.add_node("finalize", finalize_agent)
    
    # 条件路由函数
    def should_correct(state: Shadow_Writing_State) -> str:
        """决定是否需要修正"""
        validated_chunks = state.get("validated_shadow_chunks", [])
        quality_chunks = state.get("quality_shadow_chunks", [])
        
        # 如果有被拒绝的语块，进入修正流程
        if len(validated_chunks) > len(quality_chunks):
            return "correction"
        else:
            return "finalize"
    
    # 设置工作流路径
    builder.add_edge(START, "semantic_chunking")
    builder.add_edge("semantic_chunking", "sentence_shadow_writing")
    builder.add_edge("sentence_shadow_writing", "validation")
    builder.add_edge("validation", "quality")
    
    # 条件路由：quality → correction 或 finalize
    builder.add_conditional_edges(
        "quality",
        should_correct,
        {
            "correction": "correction",
            "finalize": "finalize"
        }
    )
    
    # correction 后回到 finalize
    builder.add_edge("correction", "finalize")
    builder.add_edge("finalize", END)
    
    return builder.compile()


def create_full_workflow():
    """
    创建完整的端到端工作流（包含搜索）
    
    功能：从搜索到Shadow Writing的完整流程
    
    流程：
    START → communication → [等待用户选择] 
          → semantic_chunking → sentence_shadow_writing 
          → validation → quality → [correction] → finalize → END
    
    注意：此工作流需要外部处理用户选择逻辑
    当前版本不使用此工作流，而是分离为search + shadow_writing两个工作流
    
    Returns:
        编译后的工作流
    """
    builder = StateGraph(Shadow_Writing_State)
    
    # 添加所有节点
    builder.add_node("communication", communication_agent)
    builder.add_node("semantic_chunking", Semantic_Chunking_Agent())
    builder.add_node("sentence_shadow_writing", TED_shadow_writing_agent)
    builder.add_node("validation", validation_agent)
    builder.add_node("quality", quality_agent)
    builder.add_node("correction", correction_agent)
    builder.add_node("finalize", finalize_agent)
    
    # 条件路由函数
    def has_user_selection(state: Shadow_Writing_State) -> str:
        """检查是否有用户选择"""
        if state.get("selected_ted_url"):
            return "continue"
        else:
            return "wait"
    
    def should_correct(state: Shadow_Writing_State) -> str:
        """决定是否需要修正"""
        validated_chunks = state.get("validated_shadow_chunks", [])
        quality_chunks = state.get("quality_shadow_chunks", [])
        
        if len(validated_chunks) > len(quality_chunks):
            return "correction"
        else:
            return "finalize"
    
    # 设置工作流路径
    builder.add_edge(START, "communication")
    
    # Communication后等待用户选择
    builder.add_conditional_edges(
        "communication",
        has_user_selection,
        {
            "continue": "semantic_chunking",
            "wait": END  # 返回候选列表，等待用户选择
        }
    )
    
    builder.add_edge("semantic_chunking", "sentence_shadow_writing")
    builder.add_edge("sentence_shadow_writing", "validation")
    builder.add_edge("validation", "quality")
    
    builder.add_conditional_edges(
        "quality",
        should_correct,
        {
            "correction": "correction",
            "finalize": "finalize"
        }
    )
    
    builder.add_edge("correction", "finalize")
    builder.add_edge("finalize", END)
    
    return builder.compile()


# ============================================================
# 并行处理工作流（使用Send API + operator.add）
# ============================================================

def create_chunk_pipeline():
    """
    创建单个Chunk的处理流水线子图
    
    功能：处理单个语义块，完成完整的Shadow Writing流程
    
    流程：
    START → shadow_writing → validation → quality → [correction] → finalize_chunk → END
    
    Returns:
        编译后的子图工作流
    """
    # 并行工作流agents（当前使用）
    from app.agents.parallel.shadow_writing_agent import shadow_writing_single_chunk
    from app.agents.parallel.validation_agent import validation_single_chunk
    from app.agents.parallel.quality_agent import quality_single_chunk
    from app.agents.parallel.correction_agent import correction_single_chunk
    from app.agents.parallel.finalize_agent import finalize_single_chunk
    
    pipeline = StateGraph(ChunkProcessState)
    
    # 添加所有处理节点
    pipeline.add_node("shadow_writing", shadow_writing_single_chunk)
    pipeline.add_node("validation", validation_single_chunk)
    pipeline.add_node("quality", quality_single_chunk)
    pipeline.add_node("correction", correction_single_chunk)
    pipeline.add_node("finalize_chunk", finalize_single_chunk)
    
    # 条件路由函数
    def should_correct(state: ChunkProcessState) -> str:
        """决定是否需要修正"""
        if not state.get("quality_passed", False):
            return "correction"
        else:
            return "finalize_chunk"
    
    # 设置流水线路径
    pipeline.add_edge(START, "shadow_writing")
    pipeline.add_edge("shadow_writing", "validation")
    pipeline.add_edge("validation", "quality")
    
    # 条件路由：quality → correction 或 finalize_chunk
    pipeline.add_conditional_edges(
        "quality",
        should_correct,
        {
            "correction": "correction",
            "finalize_chunk": "finalize_chunk"
        }
    )
    
    pipeline.add_edge("correction", "finalize_chunk")
    pipeline.add_edge("finalize_chunk", END)
    
    return pipeline.compile()


def create_parallel_shadow_writing_workflow():
    """
    创建并行Shadow Writing工作流（使用Send API）
    
    功能：处理TED文本，为每个语义块创建独立的处理流水线
    
    流程：
    START → semantic_chunking → [动态分发到多个chunk_pipeline] → aggregate_results → END
    
    关键技术：
    1. 使用Send API动态为每个chunk创建独立流水线
    2. 使用operator.add自动汇总所有结果
    3. 每个chunk独立运行完整的 shadow_writing→validation→quality→correction→finalize 流程
    
    Returns:
        编译后的并行工作流
    """
    builder = StateGraph(Shadow_Writing_State)
    
    # 1. 语义分块节点（保持不变）
    builder.add_node("semantic_chunking", Semantic_Chunking_Agent())
    
    # 2. Chunk处理流水线（子图）
    # 因为子图的final_shadow_chunks使用operator.add，结果会自动合并到主State
    chunk_pipeline = create_chunk_pipeline()
    builder.add_node("chunk_pipeline", chunk_pipeline)
    
    # 4. 动态分发函数（关键）
    def continue_to_pipelines(state: Shadow_Writing_State):
        """
        为每个语义块创建独立的处理流水线

        使用Send API动态分发，LangGraph会自动并行处理
        """
        semantic_chunks = state.get("semantic_chunks", [])
        task_id = state.get("task_id")

        print(f"\n[PARALLEL WORKFLOW] 准备并行处理 {len(semantic_chunks)} 个语义块")
        print(f"[PARALLEL WORKFLOW] task_id: {task_id}")
        print(f"[PARALLEL WORKFLOW] state keys: {list(state.keys())}")

        # 推送并行处理开始消息
        if task_id:
            import asyncio
            from app.sse_manager import sse_manager
            asyncio.create_task(
                sse_manager.add_message(task_id, {
                    "type": "chunks_processing_started",
                    "total_chunks": len(semantic_chunks),
                    "message": f"开始并行处理 {len(semantic_chunks)} 个语义块"
                })
            )
            print(f"[PARALLEL WORKFLOW] 推送并行处理开始消息到task_id: {task_id}")

        # 为每个chunk创建一个Send指令
        # 【重要】ChunkProcessState与主State共享final_shadow_chunks字段，使用operator.add自动合并
        total_chunks = len(semantic_chunks)
        return [
            Send(
                "chunk_pipeline",
                {
                    "chunk_text": chunk,
                    "chunk_id": i,
                    "task_id": task_id,  # 传递task_id用于进度推送
                    "total_chunks": total_chunks,  # 传递总数用于进度计算
                    # 初始化ChunkProcessState字段
                    "raw_shadow": None,
                    "validated_shadow": None,
                    "quality_passed": False,
                    "quality_score": 0.0,
                    "quality_detail": None,
                    "corrected_shadow": None,
                    "final_shadow_chunks": [],  # 初始化为空列表
                    "error": None
                }
            )
            for i, chunk in enumerate(semantic_chunks)
        ]
    
    # 3. 设置工作流路径
    builder.add_edge(START, "semantic_chunking")
    
    # 关键：使用conditional_edges + Send动态分发
    builder.add_conditional_edges(
        "semantic_chunking",
        continue_to_pipelines,
        ["chunk_pipeline"]
    )
    
    # 所有chunk_pipeline完成后，operator.add自动合并结果到final_shadow_chunks，直接结束
    builder.add_edge("chunk_pipeline", END)
    
    return builder.compile()
