"""TED文件管理器

负责 TED txt 文件的保存、缓存、删除
"""

import hashlib
from pathlib import Path
from typing import Optional
from app.config import settings
from app.models import TedTxt


class TEDFileManager:
    """
    TED文件管理器
    
    功能：
    - 保存 TED 数据为 txt 文件
    - 检查和读取缓存文件
    - 根据配置删除文件
    - 缓存管理
    """
    
    def __init__(self):
        self.cache_dir = Path(settings.ted_cache_dir)
        # 自动创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"[FILE MANAGER] 缓存目录: {self.cache_dir}")
    
    def save_ted_file(self, ted_data: TedTxt) -> str:
        """
        保存 TED 数据为 txt 文件
        
        Args:
            ted_data: TedTxt对象
            
        Returns:
            保存的文件路径
        """
        # 根据 URL 生成唯一文件名
        filename = self._url_to_filename(ted_data.url)
        filepath = self.cache_dir / filename
        
        # 生成 txt 内容
        content = self._generate_txt_content(ted_data)
        
        # 保存文件
        try:
            filepath.write_text(content, encoding='utf-8')
            print(f"[FILE MANAGER] 文件已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[ERROR] 保存文件失败: {e}")
            raise
    
    def get_cached_file(self, url: str) -> Optional[str]:
        """
        检查 URL 是否有缓存文件
        
        Args:
            url: TED演讲URL
            
        Returns:
            文件路径（如果存在），否则None
        """
        filename = self._url_to_filename(url)
        filepath = self.cache_dir / filename
        
        if filepath.exists():
            print(f"[FILE MANAGER] 找到缓存文件: {filepath}")
            return str(filepath)
        else:
            print(f"[FILE MANAGER] 无缓存文件: {url}")
            return None
    
    def delete_file(self, filepath: str):
        """
        删除文件（根据配置）
        
        Args:
            filepath: 文件路径
        """
        if not settings.auto_delete_ted_files:
            print(f"[FILE MANAGER] 自动删除已禁用，保留文件: {filepath}")
            return
        
        try:
            file_path = Path(filepath)
            if file_path.exists():
                file_path.unlink()
                print(f"[FILE MANAGER] 文件已删除: {filepath}")
            else:
                print(f"[WARNING] 文件不存在: {filepath}")
        except Exception as e:
            print(f"[ERROR] 删除文件失败: {e}")
    
    def get_cache_size(self) -> int:
        """
        获取缓存目录总大小（字节）
        
        Returns:
            缓存总大小
        """
        total_size = 0
        try:
            for file_path in self.cache_dir.glob('*.txt'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            print(f"[ERROR] 计算缓存大小失败: {e}")
        return total_size
    
    def clear_cache(self):
        """
        清空所有缓存文件
        """
        try:
            count = 0
            for file_path in self.cache_dir.glob('ted_*.txt'):
                if file_path.is_file():
                    file_path.unlink()
                    count += 1
            print(f"[FILE MANAGER] 已清空 {count} 个缓存文件")
        except Exception as e:
            print(f"[ERROR] 清空缓存失败: {e}")
    
    def _url_to_filename(self, url: str) -> str:
        """
        将 URL 转换为唯一文件名
        
        Args:
            url: TED演讲URL
            
        Returns:
            文件名
        """
        # 使用 MD5 哈希生成唯一文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"ted_{url_hash}.txt"
    
    def _generate_txt_content(self, ted_data: TedTxt) -> str:
        """
        生成 txt 文件内容
        
        Args:
            ted_data: TedTxt对象
            
        Returns:
            文件内容字符串
        """
        return f"""Title: {ted_data.title}
Speaker: {ted_data.speaker}
URL: {ted_data.url}
Duration: {ted_data.duration}
Views: {ted_data.views}

--- Transcript ---
{ted_data.transcript}
"""


# 导出便捷函数
def save_ted_to_file(ted_data: TedTxt) -> str:
    """
    便捷函数：保存 TED 文件
    
    Args:
        ted_data: TedTxt对象
        
    Returns:
        保存的文件路径
    
    Example:
        >>> ted_data = TedTxt(...)
        >>> filepath = save_ted_to_file(ted_data)
        >>> print(filepath)
    """
    manager = TEDFileManager()
    return manager.save_ted_file(ted_data)
