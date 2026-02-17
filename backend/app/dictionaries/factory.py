"""
词典解析器工厂

根据词典ID返回对应的解析器
"""

from typing import Dict, Type
from . import BaseParser
from .cambridge import CambridgeParser
from .oxford import OxfordParser
from .webster import WebsterParser

PARSERS: Dict[str, Type[BaseParser]] = {
    "cambridge": CambridgeParser,
    "oxford": OxfordParser,
    "webster": WebsterParser,
}


def get_parser(dict_id: str) -> BaseParser:
    """
    根据词典ID获取解析器

    Args:
        dict_id: 词典ID (cambridge/oxford/webster)

    Returns:
        对应的解析器实例

    Raises:
        ValueError: 不支持的词典ID
    """
    if dict_id not in PARSERS:
        raise ValueError(f"不支持的词典: {dict_id}")
    
    parser_class = PARSERS[dict_id]
    return parser_class(dict_id)


def parse_definition(dict_id: str, html: str) -> dict:
    """
    解析词典HTML为统一结构

    Args:
        dict_id: 词典ID
        html: 原始HTML

    Returns:
        统一格式的字典
    """
    parser = get_parser(dict_id)
    return parser.parse(html)
