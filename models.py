from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class MemoryStoreRequest(BaseModel):
    content: str = Field(..., description="The actual memory content")
    type: str = Field(default="semantic", description="Memory type: semantic, episodic, etc.")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    source: str = Field(default="manual", description="Where this memory came from")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score 0-1")

class MemoryStoreResponse(BaseModel):
    memory_id: str
    stored_at: datetime
    message: str

class MemoryRetrieveRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(default=5, ge=1, le=50, description="Max results to return")
    type: Optional[str] = Field(None, description="Filter by memory type")
    search_type: str = Field(default="semantic", description="Search type: 'semantic' (vector) or 'keyword' (SQL LIKE)")

class MemoryItem(BaseModel):
    id: str
    content: str
    type: str
    tags: List[str]
    source: str
    confidence: float
    created_at: datetime

class MemoryRetrieveResponse(BaseModel):
    query: str
    count: int
    memories: List[MemoryItem]

class MemoryForgetRequest(BaseModel):
    memory_id: str

class MemoryForgetResponse(BaseModel):
    memory_id: str
    deleted: bool
    message: str