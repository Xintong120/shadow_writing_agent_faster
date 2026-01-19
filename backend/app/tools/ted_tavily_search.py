from app.config import settings
from tavily import TavilyClient
from app.tools.ted_transcript_tool import extract_ted_transcript
from app.tools.ted_ai_speaker_extractor import TedAISpeakerExtractor
import re
import time
import requests
from typing import List, Dict, Any


def _enrich_with_ai_assistance(basic_info: dict) -> dict:
    """
    使用AI辅助丰富TED信息
    
    Args:
        basic_info: 基础信息字典
        
    Returns:
        丰富后的TED信息
    """
    try:
        # 初始化AI演讲者提取器
        ai_extractor = TedAISpeakerExtractor()
        
        # 从URL提取演讲者候选
        speaker_from_url = _extract_speaker_from_url(basic_info.get('url', ''))
        
        # 使用AI提取演讲者
        ai_speaker = ai_extractor.extract_speaker_from_search_result(
            title=basic_info.get('title', ''),
            url=basic_info.get('url', ''),
            content=basic_info.get('content', ''),
            speaker_from_url=speaker_from_url
        )
        
        # 如果AI提取失败，使用备用方法
        if ai_speaker == "未知演讲者":
            traditional_speaker = _extract_speaker_from_title(basic_info.get('title', ''))
            if traditional_speaker != "未知演讲者":
                ai_speaker = traditional_speaker
        
        return {
            **basic_info,
            "speaker": ai_speaker,
            "duration": _estimate_duration_from_content(basic_info.get('content', '')),
            "views": "未知",
            "description": basic_info.get('content', '暂无描述')[:200] + "..." if len(basic_info.get('content', '')) > 200 else basic_info.get('content', '暂无描述'),
            "has_transcript": False
        }
        
    except Exception as e:
        print(f"[WARNING] AI辅助提取失败: {e}")
        # 回退到传统方法
        return {
            **basic_info,
            "speaker": _extract_speaker_from_title(basic_info.get('title', '')),
            "duration": _estimate_duration_from_content(basic_info.get('content', '')),
            "views": "未知",
            "description": basic_info.get('content', '暂无描述')[:200] + "..." if len(basic_info.get('content', '')) > 200 else basic_info.get('content', '暂无描述'),
            "has_transcript": False
        }


def _extract_speaker_from_url(url: str) -> str:
    """
    从URL中提取演讲者信息
    
    Args:
        url: TED演讲URL
        
    Returns:
        提取的演讲者姓名
    """
    try:
        if '/talks/' not in url:
            return ""
        
        # 提取talks/后面的部分
        parts = url.split('/talks/')[1].split('/')
        if len(parts) == 0:
            return ""
        
        # 获取演讲者部分（通常是第一个下划线前的部分）
        speaker_part = parts[0]
        
        # 移除查询参数和锚点
        speaker_part = speaker_part.split('?')[0].split('#')[0]
        
        # 处理下划线格式：lauren_parker -> Lauren Parker
        if '_' in speaker_part:
            words = speaker_part.split('_')
            speaker_name = ' '.join(word.capitalize() for word in words)
            return speaker_name.strip()
        
        # 处理连字符格式
        if '-' in speaker_part:
            words = speaker_part.split('-')
            speaker_name = ' '.join(word.capitalize() for word in words)
            return speaker_name.strip()
        
        return ""
        
    except Exception:
        return ""


def _enrich_ted_info(basic_info: dict) -> dict:
    """
    使用ted_transcript_tool获取TED演讲的详细信息
    
    Args:
        basic_info: 从搜索获得的初始信息，包含title, url, content, score
        
    Returns:
        丰富后的TED信息，包含speaker, duration, views, description等
    """
    try:
        url = basic_info.get('url', '')
        if not url:
            return basic_info
            
        # 使用ted_transcript_tool获取详细信息
        ted_data = extract_ted_transcript(url)
        
        if ted_data:
            # 合并基础信息和详细信息
            enriched_info = basic_info.copy()
            
            # 处理有transcript的情况
            if ted_data.transcript:
                enriched_info.update({
                    "speaker": ted_data.speaker or "未知演讲者",
                    "duration": ted_data.duration if ted_data.duration and ted_data.duration != "0:00" else "未知",
                    "views": str(ted_data.views) if ted_data.views and ted_data.views != 0 else "未知",
                    "description": (ted_data.transcript[:500] + "...") if len(ted_data.transcript) > 500 else ted_data.transcript,
                    "has_transcript": True
                })
            else:
                # 处理无transcript但有基本信息的情况
                enriched_info.update({
                    "speaker": ted_data.speaker or "未知演讲者",
                    "duration": ted_data.duration if ted_data.duration and ted_data.duration != "0:00" else "未知",
                    "views": str(ted_data.views) if ted_data.views and ted_data.views != 0 else "未知",
                    "description": basic_info.get('content', '暂无描述')[:200] + "..." if len(basic_info.get('content', '')) > 200 else basic_info.get('content', '暂无描述'),
                    "has_transcript": False
                })
                
            return enriched_info
        else:
            # 如果获取详细信息完全失败，直接返回基础信息，不使用AI提取
            return {
                **basic_info,
                "speaker": _extract_speaker_from_title(basic_info.get('title', '')),
                "duration": _estimate_duration_from_content(basic_info.get('content', '')),
                "views": "未知",
                "description": basic_info.get('content', '暂无描述')[:200] + "..." if len(basic_info.get('content', '')) > 200 else basic_info.get('content', '暂无描述'),
                "has_transcript": False
            }
            
    except Exception as e:
        print(f"[WARNING] 获取TED详细信息失败: {e}")
        # 返回基础信息，添加默认值
        return {
            **basic_info,
            "speaker": _extract_speaker_from_title(basic_info.get('title', '')),
            "duration": _estimate_duration_from_content(basic_info.get('content', '')),
            "views": "未知",
            "description": basic_info.get('content', '暂无描述')[:200] + "..." if len(basic_info.get('content', '')) > 200 else basic_info.get('content', '暂无描述'),
            "has_transcript": False
        }


def _extract_speaker_from_title(title: str) -> str:
    """
    从标题中提取演讲者信息
    
    Args:
        title: TED演讲标题
        
    Returns:
        提取的演讲者名称
    """
    try:
        if not title:
            return "未知演讲者"
        
        # 清理标题，去除常见后缀
        cleaned_title = title.strip()
        # 去除TED相关的常见后缀
        suffixes_to_remove = [' | TED Talk', ' | TED', ' - TED Talk', ' - TED', ' ...']
        for suffix in suffixes_to_remove:
            if cleaned_title.endswith(suffix):
                cleaned_title = cleaned_title[:-len(suffix)].strip()
        
        # 多种格式的演讲者提取
        # 格式1: "Name: Title" 或 "Name - Title"
        if ':' in cleaned_title or '-' in cleaned_title:
            # 优先尝试冒号格式
            separator = ':' if ':' in cleaned_title else '-'
            parts = cleaned_title.split(separator, 1)
            if len(parts) == 2:
                potential_speaker = parts[0].strip()
                # 改进的演讲者名称检查
                if _is_likely_speaker_name(potential_speaker):
                    return potential_speaker
        
        # 格式2: "Name (Year)" 或 "Name (Year) Title"
        pattern = r'^([A-Za-z][A-Za-z\s\.-]+?)\s*(?:\([0-9]{4}\)|:|-)'  
        match = re.match(pattern, cleaned_title)
        if match:
            potential_speaker = match.group(1).strip()
            if _is_likely_speaker_name(potential_speaker):
                return potential_speaker
        
        # 格式3: 查找"by Name"模式
        by_pattern = r'\bby\s+([A-Za-z][A-Za-z\s\.-]+?)(?:\s*:|\s*-|\s*\||$)'
        by_match = re.search(by_pattern, cleaned_title, re.IGNORECASE)
        if by_match:
            potential_speaker = by_match.group(1).strip()
            if _is_likely_speaker_name(potential_speaker):
                return potential_speaker
        
        return "未知演讲者"
    except:
        return "未知演讲者"


def _is_likely_speaker_name(name: str) -> bool:
    """
    检查是否为可能的演讲者名称
    
    Args:
        name: 待检查的字符串
        
    Returns:
        bool: 是否像演讲者名称
    """
    if not name or len(name) > 50 or len(name) < 2:
        return False
    
    # 去除首尾空格
    name = name.strip()
    name_lower = name.lower()
    
    # 1. 首先检查是否以TED相关前缀开始（最严格）
    ted_prefixes = ['ted-', 'ted ', 'tedx-', 'tedx ', 'ted-ed', 'teded', 'ted salon', 'ted conference']
    for prefix in ted_prefixes:
        if name_lower.startswith(prefix):
            return False
    
    # 2. 排除明显的非人名词汇（更完整的列表）
    excluded_words = [
        'ted', 'talk', 'tedtalk', 'imagination', 'innovation', 'power', 'the', 'and', 'or',
        'ed', 'salon', 'conference', 'workshop', 'masterclass', 'live', 'about', 'can', 'will',
        'how', 'why', 'what', 'when', 'where', 'to', 'of', 'in', 'for', 'with', 'on', 'at', 'by',
        'economy', 'grow', 'forever', 'transformative', 'collaboration'
    ]
    
    # 如果整个名字就是排除词汇，返回False
    if name_lower in excluded_words:
        return False
    
    # 3. 检查是否包含太多排除词汇
    excluded_count = sum(1 for word in excluded_words if word in name_lower.split())
    total_words = len(name_lower.split())
    if total_words > 0 and excluded_count / total_words > 0.6:  # 如果超过60%的词都是排除词
        return False
    
    # 4. 检查是否包含数字（通常不是演讲者名称）
    if re.search(r'\d', name):
        return False
    
    # 5. 检查是否主要是标点符号
    if re.match(r'^[\W\s]+$', name):
        return False
    
    # 6. 检查是否有驼峰命名或明显的英文名模式
    # 至少应该包含一个首字母大写的单词
    words = name.split()
    has_capitalized_word = any(word[0].isupper() if word else False for word in words)
    if not has_capitalized_word:
        return False
    
    # 7. 如果包含常见的演讲标题关键词，可能不是演讲者名称
    title_keywords = [
        'how to', 'why we', 'what is', 'when to', 'where to', 'the power of', 'the science of',
        'can the', 'should we', 'will we', 'must we', 'is there', 'are there'
    ]
    if any(keyword in name_lower for keyword in title_keywords):
        return False
    
    return True


def _estimate_duration_from_content(content: str) -> str:
    """
    根据内容长度估计演讲时长
    
    Args:
        content: 演讲内容
        
    Returns:
        估计的时长字符串
    """
    try:
        if not content:
            return "15:00"  # 默认15分钟
        
        content_length = len(content)
        
        # 基于内容长度估算时长（粗略估计）
        if content_length < 500:
            return "5:00"   # 少于500字符，可能是5分钟
        elif content_length < 1500:
            return "10:00"  # 500-1500字符，10分钟
        elif content_length < 3000:
            return "15:00"  # 1500-3000字符，15分钟
        elif content_length < 6000:
            return "20:00"  # 3000-6000字符，20分钟
        else:
            return "25:00"  # 更多内容，25分钟
            
    except:
        return "15:00"  # 出错时返回默认值


def _is_valid_ted_talk_url(url: str) -> bool:
    """
    验证URL是否为有效的TED演讲
    
    有效格式：https://www.ted.com/talks/xxx
    无效格式：
    - https://www.ted.com/playlists/xxx (播放列表)
    - https://www.ted.com/speakers/xxx (演讲者页面)
    - https://www.ted.com/events/xxx (活动页面)
    - https://www.ted.com/series/xxx (系列页面)
    
    Args:
        url: 待验证的URL
        
    Returns:
        bool: URL是否为有效的TED演讲
    """
    if not url:
        return False
    
    # 必须包含 /talks/
    if '/talks/' not in url:
        return False
    
    # 排除特殊页面
    invalid_patterns = ['/playlists/', '/speakers/', '/events/', '/series/']
    for pattern in invalid_patterns:
        if pattern in url:
            return False
    
    return True


def ted_tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    搜索TED演讲（适配FastAPI环境，支持重试机制）

    Args:
        query: 搜索关键词/主题
        max_results: 最多返回结果数

    Returns:
        list: 搜索结果列表，每个结果包含title, url, content, score

    Raises:
        ValueError: 如果TAVILY_API_KEY未配置
        Exception: 搜索失败且重试后仍失败
    """
    # 1. 检查API密钥
    if not settings.tavily_api_key:
        raise ValueError("TAVILY_API_KEY not configured in .env file")

    # 2. 初始化Tavily客户端
    try:
        tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        print(f"[TAVILY SEARCH] 正在搜索: '{query}'")

    except Exception as e:
        print(f"[ERROR] Tavily客户端初始化失败: {e}")
        raise

    # 3. 执行搜索（带重试机制）
    max_retries = 3
    base_delay = 1.0  # 基础延迟1秒

    for attempt in range(max_retries):
        try:
            # 如果不是第一次尝试，打印重试信息
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))  # 指数退避
                print(f"[RETRY] 第 {attempt + 1} 次重试，等待 {delay:.1f} 秒...")
                time.sleep(delay)

            # 执行搜索请求
            search_response = tavily_client.search(
                query=f"TED talk {query}",
                topic="general",  # 通用主题
                search_depth="advanced",
                max_results=max_results,
                include_domains=["ted.com"]
            )

            # 4. 处理搜索结果
            results = search_response.get('results', [])

            if not results:
                print("[WARNING] 未找到任何结果")
                return []

            print(f"[SUCCESS] 找到 {len(results)} 个相关TED演讲\n")

            # 5. 简化并过滤返回结果
            simplified_results = []
            filtered_count = 0

            for i, result in enumerate(results, 1):
                simplified_result = {
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "content": result.get('content', ''),
                    "score": result.get('score', 0)
                }

                # 验证URL是否为有效的TED演讲
                if _is_valid_ted_talk_url(simplified_result['url']):
                    # 丰富TED信息（获取speaker、duration、views、description等）
                    enriched_result = _enrich_ted_info(simplified_result)
                    simplified_results.append(enriched_result)

                    # 打印有效结果的日志
                    print(f"  [{len(simplified_results)}] {enriched_result['title']}")
                    print(f"      URL: {enriched_result['url']}")
                    print(f"      相关度: {enriched_result['score']:.2f}")
                    if 'speaker' in enriched_result:
                        print(f"      演讲者: {enriched_result['speaker']}")
                    print("\n")
                else:
                    # 跳过无效URL
                    filtered_count += 1
                    print(f"  [SKIP] 非演讲URL: {simplified_result['url']}\n")

            if filtered_count > 0:
                print(f"[INFO] 过滤掉 {filtered_count} 个非演讲URL，返回 {len(simplified_results)} 个有效结果\n")

            return simplified_results

        except (ConnectionAbortedError, ConnectionError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            # 网络相关错误，进行重试
            if attempt == max_retries - 1:
                print(f"[ERROR] 搜索失败，已重试 {max_retries} 次: {e}")
                raise Exception(f"TED搜索失败（网络连接问题）: {e}")
            else:
                print(f"[WARNING] 网络连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                continue

        except Exception as e:
            # 非网络错误，直接抛出
            print(f"[ERROR] 搜索失败: {e}")
            raise

    # 这行代码理论上不会到达，因为循环中要么成功返回，要么抛出异常
    # 但为了满足类型检查器的要求，我们添加这个返回语句
    raise Exception("搜索失败：意外的代码路径")
