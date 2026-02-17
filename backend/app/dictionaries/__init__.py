"""
词典解析器模块

提供统一的解析接口，将不同词典的HTML解析为结构化数据
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger


class BaseParser(ABC):
    """词典解析器基类"""

    def __init__(self, dict_id: str):
        self.dict_id = dict_id

    def parse(self, html: str) -> Dict[str, Any]:
        """
        解析HTML，返回统一结构

        Args:
            html: MDX返回的原始HTML

        Returns:
            统一格式的字典
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return self._parse(soup)
        except Exception as e:
            logger.error(f"解析词典 {self.dict_id} 失败: {e}")
            return {
                "word": "",
                "phonetic": None,
                "phonetics": {},
                "audio": None,
                "parts": [],
                "dictionary": self.dict_id,
                "error": str(e)
            }

    @abstractmethod
    def _parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """内部解析方法，由子类实现"""
        pass

    def _clean_text(self, element) -> str:
        """清理元素文本"""
        if element is None:
            return ""
        text = element.get_text(strip=True)
        text = ' '.join(text.split())
        return text

    def _get_attr(self, element, attr: str, default: str = "") -> str:
        """获取元素属性"""
        if element is None:
            return default
        return element.get(attr, default)


from .cambridge import CambridgeParser
from .oxford import OxfordParser
from .webster import WebsterParser
from .factory import get_parser, parse_definition

__all__ = [
    'BaseParser',
    'CambridgeParser',
    'OxfordParser',
    'WebsterParser',
    'get_parser',
    'parse_definition',
]
