# routers/vocab.py
# 生词本API路由

import sqlite3
import os
from fastapi import APIRouter, HTTPException
from typing import List
from app.models import VocabWord, AddVocabRequest, VocabResponse

router = APIRouter(prefix="/api/vocab", tags=["vocab"])

DB_PATH = "data/vocab.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vocab_words (
                id TEXT PRIMARY KEY,
                word TEXT NOT NULL,
                definition TEXT NOT NULL,
                dictionary TEXT NOT NULL,
                added_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocab_words(word)
        """)
        conn.commit()
        print("[VOCAB] Database initialized")
    finally:
        conn.close()


@router.post("/sync")
async def sync_vocab(request: AddVocabRequest):
    """
    批量同步生词到数据库

    用于前端 LocalStorage 同步到后端
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for word in request.words:
            cursor.execute("""
                INSERT OR REPLACE INTO vocab_words (id, word, definition, dictionary, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (word.id, word.word, word.definition, word.dictionary, word.added_at))
        conn.commit()
        return {"success": True, "count": len(request.words)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
    finally:
        conn.close()


@router.get("", response_model=VocabResponse)
async def get_vocab():
    """
    获取所有生词

    按添加时间倒序返回
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, word, definition, dictionary, added_at
            FROM vocab_words ORDER BY added_at DESC
        """)
        words = [VocabWord(**dict(row)) for row in cursor.fetchall()]
        return VocabResponse(words=words, total=len(words))
    finally:
        conn.close()


@router.delete("/{word_id}")
async def delete_vocab(word_id: str):
    """
    删除生词
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM vocab_words WHERE id = ?", (word_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Word not found")
        return {"success": True}
    finally:
        conn.close()
