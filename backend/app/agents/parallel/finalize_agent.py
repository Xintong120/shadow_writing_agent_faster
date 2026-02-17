# finalize_agent.py
# 并行处理的Finalize Agent

from app.state import ChunkProcessState
from langgraph.config import get_stream_writer
import time


def finalize_single_chunk(state: ChunkProcessState) -> dict:
    """汇总单个Chunk的最终结果（并行版本）"""
    chunk_id = state.get("chunk_id", 0)

    final_result = state.get("corrected_shadow") or state.get("validated_shadow")

    if final_result:
        completion_time = time.time()
        formatted_time = time.strftime('%H:%M:%S', time.localtime(completion_time))
        print(f"[Pipeline {chunk_id}] [OK] Finalized - 时间: {formatted_time}")

        # 从全局变量获取任务信息
        from app.workflows import get_current_task_info
        task_id, total_chunks = get_current_task_info()
        print(f"[CHUNK_DEBUG] Chunk {chunk_id} 完成 - task_id: {task_id}, 时间戳: {completion_time}")

        # 成功后更新数据库进度（只在这里更新一次）
        completed_chunks = 0
        if task_id:
            try:
                from app.db import task_db
                completed_chunks = task_db.increment_completed_chunk(task_id)
                print(f"[CHUNK_DEBUG] 更新完成数: {completed_chunks}/{total_chunks}")
            except Exception as e:
                print(f"[CHUNK_DEBUG] 更新数据库失败: {e}")

        if hasattr(final_result, 'model_dump'):
            serialized_result = final_result.model_dump()
        elif hasattr(final_result, 'dict'):
            serialized_result = final_result.dict()
        elif isinstance(final_result, dict):
            serialized_result = final_result
        else:
            serialized_result = str(final_result)

        writer = get_stream_writer()
        chunk_data = {
            "type": "chunk_completed",
            "chunk_id": chunk_id,
            "task_id": task_id,
            "result": serialized_result,
            "timestamp": completion_time,
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks
        }

        message_send_time = time.time()
        print(f"[CHUNK_DEBUG] 发送chunk_completed消息 - chunk_id: {chunk_id}, 消息时间戳: {completion_time}")
        print(f"[CHUNK_DEBUG] LangGraph writer调用时间: {time.strftime('%H:%M:%S', time.localtime(message_send_time))}")
        print(f"[CHUNK_DEBUG] 从chunk完成到消息发送延迟: {message_send_time - completion_time:.6f}秒")

        writer(chunk_data)

        return {"final_shadow_chunks": [final_result]}
    else:
        print(f"[Pipeline {chunk_id}] [ERROR] No valid result - 时间: {time.strftime('%H:%M:%S', time.localtime(time.time()))}")
        from app.workflows import get_current_task_info
        task_id, total_chunks = get_current_task_info()
        print(f"[CHUNK_DEBUG] Chunk {chunk_id} 失败 - task_id: {task_id}, 时间戳: {time.time()}")
        return {"final_shadow_chunks": []}
