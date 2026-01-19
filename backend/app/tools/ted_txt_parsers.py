  # -*- coding: utf-8 -*-
"""
TED文本文件解析器
负责解析TED演讲的txt文件格式

文件格式示例:
    Title: How to spot fake AI photos
    Speaker: Hany Farid
    URL: https://www.ted.com/talks/...
    Duration: 751 seconds
    Views: 1319743
    
    --- Transcript ---
    演讲内容...
"""

from typing import Optional
from app.models import TedTxt


def parse_ted_file(file_path: str) -> Optional[TedTxt]:
    """
    解析TED文本文件
    
    Args:
        file_path: TED txt文件路径
        
    Returns:
        TedTxt对象，解析失败返回None
        
    文件格式要求:
        - Title: 必需
        - Speaker: 可选
        - URL: 可选
        - Duration: 可选，支持 "751 seconds" 或 "12:31" 格式
        - Views: 可选
        - Transcript: 必需，以 "--- Transcript ---" 开始
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            return None
        
        lines = content.split('\n')
        
        # 提取基本信息
        title = ""
        speaker = ""
        url = ""
        duration = ""
        views = ""
        transcript = ""
        
        # 解析文件内容
        current_section = None
        transcript_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
            elif line.startswith("Speaker:"):
                speaker = line.replace("Speaker:", "").strip()
            elif line.startswith("URL:"):
                url = line.replace("URL:", "").strip()
            elif line.startswith("Duration:"):
                duration_str = line.replace("Duration:", "").strip()
                # 处理 "600 seconds" 格式
                if "seconds" in duration_str:
                    seconds = int(duration_str.replace("seconds", "").strip())
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    duration = f"{minutes}:{remaining_seconds:02d}"
                else:
                    duration = duration_str
            elif line.startswith("Views:"):
                views_str = line.replace("Views:", "").strip()
                try:
                    views = int(views_str)
                except ValueError:
                    views = 0
            elif line.startswith("--- Transcript ---"):
                current_section = "transcript"
                continue
            elif line.startswith("Transcript:"):
                current_section = "transcript"
                continue
            elif current_section == "transcript":
                # 跳过分隔线
                if line.startswith("===") or line.startswith("---"):
                    continue
                transcript_lines.append(line)
        
        transcript = " ".join(transcript_lines).strip()
        
        # 确保必需字段存在
        if not title or not transcript:
            print(f"[ERROR] Parsing failed: Missing title or transcript (title={bool(title)}, transcript={bool(transcript)})")
            return None
            
        # 设置默认值
        if not speaker:
            speaker = "Unknown Speaker"
        if not url:
            url = "https://www.ted.com"
        if not duration:
            duration = "0:00"
        if not isinstance(views, int):
            views = 0
            
        print(f"[SUCCESS] Parsed file: {title} by {speaker}")
        print(f"   Duration: {duration}, Views: {views:,}")
        print(f"   Transcript: {len(transcript)} characters")
        
        if title and transcript:
            return TedTxt(
                title=title,
                speaker=speaker,
                url=url,
                duration=duration,
                views=views,
                transcript=transcript
            )
        else:
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to parse TED file: {e}")
        return None


def validate_ted_file(file_path: str) -> bool:
    """
    验证TED文件格式是否正确
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 文件格式有效返回True
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必需标记
        has_title = "Title:" in content
        has_transcript = "--- Transcript ---" in content or "Transcript:" in content
        
        return has_title and has_transcript
        
    except Exception:
        return False
