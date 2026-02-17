# communication_agent.py
# TED 搜索和内容交互 Agent

from app.state import Shadow_Writing_State
from app.tools.ted_search_optimizer import optimize_search_query
from app.tools.ted_tavily_search import ted_tavily_search
from app.tools.ted_transcript_tool import extract_ted_transcript
from app.tools.ted_file_manager import TEDFileManager
from app.memory import MemoryService, get_global_store
from typing import Dict, Any


def communication_agent(state: Shadow_Writing_State) -> Dict[str, Any]:
    """通信节点 - 搜索TED演讲"""
    topic = state.get("topic", "")
    user_id = state.get("user_id", "default_user")
    
    print(f"\n[COMMUNICATION] 搜索TED演讲: {topic}")
    
    if not topic:
        return {"errors": ["未提供搜索主题"]}
    
    try:
        memory_service = MemoryService(store=get_global_store())
        seen_urls = memory_service.get_seen_ted_urls(user_id)
        print(f"   已看过的TED: {len(seen_urls)} 个")

        optimized_query = topic

        print("   搜索中...")
        results = ted_tavily_search(topic, max_results=10)
        valid_results = [r for r in results if r.get('has_transcript', False)]
        print(f"   找到 {len(results)} 个结果，{len(valid_results)} 个有transcript")

        if len(valid_results) < 3:
            print("   结果不足，AI优化关键词...")
            optimized_query = optimize_search_query(topic)
            print(f"   优化搜索词: {topic} -> {optimized_query}")
            
            optimized_results = ted_tavily_search(optimized_query, max_results=15)
            optimized_valid = [r for r in optimized_results if r.get('has_transcript', False)]
            
            existing_urls = {r.get('url') for r in valid_results}
            for r in optimized_valid:
                if r.get('url') not in existing_urls:
                    valid_results.append(r)
                    if len(valid_results) >= 5:
                        break

        if not valid_results:
            return {"errors": [f"未找到关于 '{topic}' 的TED演讲（需要有transcript）"]}

        new_valid_results = [r for r in valid_results if r.get('url') not in seen_urls]
        print(f"   过滤后剩余 {len(new_valid_results)} 个新演讲")

        if len(new_valid_results) == 0:
            return {"errors": [f"未找到关于 '{topic}' 的新TED演讲"]}

        final_results = new_valid_results[:5]
        print(f"   返回 {len(final_results)} 个候选")

        memory_service.add_search_history(
            user_id=user_id,
            original_query=topic,
            optimized_query=optimized_query,
            alternative_queries=[],
            results_count=len(final_results),
            new_results=len(new_valid_results),
            filtered_seen=len(valid_results) - len(new_valid_results)
        )

        return {
            "ted_candidates": final_results,
            "awaiting_user_selection": True,
            "search_context": {
                "original_topic": topic,
                "optimized_query": optimized_query,
                "seen_count": len(seen_urls),
                "filtered_count": len(valid_results) - len(new_valid_results)
            }
        }
        
    except Exception as e:
        print(f"   错误: {e}")
        return {"errors": [f"通信节点出错: {e}"]}


def communication_continue_agent(state: Shadow_Writing_State) -> Dict[str, Any]:
    """处理用户选择的TED演讲"""
    selected_url = state.get("selected_ted_url", "")
    user_id = state.get("user_id", "default_user")
    search_context = state.get("search_context") or {}
    
    print(f"\n[COMMUNICATION] 处理用户选择: {selected_url}")
    
    if not selected_url:
        return {"errors": ["未提供选择的TED URL"]}
    
    try:
        ted_data = extract_ted_transcript(selected_url)
        
        if not ted_data:
            return {"errors": ["提取transcript失败"]}
        
        file_manager = TEDFileManager()
        filepath = file_manager.save_ted_file(ted_data)
        
        memory_service = MemoryService(store=get_global_store())
        memory_service.add_seen_ted(
            user_id=user_id,
            url=selected_url,
            title=ted_data.title,
            speaker=ted_data.speaker,
            search_topic=search_context.get("original_topic", ""),
            metadata={"duration": ted_data.duration, "views": ted_data.views}
        )
        
        return {
            "file_path": filepath,
            "text": ted_data.transcript,
            "ted_title": ted_data.title,
            "ted_speaker": ted_data.speaker,
            "ted_url": ted_data.url,
            "awaiting_user_selection": False
        }
        
    except Exception as e:
        print(f"   错误: {e}")
        return {"errors": [f"通信节点处理失败: {e}"]}
