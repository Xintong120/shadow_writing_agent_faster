from app.state import Shadow_Writing_State
from app.memory import MemoryService, get_global_store

def finalize_agent(state: Shadow_Writing_State) -> Shadow_Writing_State:
    """最终化节点
    
    功能：
    1. 整合最终的Shadow Writing结果
    2. 保存学习记录到Memory系统
    """
    quality_chunks = state.get("quality_shadow_chunks", [])
    corrected_chunks = state.get("corrected_shadow_chunks", [])
    
    print("\n[FINALIZE NODE] 最终处理")
    
    # 优先使用修正后的语块，否则使用质量检查通过的语块
    if corrected_chunks:
        final_chunks = corrected_chunks
        print(f"   使用修正后的语块: {len(final_chunks)} 个")
    else:
        final_chunks = quality_chunks
        print(f"   使用质量检查通过的语块: {len(final_chunks)} 个")
    
    # 保存到Memory系统
    try:
        user_id = state.get("user_id", "default_user")
        ted_url = state.get("ted_url", "")
        ted_title = state.get("ted_title", "Unknown Title")
        ted_speaker = state.get("ted_speaker", "Unknown Speaker")
        topic = state.get("topic", "")
        
        # 只有在有有效数据时才保存
        if final_chunks and ted_url:
            memory_service = MemoryService(store=get_global_store())
            
            # 转换为Memory所需的格式
            shadow_writings = []
            for chunk in final_chunks:
                # 支持两种数据格式：Pydantic模型或dict
                if hasattr(chunk, 'model_dump'):
                    # Pydantic模型
                    chunk_data = chunk.model_dump()
                else:
                    # dict格式
                    chunk_data = chunk
                
                shadow_writings.append({
                    "original": chunk_data.get("original", ""),
                    "imitation": chunk_data.get("imitation", ""),
                    "map": chunk_data.get("map", {}),
                    "paragraph": chunk_data.get("paragraph", ""),
                    "quality_score": chunk_data.get("quality_score", 6.0)
                })
            
            # 构建两级标签：一级为search_topic，二级为ted_title
            default_tags = []
            if topic:
                default_tags.append(topic)
            if ted_title and ted_title != "Unknown Title":
                default_tags.append(ted_title)
            
            # 批量保存学习记录
            record_ids = memory_service.add_batch_learning_records(
                user_id=user_id,
                ted_url=ted_url,
                ted_title=ted_title,
                ted_speaker=ted_speaker,
                shadow_writings=shadow_writings,
                default_tags=default_tags if default_tags else None
            )
            
            print(f"   [OK] 已保存 {len(record_ids)} 条学习记录到Memory")
            print(f"   用户ID: {user_id}")
            print(f"   TED: {ted_title} by {ted_speaker}")
            print(f"   标签: {default_tags}")
            
        else:
            if not final_chunks:
                print("   [WARNING] 无有效结果，跳过Memory保存")
            elif not ted_url:
                print("   [WARNING] 缺少TED URL，跳过Memory保存")
                
    except Exception as e:
        print(f"   [WARNING] Memory保存失败: {e}")
        print("   继续返回结果（Memory保存失败不影响主流程）")
    
    return {
        "final_shadow_chunks": final_chunks,
        "processing_logs": [f"最终化节点: 生成 {len(final_chunks)} 个最终语块"]
    }