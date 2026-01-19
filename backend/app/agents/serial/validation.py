from app.state import Shadow_Writing_State
from app.models import Ted_Shadows

def validation_agent(state: Shadow_Writing_State) -> Shadow_Writing_State:
    """验证节点 - 验证TED迁移结果"""
    extracted_chunks = state.get("raw_shadows_chunks", [])
    
    if not extracted_chunks:
        return {
            "validated_shadow_chunks": [],
            "errors": ["验证节点: 无提取结果可验证"]
        }
    
    validated = []
    for chunk_data in extracted_chunks:
        # 检查TED迁移结果的必要字段
        if all(chunk_data.get(key) for key in ['original', 'imitation', 'map']):
            try:
                # BaseModel验证
                shadow_result = Ted_Shadows(
                    original=chunk_data['original'],
                    imitation=chunk_data['imitation'],
                    map=chunk_data['map'],
                    paragraph=chunk_data.get('paragraph', ''),
                    quality_score=6.0
                )
                validated.append(chunk_data)
            except Exception as e:
                return {
                    "validated_shadow_chunks": [],
                    "errors": [f"验证节点: BaseModel验证失败 - {e}"]
                }
    
    return {
        "validated_shadow_chunks": validated,
        "processing_logs": [f"验证节点: {len(validated)} 个语块通过验证"]
    }