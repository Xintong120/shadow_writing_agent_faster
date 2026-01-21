# config.py
# 作用：配置管理
# 功能：
#   - 读取环境变量（GROQ_API_KEY）
#   - 模型配置（model_name: llama-3.1-8b-instant）
#   - 系统参数配置

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Any, List
import os
from pathlib import Path
from dotenv import load_dotenv

# 显式加载根目录的.env文件
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"[OK] 已加载配置文件: {env_path}")
else:
    print(f"[WARNING] 未找到配置文件: {env_path}")

class Settings(BaseSettings):
    # api配置
    groq_api_key: str = ""
    groq_api_keys: list[str] = []
    mistral_api_key: str = ""  # Mistral API Key (独立配置)
    mistral_api_keys: list[str] = []  # Mistral API Keys 列表 (独立轮换) - 在 model_post_init 中解析
    mistral_model_name: str = "mistral-large-3"  # Mistral 模型名称
    tavily_api_key: str = ""  # Tavily API Key
    openai_api_key: str = ""  # OpenAI API Key
    deepseek_api_key: str = ""  # DeepSeek API Key
    
    # 模型配置
    model_name: str = "llama-3.3-70b-versatile"  # 12K TPM (2倍于3.1-8b)，更强大的70B模型
    system_prompt: str = "You are a helpful assistant."
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    
    # FastAPI配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # CORS配置
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # API轮换配置
    api_rotation_enabled: bool = False
    current_api_provider: str = "groq"
    api_providers: list[str] = ["groq", "mistral", "openai", "deepseek"]

    # Shadow Writing 提供商选择
    use_mistral_for_shadow_writing: bool = False  # 是否使用 Mistral 进行 Shadow Writing

    # Langfuse监控配置
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
    
    # TED文件管理（缓存、删除）
    ted_cache_dir: str = "./data/ted_cache"
    auto_delete_ted_files: bool = False
    max_cache_size_mb: int = 500
    
    # 外观设置
    theme_mode: str = "light"  # light, dark, system
    font_size: str = "medium"  # small, medium, large
    
    # 学习偏好
    auto_save_progress: bool = True
    show_learning_stats: bool = True
    enable_keyboard_shortcuts: bool = True
    
    class Config:
        # .env文件在项目根目录（backend的父目录）
        env_file = "../.env"
        env_file_encoding = "utf-8"  # 文件编码
        case_sensitive = False  # 环境变量不区分大小写
        extra = "allow"  # 允许额外的环境变量（用于 GROQ_API_KEY_1, GROQ_API_KEY_2 等）

    def model_post_init(self, __context: Any) -> None:
        """初始化后自动读取多个 API Key"""
        # 确保 .env 文件已加载
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)

        # 如果已经从环境变量加载了API Keys（JSON格式），则跳过手动解析
        if self.groq_api_keys:
            print(f"从 GROQ_API_KEYS (JSON) 读取到 {len(self.groq_api_keys)} 个 API Key")
            # 设置默认Key（第一个）
            if not self.groq_api_key:
                self.groq_api_key = self.groq_api_keys[0]
            # 继续处理其他keys，不要return

        keys = []

        # 方法1: 尝试读取 GROQ_API_KEYS（逗号分隔格式，向后兼容）
        api_keys_str = os.getenv("GROQ_API_KEYS", "")
        if api_keys_str:
            keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
            print(f"从 GROQ_API_KEYS (逗号分隔) 读取到 {len(keys)} 个 API Key")

        # 方法2: 尝试读取所有 GROQ_API_KEY_开头的环境变量（向后兼容）
        if not keys:
            for key_name, value in os.environ.items():
                if key_name.startswith('GROQ_API_KEY_') and key_name != 'GROQ_API_KEY' and value:
                    keys.append(value)
            if keys:
                print(f"从 GROQ_API_KEY_* 读取到 {len(keys)} 个 API Key")

        # 方法3: 尝试读取单个 GROQ_API_KEY（向后兼容）
        if not keys and self.groq_api_key:
            keys = [self.groq_api_key]
            print("从 GROQ_API_KEY 读取到 1 个 API Key")

        # 设置API Keys
        if keys:
            self.groq_api_keys = keys
            # 设置默认Key（第一个）
            if not self.groq_api_key:
                self.groq_api_key = keys[0]
        else:
            print("[WARNING] 未找到任何 GROQ API Key 配置")
            print("请在 .env 文件中配置: GROQ_API_KEYS=[\"gsk_xxxxx1\",\"gsk_xxxxx2\"] 或 GROQ_API_KEYS=gsk_xxxxx1,gsk_xxxxx2")

        # 处理 Mistral API Keys（独立轮换）
        mistral_keys = []

        # 方法: 尝试读取所有 MISTRAL_API_KEY_ 开头的环境变量
        for key_name, value in os.environ.items():
            if key_name.startswith('MISTRAL_API_KEY_') and key_name != 'MISTRAL_API_KEY' and value:
                mistral_keys.append(value)
        if mistral_keys:
            print(f"从 MISTRAL_API_KEY_* 读取到 {len(mistral_keys)} 个 Mistral API Key")

        # 方法: 尝试读取单个 MISTRAL_API_KEY
        if not mistral_keys and self.mistral_api_key:
            mistral_keys = [self.mistral_api_key]
            print("从 MISTRAL_API_KEY 读取到 1 个 Mistral API Key")

        # 设置 Mistral API Keys
        if mistral_keys:
            self.mistral_api_keys = mistral_keys
            # 设置默认Key（第一个）
            if not self.mistral_api_key:
                self.mistral_api_key = mistral_keys[0]

    def get_available_api_providers(self) -> List[str]:
        """获取可用的API提供商列表"""
        providers = []
        if self.groq_api_key or self.groq_api_keys:
            providers.append("groq")
        if self.mistral_api_key:
            providers.append("mistral")
        if self.openai_api_key:
            providers.append("openai")
        if self.deepseek_api_key:
            providers.append("deepseek")
        return providers

    def rotate_api_key(self) -> str:
        """轮换到下一个可用的API Key"""
        available_providers = self.get_available_api_providers()
        if not available_providers:
            return self.groq_api_key  # 返回默认key
        
        current_index = available_providers.index(self.current_api_provider) if self.current_api_provider in available_providers else -1
        next_index = (current_index + 1) % len(available_providers)
        next_provider = available_providers[next_index]
        
        self.current_api_provider = next_provider
        
        # 返回对应提供商的API key
        if next_provider == "groq":
            return self.groq_api_key
        elif next_provider == "openai":
            return self.openai_api_key
        elif next_provider == "deepseek":
            return self.deepseek_api_key
        
        return self.groq_api_key

    def get_current_api_key(self) -> str:
        """获取当前使用的API Key"""
        if self.current_api_provider == "openai":
            return self.openai_api_key
        elif self.current_api_provider == "deepseek":
            return self.deepseek_api_key
        else:
            return self.groq_api_key

settings = Settings()

# 验证配置
def validate_config():
    """验证所有必需的配置项"""
    errors = []

    # 1. 必需的API Keys
    if not settings.tavily_api_key:
        errors.append("TAVILY_API_KEY 必须设置（用于搜索功能）")

    # 2. 至少需要一个主要的llmAPI提供商
    main_api_keys = [settings.groq_api_key, settings.mistral_api_key, settings.openai_api_key, settings.deepseek_api_key]
    if not any(main_api_keys):
        errors.append("至少需要设置一个主要API提供商 (GROQ/Mistral/OpenAI/DeepSeek)")

    # 3. 如果启用了API轮换，需要至少两个GROQ API Keys
    if settings.api_rotation_enabled:
        if len(settings.groq_api_keys) < 2:
            errors.append("启用API轮换时，需要至少两个GROQ API Keys")

    # 4. 至少要有一个可用的提供商有对应的API Key
    available_providers = settings.get_available_api_providers()
    if not available_providers:
        errors.append("至少需要一个API提供商有有效的API Key")

    # 如果当前提供商不可用，自动切换到第一个可用的提供商
    if settings.current_api_provider not in available_providers and available_providers:
        settings.current_api_provider = available_providers[0]
        print(f"自动切换当前API提供商到: {settings.current_api_provider}")

    # 5. 验证llm模型配置合理性
    if not (0 <= settings.temperature <= 2):
        errors.append("temperature 必须在 0-2 之间")

    if not (1 <= settings.max_tokens <= 8192):
        errors.append("max_tokens 必须在 1-8192 之间")

    if not (0 <= settings.top_p <= 1):
        errors.append("top_p 必须在 0-1 之间")

    if not (-2 <= settings.frequency_penalty <= 2):
        errors.append("frequency_penalty 必须在 -2-2 之间")

    # 如果有错误，抛出异常
    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(f"- {error}" for error in errors))

    # 打印当前配置
    print("配置验证通过")
    available_providers = settings.get_available_api_providers()
    print(f"可用提供商: {', '.join(available_providers) if available_providers else '无'}")
    print(f"当前提供商: {settings.current_api_provider}")
    print(f"使用模型: {settings.model_name}")
    print(f"温度: {settings.temperature}")
    print(f"API轮换: {'启用' if settings.api_rotation_enabled else '禁用'}")
    if settings.api_rotation_enabled:
        print(f"GROQ API Keys 数量: {len(settings.groq_api_keys)}")

# 获取设置字典（用于前端）
def get_settings_dict():
    """返回前端需要的设置字典"""
    return {
        # API配置
        "backend_api_url": f"http://{settings.api_host}:{settings.api_port}",
        "groq_api_key": settings.groq_api_key,
        "groq_api_keys": settings.groq_api_keys,
        "tavily_api_key": settings.tavily_api_key,
        "openai_api_key": settings.openai_api_key,
        "deepseek_api_key": settings.deepseek_api_key,
        "api_rotation_enabled": settings.api_rotation_enabled,
        "current_api_provider": settings.current_api_provider,

        # 外观设置
        "theme_mode": settings.theme_mode,
        "font_size": settings.font_size,

        # 学习偏好
        "auto_save_progress": settings.auto_save_progress,
        "show_learning_stats": settings.show_learning_stats,
        "enable_keyboard_shortcuts": settings.enable_keyboard_shortcuts,

        # LLM配置
        "model_name": settings.model_name,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "top_p": settings.top_p,
        "frequency_penalty": settings.frequency_penalty,

        # 可用API提供商
        "available_providers": settings.get_available_api_providers() if settings else [],
    }

# 更新设置（从前端接收）
def update_settings(settings_dict: dict):
    """更新设置"""
    global settings
    
    for key, value in settings_dict.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
        else:
            print(f"[WARNING] Unknown setting: {key}")
    
    print("Settings updated successfully")
