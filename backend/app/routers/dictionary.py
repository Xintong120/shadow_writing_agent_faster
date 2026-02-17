"""
离线词典查询服务

使用 mdict-query-r 直接查询 MDX 文件
"""
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

logger.remove()
logger.add("logs/dictionary.log", rotation="10 MB", level="INFO")

router = APIRouter(prefix="/api/dictionary", tags=["dictionary"])

DICTIONARY_BASE_PATH = Path(__file__).parent.parent.parent.parent / "dictionary"

SUPPORTED_DICTIONARIES = {
    "cambridge": {
        "name": "剑桥英汉双解词典",
        "mdx": "cdepe.mdx",
        "folder": "剑桥在线英汉双解词典完美版",
    },
    "oxford": {
        "name": "牛津高阶英汉双解词典",
        "mdx": "oaldpe.mdx",
        "folder": "牛津高阶英汉双解词典第10版完美版"
    },
    "webster": {
        "name": "韦氏高阶英汉双解词典",
        "mdx": "maldpe.mdx",
        "folder": "韦氏高阶英汉双解词典2019完美版"
    }
}

_querier_cache = {}


class WordDefinition(BaseModel):
    word: str
    definition: str
    phonetic: Optional[str] = None
    audio_url: Optional[str] = None
    dictionary: str
    dictionary_name: str


class StructuredDefinition(BaseModel):
    word: str
    phonetic: Optional[str] = None
    phonetics: Optional[dict] = None
    audio: Optional[dict] = None
    parts: list
    dictionary: str
    dictionary_name: str


class DictionaryInfo(BaseModel):
    id: str
    name: str
    installed: bool
    has_audio: bool
    entry_count: Optional[int] = None


def get_querier(dict_id: str):
    """获取查询器，支持缓存"""
    if dict_id in _querier_cache:
        return _querier_cache[dict_id]
    
    dict_info = SUPPORTED_DICTIONARIES.get(dict_id)
    if not dict_info:
        return None
    
    folder = dict_info.get("folder", "")
    dict_path = DICTIONARY_BASE_PATH / folder / dict_info["mdx"]
    
    if not dict_path.exists():
        return None
    
    try:
        from mdict_query_r.query import Querier, Dictionary
        
        d = Dictionary(dict_id, str(dict_path))
        q = Querier([d])
        _querier_cache[dict_id] = q
        
        logger.info(f"词典查询器已加载: {dict_id}")
        return q
        
    except Exception as e:
        logger.error(f"加载词典失败 {dict_id}: {e}")
        return None


def check_audio_files(dict_id: str, word: str) -> Optional[dict]:
    """检查音频文件是否存在"""
    dict_info = SUPPORTED_DICTIONARIES.get(dict_id)
    if not dict_info:
        return None
    
    folder = dict_info["folder"]
    audio: dict = {}
    
    audio_extensions = ['.mp3', '.wav', '.ogg']
    for ext in audio_extensions:
        uk_path = DICTIONARY_BASE_PATH / folder / "audio" / f"{word}_uk{ext}"
        us_path = DICTIONARY_BASE_PATH / folder / "audio" / f"{word}_us{ext}"
        
        if uk_path.exists():
            audio["uk"] = f"/api/dictionary/{dict_id}/audio/{word}_uk{ext}"
        if us_path.exists():
            audio["us"] = f"/api/dictionary/{dict_id}/audio/{word}_us{ext}"
    
    return audio if audio else None


@router.get("/list")
async def list_dictionaries() -> list[DictionaryInfo]:
    """获取所有可用词典列表"""
    dictionaries = []
    
    for dict_id, dict_info in SUPPORTED_DICTIONARIES.items():
        folder = dict_info["folder"]
        dict_path = DICTIONARY_BASE_PATH / folder
        mdx_path = dict_path / dict_info["mdx"]
        
        installed = mdx_path.exists()
        
        audio_path = dict_path / "audio"
        audio_exists = audio_path.exists() and any(audio_path.iterdir())
        
        entry_count = None
        if installed:
            try:
                q = get_querier(dict_id)
                if q:
                    result = q.query("hello")
                    entry_count = len(result) if result else 0
            except Exception:
                pass
        
        dictionaries.append(DictionaryInfo(
            id=dict_id,
            name=dict_info["name"],
            installed=installed,
            has_audio=audio_exists,
            entry_count=entry_count
        ))
    
    return dictionaries


@router.get("/{dict_id}/lookup")
async def lookup_word(
    dict_id: str,
    word: str = Query(..., description="要查询的单词")
) -> WordDefinition:
    """
    查询单词释义（原始HTML返回）
    
    Args:
        dict_id: 词典ID (cambridge/oxford/webster)
        word: 要查询的单词
    """
    if dict_id not in SUPPORTED_DICTIONARIES:
        raise HTTPException(status_code=400, detail=f"不支持的词典: {dict_id}")
    
    word_lower = word.lower().strip()
    folder = SUPPORTED_DICTIONARIES[dict_id]["folder"]
    
    querier = get_querier(dict_id)
    
    if querier is None:
        dict_path = DICTIONARY_BASE_PATH / folder / SUPPORTED_DICTIONARIES[dict_id]["mdx"]
        if not dict_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"词典 {SUPPORTED_DICTIONARIES.get(dict_id, {}).get('name', dict_id)} 未安装"
            )
    
    try:
        result = querier.query(word_lower)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到单词: {word}"
            )
        
        entry = result[0].entry
        key = entry.key_text
        definition = entry.data
        
        phonetic = None
        if "<pron>" in definition:
            pron_match = re.search(r'<pron[^>]*>(.*?)</pron>', definition)
            if pron_match:
                phonetic = pron_match.group(1)
        
        audio_url = None
        audio = check_audio_files(dict_id, word_lower)
        if audio:
            audio_url = audio.get("uk") or audio.get("us")
        
        return WordDefinition(
            word=key,
            definition=definition,
            phonetic=phonetic,
            audio_url=audio_url,
            dictionary=dict_id,
            dictionary_name=SUPPORTED_DICTIONARIES[dict_id]["name"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询词典失败 {dict_id}/{word}: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{dict_id}/lookup/structured")
async def lookup_word_structured(
    dict_id: str,
    word: str = Query(..., description="要查询的单词")
) -> StructuredDefinition:
    """
    查询单词释义（结构化数据返回）
    
    使用解析器将HTML解析为统一格式的JSON数据
    
    Args:
        dict_id: 词典ID (cambridge/oxford/webster)
        word: 要查询的单词
    """
    if dict_id not in SUPPORTED_DICTIONARIES:
        raise HTTPException(status_code=400, detail=f"不支持的词典: {dict_id}")
    
    word_lower = word.lower().strip()
    folder = SUPPORTED_DICTIONARIES[dict_id]["folder"]
    
    querier = get_querier(dict_id)
    
    if querier is None:
        dict_path = DICTIONARY_BASE_PATH / folder / SUPPORTED_DICTIONARIES[dict_id]["mdx"]
        if not dict_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"词典 {SUPPORTED_DICTIONARIES.get(dict_id, {}).get('name', dict_id)} 未安装"
            )
    
    try:
        result = querier.query(word_lower)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到单词: {word}"
            )
        
        entry = result[0].entry
        key = entry.key_text
        html = entry.data
        
        from app.dictionaries import parse_definition
        
        parsed = parse_definition(dict_id, html)
        
        audio = check_audio_files(dict_id, word_lower)
        if audio:
            parsed["audio"] = audio
        
        return StructuredDefinition(
            word=key,
            phonetic=parsed.get("phonetic"),
            phonetics=parsed.get("phonetics"),
            audio=parsed.get("audio"),
            parts=parsed.get("parts", []),
            dictionary=dict_id,
            dictionary_name=SUPPORTED_DICTIONARIES[dict_id]["name"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询词典失败 {dict_id}/{word}: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{dict_id}/audio/{filename}")
async def get_audio(dict_id: str, filename: str):
    """获取音频文件"""
    if dict_id not in SUPPORTED_DICTIONARIES:
        raise HTTPException(status_code=400, detail=f"不支持的词典: {dict_id}")
    
    folder = SUPPORTED_DICTIONARIES[dict_id]["folder"]
    audio_path = DICTIONARY_BASE_PATH / folder / "audio" / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")
    
    from fastapi.responses import FileResponse
    
    media_type = "audio/mpeg"
    if filename.endswith(".wav"):
        media_type = "audio/wav"
    elif filename.endswith(".ogg"):
        media_type = "audio/ogg"
    
    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=filename
    )


@router.get("/{dict_id}/search")
async def search_words(
    dict_id: str,
    prefix: str = Query(..., min_length=1, description="搜索前缀"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
) -> list[str]:
    """
    根据前缀搜索单词列表
    """
    if dict_id not in SUPPORTED_DICTIONARIES:
        raise HTTPException(status_code=400, detail=f"不支持的词典: {dict_id}")
    
    querier = get_querier(dict_id)
    
    if querier is None:
        raise HTTPException(status_code=404, detail="词典未安装")
    
    prefix_lower = prefix.lower().strip()
    
    try:
        result = querier.query(prefix_lower)
        
        words = []
        for r in result[:limit]:
            words.append(r.entry.key_text)
        
        return words
        
    except Exception as e:
        logger.error(f"搜索失败 {dict_id}/{prefix}: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/{dict_id}/reload")
async def reload_dictionary(dict_id: str):
    """重新加载词典（清除缓存）"""
    if dict_id not in SUPPORTED_DICTIONARIES:
        raise HTTPException(status_code=400, detail=f"不支持的词典: {dict_id}")
    
    if dict_id in _querier_cache:
        del _querier_cache[dict_id]
    
    querier = get_querier(dict_id)
    
    if querier is None:
        raise HTTPException(status_code=404, detail="词典文件不存在")
    
    return {"status": "reloaded", "dictionary": dict_id}
