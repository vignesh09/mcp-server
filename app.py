import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import HTTPException
from playwright.async_api import async_playwright
from readability import Document
from bs4 import BeautifulSoup
import asyncio
import sqlite3
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from models import (
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemoryRetrieveRequest,
    MemoryRetrieveResponse,
    MemoryItem,
    MemoryForgetRequest,
    MemoryForgetResponse
)
from db import (
    init_db,
    insert_memory,
    fetch_memories,
    delete_memory,
    get_memory_stats
)
from vector_db import (
    init_vector_db,
    add_to_vector_db,
    search_vector_db,
    delete_from_vector_db
)



load_dotenv()

LANGSEARCH_API_KEY = os.getenv("LANGSEARCH_API_KEY")
LANGSEARCH_URL = "https://api.langsearch.com/v1/web-search"

app = FastAPI(title="MCP Search Server")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    print("SQLite database initialized")
    init_vector_db()
    print("Vector database initialized")

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "service": "MCP Memory Server",
        "status": "running",
        "version": "1.0.0"
    }


class SearchRequest(BaseModel):
    query: str
    max_results: int = 1

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]

class ScrapeRequest(BaseModel):
    url: str
    max_chars: int = 8000

class ScrapeResponse(BaseModel):
    url: str
    title: str
    extracted_text: str


def parse_langsearch_response(response: dict, max_results: int = 10) -> dict:
    """
    Parses LangSearch web search response into a clean MCP-friendly format
    """

    data = response.get("data", {})
    web_pages = data.get("webPages", {})
    values = web_pages.get("value", [])

    parsed_results = []

    for item in values[:max_results]:
        title = item.get("name", "").strip()
        url = item.get("url", "").strip()

        # Prefer summary over snippet
        content = (
            item.get("summary")
            or item.get("content")
            or ""
        ).strip()

        if not title or not url or not content:
            continue

        parsed_results.append({
            "title": title,
            "url": url,
            "snippet": content
        })

    return {
        "query": data.get("queryContext", {})
                    .get("originalQuery", ""),
        "results": parsed_results
    }

async def scrape_page_via_chrome(
    url: str,
    max_chars: int = 8000
) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            "http://localhost:9222"
        )

        context = browser.contexts[0]
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        html = await page.content()
        title = await page.title()

        # --- Readability extraction ---
        doc = Document(html)
        main_html = doc.summary()

        soup = BeautifulSoup(main_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        cleaned = text[:max_chars]

        return {
            "url": url,
            "title": title,
            "text": cleaned
        }
"""
curl -X POST http://localhost:4444/search   -H "Content-Type: application/json"   -d '{"query": "edge AI local LLMs"}'

"""

@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    headers = {
        "Authorization": f"Bearer {LANGSEARCH_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": req.query,
        "count": req.max_results,
        "freshness": "oneYear",
        "summary": True
    }

    response = requests.post(
        LANGSEARCH_URL,
        headers=headers,
        json=payload,
        timeout=10
    )
    response.raise_for_status()

    # data = response.json()

    # print(f"Search response data: {data}")
    parsed = parse_langsearch_response(response.json(), req.max_results)
    return parsed
"""
curl -X POST http://localhost:4444/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://en.wikipedia.org/wiki/William_Anderson_(RAAF_officer)"
  }'


"""
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    try:
        scraped = await scrape_page_via_chrome(
            req.url,
            req.max_chars
        )

        return {
            "url": scraped["url"],
            "title": scraped["title"],
            "extracted_text": scraped["text"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/memory/store", response_model=MemoryStoreResponse)
def store_memory(request: MemoryStoreRequest):
    """
    Store a new memory explicitly.
    Stores in both SQLite (metadata) and ChromaDB (embeddings for semantic search).
    """
    memory_id = str(uuid.uuid4())

    try:
        # Store in SQLite
        insert_memory(
            memory_id=memory_id,
            content=request.content,
            type=request.type,
            tags=request.tags,
            source=request.source,
            confidence=request.confidence
        )

        # Store in vector DB for semantic search
        add_to_vector_db(
            memory_id=memory_id,
            content=request.content,
            metadata={
                "type": request.type,
                "tags": request.tags,
                "source": request.source,
                "confidence": request.confidence,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        return MemoryStoreResponse(
            memory_id=memory_id,
            stored_at=datetime.utcnow(),
            message="Memory stored successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")

@app.post("/memory/retrieve", response_model=MemoryRetrieveResponse)
def retrieve_memories(request: MemoryRetrieveRequest):
    """
    Retrieve memories matching the query.
    Supports two search types:
    - 'semantic' (default): Vector similarity search using embeddings
    - 'keyword': SQL LIKE search on content
    """
    try:
        if request.search_type == "semantic":
            # Semantic search using vector DB
            results = search_vector_db(
                query=request.query,
                limit=request.limit,
                type_filter=request.type
            )
            memories = []
            for result in results:
                # Parse created_at if it's a string
                created_at = result.get("created_at", "")
                if isinstance(created_at, str) and created_at:
                    created_at = datetime.fromisoformat(created_at)
                else:
                    created_at = datetime.utcnow()

                memories.append(MemoryItem(
                    id=result["id"],
                    content=result["content"],
                    type=result["type"],
                    tags=result["tags"],
                    source=result["source"],
                    confidence=result["confidence"],
                    created_at=created_at
                ))
        else:
            # Keyword search using SQLite
            results = fetch_memories(
                query=request.query,
                limit=request.limit,
                type_filter=request.type
            )
            memories = [MemoryItem(**result) for result in results]

        return MemoryRetrieveResponse(
            query=request.query,
            count=len(memories),
            memories=memories
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {str(e)}")

@app.post("/memory/forget", response_model=MemoryForgetResponse)
def forget_memory(request: MemoryForgetRequest):
    """
    Delete a memory by ID.
    Deletes from both SQLite and vector DB.
    """
    try:
        # Delete from SQLite
        deleted = delete_memory(request.memory_id)

        # Delete from vector DB
        delete_from_vector_db(request.memory_id)

        return MemoryForgetResponse(
            memory_id=request.memory_id,
            deleted=deleted,
            message="Memory deleted" if deleted else "Memory not found"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")

@app.get("/memory/stats")
def memory_stats():
    """Get statistics about stored memories"""
    try:
        return get_memory_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    


"""
uvicorn app:app --reload --port 4444
"""