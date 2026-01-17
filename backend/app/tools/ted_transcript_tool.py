"""TED Transcript提取工具

包装 ted-transcript-extractor 包，从 TED URL 提取完整 transcript
"""

from typing import Optional
from ted_extractor import TEDTranscriptExtractor
from app.models import TedTxt
from app.tools.ted_ai_speaker_extractor import TedAISpeakerExtractor
import re


class TEDTranscriptTool:
    """
    TED Transcript提取工具类
    
    封装 ted-transcript-extractor 包，提供便捷的 TED 演讲 transcript 提取功能
    """
    
    def __init__(self):
        self.extractor = TEDTranscriptExtractor(
            delay_between_requests=2.0,  # 请求间隔 2 秒，避免被封
            timeout=30,  # 超时时间 30 秒
            max_retries=3  # 最大重试次数
        )
        # 初始化AI演讲者提取器（优先使用）
        self.ai_extractor = TedAISpeakerExtractor()
    
    def extract_transcript(self, url: str) -> Optional[TedTxt]:
        """
        从 TED URL 提取完整 transcript
        
        Args:
            url: TED演讲URL
            
        Returns:
            TedTxt对象，失败返回None
        """
        try:
            print(f"[TED EXTRACTOR] 开始爬取: {url}")
            
            # 使用 ted-transcript-extractor 包提取
            talk = self.extractor.extract_single(url)
            
            if not talk.success:
                error_msg = talk.error_message or "未知错误"
                print(f"[ERROR] 提取失败: {error_msg}")
                # 直接返回None，不需要ai提取
                return None
            
            # 转换为 TedTxt 格式，处理可能的None值
            ted_data = TedTxt(
                title=talk.title or "TED演讲",
                speaker=talk.speaker or "未知演讲者",
                url=talk.url or url,
                duration=self._format_duration(talk.duration) if talk.duration else "未知",
                views=talk.views if hasattr(talk, 'views') and talk.views else 0,
                transcript=talk.transcript or ""
            )
            
            print("[SUCCESS] 提取成功")
            print(f"  标题: {ted_data.title}")
            print(f"  演讲者: {ted_data.speaker}")
            print(f"  时长: {ted_data.duration}")
            print(f"  Transcript长度: {len(ted_data.transcript)} 字符\n")
            
            return ted_data
            
        except Exception as e:
            print(f"[ERROR] 提取异常: {e}")
            return None
    
    def _extract_basic_info_from_url(self, url: str, error_message: str) -> Optional[TedTxt]:
        """
        当transcript不可用时，尝试从URL中提取基本信息
        
        Args:
            url: TED演讲URL
            error_message: 原始错误信息
            
        Returns:
            包含基本信息的TedTxt对象
        """
        try:
            print("[INFO] 尝试从URL提取基本信息...")
            
            # 从URL中提取演讲标题（包含演讲者名）
            title_with_speaker = self._extract_title_from_url(url)
            
            # 从URL中提取候选演讲者
            speaker_from_url = self._extract_speaker_from_url(url)
            
            # 优先使用AI提取演讲者（用户要求优先使用AI）
            print("[INFO] 优先使用AI提取演讲者...")
            speaker_from_ai = self.ai_extractor.extract_speaker_from_search_result(
                title=title_with_speaker,
                url=url,
                content="",  # 基本提取时没有搜索内容
                speaker_from_url=speaker_from_url
            )
            
            # 使用AI提取的结果，如果没有则回退到URL提取
            final_speaker = speaker_from_ai if speaker_from_ai != "未知演讲者" else speaker_from_url
            
            # 从标题中提取纯标题（去除演讲者名）
            title_without_speaker = self._extract_title_without_speaker(title_with_speaker, final_speaker) if final_speaker != "未知演讲者" else title_with_speaker
            
            # 估算演讲时长（修复硬编码问题）
            estimated_duration = self._estimate_duration_from_title_and_url(title_without_speaker, url)
            if estimated_duration in ["未知", "unknown", "N/A"]:
                estimated_duration = "未知"
            
            # 估算观看次数（修复硬编码问题）
            estimated_views = self._estimate_views_from_title_and_url(title_without_speaker, url)
            # 如果无法获取真实观看次数，返回0而不是估算值
            # 注：0值会在前端显示为“未知”
            
            # 创建基本TedTxt对象
            ted_data = TedTxt(
                title=title_without_speaker or "TED演讲",
                speaker=final_speaker,  # 使用AI优先提取的演讲者
                url=url,
                duration=estimated_duration,  # 使用估算的时长，而不是硬编码
                views=estimated_views,  # 使用估算的观看次数，而不是硬编码
                transcript=""  # 无transcript时为空是合理的
            )
            
            print(f"[SUCCESS] 基本信息提取成功")
            print(f"  标题: {ted_data.title}")
            print(f"  演讲者: {ted_data.speaker}")
            print(f"  时长: {ted_data.duration}")
            print(f"  注意: 无可用transcript ({error_message})\n")
            
            return ted_data
            
        except Exception as e:
            print(f"[ERROR] 基本信息提取失败: {e}")
            return None
    
    def _extract_title_from_url(self, url: str) -> str:
        """
        从TED URL中提取演讲标题
        
        Args:
            url: TED演讲URL
            
        Returns:
            提取的标题字符串，如果提取失败返回默认值
        """
        try:
            # URL格式: https://www.ted.com/talks/speaker_name_talk_title
            if '/talks/' in url:
                # 提取talks/后面的部分
                parts = url.split('/talks/')[1].split('/')
                if len(parts) > 0:
                    # 去除参数和后缀，提取主要标题
                    title_part = parts[0].split('?')[0].split('#')[0]
                    # 替换下划线和连字符为空格
                    title = title_part.replace('_', ' ').replace('-', ' ')
                    # 简单标题格式化
                    title = ' '.join(word.capitalize() for word in title.split())
                    return title if title.strip() else "TED演讲"
            return "TED演讲"
        except:
            return "TED演讲"
    
    def _extract_speaker_from_url(self, url: str) -> str:
        """
        从TED URL中直接提取演讲者名称
        
        Args:
            url: TED演讲URL
            
        Returns:
            提取的演讲者名称，如果提取失败返回"未知演讲者"
        """
        try:
            # URL格式: https://www.ted.com/talks/speaker_name_talk_title
            if '/talks/' in url:
                # 提取talks/后面的部分
                parts = url.split('/talks/')[1].split('/')
                if len(parts) > 0:
                    # 去除参数和后缀，提取主要标题
                    title_part = parts[0].split('?')[0].split('#')[0]
                    
                    # 从标题部分中提取演讲者名
                    # TED URL格式通常是: speaker_name_talk_title
                    # 我们需要识别演讲者名和标题的分界点
                    
                    # 常见演讲者名模式识别
                    # 1. 查找第一个明显是标题关键词的位置
                    title_keywords = [
                        'and', 'the', 'of', 'to', 'in', 'for', 'with', 'on', 'at', 'by',
                        'how', 'why', 'what', 'when', 'where', 'can', 'will', 'is', 'are',
                        'your', 'our', 'their', 'this', 'that', 'these', 'those',
                        'sustainability', 'making', 'living', 'power', 'vulnerability', 'body', 'language',
                        'leadership', 'action', 'innovation', 'change', 'future', 'world', 'life'
                    ]
                    
                    # 分割成单词
                    words = title_part.split('_')
                    if len(words) >= 2:
                        # 尝试识别演讲者名边界
                        speaker_words = []
                        title_words = []
                        
                        # 从前向后查找标题关键词
                        found_title_start = False
                        for i, word in enumerate(words):
                            if not found_title_start:
                                # 检查是否是演讲者名的一部分
                                # 演讲者名通常是首字母大写的英文名
                                if word.lower() in title_keywords and i > 0:
                                    # 前面已经有一些词作为演讲者名
                                    found_title_start = True
                                    title_words = words[i:]
                                    if i > 0:
                                        speaker_words = words[:i]
                                    break
                        
                        # 如果没有找到标题关键词，尝试其他方法
                        if not found_title_start:
                            # 假设演讲者名是前1-3个词
                            for i in range(1, min(4, len(words))):
                                potential_speaker = '_'.join(words[:i])
                                potential_title = '_'.join(words[i:])
                                
                                # 检查是否像演讲者名（包含大写字母）
                                if any(word[0].isupper() if word else False for word in potential_speaker.split('_')):
                                    # 检查标题是否像标题（包含标题关键词或多个词）
                                    if len(potential_title.split('_')) >= 2:
                                        speaker_words = words[:i]
                                        title_words = words[i:]
                                        break
                        
                        # 如果找到了演讲者名，格式化并返回
                        if speaker_words:
                            speaker_name = ' '.join(word.capitalize() for word in speaker_words)
                            if self._is_likely_speaker_name(speaker_name):
                                return speaker_name
                    
                    # 如果上述方法都失败，尝试整个标题作为演讲者名（特殊情况）
                    full_title = title_part.replace('_', ' ')
                    if self._is_likely_speaker_name(full_title):
                        return ' '.join(word.capitalize() for word in full_title.split())
            
            return "未知演讲者"
            
        except Exception as e:
            print(f"[DEBUG] URL演讲者提取异常: {e}")
            return "未知演讲者"
    
    def _extract_title_without_speaker(self, title_with_speaker: str, speaker_name: str) -> str:
        """
        从包含演讲者名的标题中提取纯标题
        
        Args:
            title_with_speaker: 包含演讲者名的标题
            speaker_name: 演讲者名
            
        Returns:
            去除演讲者名后的纯标题
        """
        try:
            if not speaker_name or speaker_name == "未知演讲者":
                return title_with_speaker
            
            # 将演讲者名转换为下划线格式以便在标题中查找
            speaker_underscore = speaker_name.lower().replace(' ', '_')
            
            # 尝试从标题开头去除演讲者名
            if title_with_speaker.lower().startswith(speaker_name.lower()):
                # 去除演讲者名及其后的空格
                remaining = title_with_speaker[len(speaker_name):].strip()
                if remaining:
                    # 如果剩余部分以常见连接词开始，进一步清理
                    if remaining.lower().startswith(('and ', 'the ', 'of ', 'to ')):
                        return remaining
                    elif remaining:
                        return remaining
            
            # 如果没有成功去除演讲者名，返回原标题（可能演讲者名不在开头）
            return title_with_speaker
            
        except Exception as e:
            print(f"[DEBUG] 标题清理异常: {e}")
            return title_with_speaker

    def _format_duration(self, seconds: int) -> str:
        """
        将秒转换为 MM:SS 格式
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化后的时长字符串
        """
        if not seconds or seconds < 0:
            return "0:00"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"
    
    def _extract_speaker_from_title(self, title: str) -> str:
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
            
            # 改进的编码处理
            try:
                # 尝试UTF-8解码
                title = title.encode('utf-8').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                try:
                    # 尝试Latin-1解码
                    title = title.encode('latin-1').decode('utf-8', errors='ignore')
                except:
                    # 如果还是有问题，清理特殊字符
                    title = re.sub(r'[^\w\s\-\:\.\(\)]', ' ', str(title))
            
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
                    if self._is_likely_speaker_name(potential_speaker):
                        return potential_speaker
            
            # 格式2: "Name (Year)" 或 "Name (Year) Title"
            pattern = r'^([A-Za-z][A-Za-z\s\.-]+?)\s*(?:\([0-9]{4}\)|:|-)'  
            match = re.match(pattern, cleaned_title)
            if match:
                potential_speaker = match.group(1).strip()
                if self._is_likely_speaker_name(potential_speaker):
                    return potential_speaker
            
            # 格式3: 查找"by Name"模式
            by_pattern = r'\bby\s+([A-Za-z][A-Za-z\s\.-]+?)(?:\s*:|\s*-|\s*\||$)'
            by_match = re.search(by_pattern, cleaned_title, re.IGNORECASE)
            if by_match:
                potential_speaker = by_match.group(1).strip()
                if self._is_likely_speaker_name(potential_speaker):
                    return potential_speaker
            
            # 如果所有格式都失败，返回未知演讲者
            return "未知演讲者"
            
        except Exception as e:
            print(f"[DEBUG] 演讲者提取异常: {e}")
            return "未知演讲者"
    
    def _is_likely_speaker_name(self, name: str) -> bool:
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
        
        # 2. 排除明显的非人名词汇（更严格的列表）
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
    
    def _estimate_duration_from_title_and_url(self, title: str, url: str) -> str:
        """
        根据标题和URL估算演讲时长
        
        Args:
            title: 演讲标题
            url: TED演讲URL
            
        Returns:
            估算的时长字符串，如果无法估算则返回"未知"
        """
        try:
            if not title:
                return "未知"
            
            # 分析标题内容来估算时长
            title_lower = title.lower()
            url_lower = url.lower()
            
            # 短演讲关键词（5-8分钟）
            short_keywords = ['quick', 'fast', 'brief', 'short', 'minute', 'seconds', 'tip', 'hack', 'rapid']
            # 长演讲关键词（18-25分钟）
            long_keywords = ['deep', 'comprehensive', 'complete', 'full', 'detailed', 'extensive', 'thorough']
            # 超长演讲关键词（25分钟以上）
            very_long_keywords = ['masterclass', 'workshop', 'course', 'series', 'part 1', 'part 2', 'training']
            
            # 检查URL中是否包含特殊标识
            
            # TED演讲的标准时长估算 - 更严格和智能的条件
            if any(keyword in title_lower for keyword in very_long_keywords):
                return "25:00"
            elif any(keyword in title_lower for keyword in long_keywords):
                return "18:00"
            elif any(keyword in title_lower for keyword in short_keywords):
                return "8:00"
            elif 'tedx' in url_lower:
                # TEDx演讲通常较短，但只有明确标识时才估算
                return "12:00"
            elif 'ted-sal' in url_lower:
                # TED Salon演讲通常中等长度，但只有明确标识时才估算
                return "15:00"
            else:
                # 无法确定时返回"未知"而不是默认估算
                return "未知"
                
        except Exception as e:
            print(f"[DEBUG] 时长估算异常: {e}")
            return "未知"
    
    def _estimate_views_from_title_and_url(self, title: str, url: str) -> int:
        """
        返回0，因为无法获取真实的观看次数
        0值会在前端显示为"未知"
        
        Args:
            title: 演讲标题
            url: TED演讲URL
            
        Returns:
            0（显示未知）
        """
        return 0


# 导出便捷函数
def extract_ted_transcript(url: str) -> Optional[TedTxt]:
    """
    便捷函数：提取 TED transcript
    
    Args:
        url: TED演讲URL
        
    Returns:
        TedTxt对象，失败返回None
    
    Example:
        >>> ted_data = extract_ted_transcript(
        ...     "https://www.ted.com/talks/brene_brown_the_power_of_vulnerability"
        ... )
        >>> if ted_data:
        ...     print(ted_data.title)
    """
    tool = TEDTranscriptTool()
    return tool.extract_transcript(url)
