import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from typing import List, Optional, Dict

DB_PATH = "memory.db"

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Returns dict-like rows
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database schema"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                type TEXT,
                tags TEXT,
                source TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def insert_memory(
    memory_id: str,
    content: str,
    type: str,
    tags: List[str],
    source: str,
    confidence: float
) -> bool:
    """Store a memory in the database"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memory (id, content, type, tags, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            content,
            type,
            json.dumps(tags),  # Store tags as JSON string
            source,
            confidence
        ))
        conn.commit()
        return True

def fetch_memories(
    query: str,
    limit: int,
    type_filter: Optional[str] = None
) -> List[Dict]:
    """Retrieve memories matching the query"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Build query dynamically
        sql = """
            SELECT * FROM memory
            WHERE content LIKE ?
        """
        params = [f"%{query}%"]
        
        # Add type filter if provided
        if type_filter:
            sql += " AND type = ?"
            params.append(type_filter)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "content": row["content"],
                "type": row["type"],
                "tags": json.loads(row["tags"]),
                "source": row["source"],
                "confidence": row["confidence"],
                "created_at": row["created_at"]
            })
        
        return results

def delete_memory(memory_id: str) -> bool:
    """Delete a memory by ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_memory_stats() -> Dict:
    """Get basic statistics about stored memories"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM memory")
        total = cursor.fetchone()["total"]
        
        cursor.execute("SELECT type, COUNT(*) as count FROM memory GROUP BY type")
        by_type = {row["type"]: row["count"] for row in cursor.fetchall()}
        
        return {
            "total_memories": total,
            "by_type": by_type
        }