# SSE Manager - 替换WebSocket管理器
# 作用：管理SSE消息队列，实现消息缓存和断点续传
# 功能：
#   - 消息队列管理（每个task_id一个队列）
#   - 消息缓存（支持断点续传）
#   - 自动清理过期消息

import asyncio
import time
from collections import deque
from typing import Dict, List, Any, Optional
from datetime import datetime

class SSEManager:
    """
    SSE管理器，负责消息缓存和分发
    """

    def __init__(self, max_messages_per_task: int = 100, message_ttl: int = 300):
        """
        初始化SSE管理器

        Args:
            max_messages_per_task: 每个任务最大消息数
            message_ttl: 消息存活时间（秒）
        """
        self.max_messages_per_task = max_messages_per_task
        self.message_ttl = message_ttl
        self.message_queues: Dict[str, deque] = {}
        self.task_timestamps: Dict[str, float] = {}  # 任务最后活动时间

    async def add_message(self, task_id: str, message: dict) -> None:
        """
        添加消息到队列

        Args:
            task_id: 任务ID
            message: 消息内容，必须包含 'id', 'type', 'timestamp' 字段
        """
        if task_id not in self.message_queues:
            self.message_queues[task_id] = deque(maxlen=self.max_messages_per_task)

        # 确保消息有ID和时间戳
        if 'id' not in message:
            message['id'] = f"{task_id}_{int(time.time() * 1000)}"

        if 'timestamp' not in message:
            message['timestamp'] = time.time()

        self.message_queues[task_id].append(message)
        self.task_timestamps[task_id] = time.time()

        print(f"[SSE] 消息已缓存: task_id={task_id}, type={message.get('type')}, id={message['id']}")

    async def get_messages(self, task_id: str, last_event_id: Optional[str] = None) -> List[dict]:
        """
        获取任务的消息，支持断点续传

        Args:
            task_id: 任务ID
            last_event_id: 最后收到的事件ID，用于断点续传

        Returns:
            消息列表
        """
        if task_id not in self.message_queues:
            return []

        messages = list(self.message_queues[task_id])

        if last_event_id:
            # 过滤出last_event_id之后的消息
            filtered_messages = []
            for msg in messages:
                if msg.get('id', '') > last_event_id:
                    filtered_messages.append(msg)
            return filtered_messages

        return messages

    async def get_latest_message(self, task_id: str) -> Optional[dict]:
        """
        获取最新的消息

        Args:
            task_id: 任务ID

        Returns:
            最新消息或None
        """
        if task_id not in self.message_queues or not self.message_queues[task_id]:
            return None

        return self.message_queues[task_id][-1]

    async def clear_task_messages(self, task_id: str) -> None:
        """
        清除任务的所有消息

        Args:
            task_id: 任务ID
        """
        if task_id in self.message_queues:
            del self.message_queues[task_id]

        if task_id in self.task_timestamps:
            del self.task_timestamps[task_id]

        print(f"[SSE] 清除任务消息: task_id={task_id}")

    def cleanup_expired_messages(self) -> None:
        """
        清理过期消息（定期调用）
        """
        current_time = time.time()
        expired_tasks = []

        for task_id, timestamp in self.task_timestamps.items():
            if current_time - timestamp > self.message_ttl:
                expired_tasks.append(task_id)

        for task_id in expired_tasks:
            self.clear_task_messages(task_id)
            print(f"[SSE] 清理过期任务: task_id={task_id}")

    def get_active_tasks_count(self) -> int:
        """
        获取活跃任务数量
        """
        return len(self.message_queues)

    def get_task_message_count(self, task_id: str) -> int:
        """
        获取任务的消息数量
        """
        return len(self.message_queues.get(task_id, []))

# 创建全局SSE管理器实例
sse_manager = SSEManager()

# 定期清理过期消息
async def cleanup_task():
    """后台清理任务"""
    while True:
        sse_manager.cleanup_expired_messages()
        await asyncio.sleep(60)  # 每分钟清理一次

# 启动清理任务
def start_cleanup_task():
    """启动后台清理任务"""
    asyncio.create_task(cleanup_task())
    print("[SSE] 消息清理任务已启动")
