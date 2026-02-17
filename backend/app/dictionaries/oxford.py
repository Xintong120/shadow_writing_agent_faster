"""
牛津高阶英汉双解词典解析器

解析 oaldpe.mdx 返回的HTML
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from . import BaseParser


class OxfordParser(BaseParser):
    """牛津词典解析器"""

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
        "combining form": "comb. form",
        "prefix": "prefix",
        "suffix": "suffix.",
    }

    def _parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """解析牛津词典HTML"""
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
        elem = soup.find("h1", class_="headword")
        if elem:
            return self._clean_text(elem)
        return ""

    def _extract_phonetic(self, soup: BeautifulSoup) -> str:
        """提取音标"""
        phonetics = self._extract_phonetics(soup)
        return phonetics.get("uk") or phonetics.get("us") or ""

    def _extract_phonetics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取音标"""
        phonetics: Dict[str, str] = {}
        
        # 查找音标元素
        phons_br = soup.find("div", class_="phons_br")
        if phons_br:
            phon = phons_br.find("span", class_="phon")
            if phon:
                phonetics["uk"] = self._clean_text(phon)
        
        phons_am = soup.find("div", class_="phons_n_am")
        if phons_am:
            phon = phons_am.find("span", class_="phon")
            if phon:
                phonetics["us"] = self._clean_text(phon)
        
        return phonetics

    def _extract_parts(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取词性和释义"""
        parts: List[Dict[str, Any]] = []
        
        # 找到主内容区
        entry = soup.find("div", class_="entry")
        if not entry:
            return parts
        
        # 从top-container获取词性
        top_container = entry.find("div", class_="top-container")
        if top_container:
            pos_elem = top_container.find("span", class_="pos")
            if pos_elem:
                pos = self._normalize_pos(pos_elem)
                
                # 获取所有义项
                meanings = self._extract_meanings(entry)
                
                if pos and meanings:
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
        
        # 查找 senses_multiple
        senses_multiple = entry.find("ol", class_="senses_multiple")
        if not senses_multiple:
            return meanings
        
        # 遍历所有 li_sense
        for child in senses_multiple.children:
            if not hasattr(child, 'get'):
                continue
            
            classes = child.get('class', [])
            if 'li_sense' not in classes:
                continue
            
            # 查找 sense
            sense = child.find("li", class_="sense")
            if not sense:
                continue
            
            meaning = self._parse_meaning(sense)
            if meaning:
                meanings.append(meaning)
        
        return meanings

    def _parse_meaning(self, sense) -> Dict[str, Any]:
        """解析单个释义"""
        # 英文释义
        def_elem = sense.find("span", class_="def")
        en = self._clean_text(def_elem) if def_elem else ""
        
        if not en:
            return {}
        
        # 中文翻译在 deft 里面的 chn
        deft = sense.find("deft")
        zh = ""
        if deft:
            chn = deft.find("chn", class_="simple")
            if chn:
                zh = self._clean_text(chn)
        
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
        
        # 查找 examples
        examples_div = sense.find("ul", class_="examples")
        if not examples_div:
            # 尝试其他方式
            examples_div = sense.find(class_=lambda x: x and 'examples' in str(x) if x else False)
        
        if examples_div:
            for li in examples_div.find_all("li", recursive=False)[:3]:
                en_elem = li.find("span", class_="eg")
                en = self._clean_text(en_elem) if en_elem else ""
                
                # 中文翻译
                zh_elem = li.find(class_=lambda x: x and 'chn' in str(x).lower() if x else False)
                zh = self._clean_text(zh_elem) if zh_elem else ""
                
                if en:
                    examples.append({"en": en, "zh": zh})
        
        return examples

    def _extract_audio(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取音频URL"""
        audio: Dict[str, str] = {}
        
        # 查找发音链接
        uk_link = soup.find("a", class_="pron-uk")
        us_link = soup.find("a", class_="pron-us")
        
        if uk_link:
            href = uk_link.get("href", "")
            if href:
                audio["uk"] = href
        
        if us_link:
            href = us_link.get("href", "")
            if href:
                audio["us"] = href
        
        return audio
