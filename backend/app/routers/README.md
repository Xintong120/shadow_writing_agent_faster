# Memory API 使用指南

## 概述

Memory API提供了完整的用户记忆管理功能，包括：
- TED观看历史
- 搜索历史
- Shadow Writing学习记录
- 学习统计和总览

## API端点列表

### 1. 获取TED观看历史

```http
GET /memory/ted-history/{user_id}?limit=50
```

**参数**:
- `user_id` (path): 用户ID
- `limit` (query): 返回数量，默认50，范围1-200

**响应示例**:
```json
[
  {
    "url": "https://ted.com/talks/leadership",
    "title": "How to be a great leader",
    "speaker": "Simon Sinek",
    "watched_at": "2025-10-10T09:00:00",
    "search_topic": "leadership",
    "chunks_processed": 15,
    "shadow_writing_count": 12,
    "metadata": {}
  }
]
```

---

### 2. 获取搜索历史

```http
GET /memory/search-history/{user_id}?limit=50
```

**参数**:
- `user_id` (path): 用户ID
- `limit` (query): 返回数量，默认50

**响应示例**:
```json
[
  {
    "search_id": "uuid-xxx",
    "original_query": "leadership",
    "optimized_query": "effective leadership strategies",
    "alternative_queries": ["team management"],
    "results_count": 5,
    "selected_url": "https://ted.com/talks/...",
    "selected_title": "...",
    "searched_at": "2025-10-10T09:00:00",
    "search_duration_ms": 1250,
    "new_results": 5,
    "filtered_seen": 3
  }
]
```

---

### 3. 获取学习记录

```http
GET /memory/learning-records/{user_id}?limit=50&min_quality=7.0&tags=leadership
```

**参数**:
- `user_id` (path): 用户ID
- `limit` (query): 返回数量，默认50
- `ted_url` (query): 按TED URL过滤（可选）
- `min_quality` (query): 最小质量分数，0-10（可选）
- `tags` (query): 按标签过滤，逗号分隔（可选）

**响应示例**:
```json
{
  "user_id": "user_123",
  "total": 10,
  "records": [
    {
      "record_id": "uuid-xxx",
      "ted_url": "https://ted.com/talks/...",
      "ted_title": "How to be a great leader",
      "ted_speaker": "Simon Sinek",
      "original": "leadership is about service",
      "imitation": "true leadership means serving others",
      "map": {
        "noun": ["leadership", "service"],
        "verb": ["be", "serve"]
      },
      "paragraph": "Leadership is not about...",
      "quality_score": 8.5,
      "learned_at": "2025-10-10T09:00:00",
      "tags": ["leadership", "management"]
    }
  ]
}
```

---

### 4. 获取单条学习记录

```http
GET /memory/learning-records/{user_id}/{record_id}
```

**参数**:
- `user_id` (path): 用户ID
- `record_id` (path): 记录ID

**响应**: 返回单条学习记录详情（格式同上）

---

### 5. 获取学习统计

```http
GET /memory/stats/{user_id}
```

**响应示例**:
```json
{
  "user_id": "user_123",
  "learning_records": {
    "total_records": 150,
    "avg_quality_score": 7.8,
    "top_tags": ["leadership", "innovation", "communication"],
    "records_by_ted": {
      "https://ted.com/talks/...": {
        "count": 12,
        "title": "How to be a great leader"
      }
    },
    "recent_activity": "2025-10-10T14:00:00",
    "quality_trend": [
      {"learned_at": "2025-10-10T09:00:00", "quality_score": 7.5},
      {"learned_at": "2025-10-10T10:00:00", "quality_score": 8.0}
    ]
  },
  "ted_history": {
    "total_watched": 10,
    "watched_urls": ["https://ted.com/talks/..."]
  },
  "search_history": {
    "total_searches": 25,
    "recent_searches": [...]
  }
}
```

---

### 6. 获取用户总览

```http
GET /memory/summary/{user_id}
```

**响应示例**:
```json
{
  "user_id": "user_123",
  "summary": {
    "total_learning_records": 150,
    "avg_quality_score": 7.8,
    "total_ted_watched": 10,
    "total_searches": 25,
    "recent_activity": "2025-10-10T14:00:00"
  },
  "top_tags": ["leadership", "innovation", "communication"],
  "recent_searches": ["leadership", "innovation", "teamwork"]
}
```

---

### 7. 添加学习记录

```http
POST /memory/learning-records
Content-Type: application/json
```

**请求体**:
```json
{
  "user_id": "user_123",
  "ted_url": "https://ted.com/talks/leadership",
  "ted_title": "How to be a great leader",
  "ted_speaker": "Simon Sinek",
  "original": "leadership is about service",
  "imitation": "true leadership means serving others",
  "word_map": {
    "noun": ["leadership", "service"],
    "verb": ["be", "serve"]
  },
  "paragraph": "Leadership is not about being in charge...",
  "quality_score": 8.5,
  "tags": ["leadership", "management"]
}
```

**响应**:
```json
{
  "success": true,
  "record_id": "uuid-xxx",
  "message": "学习记录已添加"
}
```

---

### 8. 删除学习记录

```http
DELETE /memory/learning-records/{user_id}/{record_id}
```

**参数**:
- `user_id` (path): 用户ID
- `record_id` (path): 记录ID

**响应**:
```json
{
  "success": true,
  "message": "记录已删除: uuid-xxx"
}
```

---

## 测试步骤

### 1. 启动服务

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 2. 访问API文档

打开浏览器访问：http://localhost:8000/docs

在Swagger UI中可以看到所有Memory API端点，可以直接在浏览器中测试。

### 3. 运行自动化测试

```bash
cd backend
python test_memory_api.py
```

测试脚本会自动执行所有API端点的测试，并输出结果。

---

## 使用示例

### Python客户端示例

```python
import requests

BASE_URL = "http://localhost:8000"
USER_ID = "user_123"

# 1. 添加学习记录
response = requests.post(
    f"{BASE_URL}/memory/learning-records",
    json={
        "user_id": USER_ID,
        "ted_url": "https://ted.com/talks/leadership",
        "ted_title": "How to be a great leader",
        "ted_speaker": "Simon Sinek",
        "original": "leadership is about service",
        "imitation": "true leadership means serving others",
        "word_map": {"noun": ["leadership", "service"]},
        "paragraph": "Leadership is not about...",
        "quality_score": 8.5,
        "tags": ["leadership"]
    }
)
print(response.json())

# 2. 获取学习记录
response = requests.get(f"{BASE_URL}/memory/learning-records/{USER_ID}")
print(response.json())

# 3. 获取统计数据
response = requests.get(f"{BASE_URL}/memory/stats/{USER_ID}")
print(response.json())

# 4. 按质量过滤
response = requests.get(
    f"{BASE_URL}/memory/learning-records/{USER_ID}?min_quality=8.0"
)
print(response.json())

# 5. 按标签过滤
response = requests.get(
    f"{BASE_URL}/memory/learning-records/{USER_ID}?tags=leadership,innovation"
)
print(response.json())
```

### JavaScript客户端示例

```javascript
const BASE_URL = 'http://localhost:8000';
const USER_ID = 'user_123';

// 1. 获取学习记录
fetch(`${BASE_URL}/memory/learning-records/${USER_ID}`)
  .then(res => res.json())
  .then(data => console.log(data));

// 2. 获取用户总览
fetch(`${BASE_URL}/memory/summary/${USER_ID}`)
  .then(res => res.json())
  .then(data => console.log(data));

// 3. 添加学习记录
fetch(`${BASE_URL}/memory/learning-records`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    user_id: USER_ID,
    ted_url: 'https://ted.com/talks/leadership',
    ted_title: 'How to be a great leader',
    ted_speaker: 'Simon Sinek',
    original: 'leadership is about service',
    imitation: 'true leadership means serving others',
    word_map: {noun: ['leadership', 'service']},
    paragraph: 'Leadership is not about...',
    quality_score: 8.5,
    tags: ['leadership']
  })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 错误处理

所有API端点都会返回标准的HTTP状态码：

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

---

## 注意事项

1. **用户隔离**: 所有API都基于`user_id`隔离，不同用户的数据互不影响

2. **InMemoryStore**: 开发环境使用内存存储，重启服务后数据会丢失
   - 生产环境需配置PostgreSQL实现持久化

3. **分页**: 所有列表接口都支持`limit`参数控制返回数量

4. **过滤**: 学习记录接口支持多种过滤条件：
   - `ted_url`: 按TED URL过滤
   - `min_quality`: 按质量分数过滤
   - `tags`: 按标签过滤（支持多个标签，逗号分隔）

5. **性能**: 查询性能 <50ms（InMemoryStore），<100ms（PostgreSQL）

---

## 下一步

完成Memory API后，需要：

1. **集成到workflow**: 在Shadow Writing完成后自动保存学习记录
2. **配置PostgreSQL**: 实现数据持久化
3. **前端集成**: 在UI中展示用户的学习历史和统计

详见 `PLAN.md` 中的后续任务。
