"""TED演讲核心观点提取服务"""

import re
from typing import Optional, List


class ArgumentExtractor:
    """从TED transcript提取核心观点"""
    
    CHUNK_SUMMARY_PROMPT = """You are a TED Talk analysis expert. Your task is to extract 2-3 key points from the following part of a TED Talk transcript. These should be the speaker's important points or arguments in this section. For each point, summarize it in one clear sentence. Output format: numbered list only. Do not add any extra explanations.

Talk Title: {title}
Speaker: {speaker}

Transcript Section:
{chunk}
"""

    FINAL_SUMMARY_PROMPT = """You are a TED Talk analysis expert. Below are key points extracted from different sections of a TED Talk. Your task is to consolidate them into 3-5 core arguments that represent the speaker's main message across the entire talk. For each argument, summarize it in one clear sentence and include a key quote or example as evidence. Output format: numbered list only. Do not add any extra explanations.

Talk Title: {title}
Speaker: {speaker}

Key points from different sections:
{points}

Core Arguments:
"""

    CHUNK_MAX_LENGTH = 3000
    
    def __init__(self):
        """初始化提取器，使用用户配置的模型"""
        from app.infrastructure.config.llm_model_map import create_llm_for_purpose
        self.llm = create_llm_for_purpose("debate", streaming=False)
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """将文本分割为适当大小的chunk"""
        if len(text) <= self.CHUNK_MAX_LENGTH:
            return [text]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) > self.CHUNK_MAX_LENGTH and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_from_chunk(self, chunk: str, title: str, speaker: str) -> str:
        """从单个chunk中提取观点"""
        prompt = self.CHUNK_SUMMARY_PROMPT.format(
            title=title,
            speaker=speaker,
            chunk=chunk
        )
        
        response = self.llm.invoke(prompt)
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    def _consolidate_arguments(self, points_list: List[str], title: str, speaker: str) -> str:
        """将多个chunk的观点整合为最终的核心观点"""
        combined_points = "\n".join(points_list)
        
        prompt = self.FINAL_SUMMARY_PROMPT.format(
            title=title,
            speaker=speaker,
            points=combined_points
        )
        
        response = self.llm.invoke(prompt)
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    def extract(
        self, 
        transcript: str, 
        title: str = "", 
        speaker: str = ""
    ) -> str:
        """
        使用LLM从transcript提取核心观点（支持chunking）
        
        Args:
            transcript: TED演讲完整文本
            title: 演讲标题
            speaker: 演讲者
            
        Returns:
            提取的核心观点（编号列表格式）
        """
        chunks = self._split_into_chunks(transcript)
        
        if len(chunks) == 1:
            return self._extract_from_chunk(chunks[0], title, speaker)
        
        chunk_points = []
        for i, chunk in enumerate(chunks):
            print(f"[ArgumentExtractor] Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            points = self._extract_from_chunk(chunk, title, speaker)
            chunk_points.append(points)
        
        print(f"[ArgumentExtractor] Consolidating {len(chunk_points)} chunk summaries into final arguments")
        final_arguments = self._consolidate_arguments(chunk_points, title, speaker)
        
        return final_arguments


class ArgumentExtractionError(Exception):
    """观点提取错误"""
    pass


_extractor: Optional[ArgumentExtractor] = None


def get_argument_extractor() -> ArgumentExtractor:
    """获取观点提取器单例"""
    global _extractor
    if _extractor is None:
        _extractor = ArgumentExtractor()
    return _extractor
