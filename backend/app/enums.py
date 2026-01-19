# enums.py
# 作用：系统枚举类型和常量定义
# 功能：
#   - 定义任务状态枚举
#   - 定义WebSocket消息类型枚举
#   - 定义其他系统常量
#   - 消除Magic String，提高代码可维护性

from enum import Enum


# ==================== 任务状态枚举 ====================

class TaskStatus(str, Enum):
    """任务状态枚举
    
    用于 TaskManager 和相关API接口
    """
    PENDING = "pending"           # 任务已创建，等待处理
    PROCESSING = "processing"     # 任务处理中
    COMPLETED = "completed"       # 任务已完成
    FAILED = "failed"            # 任务失败
    
    def __str__(self) -> str:
        """返回枚举值字符串"""
        return self.value


# ==================== WebSocket消息类型枚举 ====================

class MessageType(str, Enum):
    """WebSocket消息类型枚举
    
    用于实时进度推送的消息分类
    """
    # 连接相关
    CONNECTED = "connected"                   # 客户端已连接
    
    # 任务生命周期
    STARTED = "started"                       # 任务开始
    PROGRESS = "progress"                     # 进度更新
    COMPLETED = "completed"                   # 任务完成
    TASK_COMPLETED = "task_completed"         # 任务最终完成（含完整数据）
    
    # 处理步骤
    STEP = "step"                             # 处理步骤（如：提取transcript、shadow writing）
    URL_COMPLETED = "url_completed"           # 单个URL处理完成
    
    # 错误处理
    ERROR = "error"                           # 错误消息
    
    def __str__(self) -> str:
        """返回枚举值字符串"""
        return self.value


# ==================== 处理步骤枚举 ====================

class ProcessingStep(str, Enum):
    """处理步骤枚举
    
    用于标识批量处理中的具体步骤
    """
    EXTRACTING_TRANSCRIPT = "extracting_transcript"    # 提取字幕
    SHADOW_WRITING = "shadow_writing"                  # 生成Shadow Writing
    VALIDATING = "validating"                          # 验证结果
    QUALITY_CHECK = "quality_check"                    # 质量检查
    CORRECTING = "correcting"                          # 修正
    FINALIZING = "finalizing"                          # 最终化
    SAVING = "saving"                                  # 保存结果
    
    def __str__(self) -> str:
        """返回枚举值字符串"""
        return self.value


# ==================== Memory命名空间类型枚举 ====================

class MemoryNamespace(str, Enum):
    """Memory命名空间类型枚举
    
    用于区分不同类型的Memory存储
    """
    TED_HISTORY = "ted_history"               # TED观看历史
    SEARCH_HISTORY = "search_history"         # 搜索历史
    LEARNING_RECORDS = "learning_records"     # 学习记录
    
    def __str__(self) -> str:
        """返回枚举值字符串"""
        return self.value


# ==================== 系统配置常量 ====================

class SystemConfig:
    """系统配置常量类
    
    集中管理系统级别的Magic Number
    """
    
    # ========== Memory配置 ==========
    DEFAULT_COOLDOWN_SECONDS = 60          # API Key冷却时间（秒）
    MAX_CACHE_SIZE_MB = 500                # 最大缓存大小（MB）
    MEMORY_CLEANUP_AGE_HOURS = 24          # Memory清理时间（小时）
    
    # ========== 分块配置 ==========
    CHUNK_SIZE = 4000                      # 语义分块大小（字符）
    SMALL_CHUNK_SIZE = 200                 # 小语义块大小（字符，用于初步分割）
    MIN_CHUNK_LENGTH = 50                  # 最小语义块长度（字符）
    
    # ========== 质量控制配置 ==========
    MIN_QUALITY_SCORE = 6.0                # 最低质量分数（8分制）
    MAX_QUALITY_SCORE = 8.0                # 最高质量分数
    MIN_WORD_COUNT = 8                     # 最少单词数
    MAX_WORD_COUNT = 50                    # 最多单词数
    
    # ========== LLM配置 ==========
    DEFAULT_TEMPERATURE = 0.1              # 默认温度参数
    QUALITY_CHECK_TEMPERATURE = 0.1        # 质量检查温度（更稳定）
    CREATIVE_TEMPERATURE = 0.4             # 创作性任务温度（更灵活）
    MAX_TOKENS = 4096                      # 最大Token数
    
    # ========== API配置 ==========
    MAX_RETRY_COUNT = 3                    # 最大重试次数
    REQUEST_TIMEOUT_SECONDS = 30           # 请求超时时间（秒）
    BATCH_SIZE_LIMIT = 10                  # 批量处理最大数量
    
    # ========== 搜索配置 ==========
    DEFAULT_SEARCH_RESULTS = 5             # 默认搜索结果数
    MAX_SEARCH_RESULTS = 10                # 最大搜索结果数
    MIN_SEARCH_RESULTS = 3                 # 最少搜索结果数
    
    # ========== 文件管理配置 ==========
    AUTO_DELETE_FILES = False              # 是否自动删除临时文件
    TEMP_FILE_PREFIX = "ted_"              # 临时文件前缀
    
    # ========== WebSocket配置 ==========
    WS_HEARTBEAT_INTERVAL = 30             # WebSocket心跳间隔（秒）
    WS_MESSAGE_TIMEOUT = 0.1               # WebSocket消息接收超时（秒）
    
    # ========== 监控配置 ==========
    MONITORING_ENABLED = True              # 是否启用监控
    DASHBOARD_REFRESH_INTERVAL = 5         # Dashboard刷新间隔（秒）


# ==================== 模型名称枚举 ====================

class ModelName(str, Enum):
    """LLM模型名称枚举
    
    用于统一管理使用的模型
    """
    # Groq模型
    LLAMA_3_1_8B = "llama-3.1-8b-instant"          # 轻量级，快速
    LLAMA_3_3_70B = "llama-3.3-70b-versatile"      # 高级，强推理
    
    # 默认模型
    DEFAULT = "llama-3.3-70b-versatile"
    LIGHT = "llama-3.1-8b-instant"
    ADVANCED = "llama-3.3-70b-versatile"
    
    def __str__(self) -> str:
        """返回枚举值字符串"""
        return self.value


# ==================== 错误类型枚举 ====================

class ErrorType(str, Enum):
    """错误类型枚举
    
    用于分类和处理不同类型的错误
    """
    VALIDATION_ERROR = "validation_error"           # 数据验证错误
    API_ERROR = "api_error"                         # API调用错误
    RATE_LIMIT_ERROR = "rate_limit_error"          # 速率限制错误
    TIMEOUT_ERROR = "timeout_error"                 # 超时错误
    PARSING_ERROR = "parsing_error"                 # 解析错误
    NOT_FOUND_ERROR = "not_found_error"            # 资源未找到
    PERMISSION_ERROR = "permission_error"           # 权限错误
    SYSTEM_ERROR = "system_error"                   # 系统错误
    
    def __str__(self) -> str:
        """返回枚举值字符串"""
        return self.value


# ==================== 帮助函数 ====================

def get_enum_values(enum_class) -> list:
    """获取枚举类的所有值
    
    Args:
        enum_class: 枚举类
        
    Returns:
        list: 枚举值列表
        
    Example:
        >>> get_enum_values(TaskStatus)
        ['pending', 'processing', 'completed', 'failed']
    """
    return [e.value for e in enum_class]


def is_valid_enum_value(enum_class, value: str) -> bool:
    """检查值是否是有效的枚举值
    
    Args:
        enum_class: 枚举类
        value: 要检查的值
        
    Returns:
        bool: 是否有效
        
    Example:
        >>> is_valid_enum_value(TaskStatus, "pending")
        True
        >>> is_valid_enum_value(TaskStatus, "invalid")
        False
    """
    return value in get_enum_values(enum_class)
