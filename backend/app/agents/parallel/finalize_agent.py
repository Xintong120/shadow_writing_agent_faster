# finalize_agent.py
# 并行处理的Finalize Agent

from app.state import ChunkProcessState


def finalize_single_chunk(state: ChunkProcessState) -> dict:
    """
    汇总单个Chunk的最终结果（并行版本）
    
    【关键】：只返回final_shadow_chunks，不返回其他字段以避免并发写入冲突
    """
    chunk_id = state.get("chunk_id", 0)
    
    # 优先使用修正后的结果
    final_result = state.get("corrected_shadow") or state.get("validated_shadow")
    
    if final_result:
        print(f"[Pipeline {chunk_id}] [OK] Finalized")
        # 【重要】只返回final_shadow_chunks，避免并发写入主State的其他字段
        return {"final_shadow_chunks": [final_result]}
    else:
        print(f"[Pipeline {chunk_id}] [ERROR] No valid result")
        return {"final_shadow_chunks": []}
