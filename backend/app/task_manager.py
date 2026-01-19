# task_manager.py
# 作用：管理批量处理任务的状态和进度

import uuid
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from app.enums import TaskStatus

@dataclass
class Task:
    """任务数据结构"""
    task_id: str
    status: TaskStatus  # 使用枚举类型
    total: int
    current: int
    urls: List[str]
    user_id: str
    results: List[dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    current_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,  # 转换枚举为字符串
            "total": self.total,
            "current": self.current,
            "urls": self.urls,
            "user_id": self.user_id,
            "results": self.results,
            "errors": self.errors,
            "current_url": self.current_url,
            "created_at": self.created_at.isoformat()
        }


class TaskManager:
    """任务管理器 - 管理所有后台处理任务"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    def create_task(self, urls: List[str], user_id: str = "default") -> str:
        """
        创建新任务
        
        Args:
            urls: 要处理的URL列表
            user_id: 用户ID
            
        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            status=TaskStatus.PENDING,
            total=len(urls),
            current=0,
            urls=urls,
            user_id=user_id
        )
        self.tasks[task_id] = task
        
        print(f"[TASK MANAGER] 创建任务: {task_id}, URLs: {len(urls)}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            print(f"[TASK MANAGER] 任务 {task_id} 状态: {status.value}")
    
    def update_progress(self, task_id: str, current: int, current_url: str = None):
        """更新任务进度"""
        if task_id in self.tasks:
            self.tasks[task_id].current = current
            self.tasks[task_id].current_url = current_url
            self.tasks[task_id].status = TaskStatus.PROCESSING
            print(f"[TASK MANAGER] 任务 {task_id} 进度: {current}/{self.tasks[task_id].total}")
    
    def add_result(self, task_id: str, result: dict):
        """添加处理结果"""
        if task_id in self.tasks:
            self.tasks[task_id].results.append(result)
            print(f"[TASK MANAGER] 任务 {task_id} 添加结果，总数: {len(self.tasks[task_id].results)}")
    
    def add_error(self, task_id: str, error: str):
        """添加错误信息"""
        if task_id in self.tasks:
            self.tasks[task_id].errors.append(error)
            print(f"[TASK MANAGER] 任务 {task_id} 添加错误: {error}")
    
    def complete_task(self, task_id: str):
        """完成任务"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            print(f"[TASK MANAGER] 任务 {task_id} 完成")
    
    def fail_task(self, task_id: str, error: str):
        """任务失败"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED
            self.tasks[task_id].errors.append(error)
            print(f"[TASK MANAGER] 任务 {task_id} 失败: {error}")
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务（可选）"""
        now = datetime.now()
        to_delete = []
        
        for task_id, task in self.tasks.items():
            age = (now - task.created_at).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(task_id)
        
        for task_id in to_delete:
            del self.tasks[task_id]
            print(f"[TASK MANAGER] 清理旧任务: {task_id}")


# 全局任务管理器实例
task_manager = TaskManager()
