"""Store Factory - 根据配置创建Store实例"""

import os
from typing import Optional, Dict, Set
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

def create_store() -> BaseStore:
    """根据环境变量创建Store实例
    
    Returns:
        Store实例（InMemoryStore, SQLiteStore或PostgresStore）
    """
    store_type = os.getenv("MEMORY_STORE_TYPE", "sqlite").lower()
    
    if store_type == "sqlite":
        # Electron桌面应用：SQLite本地存储
        try:
            from app.memory.postgres_store import SQLiteStore
            
            db_path = os.getenv("SQLITE_DB_PATH")  # 可选：自定义数据库路径
            store = SQLiteStore(db_path=db_path)
            
            print("[Memory] 使用SQLiteStore（桌面应用）")
            return store
            
        except Exception as e:
            print(f"[Memory] [WARNING] SQLite配置失败: {e}")
            print("[Memory] 降级使用InMemoryStore")
            return InMemoryStore()
    
    elif store_type == "postgres":
        # 生产环境：使用LangGraph官方PostgresStore
        try:
            from langgraph.store.postgres import PostgresStore
            
            postgres_uri = os.getenv("POSTGRES_URI")
            if not postgres_uri:
                raise ValueError("POSTGRES_URI环境变量未设置")
            
            # 隐藏密码的日志输出
            safe_uri = postgres_uri
            password = os.getenv('POSTGRES_PASSWORD', '')
            if password:
                safe_uri = postgres_uri.replace(password, '***')
            
            print(f"[Memory] 使用PostgresStore: {safe_uri}")
            
            # 使用官方PostgresStore（支持连接池和pgvector）
            # 注意：第一次使用需要调用store.setup()创建表
            store = PostgresStore.from_conn_string(
                postgres_uri,
                pool_config={
                    "min_size": 1,
                    "max_size": 10,
                }
            )
            
            # 自动初始化表结构
            try:
                store.setup()
                print("[Memory] [OK] PostgreSQL表结构初始化成功")
            except Exception as e:
                # 表可能已存在，忽略错误
                print(f"[Memory] 表结构已存在或初始化跳过: {e}")
            
            return store
            
        except ImportError as e:
            print(f"[Memory] [WARNING] PostgreSQL依赖未安装: {e}")
            print("[Memory] 请运行: pip install -U 'psycopg[binary,pool]' langgraph-checkpoint-postgres")
            print("[Memory] 降级使用InMemoryStore")
            return InMemoryStore()
        except Exception as e:
            print(f"[Memory] [WARNING] PostgreSQL配置失败: {e}")
            print("[Memory] 降级使用InMemoryStore")
            import traceback
            traceback.print_exc()
            return InMemoryStore()
    
    else:
        # 开发环境：InMemoryStore
        print("[Memory] 使用InMemoryStore（开发环境）")
        
        # TODO: 可选添加embedding支持
        # embedding_model = os.getenv("MEMORY_EMBEDDING_MODEL", "text-embedding-3-small")
        # def embed(texts):
        #     return openai.embeddings.create(model=embedding_model, input=texts)
        
        return InMemoryStore()

# 全局Store实例（单例模式）
_global_store: Optional[BaseStore] = None
_store_initialized = False

def _sync_from_history_db(store: BaseStore) -> None:
    """从 history_db 同步已看过的 TED 到 Memory Store"""
    try:
        from app.db import history_db
        from app.memory.ted_history_memory import TEDHistoryMemory
        
        ted_memory = TEDHistoryMemory(store)
        
        # 获取所有历史记录
        records = history_db.list_all(limit=1000)
        
        # 按 user_id 分组
        user_urls: Dict[str, Dict[str, Dict]] = {}
        for r in records:
            ted_url = r.get('ted_url')
            if not ted_url:
                continue
            
            # 同步到 user_123 和 guest_user
            for user_id in ['user_123', 'guest_user']:
                if user_id not in user_urls:
                    user_urls[user_id] = {}
                user_urls[user_id][ted_url] = {
                    'title': r.get('ted_title', 'Unknown'),
                    'speaker': r.get('ted_speaker', 'Unknown')
                }
        
        # 同步到 Memory Store
        for user_id, url_info in user_urls.items():
            for url, info in url_info.items():
                # 检查是否已存在
                if ted_memory.is_seen(user_id, url):
                    continue
                
                ted_memory.add_seen_ted(
                    user_id=user_id,
                    url=url,
                    title=info['title'],
                    speaker=info['speaker'],
                    search_topic='synced',
                    metadata={'synced_from': 'history_db'}
                )
        
        if user_urls:
            total = sum(len(urls) for urls in user_urls.values())
            print(f"[Memory] 从 history_db 同步了 {total} 条已看过的 TED")
            
    except Exception as e:
        print(f"[Memory] 同步 history_db 失败: {e}")


def get_global_store() -> BaseStore:
    """获取全局Store实例（单例）
    
    Returns:
        全局Store实例
    """
    global _global_store, _store_initialized
    
    if _global_store is None:
        _global_store = create_store()
    
    # 首次初始化时从 history_db 同步
    if not _store_initialized and _global_store is not None:
        _store_initialized = True
        _sync_from_history_db(_global_store)
    
    return _global_store
