# workflows.py
# LangGraph 工作流定义

from langgraph.graph import StateGraph, END, START
from langgraph.types import Send
from app.state import Shadow_Writing_State, ChunkProcessState
from app.agents.shared.semantic_chunking import Semantic_Chunking_Agent
from app.agents.communication_agent import communication_agent
from app.agents.parallel.shadow_writing_agent import shadow_writing_single_chunk
from app.agents.parallel.validation_agent import validation_single_chunk
from app.agents.parallel.quality_agent import quality_single_chunk
from app.agents.parallel.correction_agent import correction_single_chunk
from app.agents.parallel.finalize_agent import finalize_single_chunk

_current_task_id = None
_current_total_chunks = 0


def create_chunk_pipeline():
    """创建单个 Chunk 的处理流水线子图"""
    pipeline = StateGraph(ChunkProcessState)

    pipeline.add_node("shadow_writing", shadow_writing_single_chunk)
    pipeline.add_node("validation", validation_single_chunk)
    pipeline.add_node("quality", quality_single_chunk)
    pipeline.add_node("correction", correction_single_chunk)
    pipeline.add_node("finalize_chunk", finalize_single_chunk)

    def should_correct(state: ChunkProcessState) -> str:
        return "correction" if not state.get("quality_passed", False) else "finalize_chunk"

    pipeline.add_edge(START, "shadow_writing")
    pipeline.add_edge("shadow_writing", "validation")
    pipeline.add_edge("validation", "quality")
    pipeline.add_conditional_edges(
        "quality", should_correct,
        {"correction": "correction", "finalize_chunk": "finalize_chunk"}
    )
    pipeline.add_edge("correction", "finalize_chunk")
    pipeline.add_edge("finalize_chunk", END)

    return pipeline.compile()


def create_parallel_shadow_writing_workflow():
    """并行 Shadow Writing 工作流"""
    global _current_task_id, _current_total_chunks

    builder = StateGraph(Shadow_Writing_State)

    builder.add_node("semantic_chunking", Semantic_Chunking_Agent())
    chunk_pipeline = create_chunk_pipeline()
    builder.add_node("chunk_pipeline", chunk_pipeline)

    def continue_to_pipelines(state: Shadow_Writing_State):
        semantic_chunks = state.get("semantic_chunks", [])
        global _current_task_id, _current_total_chunks
        _current_task_id = state.get("task_id")
        _current_total_chunks = len(semantic_chunks)

        print(f"[WORKFLOW DEBUG] continue_to_pipelines - task_id: {_current_task_id}")
        print(f"[WORKFLOW DEBUG] semantic_chunks count: {_current_total_chunks}")

        return [
            Send(
                "chunk_pipeline",
                {
                    "chunk_text": chunk,
                    "chunk_id": i,
                    "raw_shadow": None,
                    "validated_shadow": None,
                    "quality_passed": False,
                    "quality_score": 0.0,
                    "quality_detail": None,
                    "corrected_shadow": None,
                    "final_shadow_chunks": [],
                    "error": None
                }
            )
            for i, chunk in enumerate(semantic_chunks)
        ]

    builder.add_edge(START, "semantic_chunking")
    builder.add_conditional_edges("semantic_chunking", continue_to_pipelines, ["chunk_pipeline"])
    builder.add_edge("chunk_pipeline", END)

    return builder.compile()


def get_current_task_info():
    """获取当前任务的 task_id 和 total_chunks"""
    global _current_task_id, _current_total_chunks
    return _current_task_id, _current_total_chunks


def create_search_workflow():
    """搜索工作流"""
    builder = StateGraph(Shadow_Writing_State)
    builder.add_node("communication", communication_agent)
    builder.add_edge(START, "communication")
    builder.add_edge("communication", END)
    return builder.compile()
