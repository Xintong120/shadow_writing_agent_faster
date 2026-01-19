# Memory系统实现说明

## 概述

基于LangGraph Store API实现的长期记忆系统，采用模块化拆分设计。

## 目录结构

```
app/memory/
├── __init__.py                    # 模块导出
├── base_memory.py                 # 基础Memory类（50行）
├── ted_history_memory.py          # TED观看历史（130行）
├── search_history_memory.py       # 搜索历史（110行）
├── learning_records_memory.py     # 学习记录（待实现）
├── store_factory.py               # Store工厂（55行）
├── service.py                     # 统一服务入口（150行）
└── README.md                      # 本文档
```

## 已实现功能

### 1. TED观看历史（TEDHistoryMemory）

**用途**: 记录用户看过的TED演讲，用于去重和避免重复推荐

**核心方法**:
- `get_seen_urls(user_id)` - 获取已看过的URL集合
- `add_seen_ted(...)` - 添加观看记录
- `is_seen(user_id, url)` - 检查是否已看过
- `get_ted_info(user_id, url)` - 获取TED详细信息
- `update_processing_stats(...)` - 更新处理统计

**Namespace**: `(user_id, "ted_history")`

**数据结构**:
```python
{
    "url": "https://ted.com/talks/...",
    "title": "演讲标题",
    "speaker": "演讲者",
    "watched_at": "2025-10-09T21:00:00",
    "search_topic": "搜索主题",
    "chunks_processed": 15,
    "shadow_writing_count": 12,
    "metadata": {}
}
```

### 2. 搜索历史（SearchHistoryMemory）

**用途**: 记录用户的搜索行为，用于分析和优化搜索体验

**核心方法**:
- `add_search(...)` - 添加搜索记录
- `get_recent_searches(user_id, limit)` - 获取最近搜索
- `update_selected_url(...)` - 更新用户选择结果

**Namespace**: `(user_id, "search_history")`

**数据结构**:
```python
{
    "original_query": "leadership",
    "optimized_query": "effective leadership strategies",
    "alternative_queries": ["team management"],
    "results_count": 5,
    "selected_url": "...",
    "selected_title": "...",
    "searched_at": "2025-10-09T21:00:00",
    "search_duration_ms": 1250,
    "new_results": 5,
    "filtered_seen": 3
}
```

### 3. 学习记录（LearningRecordsMemory）

**状态**: 待实现（已预留接口）

**Namespace**: `(user_id, "shadow_writing_records")`

## 使用示例

### 基础使用

```python
from app.memory import MemoryService, get_global_store

# 创建Memory服务
memory_service = MemoryService(store=get_global_store())

# TED观看历史
memory_service.add_seen_ted(
    user_id="user_123",
    url="https://ted.com/talks/leadership",
    title="How to be a great leader",
    speaker="Simon Sinek",
    search_topic="leadership"
)

# 检查是否看过
is_seen = memory_service.is_ted_seen("user_123", "https://ted.com/talks/leadership")

# 获取已看过的URL
seen_urls = memory_service.get_seen_ted_urls("user_123")

# 搜索历史
search_id = memory_service.add_search_history(
    user_id="user_123",
    original_query="leadership",
    optimized_query="effective leadership strategies",
    alternative_queries=["team management"],
    results_count=5,
    new_results=5,
    filtered_seen=0
)

# 获取最近搜索
searches = memory_service.get_recent_searches("user_123", limit=10)
```

### Agent集成

```python
# 在Communication Agent中使用
def communication_agent(state):
    user_id = state.get("user_id", "default_user")
    
    # 1. 获取已看过的TED
    memory_service = MemoryService(store=get_global_store())
    seen_urls = memory_service.get_seen_ted_urls(user_id)
    
    # 2. 搜索并过滤
    results = search_api(query)
    new_results = [r for r in results if r['url'] not in seen_urls]
    
    # 3. 记录搜索
    search_id = memory_service.add_search_history(
        user_id=user_id,
        original_query=query,
        optimized_query=optimized,
        results_count=len(new_results),
        filtered_seen=len(results) - len(new_results)
    )
    
    return {"ted_candidates": new_results}
```

## 设计模式

### 1. Facade模式
`MemoryService`作为统一入口，封装了三个子Memory服务

### 2. 单例模式
`get_global_store()`确保全局只有一个Store实例

### 3. 继承模式
所有Memory类继承自`BaseMemory`，共享工具方法

## Store配置

### 开发环境（InMemoryStore）

默认配置，数据存储在内存中，重启后丢失。

```python
# 无需额外配置
memory_service = MemoryService()  # 自动使用InMemoryStore
```

### 生产环境（PostgresStore）

配置环境变量：

```bash
# .env
MEMORY_STORE_TYPE=postgres
POSTGRES_URI=postgresql://user:password@localhost:5432/shadow_writing_db
```

## 测试

运行测试：

```bash
cd backend
python tests/test_memory.py
```

测试覆盖：
- ✅ TED观看历史功能
- ✅ 搜索历史功能
- ✅ 多用户隔离
- ✅ 更新处理统计
- ✅ 学习记录接口（NotImplementedError）

## 设计优势

| 优势 | 说明 |
|------|------|
| **职责清晰** | 每个Memory类单一职责 |
| **易于测试** | 可独立测试每个Memory类型 |
| **便于扩展** | 添加新Memory类型不影响现有代码 |
| **文件小巧** | 每个文件<150行，便于维护 |
| **多用户隔离** | 使用namespace实现用户数据隔离 |

## 后续工作

### 短期
1. 实现`LearningRecordsMemory`类
2. 集成到Communication Agent
3. 添加API接口

### 长期
1. 添加embedding支持，实现语义搜索
2. 实现跨设备同步
3. 添加数据导出/导入功能
4. 学习分析和可视化

## 架构对比

### TED观看历史 vs 搜索历史

| 维度 | TED观看历史 | 搜索历史 |
|------|------------|---------|
| **记录对象** | 确认观看的TED | 搜索行为 |
| **触发时机** | 用户选择TED后 | 执行搜索时 |
| **主要用途** | 去重过滤 | 分析优化 |
| **生命周期** | 永久保存 | 可定期清理 |

**类比**: TED观看历史 = 订单历史，搜索历史 = 搜索记录

## 依赖

```txt
langgraph>=0.2.0
langgraph-checkpoint-postgres>=1.0.0  # 生产环境
```

## 作者

Shadow Writing Agent Team

## 最后更新

2025-10-09
