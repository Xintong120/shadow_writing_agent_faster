# aggregate_agent.py
# 并行处理的汇总Agent

def aggregate_results_node(state) -> dict:
    """
    汇总所有Chunk的处理结果
    
    此时state["final_shadow_chunks"]已经自动包含了所有chunk的结果
    （由operator.add自动合并）
    """
    
    final_chunks = state.get("final_shadow_chunks", [])
    
    print("\n[AGGREGATE] 汇总完成")
    print(f"   总语义块: {len(state.get('semantic_chunks', []))}")
    print(f"   成功处理: {len(final_chunks)}")
    if len(state.get('semantic_chunks', [])) > 0:
        print(f"   成功率: {len(final_chunks) / len(state.get('semantic_chunks', [])) * 100:.1f}%")
    
    return {
        "current_node": "aggregate_results",
        "processing_logs": [f"Successfully processed {len(final_chunks)} chunks"]
    }
