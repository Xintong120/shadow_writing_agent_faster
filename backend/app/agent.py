# agent.py
# 作用：TED Agent核心逻辑封装
# 功能：
#   - 提供process_ted_text()函数供main.py调用
#   - 使用workflows.py中定义的工作流
#   - 返回结构化结果

import asyncio
import time
from app.workflows import create_parallel_shadow_writing_workflow
from app.state import Shadow_Writing_State
from typing import cast
from langchain_core.runnables import RunnableConfig


# 暴露给main.py的处理函数
def process_ted_text(
    text: str,
    target_topic: str = "",
    ted_title: str | None = None,
    ted_speaker: str | None = None,
    ted_url: str | None = None
) -> dict:
    """
    处理TED文本的主函数
    
    Args:
        text: TED演讲文本
        target_topic: 目标话题（可选）
        ted_title: TED演讲标题（可选）
        ted_speaker: TED演讲者（可选）
        ted_url: TED演讲URL（可选）
        
    Returns:
        dict: 包含处理结果的字典
    """
    
    # 创建并行工作流（推荐）
    workflow = create_parallel_shadow_writing_workflow()
    # workflow = create_shadow_writing_workflow()  # 旧版串行（已弃用）
    
    # 初始状态（并行版本简化）
    initial_state = {
        "text": text,
        "target_topic": target_topic,
        "ted_title": ted_title,
        "ted_speaker": ted_speaker,
        "ted_url": ted_url,        
        "semantic_chunks": [],
        "final_shadow_chunks": [],  # 并行版本：operator.add自动汇总
        "current_node": "",
        "error_message": None
    }
    
    # 获取全局Langfuse处理器
    from app.main import langfuse_handler

    # 运行并行工作流（带Langfuse监控）
    if langfuse_handler:
        config = cast(RunnableConfig, {"callbacks": [langfuse_handler]})
        result = workflow.invoke(cast(Shadow_Writing_State, initial_state), config=config)
    else:
        result = workflow.invoke(cast(Shadow_Writing_State, initial_state))
    
    # 提取最终结果
    final = result.get("final_shadow_chunks", [])
    
    # 处理返回值：final 可能是字典列表或对象列表
    results = []
    for item in final:
        if isinstance(item, dict):
            results.append(item)
        elif hasattr(item, 'dict'):
            results.append(item.dict())
        elif hasattr(item, 'model_dump'):
            results.append(item.model_dump())
        else:
            results.append(str(item))
    
    return {
        "success": True,
        "results": results,
        "result_count": len(results)
    }


async def process_ted_text_stream(
    text: str,
    target_topic: str = "",
    ted_title: str | None = None,
    ted_speaker: str | None = None,
    ted_url: str | None = None,
    task_id: str | None = None
):
    """
    异步流式处理TED文本

    Args:
        text: TED演讲文本
        target_topic: 目标话题（可选）
        ted_title: TED演讲标题（可选）
        ted_speaker: TED演讲者（可选）
        ted_url: TED演讲URL（可选）
        task_id: 任务ID（用于SSE推送）

    Yields:
        流式输出每个完成的chunk结果
    """

    workflow = create_parallel_shadow_writing_workflow()

    initial_state = {
        "text": text,
        "target_topic": target_topic,
        "ted_title": ted_title,
        "ted_speaker": ted_speaker,
        "ted_url": ted_url,
        "task_id": task_id,  # 传递task_id给子图
        "semantic_chunks": [],
        "final_shadow_chunks": [],
        "current_node": "",
        "error_message": None
    }

    # 获取全局Langfuse处理器
    from app.main import langfuse_handler

    # 使用astream()进行异步流式执行
    config = cast(RunnableConfig, {"callbacks": [langfuse_handler]}) if langfuse_handler else None

    print(f"[STREAM_DEBUG] Starting astream for task_id: {task_id}")
    print(f"[STREAM_DEBUG] Initial state keys: {list(initial_state.keys())}")
    print(f"[STREAM_DEBUG] Semantic chunks count: {len(initial_state.get('semantic_chunks', []))}")
    print(f"[STREAM_DEBUG] 开始时间: {time.strftime('%H:%M:%S', time.localtime(time.time()))}")

    try:
        async for event in workflow.astream(
            cast(Shadow_Writing_State, initial_state),
            config=config,
            stream_mode=["updates", "custom"],  # 同时监听状态更新和自定义数据
            subgraphs=True  # 关键：包含子图输出，这样finalize_agent中的流式数据才能传递出来
        ):
            print(f"[STREAM_DEBUG] Received event: {event}")
            print(f"[STREAM_DEBUG] Event type: {type(event)}, length: {len(event) if isinstance(event, tuple) else 'Not tuple'}")

            # 处理astream的实际返回值格式
            metadata = None  # 初始化metadata
            if isinstance(event, tuple):
                if len(event) == 2:
                    mode, data = event
                    print(f"[STREAM_DEBUG] Unpacked as (mode, data): mode={mode}, data_type={type(data)}")
                elif len(event) == 3:
                    mode, data, metadata = event
                    print(f"[STREAM_DEBUG] Unpacked as (mode, data, metadata): mode={mode}, data_type={type(data)}")
                else:
                    print(f"[STREAM_DEBUG] Unexpected tuple length: {len(event)}, full event: {event}")
                    continue
            else:
                # 单值模式
                data = event
                mode = "unknown"
                print(f"[STREAM_DEBUG] Single value mode, data_type={type(data)}")

            if data == "custom" and metadata is not None:  # 自定义流式数据 (修正：检查data而不是mode，确保metadata存在)
                chunk_data = metadata  # 修正：使用metadata而不是data
                print(f"[STREAM_DEBUG] Custom data keys: {list(chunk_data.keys()) if isinstance(chunk_data, dict) else 'Not dict'}")

                if chunk_data.get("type") == "chunk_completed":
                        chunk_receive_time = time.time()
                        print(f"[STREAM_DEBUG] 收到chunk_completed - chunk_id: {chunk_data.get('chunk_id')}, 时间: {time.strftime('%H:%M:%S', time.localtime(chunk_receive_time))}")
                        print(f"[STREAM_DEBUG] 从astream开始到收到消息耗时: {chunk_receive_time - time.time() + 1:.3f}秒")  # 近似值

                        # 增强调试日志 - 记录chunk原始时间戳和当前接收时间
                        original_timestamp = chunk_data.get("timestamp", 0)
                        if original_timestamp > 0:
                            time_diff = chunk_receive_time - original_timestamp
                            print(f"[STREAM_DEBUG] Chunk原始完成时间: {time.strftime('%H:%M:%S', time.localtime(original_timestamp))}")
                            print(f"[STREAM_DEBUG] 从chunk完成到astream接收延迟: {time_diff:.6f}秒")

                        # 转发给SSE管理器
                        if task_id:
                            print(f"[SSE] About to call sse_manager.add_message for task_id: {task_id}")
                            try:
                                from app.sse_manager import sse_manager
                                # 序列化Ted_Shadows对象为字典
                                result_data = chunk_data["result"]
                                if hasattr(result_data, 'model_dump'):
                                    serialized_result = result_data.model_dump()
                                elif hasattr(result_data, 'dict'):
                                    serialized_result = result_data.dict()
                                else:
                                    serialized_result = str(result_data)

                                sse_add_start_time = time.time()
                                print(f"[SSE] 调用sse_manager.add_message - chunk_id: {chunk_data['chunk_id']}, 时间: {time.strftime('%H:%M:%S', time.localtime(sse_add_start_time))}")

                                await sse_manager.add_message(task_id, {
                                    "type": "chunk_completed",
                                    "chunk_id": chunk_data["chunk_id"],
                                    "result": serialized_result,
                                    "timestamp": chunk_data["timestamp"]
                                })

                                sse_add_end_time = time.time()
                                print(f"[SSE] Message sent successfully for chunk {chunk_data['chunk_id']}")
                                print(f"[SSE] sse_manager.add_message调用耗时: {sse_add_end_time - sse_add_start_time:.6f}秒")
                                print(f"[SSE] 从chunk完成到SSE缓存总延迟: {sse_add_end_time - original_timestamp:.6f}秒")
                            except Exception as e:
                                print(f"[SSE] Error sending message: {e}")
                                import traceback
                                traceback.print_exc()

                        yield chunk_data  # 返回给调用方

            elif mode == "updates":  # 状态更新
                print(f"[STREAM] State update received")
                # 可以处理其他状态更新...
                pass

    except Exception as e:
        print(f"[STREAM] Error in astream: {e}")
        import traceback
        traceback.print_exc()
        raise
