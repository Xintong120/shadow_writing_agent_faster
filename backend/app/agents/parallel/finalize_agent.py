# finalize_agent.py
# 并行处理的Finalize Agent

from app.state import ChunkProcessState
from langgraph.config import get_stream_writer
import time


def finalize_single_chunk(state: ChunkProcessState) -> dict:
    """
    汇总单个Chunk的最终结果（并行版本）

    【新增】：使用LangGraph流式输出在chunk完成时立即推送结果
    【关键】：只返回final_shadow_chunks，不返回其他字段以避免并发写入冲突
    """
    chunk_id = state.get("chunk_id", 0)
    task_id = state.get("task_id")

    # 优先使用修正后的结果
    final_result = state.get("corrected_shadow") or state.get("validated_shadow")

    if final_result:
        completion_time = time.time()
        formatted_time = time.strftime('%H:%M:%S', time.localtime(completion_time))
        print(f"[Pipeline {chunk_id}] [OK] Finalized - 时间: {formatted_time}")
        print(f"[CHUNK_DEBUG] Chunk {chunk_id} 完成 - task_id: {task_id}, 时间戳: {completion_time}")

        # 【关键】使用LangGraph流式输出推送chunk完成消息
        writer = get_stream_writer()
        chunk_data = {
            "type": "chunk_completed",
            "chunk_id": chunk_id,
            "task_id": task_id,
            "result": final_result,  # 完整的shadow writing结果
            "timestamp": completion_time
        }

        # 增强调试日志 - 记录消息发送的精确时间
        message_send_time = time.time()
        print(f"[CHUNK_DEBUG] 发送chunk_completed消息 - chunk_id: {chunk_id}, 消息时间戳: {completion_time}")
        print(f"[CHUNK_DEBUG] LangGraph writer调用时间: {time.strftime('%H:%M:%S', time.localtime(message_send_time))}")
        print(f"[CHUNK_DEBUG] 从chunk完成到消息发送延迟: {message_send_time - completion_time:.6f}秒")

        writer(chunk_data)

        # 【重要】只返回final_shadow_chunks，避免并发写入主State的其他字段
        return {"final_shadow_chunks": [final_result]}
    else:
        print(f"[Pipeline {chunk_id}] [ERROR] No valid result - 时间: {time.strftime('%H:%M:%S', time.localtime(time.time()))}")
        print(f"[CHUNK_DEBUG] Chunk {chunk_id} 失败 - task_id: {task_id}, 时间戳: {time.time()}")
        return {"final_shadow_chunks": []}
