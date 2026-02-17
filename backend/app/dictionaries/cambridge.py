"""
剑桥英汉双解词典解析器

解析 cdepe.mdx 返回的HTML
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from . import BaseParser


class CambridgeParser(BaseParser):
    """剑桥词典解析器"""

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
        "suffix": "suffix",
        "number": "num.",
        "pronoun": "pron.",
        "determiner": "det.",
        "auxiliary verb": "aux. v.",
    }

    def _parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """解析剑桥词典HTML"""
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
        elem = soup.find("span", class_="headword") or soup.find("span", class_="hw")
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
        
        for pron in soup.find_all("span", class_="pron"):
            text = self._clean_text(pron)
            classes = pron.get("class", [])
            if "uk" in classes and text:
                phonetics["uk"] = text
            elif "us" in classes and text:
                phonetics["us"] = text
        
        if not phonetics:
            ipa = soup.find(class_="ipa")
            if ipa:
                phonetics["uk"] = self._clean_text(ipa)
        
        return phonetics

    def _extract_parts(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取词性和释义"""
        parts: List[Dict[str, Any]] = []
        
        for entry_el in soup.find_all("div", class_="entry-body__el"):
            pos_header = entry_el.find("div", class_="pos-header")
            
            pos_elem = None
            if pos_header:
                pos_elem = pos_header.find("span", class_="pos")
            
            if not pos_elem:
                continue
                
            pos = self._normalize_pos(pos_elem)
            
            pos_body = entry_el.find("div", class_="pos-body")
            if not pos_body:
                continue
                
            meanings = self._extract_meanings(pos_body)
            
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

    def _extract_meanings(self, pos_body) -> List[Dict[str, Any]]:
        """提取释义列表"""
        meanings: List[Dict[str, Any]] = []
        
        for def_block in pos_body.find_all("div", class_="def-block"):
            meaning = self._parse_meaning(def_block)
            if meaning:
                meanings.append(meaning)
        
        return meanings

    def _parse_meaning(self, def_block) -> Dict[str, Any]:
        """解析单个释义"""
        # ddef_d 在 def div 里面，需要递归查找
        en_elem = def_block.find(class_=lambda x: x and 'ddef_d' in x if x else None)
        
        en = ""
        if en_elem:
            clone = BeautifulSoup(str(en_elem), 'html.parser')
            trans = clone.find(class_=lambda x: x and 'dtrans' in x if x else None)
            if trans:
                trans.extract()
            en = self._clean_text(clone)
        
        if not en:
            return {}
        
        # 中文翻译
        zh_elem = def_block.find(class_=lambda x: x and 'dtrans' in x if x else None)
        zh = self._clean_text(zh_elem) if zh_elem else ""
        
        # 例句
        examples = self._extract_examples(def_block)
        
        return {
            "en": en,
            "zh": zh,
            "examples": examples
        }

    def _extract_examples(self, parent) -> List[Dict[str, str]]:
        """提取例句"""
        examples: List[Dict[str, str]] = []
        
        for examp in parent.find_all("div", class_="examp")[:3]:
            # deg 可能在 span 或其他元素里面
            en_elem = examp.find(class_=lambda x: x and 'deg' in x if x else None)
            
            en = ""
            if en_elem:
                clone = BeautifulSoup(str(en_elem), 'html.parser')
                trans = clone.find(class_=lambda x: x and 'dtrans' in x if x else None)
                if trans:
                    trans.extract()
                en = self._clean_text(clone)
            
            zh_elem = examp.find(class_=lambda x: x and 'dtrans' in x if x else None)
            zh = self._clean_text(zh_elem) if zh_elem else ""
            
            if en:
                examples.append({"en": en, "zh": zh})
        
        return examples

    def _extract_audio(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取音频URL"""
        audio: Dict[str, str] = {}
        
        for audio_elem in soup.find_all("audio"):
            source = audio_elem.find("source")
            if source and source.get("src"):
                src = source["src"]
                if "uk" in src or "gb" in src:
                    audio["uk"] = src
                elif "us" in src:
                    audio["us"] = src
        
        return audio
