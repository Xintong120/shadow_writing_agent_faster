# batch_processor.py
# 作用：批量处理多个TED URLs的核心逻辑

from typing import List
from app.task_manager import task_manager
from app.sse_manager import sse_manager
from app.tools.ted_transcript_tool import extract_ted_transcript
from app.workflows import create_parallel_shadow_writing_workflow
from app.enums import TaskStatus, MessageType, ProcessingStep
from app.db import task_db, history_db, TaskStatus as DBTaskStatus
from langchain_core.runnables import RunnableConfig
from typing import cast
from app.state import Shadow_Writing_State


async def process_urls_batch(task_id: str, urls: List[str]):
    """
    批量异步处理多个TED URLs

    流程：
    1. 遍历每个URL
    2. 提取transcript
    3. 运行Shadow Writing工作流
    4. 实时推送进度
    5. 收集结果

    Args:
        task_id: 任务ID
        urls: TED URL列表
    """
    import time
    start_time = time.time()

    total = len(urls)
    task_manager.update_status(task_id, TaskStatus.PROCESSING)

    print(f"\n[BATCH PROCESSOR] 开始处理 {total} 个URLs - 开始时间: {time.strftime('%H:%M:%S')}")

    # 初始化数据库状态
    task_db.update(task_id, {
        "status": DBTaskStatus.PENDING.value,
        "current_step": "准备处理",
        "total": total,
        "progress": 0
    })

    # 发送开始消息
    print(f"[BATCH_PROCESSOR] [{task_id}] 准备发送started消息 - 时间: {time.strftime('%H:%M:%S')}")
    await sse_manager.add_message(
        task_id,
        {
            "type": MessageType.STARTED.value,
            "total": total,
            "message": f"开始处理 {total} 个TED演讲"
        }
    )
    print(f"[BATCH_PROCESSOR] [{task_id}] started消息发送完成 - 时间: {time.strftime('%H:%M:%S')}")
    
    # 创建Shadow Writing工作流（并行版本）
    workflow = create_parallel_shadow_writing_workflow()
    # workflow = create_shadow_writing_workflow()  # 旧版串行（已弃用）
    
    # 遍历处理每个URL
    for idx, url in enumerate(urls, 1):
        url_start_time = time.time()
        try:
            print(f"\n[BATCH PROCESSOR] 处理 [{idx}/{total}]: {url} - 开始时间: {time.strftime('%H:%M:%S')}")
            
            # 更新进度到数据库
            task_manager.update_progress(task_id, idx, url)
            
            progress = int((idx - 1) / total * 100)
            task_db.update(task_id, {
                "status": DBTaskStatus.PARSING.value,
                "current_step": f"处理 ({idx}/{total}): {url[:50]}...",
                "current": idx - 1,
                "total": total,
                "current_url": url,
                "progress": progress
            })
            
            print(f"[BATCH_PROCESSOR] [{task_id}] 准备发送progress消息 - URL {idx}/{total} - 时间: {time.strftime('%H:%M:%S')}")
            await sse_manager.add_message(
                task_id,
                {
                    "type": MessageType.PROGRESS.value,
                    "current": idx,
                    "total": total,
                    "url": url,
                    "status": f"Processing {idx}/{total}"
                }
            )
            print(f"[BATCH_PROCESSOR] [{task_id}] progress消息发送完成 - URL {idx}/{total} - 时间: {time.strftime('%H:%M:%S')}")

            # ========== 步骤1: 提取Transcript ==========
            task_db.update(task_id, {
                "status": DBTaskStatus.PARSING.value,
                "current_step": f"提取字幕 ({idx}/{total})"
            })
            
            await sse_manager.add_message(
                task_id,
                {
                    "type": MessageType.STEP.value,
                    "current": idx,
                    "total": total,
                    "step": ProcessingStep.EXTRACTING_TRANSCRIPT.value,
                    "url": url,
                    "message": f"正在提取字幕 ({idx}/{total})"
                }
            )
            
            transcript_data = extract_ted_transcript(url)
            
            if not transcript_data or not transcript_data.transcript:
                raise Exception("Failed to extract transcript")
            
            print(f"   提取字幕成功: {len(transcript_data.transcript)} 字符")
            
            # ========== 步骤2: 运行Shadow Writing工作流 ==========
            task_db.update(task_id, {
                "status": DBTaskStatus.SHADOW_WRITING.value,
                "current_step": f"生成Shadow Writing ({idx}/{total})"
            })
            
            await sse_manager.add_message(
                task_id,
                {
                    "type": MessageType.STEP.value,
                    "current": idx,
                    "total": total,
                    "step": ProcessingStep.SHADOW_WRITING.value,
                    "url": url,
                    "message": f"正在生成Shadow Writing ({idx}/{total})"
                }
            )
            
            # 准备工作流初始状态（并行版本简化）
            initial_state = {
                "text": transcript_data.transcript,
                "target_topic": "",
                "ted_title": transcript_data.title,
                "ted_speaker": transcript_data.speaker,
                "ted_url": url,
                "task_id": task_id,  # 添加task_id用于进度推送
                "semantic_chunks": [],
                "final_shadow_chunks": [],  # 并行版本：operator.add自动汇总
                "current_node": "",
                "error_message": None
            }
            
            # 运行并行工作流（流式版本，带Langfuse监控）
            print("   启动并行Shadow Writing工作流（流式）...")
            from app.dependencies import get_langfuse_handler
            langfuse_handler = get_langfuse_handler()

            # 使用astream监听chunk完成事件
            config = cast(RunnableConfig, {"callbacks": [langfuse_handler]}) if langfuse_handler else None

            processed_results = []
            async for event in workflow.astream(
                cast(Shadow_Writing_State, initial_state),
                config=config,
                stream_mode=["updates", "custom"],
                subgraphs=True
            ):
                # 处理astream事件
                if isinstance(event, tuple) and len(event) == 3:
                    namespace, mode, data = event
                    if mode == "custom" and data.get("type") == "chunk_completed":
                        # 每个chunk完成时立即推送SSE消息
                        chunk_data = data

                        # 序列化Ted_Shadows对象
                        result_obj = chunk_data["result"]
                        if hasattr(result_obj, 'model_dump'):
                            serialized_result = result_obj.model_dump()
                        elif hasattr(result_obj, 'dict'):
                            serialized_result = result_obj.dict()
                        else:
                            serialized_result = str(result_obj)

                        processed_results.append(serialized_result)

                        # 实时推送chunk结果到前端
                        await sse_manager.add_message(
                            task_id,
                            {
                                "type": "chunk_completed",
                                "chunk_id": chunk_data["chunk_id"],
                                "result": serialized_result,
                                "timestamp": chunk_data["timestamp"]
                            }
                        )
                elif isinstance(event, dict) and event.get("type") == "chunk_completed":
                    # 处理单值模式
                    result_obj = event["result"]
                    if hasattr(result_obj, 'model_dump'):
                        serialized_result = result_obj.model_dump()
                    elif hasattr(result_obj, 'dict'):
                        serialized_result = result_obj.dict()
                    else:
                        serialized_result = str(result_obj)

                    processed_results.append(serialized_result)
                    await sse_manager.add_message(task_id, {
                        "type": "chunk_completed",
                        "chunk_id": event["chunk_id"],
                        "result": serialized_result,
                        "timestamp": event["timestamp"]
                    })
            
            url_end_time = time.time()
            url_duration = url_end_time - url_start_time
            print(f"   Shadow Writing完成: {len(processed_results)} 个结果 - 耗时: {url_duration:.2f}秒")

            # ========== 步骤3: 保存结果 ==========
            result_data = {
                "url": url,
                "ted_info": {
                    "title": transcript_data.title,
                    "speaker": transcript_data.speaker,
                    "url": url,
                    "transcript_length": len(transcript_data.transcript)
                },
                "results": processed_results,
                "result_count": len(processed_results)
            }
            
            task_manager.add_result(task_id, result_data)
            
            # 保存到历史记录
            import uuid as uuid_lib
            record_id = str(uuid_lib.uuid4())
            history_db.create(
                record_id=record_id,
                task_id=task_id,
                ted_title=transcript_data.title,
                ted_speaker=transcript_data.speaker,
                ted_url=url,
                result={"chunks": processed_results},
                transcript=transcript_data.transcript
            )
            
            # 更新数据库状态
            task_db.update(task_id, {
                "status": DBTaskStatus.COMPLETED.value,
                "current_step": f"完成 ({idx}/{total}): {transcript_data.title[:30]}...",
                "current": idx,
                "total": total,
                "current_url": url,
                "progress": int(idx / total * 100)
            })
            
            # ========== 步骤4: 推送完成消息 ==========
            await sse_manager.add_message(
                task_id,
                {
                    "type": MessageType.URL_COMPLETED.value,
                    "current": idx,
                    "total": total,
                    "url": url,
                    "result_count": len(processed_results),
                    "message": f"完成 ({idx}/{total}): 生成 {len(processed_results)} 个结果"
                }
            )
            
        except Exception as e:
            error_msg = f"Error processing {url}: {str(e)}"
            print(f"   [ERROR] {error_msg}")
            
            task_manager.add_error(task_id, error_msg)
            
            # 更新数据库错误状态
            task_db.update(task_id, {
                "status": DBTaskStatus.FAILED.value,
                "current_step": f"失败 ({idx}/{total})",
                "error": error_msg
            })
            
            await sse_manager.add_message(
                task_id,
                {
                    "type": MessageType.ERROR.value,
                    "current": idx,
                    "total": total,
                    "url": url,
                    "error": error_msg
                }
            )
    
    # ========== 全部完成 ==========
    task_manager.complete_task(task_id)
    
    task = task_manager.get_task(task_id)
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 更新数据库完成状态
    task_db.update(task_id, {
        "status": DBTaskStatus.COMPLETED.value,
        "current_step": "全部完成",
        "progress": 100
    })

    await sse_manager.add_message(
        task_id,
        {
            "type": MessageType.COMPLETED.value,
            "total": total,
            "successful": len(task.results) if task else 0,
            "failed": len(task.errors) if task else 0,
            "message": f"全部完成: 成功 {len(task.results) if task else 0}/{total}",
            "duration": total_duration
        }
    )

    print(f"\n[BATCH PROCESSOR] 批量处理完成: 成功 {len(task.results) if task else 0}/{total}")
    print(f"[BATCH PROCESSOR] 总耗时: {total_duration:.2f} 秒")
    print(f"[BATCH PROCESSOR] 结束时间: {time.strftime('%H:%M:%S')}")
