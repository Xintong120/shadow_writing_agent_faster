# agent.py
# 作用：TED Agent核心逻辑封装
# 功能：
#   - 提供process_ted_text()函数供main.py调用
#   - 使用workflows.py中定义的工作流
#   - 返回结构化结果

from app.workflows import create_parallel_shadow_writing_workflow


# 暴露给main.py的处理函数
def process_ted_text(
    text: str, 
    target_topic: str = "",
    ted_title: str = None,
    ted_speaker: str = None,
    ted_url: str = None
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
    
    # 运行并行工作流
    result = workflow.invoke(initial_state)
    
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