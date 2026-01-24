import re
from typing import List
from app.state import Shadow_Writing_State


class Semantic_Chunking_Agent:
    """智能语义分块Agent - 控制块大小在400-600字符"""
    
    def __init__(self):
        self.target_chunk_size = 200   # 目标块大小
        self.min_chunk_size = 150      # 最小块大小
        self.max_chunk_size = 250      # 最大块大小
    
    def split_into_chunks(self, text: str) -> List[str]:
        """将文本分割为适当大小的语义块"""
        if len(text) <= self.max_chunk_size:
            return [text]
        
        # 按句子分割
        sentences = re.split(r'[.!?]+\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 如果添加这个句子会超过最大大小，先保存当前块
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # 当前块太小，继续添加
                    current_chunk += " " + sentence if current_chunk else sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_transcript(self, transcript: str, task_id: str | None = None) -> List[str]:
        """处理完整的transcript，返回语义块列表"""
        print("\n开始智能语义分块处理...")
        print(f"原始文本长度: {len(transcript)} 字符")

        chunks = self.split_into_chunks(transcript)

        print(f"分块完成: {len(chunks)} 个语义块")
        for i, chunk in enumerate(chunks, 1):
            print(f"  语义块 {i}: {len(chunk)} 字符")

        return chunks
    
    def __call__(self, state: Shadow_Writing_State) -> Shadow_Writing_State:
        """使其成为可调用的 LangGraph 节点

        Args:
            state: 工作流状态

        Returns:
            更新后的状态
        """
        text = state.get("text", "")
        task_id = state.get("task_id")

        print("\n [SEMANTIC CHUNKING NODE] 开始语义分块")
        print(f"[SEMANTIC CHUNKING NODE] task_id: {task_id}")

        if not text:
            return {
                **state,  # 保留原有状态
                "semantic_chunks": [],
                "errors": ["语义分块节点: 无文本内容"]
            }

        # 调用分块处理，传递task_id用于进度推送
        chunks = self.process_transcript(text, task_id)

        return {
            **state,  # 保留原有状态
            "semantic_chunks": chunks,
            "processing_logs": [f"语义分块节点: 生成 {len(chunks)} 个语义块"]
        }
