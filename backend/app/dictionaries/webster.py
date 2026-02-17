"""
韦氏高阶英汉双解词典解析器

解析 maldpe.mdx 返回的HTML
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from . import BaseParser


class WebsterParser(BaseParser):
    """韦氏词典解析器"""

    POS_MAP = {
        "noun": "n.",
        "verb": "v.",
        "adjective": "adj.",
        "adverb": "adv.",
        "abbreviation": "abbr.",
        "exclamation": "interj.",
        "idiom": "idiom",
        "conjunction": "conj.",
        "preposition": "prep.",
        "modal verb": "modal v.",
        "pronoun": "pron.",
        "determiner": "det.",
    }

    def _parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """解析韦氏词典HTML"""
        result = {
            "word": self._extract_word(soup),
            "phonetic": self._extract_phonetic(soup),
            "phonetics": self._extract_phonetics(soup),
            "audio": {},
            "parts": self._extract_parts(soup),
            "dictionary": self.dict_id
        }

        result["audio"] = self._extract_audio(soup)

        return result

    def _extract_word(self, soup: BeautifulSoup) -> str:
        """提取单词"""
        elem = soup.find("span", class_="hw_txt")
        if elem:
            return self._clean_text(elem)
        
        # 备选
        h1 = soup.find("h1")
        if h1:
            return self._clean_text(h1)
        
        return ""

    def _extract_phonetic(self, soup: BeautifulSoup) -> str:
        """提取音标"""
        phonetics = self._extract_phonetics(soup)
        return phonetics.get("uk") or phonetics.get("us") or ""

    def _extract_phonetics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取音标"""
        phonetics: Dict[str, str] = {}
        
        # 查找音标
        hpron = soup.find("span", class_="hpron_word")
        if hpron:
            text = self._clean_text(hpron)
            phonetics["uk"] = text
        
        return phonetics

    def _extract_parts(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取词性和释义"""
        parts: List[Dict[str, Any]] = []
        
        # 找到主内容区
        entry = soup.find("div", class_="entry_v2")
        if not entry:
            return parts
        
        # 获取词性
        fl_elem = entry.find("span", class_="fl")
        pos = self._normalize_pos(fl_elem) if fl_elem else ""
        
        if not pos:
            return parts
        
        # 获取所有义项
        meanings = self._extract_meanings(entry)
        
        if meanings:
            parts.append({
                "pos": pos,
                "meanings": meanings
            })
        
        return parts

    def _normalize_pos(self, element) -> str:
        """标准化词性"""
        if element is None:
            return ""
        text = self._clean_text(element)
        return self.POS_MAP.get(text.lower(), text)

    def _extract_meanings(self, entry) -> List[Dict[str, Any]]:
        """提取释义列表"""
        meanings: List[Dict[str, Any]] = []
        
        for sense in entry.find_all("div", class_="sense"):
            meaning = self._parse_meaning(sense)
            if meaning:
                meanings.append(meaning)
        
        return meanings

    def _parse_meaning(self, sense) -> Dict[str, Any]:
        """解析单个释义"""
        # 英文释义
        def_elem = sense.find("span", class_="def_text")
        en = self._clean_text(def_elem) if def_elem else ""
        
        # 清理英文中混合的中文
        if en:
            # 移除末尾的中文
            import re
            en = re.sub(r'[\u4e00-\u9fff]+$', '', en).strip()
        
        if not en:
            return {}
        
        # 中文翻译
        zh_elem = sense.find("span", class_="mw_zh")
        zh = self._clean_text(zh_elem) if zh_elem else ""
        
        # 例句
        examples = self._extract_examples(sense)
        
        return {
            "en": en,
            "zh": zh,
            "examples": examples
        }

    def _extract_examples(self, sense) -> List[Dict[str, str]]:
        """提取例句"""
        examples: List[Dict[str, str]] = []
        
        # 查找例句容器
        vis_w = sense.find("div", class_="vis_w")
        if vis_w:
            for vi in vis_w.find_all("li", class_="vi")[:3]:
                en_elem = vi.find("span", class_="vi_content")
                en = self._clean_text(en_elem) if en_elem else ""
                
                zh_elem = vi.find("span", class_="mw_zh")
                zh = self._clean_text(zh_elem) if zh_elem else ""
                
                if en:
                    examples.append({"en": en, "zh": zh})
        
        return examples

    def _extract_audio(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取音频URL"""
        audio: Dict[str, str] = {}
        
        # 查找发音链接
        play_pron = soup.find("a", class_="play_pron")
        if play_pron:
            data_dir = play_pron.get("data-dir", "")
            data_file = play_pron.get("data-file", "")
            
            if data_dir and data_file:
                audio_url = f"https://media.merriam-webster.com/audio/prons/{data_dir}/{data_file}.mp3"
                if data_dir == "b" or "british" in data_dir.lower():
                    audio["uk"] = audio_url
                else:
                    audio["us"] = audio_url
        
        return audio
