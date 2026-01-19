"""
TED AI演讲者提取工具

使用AI模型从Tavily搜索结果中智能提取演讲者信息
"""

from app.utils import create_llm_function_light
import re
import json


class TedAISpeakerExtractor:
    """TED AI演讲者提取器"""
    
    def __init__(self):
        """初始化AI演讲者提取器"""
        # 使用轻量级模型以提高响应速度
        self.llm = create_llm_function_light(
            system_prompt="""你是一个TED演讲专家，专门从TED演讲标题和内容中识别演讲者姓名。

任务要求：
1. 仔细分析提供的TED演讲信息
2. 识别并返回演讲者的真实姓名
3. 如果无法确定演讲者，返回"未知演讲者"

输出格式要求：
- 必须是JSON格式：{"speaker": "演讲者姓名"}
- 演讲者姓名应该完整且准确
- 如果无法确定，返回{"speaker": "未知演讲者"}

注意事项：
- 演讲者通常是个人姓名，不是组织或公司
- TED演讲通常以演讲者姓名开头或包含在标题中
- 排除明显的标题关键词（如"how to", "why we", "the power of"等）
- 姓名通常包含首字母大写的英文单词"""
        )
    
    def extract_speaker_from_search_result(self, title: str, url: str, content: str = "", speaker_from_url: str = "") -> str:
        """
        从Tavily搜索结果中提取演讲者信息
        
        Args:
            title: TED演讲标题
            url: TED演讲URL
            content: 搜索内容摘要
            speaker_from_url: 从URL提取的候选演讲者名称
            
        Returns:
            提取的演讲者姓名
        """
        try:
            print(f"[AI SPEAKER EXTRACTOR] 开始AI提取演讲者...")
            print(f"  标题: {title}")
            print(f"  URL演讲者候选: {speaker_from_url}")
            
            # 构建用户提示词
            user_prompt = self._build_prompt(title, url, content, speaker_from_url)
            
            # 调用AI提取演讲者
            response = self.llm(
                user_prompt=user_prompt,
                output_format={"speaker": "str"},
                temperature=0.1
            )
            
            if response and "speaker" in response:
                speaker = response["speaker"].strip()
                
                # 验证提取的演讲者名称
                if self._validate_speaker_name(speaker):
                    print(f"[AI SPEAKER EXTRACTOR] AI提取成功: {speaker}")
                    return speaker
                else:
                    print(f"[AI SPEAKER EXTRACTOR] AI提取结果无效: {speaker}")
                    return "未知演讲者"
            else:
                print("[AI SPEAKER EXTRACTOR] AI响应格式错误")
                return "未知演讲者"
                
        except Exception as e:
            print(f"[AI SPEAKER EXTRACTOR] AI提取失败: {e}")
            return "未知演讲者"
    
    def _build_prompt(self, title: str, url: str, content: str, speaker_from_url: str) -> str:
        """
        构建AI提示词
        
        Args:
            title: TED演讲标题
            url: TED演讲URL
            content: 搜索内容摘要
            speaker_from_url: 从URL提取的候选演讲者名称
            
        Returns:
            格式化的提示词
        """
        prompt_parts = []
        
        if title:
            prompt_parts.append(f"TED演讲标题: {title}")
        
        if url:
            prompt_parts.append(f"TED演讲URL: {url}")
        
        if speaker_from_url:
            prompt_parts.append(f"URL演讲者候选: {speaker_from_url}")
        
        if content:
            # 限制内容长度避免超出token限制
            content_preview = content[:500] + "..." if len(content) > 500 else content
            prompt_parts.append(f"搜索内容摘要: {content_preview}")
        
        prompt = "\n\n".join(prompt_parts)
        
        if not prompt:
            prompt = "无可用信息进行演讲者提取"
        
        return prompt
    
    def _validate_speaker_name(self, name: str) -> bool:
        """
        验证演讲者名称的有效性
        
        Args:
            name: 待验证的演讲者名称
            
        Returns:
            bool: 名称是否有效
        """
        if not name or name == "未知演讲者":
            return False
        
        # 基本长度检查
        if len(name) < 2 or len(name) > 50:
            return False
        
        # 去除首尾空格
        name = name.strip()
        
        # 检查是否包含明显的非人名词汇
        excluded_patterns = [
            r'^TED', r'TED$', r'TEDx', r'TED-',
            r'^How to', r'^Why we', r'^What is', r'^The power of',
            r'^The science of', r'^How can', r'^Why should',
            r'\btalk\b', r'\bspeech\b', r'\bpresentation\b',
            r'\bmasterclass\b', r'\bcourse\b', r'\bworkshop\b'
        ]
        
        name_lower = name.lower()
        for pattern in excluded_patterns:
            if re.search(pattern, name_lower, re.IGNORECASE):
                return False
        
        # 检查是否包含数字（通常不是人名）
        if re.search(r'\d', name):
            return False
        
        # 至少应该包含一个首字母大写的单词
        words = name.split()
        has_capitalized_word = any(word[0].isupper() if word else False for word in words)
        if not has_capitalized_word:
            return False
        
        return True
    
    def extract_speaker_fallback(self, title: str, url: str) -> str:
        """
        备用演讲者提取方法（当AI失败时使用）
        
        Args:
            title: TED演讲标题
            url: TED演讲URL
            
        Returns:
            提取的演讲者姓名或"未知演讲者"
        """
        try:
            # 从URL提取演讲者
            speaker_from_url = self._extract_speaker_from_url(url)
            if speaker_from_url and speaker_from_url != "未知演讲者":
                return speaker_from_url
            
            # 从标题提取演讲者
            speaker_from_title = self._extract_speaker_from_title(title)
            if speaker_from_title and speaker_from_title != "未知演讲者":
                return speaker_from_title
            
            return "未知演讲者"
            
        except Exception as e:
            print(f"[AI SPEAKER EXTRACTOR] 备用提取失败: {e}")
            return "未知演讲者"
    
    def _extract_speaker_from_url(self, url: str) -> str:
        """
        从URL中提取演讲者信息
        
        Args:
            url: TED演讲URL
            
        Returns:
            提取的演讲者姓名
        """
        try:
            if '/talks/' not in url:
                return "未知演讲者"
            
            # 提取talks/后面的部分
            parts = url.split('/talks/')[1].split('/')
            if len(parts) == 0:
                return "未知演讲者"
            
            # 获取演讲者部分（通常是第一个下划线前的部分）
            speaker_part = parts[0]
            
            # 移除查询参数和锚点
            speaker_part = speaker_part.split('?')[0].split('#')[0]
            
            # 处理下划线格式：lauren_parker -> Lauren Parker
            if '_' in speaker_part:
                words = speaker_part.split('_')
                speaker_name = ' '.join(word.capitalize() for word in words)
                return speaker_name if speaker_name.strip() else "未知演讲者"
            
            # 处理连字符格式
            if '-' in speaker_part:
                words = speaker_part.split('-')
                speaker_name = ' '.join(word.capitalize() for word in words)
                return speaker_name if speaker_name.strip() else "未知演讲者"
            
            # 简单驼峰命名处理
            speaker_name = speaker_part.replace('_', ' ').replace('-', ' ')
            speaker_name = ' '.join(word.capitalize() for word in speaker_name.split())
            return speaker_name if speaker_name.strip() else "未知演讲者"
            
        except Exception as e:
            print(f"[DEBUG] URL演讲者提取失败: {e}")
            return "未知演讲者"
    
    def _extract_speaker_from_title(self, title: str) -> str:
        """
        从标题中提取演讲者信息（改进版）
        
        Args:
            title: TED演讲标题
            
        Returns:
            提取的演讲者姓名
        """
        try:
            if not title:
                return "未知演讲者"
            
            # 清理标题
            cleaned_title = title.strip()
            suffixes_to_remove = [' | TED Talk', ' | TED', ' - TED Talk', ' - TED', ' ...']
            for suffix in suffixes_to_remove:
                if cleaned_title.endswith(suffix):
                    cleaned_title = cleaned_title[:-len(suffix)].strip()
            
            # 多种格式的演讲者提取
            
            # 格式1: "Name: Title" 或 "Name - Title"
            if ':' in cleaned_title or '-' in cleaned_title:
                separator = ':' if ':' in cleaned_title else '-'
                parts = cleaned_title.split(separator, 1)
                if len(parts) == 2:
                    potential_speaker = parts[0].strip()
                    if self._validate_speaker_name(potential_speaker):
                        return potential_speaker
            
            # 格式2: "Name (Year)" 开头
            pattern = r'^([A-Za-z][A-Za-z\s\.-]+?)\s*(?:\([0-9]{4}\)|:|-)'
            match = re.match(pattern, cleaned_title)
            if match:
                potential_speaker = match.group(1).strip()
                if self._validate_speaker_name(potential_speaker):
                    return potential_speaker
            
            # 格式3: "by Name" 模式
            by_pattern = r'\bby\s+([A-Za-z][A-Za-z\s\.-]+?)(?:\s*:|\s*-|\s*\||$)'
            by_match = re.search(by_pattern, cleaned_title, re.IGNORECASE)
            if by_match:
                potential_speaker = by_match.group(1).strip()
                if self._validate_speaker_name(potential_speaker):
                    return potential_speaker
            
            return "未知演讲者"
            
        except Exception as e:
            print(f"[DEBUG] 标题演讲者提取失败: {e}")
            return "未知演讲者"


# 便捷函数
def extract_speaker_with_ai(title: str, url: str, content: str = "", speaker_from_url: str = "") -> str:
    """
    便捷函数：使用AI提取演讲者
    
    Args:
        title: TED演讲标题
        url: TED演讲URL
        content: 搜索内容摘要
        speaker_from_url: 从URL提取的候选演讲者名称
        
    Returns:
        提取的演讲者姓名
    """
    extractor = TedAISpeakerExtractor()
    return extractor.extract_speaker_from_search_result(title, url, content, speaker_from_url)