from app.config import settings
from tavily import TavilyClient

def ted_tavily_extract(url: str) -> dict:
    """
    提取TED演讲页面详情（适配FastAPI环境）
    
    Args:
        url: TED演讲URL
        
    Returns:
        dict: 包含url, raw_content, success字段的字典
        
    Raises:
        ValueError: 如果TAVILY_API_KEY未配置
    """
    # 1. 检查API密钥
    if not settings.tavily_api_key:
        raise ValueError("TAVILY_API_KEY not configured in .env file")
    
    # 2. 初始化客户端并提取内容
    try:
        tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        
        print(f"[TAVILY EXTRACT] 正在提取: {url}")
        
        extract_response = tavily_client.extract(url)
        
        # 3. 处理提取结果
        if extract_response.get('results') and extract_response['results']:
            raw_content = extract_response['results'][0]['raw_content']
            
            print("[SUCCESS] 内容提取成功")
            print(f"  内容长度: {len(raw_content)} 字符")
            print(f"  预计单词数: {len(raw_content.split())} 词\n")
            
            return {
                "url": url,
                "raw_content": raw_content,
                "success": True
            }
        else:
            print("[WARNING] 未能提取到内容")
            return {
                "url": url,
                "error": "No content extracted",
                "success": False
            }
            
    except Exception as e:
        print(f"[ERROR] 内容提取失败: {e}")
        return {
            "url": url,
            "error": str(e),
            "success": False
        }
