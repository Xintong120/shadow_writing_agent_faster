"""TED搜索优化工具

负责：
1. 使用LLM优化用户输入的搜索词
2. 生成替代搜索词（当主搜索结果不足时）
"""

from typing import List
from app.utils import create_llm_function_light


def optimize_search_query(user_topic: str) -> str:
    """
    使用LLM优化用户输入的搜索词
    
    将用户输入转换为适合搜索TED的英文关键词
    
    Args:
        user_topic: 用户输入的主题
        
    Returns:
        优化后的搜索关键词
        
    Example:
        >>> optimize_search_query("我想学习关于气候变化的英语")
        "climate change environment"
    """
    prompt = f"""
You are a TED talk search query optimizer.

USER INPUT: "{user_topic}"

Your task: Convert the user's input into optimal English keywords for searching TED talks.

Rules:
1. Output 2-5 keywords as a SINGLE STRING (space-separated)
2. Use English keywords (even if input is Chinese)
3. Focus on the core topic, not learning goals
4. Use terms commonly found in TED talk titles

Examples:
- "我想学习关于气候变化的英语" -> "climate change environment"
- "提高领导力" -> "leadership management"
- "量子计算" -> "quantum computing technology"

IMPORTANT: Return a single string of space-separated keywords, NOT a list or array.

Output the optimized keywords as a string in JSON format.
"""
    
    try:
        llm = create_llm_function_light()
        result = llm(prompt, {"keywords": "Optimized search keywords as space-separated string, str"}, temperature=0.1)
        
        if result and isinstance(result, dict):
            keywords = result.get("keywords", user_topic)
            
            # 如果LLM返回了列表，转换为字符串
            if isinstance(keywords, list):
                keywords = " ".join(str(k) for k in keywords)
                print(f"   [SEARCH OPTIMIZER] 转换列表为字符串: {keywords}")
            
            # 确保返回字符串
            keywords = str(keywords).strip()
            print(f"   [SEARCH OPTIMIZER] 优化搜索词: {user_topic} -> {keywords}")
            return keywords
        
        # 如果失败，返回原始输入
        print("   [SEARCH OPTIMIZER] LLM返回空，使用原始输入")
        return user_topic
        
    except Exception as e:
        print(f"   [SEARCH OPTIMIZER] 搜索词优化失败，使用原始输入: {e}")
        return user_topic


def generate_alternative_queries(user_topic: str) -> List[str]:
    """
    生成替代搜索词（当主搜索结果不足时使用）
    
    Args:
        user_topic: 用户输入的主题
        
    Returns:
        2-3个替代搜索词列表
        
    Example:
        >>> generate_alternative_queries("AI ethics")
        ["artificial intelligence", "machine learning ethics", "AI safety"]
    """
    prompt = f"""
Generate 3 alternative search queries for TED talks about: "{user_topic}"

Each query should:
- Be different from the original
- Cover related but distinct angles
- Be 2-4 English keywords per query
- Each query should be a string (space-separated keywords)

Examples:
- Input: "AI ethics"
- Output: {{"alternatives": ["artificial intelligence morality", "machine learning bias", "technology society impact"]}}

IMPORTANT: 
- Return a list of 3 strings, where each string contains space-separated keywords
- Use the JSON key "alternatives" (not "alternative_queries" or other variations)

Output in JSON format with the key "alternatives".
"""
    
    try:
        llm = create_llm_function_light()
        result = llm(prompt, {"alternatives": "List of 3 alternative query strings, list[str]"}, temperature=0.2)
        
        if result and isinstance(result, dict):
            # 尝试多个可能的key名称（LLM可能使用不同的命名）
            alternatives = (
                result.get("alternatives") or 
                result.get("alternative_queries") or 
                result.get("alternative_search_queries") or
                result.get("queries") or
                []
            )
            
            # 确保返回的是字符串列表
            if isinstance(alternatives, list) and len(alternatives) > 0:
                # 清理和验证每个元素
                clean_alternatives = []
                for alt in alternatives[:3]:
                    if isinstance(alt, str) and alt.strip():
                        clean_alternatives.append(alt.strip())
                    elif isinstance(alt, list):
                        # 如果是列表，转换为字符串
                        clean_alternatives.append(" ".join(str(k) for k in alt))
                
                if clean_alternatives:
                    print(f"   [SEARCH OPTIMIZER] 生成替代搜索词: {clean_alternatives}")
                    return clean_alternatives
        
        print("   [SEARCH OPTIMIZER] 未生成替代搜索词")
        return []
        
    except Exception as e:
        print(f"   [SEARCH OPTIMIZER] 生成替代搜索词失败: {e}")
        return []
