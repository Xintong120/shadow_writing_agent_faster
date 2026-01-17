from litellm import completion
from app.config import settings
import json
import time
import asyncio
from collections import deque
from typing import Callable, Optional, Dict, Any
from app.monitoring.api_key_monitor import api_key_monitor

def ensure_dependencies():
    """检查是否有任何可用的 API key"""
    # 检查所有可用的API提供商
    available_keys = [
        settings.groq_api_key,
        settings.mistral_api_key,
        settings.openai_api_key,
        settings.deepseek_api_key
    ]

    if not any(available_keys):
        raise ValueError("No API key configured. Please set at least one of: GROQ_API_KEY, MISTRAL_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY")

    # 打印当前可用的API
    available_providers = []
    if settings.groq_api_key:
        available_providers.append("Groq")
    if settings.mistral_api_key:
        available_providers.append("Mistral")
    if settings.openai_api_key:
        available_providers.append("OpenAI")
    if settings.deepseek_api_key:
        available_providers.append("DeepSeek")

    print(f"API configured: {', '.join(available_providers)}")


def ensure_mistral_dependencies():
    """检查 Mistral API key 是否配置"""
    if not settings.mistral_api_key:
        raise ValueError("MISTRAL_API_KEY not set")
    print("Mistral API already configured")


# ==================== API Key 管理器 ====================

class APIKeyManager:
    """API Key 轮换管理器
    
    功能：
    - 管理多个 API Key 的轮询使用
    - 检测速率限制错误并自动切换
    - 对达到限制的 Key 设置冷却时间
    """
    
    def __init__(self, keys: list[str], cooldown_seconds: int = 60):
        """初始化 API Key 管理器
        
        Args:
            keys: API Key 列表
            cooldown_seconds: 冷却时间（秒），默认60秒
        """
        if not keys:
            raise ValueError("至少需要提供一个 API Key")
        
        self.keys = deque(keys)  # 使用双端队列便于轮询
        self.cooldown_seconds = cooldown_seconds
        self.key_failures = {key: 0 for key in keys}  # 记录每个 Key 的失败次数
        self.key_cooldown = {}  # 记录每个 Key 的冷却结束时间戳
        self.total_calls = 0  # 总调用次数
        self.total_switches = 0  # 总切换次数
        
        # 【监控集成】注册所有Key到监控器
        for i, key in enumerate(keys):
            key_id = f"KEY_{i+1}"
            api_key_monitor.register_key(key_id, key)
        
        print(f"API Key 管理器初始化: {len(keys)} 个 Key, 冷却时间 {cooldown_seconds}秒")
    
    def get_key(self) -> str:
        """获取当前可用的 Key
        
        Returns:
            str: 当前可用的 API Key
        """
        current_time = time.time()
        
        # 尝试找到一个不在冷却期的 Key
        for _ in range(len(self.keys)):
            key = self.keys[0]
            cooldown_until = self.key_cooldown.get(key, 0)
            
            if current_time >= cooldown_until:
                # 找到可用的 Key
                return key
            
            # 当前 Key 还在冷却，尝试下一个
            remaining_time = int(cooldown_until - current_time)
            print(f"Key ***{key[-8:]} 冷却中，剩余 {remaining_time}秒")
            self.keys.rotate(-1)
        
        # 所有 Key 都在冷却，返回第一个并等待
        key = self.keys[0]
        cooldown_until = self.key_cooldown.get(key, 0)
        wait_time = max(0, cooldown_until - current_time)
        
        if wait_time > 0:
            print(f"所有 Key 都在冷却中，等待 {int(wait_time)}秒...")
            time.sleep(wait_time)
        
        return key
    
    def rotate_key(self):
        """切换到下一个 Key"""
        self.keys.rotate(-1)
        self.total_switches += 1
        new_key = self.keys[0]
        print(f"切换到下一个 API Key: ***{new_key[-8:]}")
    
    def mark_failure(self, key: str, error_message: str):
        """标记 Key 失败并处理

        Args:
            key: 失败的 API Key
            error_message: 错误信息
        """
        self.key_failures[key] = self.key_failures.get(key, 0) + 1

        # 检查是否是速率限制或连接错误
        error_lower = error_message.lower()
        is_rate_limit = any(keyword in error_lower for keyword in [
            'rate', 'limit', 'quota', 'exceeded', 'too many'
        ])
        is_connection_error = any(keyword in error_lower for keyword in [
            'server disconnected', 'internal server error', 'connection',
            'timeout', 'network', 'service unavailable'
        ])

        # 【监控集成】获取Key ID
        key_id = self._get_key_id(key)

        if is_rate_limit or is_connection_error:
            # 对于连接错误，使用较短的冷却时间（5秒基底）
            if is_connection_error and not is_rate_limit:
                # 连接错误：较短冷却时间
                failure_count = self.key_failures[key]
                base_backoff = min(5, 2 ** (failure_count - 1))  # 连接错误基底5秒
                max_backoff = 30  # 连接错误最大30秒
                error_type = "连接错误"
            else:
                # 速率限制：指数退避策略
                failure_count = self.key_failures[key]
                base_backoff = 2 ** (failure_count - 1)  # 指数退避：1, 2, 4, 8, 16, 32...
                max_backoff = 60  # 最大等待时间60秒
                error_type = "速率限制"

            cooldown_seconds = min(base_backoff, max_backoff)

            # 添加随机抖动 (±25%) 避免惊群效应
            import random
            jitter = cooldown_seconds * 0.25 * (random.random() * 2 - 1)
            cooldown_seconds = max(1, cooldown_seconds + jitter)  # 最少1秒

            # 设置冷却时间
            cooldown_until = time.time() + cooldown_seconds
            self.key_cooldown[key] = cooldown_until

            # 【监控集成】标记冷却状态
            if key_id:
                api_key_monitor.mark_cooling(key_id, int(cooldown_seconds))

            print(f"[指数退避] Key ***{key[-8:]} 达到{error_type}，等待 {cooldown_seconds:.1f}秒")
            print(f"失败次数: {failure_count}，基础等待: {base_backoff}秒")

            # 切换到下一个 Key
            self.rotate_key()
        else:
            print(f"[ERROR] Key ***{key[-8:]} 调用失败（非限制类错误）: {error_message[:100]}")
    
    def _get_key_id(self, key: str) -> Optional[str]:
        """根据Key值获取Key ID
        
        Args:
            key: API Key值
            
        Returns:
            str: Key ID (如: KEY_1) 或 None
        """
        for i, k in enumerate(self.keys):
            if k == key:
                return f"KEY_{i+1}"
        return None
    
    def get_stats(self) -> dict:
        """获取统计信息
        
        Returns:
            dict: 包含总调用次数、切换次数、失败次数等信息
        """
        return {
            'total_keys': len(self.keys),
            'total_calls': self.total_calls,
            'total_switches': self.total_switches,
            'key_failures': dict(self.key_failures),
            'active_key': f"***{self.keys[0][-8:]}"
        }


# ==================== 并发控制管理器 ====================

class ConcurrencyLimiter:
    """并发请求限制器

    使用信号量控制同时进行的API请求数量，避免过载
    """

    def __init__(self, max_concurrent: int = 3):
        """初始化并发限制器

        Args:
            max_concurrent: 最大并发请求数，默认3个
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0
        print(f"并发限制器初始化: 最大并发 {max_concurrent} 个请求")

    async def acquire(self) -> None:
        """获取并发许可"""
        await self.semaphore.acquire()
        self.active_requests += 1
        print(f"[并发控制] 请求开始，当前活跃: {self.active_requests}/{self.max_concurrent}")

    def release(self) -> None:
        """释放并发许可"""
        self.semaphore.release()
        self.active_requests -= 1
        print(f"[并发控制] 请求完成，当前活跃: {self.active_requests}/{self.max_concurrent}")

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


# 全局并发限制器实例
concurrency_limiter: Optional[ConcurrencyLimiter] = None


def initialize_concurrency_limiter(max_concurrent: int = 3):
    """初始化并发限制器

    Args:
        max_concurrent: 最大并发请求数
    """
    global concurrency_limiter
    concurrency_limiter = ConcurrencyLimiter(max_concurrent)


# 全局 API Key 管理器实例
api_key_manager: Optional[APIKeyManager] = None

# 独立的 Mistral API Key 管理器实例
mistral_key_manager: Optional[APIKeyManager] = None


def check_key_health(key: str) -> bool:
    """
    检查单个 API Key 是否健康

    通过发送简单的测试请求来验证密钥可用性

    Args:
        key: API Key 值

    Returns:
        bool: True=健康可用, False=永久失效
    """
    try:
        # 发送一个简单的测试请求（只返回1个token节省成本）
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "test"}],
            api_key=key,
            max_tokens=1,
            temperature=0
        )

        # 检查响应是否有效
        if response and response.choices and len(response.choices) > 0:
            print(f"密钥健康: ***{key[-8:]}")
            return True
        else:
            print(f"密钥返回无效响应: ***{key[-8:]}")
            return False

    except Exception as e:
        error_msg = str(e).lower()

        # 检查是否是永久性错误（不应该重试）
        permanent_errors = [
            'organization_restricted',
            'invalid_api_key',
            'unauthorized',
            'forbidden',
            'account_disabled'
        ]

        if any(keyword in error_msg for keyword in permanent_errors):
            print(f"密钥永久失效: ***{key[-8:]} - {str(e)[:100]}")
            return False  # 永久失效
        else:
            # 临时性错误（如网络问题、临时限制），标记为健康但记录警告
            print(f"密钥暂时不可用: ***{key[-8:]} - {str(e)[:100]}")
            print("   这可能是临时问题，系统将继续尝试使用此密钥")
            return True   # 临时问题，可以重试


def initialize_key_manager(cooldown_seconds: int = 60):
    """
    初始化 API Key 管理器（带健康检查）

    Args:
        cooldown_seconds: 冷却时间（秒）
    """
    global api_key_manager

    print("\n开始 GROQ API Key 健康检查...")

    if settings.groq_api_keys and len(settings.groq_api_keys) > 1:
        # 多密钥模式：检查所有密钥健康状态
        healthy_keys = []
        unhealthy_keys = []

        for i, key in enumerate(settings.groq_api_keys):
            key_suffix = key[-8:] if len(key) >= 8 else "****"
            print(f"检查密钥 {i+1}/{len(settings.groq_api_keys)}: ***{key_suffix}")

            if check_key_health(key):
                healthy_keys.append(key)
            else:
                unhealthy_keys.append(key)

        if not healthy_keys:
            raise ValueError(f"所有 {len(settings.groq_api_keys)} 个 GROQ API Key 都不可用，请检查配置")

        api_key_manager = APIKeyManager(healthy_keys, cooldown_seconds)

        print("\n健康检查结果:")
        print(f"健康密钥: {len(healthy_keys)}/{len(settings.groq_api_keys)}")
        if unhealthy_keys:
            print(f"失效密钥: {len(unhealthy_keys)} 个（已跳过）")

        print("GROQ 多 Key 轮换已启用")

    else:
        # 单密钥模式
        api_key_manager = None
        if settings.groq_api_key:
            print("检查单密钥: ***" + settings.groq_api_key[-8:] if len(settings.groq_api_key) >= 8 else "****")

            if check_key_health(settings.groq_api_key):
                print("GROQ 单密钥模式就绪")
            else:
                raise ValueError("配置的 GROQ API Key 不可用，请检查配置")
        else:
            print("未配置 GROQ API Key")


def check_mistral_key_health(key: str) -> bool:
    """
    检查单个 Mistral API Key 是否健康

    通过发送简单的测试请求来验证密钥可用性

    Args:
        key: Mistral API Key 值

    Returns:
        bool: True=健康可用, False=永久失效
    """
    try:
        # 发送一个简单的测试请求（只返回1个token节省成本）
        response = completion(
            model=f"mistral/{settings.mistral_model_name}",
            messages=[{"role": "user", "content": "test"}],
            api_key=key,
            max_tokens=1,
            temperature=0
        )

        # 检查响应是否有效
        if response and response.choices and len(response.choices) > 0:
            print(f"Mistral 密钥健康: ***{key[-8:]}")
            return True
        else:
            print(f"Mistral 密钥返回无效响应: ***{key[-8:]}")
            return False

    except Exception as e:
        error_msg = str(e).lower()

        # 检查是否是永久性错误（不应该重试）
        permanent_errors = [
            'organization_restricted',
            'invalid_api_key',
            'unauthorized',
            'forbidden',
            'account_disabled'
        ]

        if any(keyword in error_msg for keyword in permanent_errors):
            print(f"Mistral 密钥永久失效: ***{key[-8:]} - {str(e)[:100]}")
            return False  # 永久失效
        else:
            # 临时性错误（如网络问题、临时限制），标记为健康但记录警告
            print(f"Mistral 密钥暂时不可用: ***{key[-8:]} - {str(e)[:100]}")
            print("   这可能是临时问题，系统将继续尝试使用此密钥")
            return True   # 临时问题，可以重试


def initialize_mistral_key_manager(cooldown_seconds: int = 60):
    """
    初始化独立的 Mistral API Key 管理器（带健康检查）

    Args:
        cooldown_seconds: 冷却时间（秒）
    """
    global mistral_key_manager

    print("\n开始 Mistral API Key 健康检查...")

    if settings.mistral_api_keys and len(settings.mistral_api_keys) > 1:
        # 多密钥模式：检查所有密钥健康状态
        healthy_keys = []
        unhealthy_keys = []

        for i, key in enumerate(settings.mistral_api_keys):
            key_suffix = key[-8:] if len(key) >= 8 else "****"
            print(f"检查 Mistral 密钥 {i+1}/{len(settings.mistral_api_keys)}: ***{key_suffix}")

            if check_mistral_key_health(key):
                healthy_keys.append(key)
            else:
                unhealthy_keys.append(key)

        if healthy_keys:
            mistral_key_manager = APIKeyManager(healthy_keys, cooldown_seconds)

            print("\nMistral 健康检查结果:")
            print(f"健康密钥: {len(healthy_keys)}/{len(settings.mistral_api_keys)}")
            if unhealthy_keys:
                print(f"失效密钥: {len(unhealthy_keys)} 个（已跳过）")

            print("Mistral 多 Key 轮换已启用")
        else:
            print(f"\nMistral 健康检查结果:")
            print(f"所有 {len(settings.mistral_api_keys)} 个 API Key 都不可用")
            print("Mistral 将使用单密钥模式（如果配置了单个key）")
            mistral_key_manager = None

    else:
        # 单密钥模式
        mistral_key_manager = None
        if settings.mistral_api_key:
            print("检查 Mistral 单密钥: ***" + settings.mistral_api_key[-8:] if len(settings.mistral_api_key) >= 8 else "****")

            if check_mistral_key_health(settings.mistral_api_key):
                print("Mistral 单密钥模式就绪")
            else:
                raise ValueError("配置的 Mistral API Key 不可用，请检查配置")
        else:
            print("未配置 Mistral API Key")


# ==================== LLM 调用函数 ====================

def create_llm_function(system_prompt: Optional[str] = None, model: Optional[str] = None) -> Callable:
    """创建 LLM 调用函数

    Args:
        system_prompt: 系统提示词（可选）
        model: 模型名称（可选，默认使用settings.model_name）

    Returns:
        callable: LLM 调用函数
    """

    def call_llm(user_prompt: str, output_format: Optional[Dict] = None, temperature: Optional[float] = None, _retry_count: int = 0) -> Any:
        """调用 LLM（支持自动 Key 切换）

        Args:
            user_prompt: 用户提示词
            output_format: 输出格式字典（如果指定，则返回 JSON）
            temperature: 温度参数（可选）
            _retry_count: 重试计数（内部使用）

        Returns:
            str or dict: LLM 响应内容
        """
        # 获取当前可用的 API Key
        if api_key_manager:
            current_key = api_key_manager.get_key()
            api_key_manager.total_calls += 1
            key_id = api_key_manager._get_key_id(current_key)
        else:
            current_key = settings.groq_api_key
            key_id = None

        start_time = time.time()  # 【监控集成】记录开始时间

        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            # 调用参数
            kwargs = {
                "model": f"groq/{model or settings.model_name}",  # 使用传入的model或默认值
                "messages": messages,
                "temperature": temperature if temperature is not None else settings.temperature,
                "api_key": current_key,  # 使用当前 Key
            }

            # 如果需要 JSON 输出
            if output_format:
                kwargs["response_format"] = {"type": "json_object"}

            # 调用 LiteLLM
            response = completion(**kwargs)
            content = response.choices[0].message.content

            # 【监控集成】记录成功调用
            if key_id:
                response_time = time.time() - start_time
                # 尝试从response中获取响应头（LiteLLM可能不提供）
                response_headers = getattr(response, '_hidden_params', {}).get('response_headers', None)
                api_key_monitor.record_call(
                    key_id=key_id,
                    success=True,
                    response_time=response_time,
                    rate_limited=False,
                    response_headers=response_headers
                )

            # 解析 JSON
            if output_format:
                return json.loads(content)

            return content

        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            # 【监控集成】记录失败（JSON解析错误也算失败）
            if key_id:
                response_time = time.time() - start_time
                api_key_monitor.record_call(
                    key_id=key_id,
                    success=False,
                    response_time=response_time,
                    rate_limited=False
                )
            return None

        except Exception as e:
            error_msg = str(e)

            # 检测是否是速率限制或连接错误
            is_rate_limit_or_connection = any(keyword in error_msg.lower() for keyword in [
                'rate', 'limit', 'quota', 'exceeded', 'too many',
                'server disconnected', 'internal server error', 'connection',
                'timeout', 'network', 'service unavailable'
            ])

            # 【监控集成】记录失败调用
            if key_id:
                response_time = time.time() - start_time
                api_key_monitor.record_call(
                    key_id=key_id,
                    success=False,
                    response_time=response_time,
                    rate_limited=is_rate_limit_or_connection
                )

            if is_rate_limit_or_connection and api_key_manager:
                # 标记当前 Key 失败
                api_key_manager.mark_failure(current_key, error_msg)

                # 限制重试次数（最多重试 Key 数量次）
                max_retries = len(api_key_manager.keys)
                if _retry_count < max_retries:
                    print(f"[RETRY] 重试中... ({_retry_count + 1}/{max_retries})")
                    # 递归重试（会自动使用下一个 Key）
                    return call_llm(user_prompt, output_format, temperature, _retry_count + 1)
                else:
                    print("[ERROR] 所有 API Key 都已尝试，仍然失败")
                    return None
            else:
                # 非速率限制错误或没有管理器
                print(f"LLM call failed: {e}")
                return None

    return call_llm


def create_llm_function_native() -> Callable:
    """创建原生 LLM 函数（兼容旧代码）

    使用 settings.model_name 配置的默认模型

    Returns:
        callable: LLM 调用函数
    """
    return create_llm_function(system_prompt=settings.system_prompt)


def create_llm_function_mistral(system_prompt: Optional[str] = None, small_model: Optional[str] = None) -> Callable:
    """创建独立的 Mistral LLM 函数

    使用 Mistral API 和独立配置，不依赖 Groq

    Args:
        system_prompt: 系统提示词（可选）
        small_model: 轻量级Mistral模型名称（可选，默认使用settings.mistral_model_name）

    Returns:
        callable: LLM 调用函数
    """
    def call_llm_mistral(user_prompt: str, output_format: Optional[Dict] = None, temperature: Optional[float] = None, _retry_count: int = 0) -> Any:
        """调用 Mistral LLM（支持独立 Key 轮换）

        Args:
            user_prompt: 用户提示词
            output_format: 输出格式字典（如果指定，则返回 JSON）
            temperature: 温度参数（可选）
            _retry_count: 重试计数（内部使用）

        Returns:
            str or dict: LLM 响应内容
        """
        # 获取当前可用的 Mistral API Key
        if mistral_key_manager:
            current_key = mistral_key_manager.get_key()
            mistral_key_manager.total_calls += 1
        else:
            current_key = settings.mistral_api_key

        start_time = time.time()

        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            # 调用参数
            kwargs = {
                "model": f"mistral/{small_model or settings.mistral_model_name}",  # 使用传入的small_model或默认配置
                "messages": messages,
                "temperature": temperature if temperature is not None else 0.1,
                "max_tokens": 4096,
                "api_key": current_key,  # 使用轮换的 Key
            }

            # 如果需要 JSON 输出
            if output_format:
                kwargs["response_format"] = {"type": "json_object"}

            # 调用 LiteLLM
            response = completion(**kwargs)
            content = response.choices[0].message.content

            # 解析 JSON
            if output_format:
                return json.loads(content) if content else None

            return content

        except json.JSONDecodeError as e:
            print(f"Mistral JSON parsing failed: {e}")
            return None

        except Exception as e:
            error_msg = str(e)

            # 检测是否是速率限制或连接错误
            is_rate_limit_or_connection = any(keyword in error_msg.lower() for keyword in [
                'rate', 'limit', 'quota', 'exceeded', 'too many',
                'server disconnected', 'internal server error', 'connection',
                'timeout', 'network', 'service unavailable'
            ])

            if is_rate_limit_or_connection and mistral_key_manager:
                # 标记当前 Key 失败
                mistral_key_manager.mark_failure(current_key, error_msg)

                # 限制重试次数（最多重试 Key 数量次）
                max_retries = len(mistral_key_manager.keys)
                if _retry_count < max_retries:
                    print(f"[Mistral RETRY] 重试中... ({_retry_count + 1}/{max_retries})")
                    # 递归重试（会自动使用下一个 Key）
                    return call_llm_mistral(user_prompt, output_format, temperature, _retry_count + 1)
                else:
                    print("[Mistral ERROR] 所有 API Key 都已尝试，仍然失败")
                    return None
            else:
                # 非速率限制错误
                print(f"Mistral LLM call failed: {e}")
                return None

    return call_llm_mistral


def create_llm_function_light(system_prompt: Optional[str] = None) -> Callable:
    """创建轻量级LLM函数，智能选择最快的可用模型

    适用场景：
    - 关键词提取和优化
    - 简单文本转换
    - 快速分类任务
    - 不需要复杂推理的任务

    优先级：
    1. GROQ llama-3.1-8b-instant (最快)
    2. Mistral mistral-small-2506 (轻量级替代)

    Args:
        system_prompt: 系统提示词（可选）

    Returns:
        callable: LLM 调用函数

    Raises:
        ValueError: 当没有任何轻量级API可用时

    Example:
        >>> llm = create_llm_function_light()
        >>> result = llm("Translate to English: 人工智能", {"translation": "str"})
    """
    # 检查可用的API
    available_apis = []
    if settings.groq_api_key:
        available_apis.append("groq")
    if settings.mistral_api_key:
        available_apis.append("mistral")

    # 优先级：GROQ (最快) > Mistral
    if "groq" in available_apis:
        # 使用GROQ llama-3.1-8b-instant
        return create_llm_function(system_prompt=system_prompt, model="llama-3.1-8b-instant")
    elif "mistral" in available_apis:
        # 使用Mistral mistral-small-2506 (轻量级)
        return create_llm_function_mistral(system_prompt=system_prompt, small_model="mistral-small-2506")
    else:
        raise ValueError("No lightweight API available. Please configure GROQ_API_KEY or MISTRAL_API_KEY")


def create_llm_function_advanced(system_prompt: Optional[str] = None) -> Callable:
    """创建高级 LLM 调用函数（llama-3.3-70b-versatile）
    
    适用场景：
    - 复杂推理任务
    - 质量评估和打分
    - 错误修正和改进
    - 需要深度理解的任务
    
    特点：
    - 推理能力强
    - 适合复杂任务
    - 响应较慢（约2-3秒）
    
    Args:
        system_prompt: 系统提示词（可选）
        
    Returns:
        callable: LLM 调用函数
        
    Example:
        >>> llm = create_llm_function_advanced()
        >>> result = llm(correction_prompt, correction_format)
    """
    return create_llm_function(system_prompt=system_prompt, model="llama-3.3-70b-versatile")
