# settings.py
# 设置相关的API路由
# 功能：
#   - 获取当前设置
#   - 更新设置
#   - 测试API连接

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx
import asyncio
from ..config import settings, get_settings_dict, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Pydantic模型
class SettingsUpdateRequest(BaseModel):
    """设置更新请求模型"""
    # API配置
    backend_api_url: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_api_keys: Optional[List[str]] = None
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    api_rotation_enabled: Optional[bool] = None
    current_api_provider: Optional[str] = None
    
    # 外观设置
    theme_mode: Optional[str] = None
    font_size: Optional[str] = None
    
    # 学习偏好
    auto_save_progress: Optional[bool] = None
    show_learning_stats: Optional[bool] = None
    enable_keyboard_shortcuts: Optional[bool] = None
    
    # LLM配置
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None

class ApiKeyTestRequest(BaseModel):
    """API密钥测试请求模型"""
    provider: str
    api_key: str

class ApiKeyTestResponse(BaseModel):
    """API密钥测试响应模型"""
    success: bool
    message: str
    provider: str
    response_time: Optional[float] = None

@router.get("/")
async def get_settings():
    """获取当前设置"""
    try:
        return {
            "success": True,
            "data": get_settings_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设置失败: {str(e)}")

@router.put("/")
async def update_settings_endpoint(request: SettingsUpdateRequest):
    """更新设置"""
    try:
        # 过滤出非None的值
        settings_dict = {}
        for key, value in request.dict(exclude_unset=True).items():
            if value is not None:
                settings_dict[key] = value
        
        update_settings(settings_dict)
        
        return {
            "success": True,
            "message": "设置更新成功",
            "data": get_settings_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")

@router.post("/test-api-key")
async def test_api_key(request: ApiKeyTestRequest):
    """测试API密钥连接"""
    try:
        import time
        start_time = time.time()
        
        # 根据提供商类型进行不同的测试
        if request.provider == "openai":
            # 测试OpenAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="OpenAI API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"OpenAI API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                    
        elif request.provider == "deepseek":
            # 测试DeepSeek API (假设使用OpenAI兼容接口)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="DeepSeek API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"DeepSeek API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                    
        elif request.provider == "groq":
            # 测试Groq API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="Groq API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"Groq API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()

        elif request.provider == "tavily":
            # 测试Tavily Search API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "query": "test",
                        "api_key": request.api_key
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="Tavily API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"Tavily API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
        else:
            raise HTTPException(status_code=400, detail=f"不支持的API提供商: {request.provider}")
            
    except asyncio.TimeoutError:
        return ApiKeyTestResponse(
            success=False,
            message="API连接超时",
            provider=request.provider
        ).dict()
    except Exception as e:
        return ApiKeyTestResponse(
            success=False,
            message=f"API连接测试失败: {str(e)}",
            provider=request.provider
        ).dict()

@router.post("/rotate-api-key")
async def rotate_api_key():
    """轮换到下一个可用的API密钥"""
    try:
        next_key = settings.rotate_api_key()
        return {
            "success": True,
            "message": "API密钥轮换成功",
            "current_provider": settings.current_api_provider,
            "has_key": bool(next_key)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API密钥轮换失败: {str(e)}")

@router.get("/api-providers")
async def get_api_providers():
    """获取可用的API提供商列表"""
    try:
        providers = settings.get_available_api_providers()
        return {
            "success": True,
            "data": {
                "available_providers": providers,
                "current_provider": settings.current_api_provider,
                "rotation_enabled": settings.api_rotation_enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取API提供商列表失败: {str(e)}")
