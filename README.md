# MCP Memory Server with RAG

A FastAPI-based **MCP-compatible server** that provides:

1. **Web search** via LangSearch
2. **Live webpage scraping** via an existing Chrome instance (remote debugging)
3. **Readable content extraction** (Reader-mode quality)
4. **Persistent memory storage** with SQLite
5. **RAG-powered semantic search** using ChromaDB and embeddings

This server is designed to be used as a **tool backend** for LLM agents (MCP-style), RAG pipelines, or automated research workflows.

---

## ✨ Features

* 🔍 Web search using **LangSearch API**
* 🌐 Attach to a **running Chrome browser** via DevTools (CDP)
* 🔐 Reuse logged-in sessions, cookies, and profiles
* 📰 High-quality article extraction using **Mozilla Readability**
* 🧠 **Persistent memory system** with dual storage (SQLite + ChromaDB)
* 🔮 **RAG-powered semantic search** using sentence-transformers
* ⚡ Async FastAPI endpoints
* 🧩 Clean, deterministic JSON responses
* 🔄 Easy to extend with any summarization model (OpenAI, Ollama, local LLMs)

---

## 🏗 Architecture Overview

```
┌────────────┐
│   Client   │ (LLM / MCP Agent / curl)
└─────┬──────┘
      │
      ▼
┌────────────────────┐
│  FastAPI Server    │
├────────────────────┤
│ /search            │───▶ LangSearch API
│ /scrape            │───▶ Chrome (CDP 9222)
│ /memory/store      │───▶ SQLite + ChromaDB
│ /memory/retrieve   │───▶ Vector Search (semantic)
│                    │───▶ Keyword Search (SQL)
│ /memory/forget     │───▶ Delete from both DBs
└────────────────────┘
```

### Memory Storage Architecture

```
Memory Store Request
    ↓
┌─────────────────────┐
│ /memory/store       │
├─────────────────────┤
├─ SQLite            │ ← Metadata, tags, timestamps
├─ ChromaDB          │ ← Embeddings for semantic search
└─────────────────────┘

Memory Retrieve Request
    ↓
┌─────────────────────┐
│ /memory/retrieve    │
├─────────────────────┤
├─ Semantic Search   │ ← Vector similarity (default)
├─ Keyword Search    │ ← SQL LIKE fallback
└─────────────────────┘
```

---

## 📦 Tech Stack

* **Python 3.10+**
* **FastAPI** – API framework
* **Playwright** – Chrome DevTools Protocol client
* **Mozilla Readability** – main content extraction
* **BeautifulSoup** – HTML cleaning
* **Requests** – LangSearch HTTP client
* **Pydantic** – request/response validation
* **SQLite** – metadata storage
* **ChromaDB** – vector database for embeddings
* **sentence-transformers** – local embedding generation (`all-MiniLM-L6-v2`)

---

## 🚀 Setup Instructions

### 1️⃣ Clone the repository

```bash
git clone <your-repo-url>
cd mcp-server
```

---

### 2️⃣ Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

---

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

The following dependencies are included:
- `fastapi`, `uvicorn` – web framework
- `playwright` – browser automation
- `chromadb` – vector database
- `sentence-transformers` – embedding generation
- `requests`, `beautifulsoup4`, `readability` – web scraping

---

### 4️⃣ Configure environment variables

Create a `.env` file in the project root:

```env
LANGSEARCH_API_KEY=your_langsearch_api_key
```

---

## 🌐 Chrome Remote Debugging Setup

This server **does not launch Chrome itself**. It attaches to an existing instance.

### Start Chrome with debugging enabled

```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-profile
```

✅ Benefits:

* Reuses logins (Google, Medium, etc.)
* Works with authenticated pages
* Mirrors real user browsing

> ⚠️ Ensure no other Chrome instance is already using that profile directory.

---

## ▶️ Running the Server

```bash
uvicorn app:app --host 0.0.0.0 --port 4444 --reload
```

Open Swagger UI:

```
http://localhost:4444/docs
```

---

## 🔍 API Reference

### 1️⃣ Web Search

**Endpoint**

```
POST /search
```

**Request Body**

```json
{
  "query": "run llm on android phone",
  "max_results": 3
}
```

**Response**

```json
{
  "query": "run llm on android phone",
  "results": [
    {
      "title": "How I ran a local LLM on my Android phone",
      "url": "https://example.com",
      "snippet": "I experimented with running LLMs locally..."
    }
  ]
}
```

---

### 2️⃣ Scrape Webpage

**Endpoint**

```
POST /scrape
```

**Request Body**

```json
{
  "url": "https://en.wikipedia.org/wiki/William_Anderson_(RAAF_officer)",
  "max_chars": 8000
}
```

**Response**

```json
{
  "url": "https://en.wikipedia.org/wiki/...",
  "title": "William Anderson (RAAF officer)",
  "extracted_text": "William Anderson was born..."
}
```

---

### 3️⃣ Memory Storage (NEW)

**Endpoint**

```
POST /memory/store
```

**Request Body**

```json
{
  "content": "Python is a high-level programming language known for its simplicity",
  "type": "fact",
  "tags": ["programming", "python"],
  "source": "manual",
  "confidence": 0.9
}
```

**Response**

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "stored_at": "2026-01-13T10:30:00",
  "message": "Memory stored successfully"
}
```

---

### 4️⃣ Memory Retrieval with RAG (NEW)

**Endpoint**

```
POST /memory/retrieve
```

**Request Body (Semantic Search - Default)**

```json
{
  "query": "coding languages",
  "limit": 5,
  "search_type": "semantic"
}
```

This will find memories that are **semantically similar** to "coding languages" (e.g., memories about Python, JavaScript, programming concepts).

**Request Body (Keyword Search - Fallback)**

```json
{
  "query": "Python",
  "limit": 5,
  "search_type": "keyword"
}
```

This performs traditional SQL `LIKE` search (exact keyword matching).

**Response**

```json
{
  "query": "coding languages",
  "count": 2,
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Python is a high-level programming language...",
      "type": "fact",
      "tags": ["programming", "python"],
      "source": "manual",
      "confidence": 0.9,
      "created_at": "2026-01-13T10:30:00"
    }
  ]
}
```

---

### 5️⃣ Memory Deletion (NEW)

**Endpoint**

```
POST /memory/forget
```

**Request Body**

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**

```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted": true,
  "message": "Memory deleted"
}
```

---

### 6️⃣ Memory Statistics (NEW)

**Endpoint**

```
GET /memory/stats
```

**Response**

```json
{
  "total_memories": 42,
  "by_type": {
    "fact": 20,
    "episodic": 15,
    "semantic": 7
  }
}
```

---

## 🧠 RAG Implementation Details

### Vector Database
- **ChromaDB**: Persistent vector storage in `./chroma_db/` directory
- **Embedding Model**: `all-MiniLM-L6-v2` (~80MB, downloads on first run)
- **Embedding Dimension**: 384
- **Similarity Metric**: Cosine similarity

### Dual Storage System
1. **SQLite**: Stores metadata (tags, source, confidence, timestamps)
2. **ChromaDB**: Stores embeddings for semantic search

### Search Modes
- **Semantic Search** (default): Uses vector embeddings to find conceptually similar memories
- **Keyword Search**: Traditional SQL `LIKE` pattern matching

### Example Use Case
```bash
# Store a memory about Python
curl -X POST http://localhost:4444/memory/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Python uses indentation for code blocks", "type": "fact"}'

# Semantic search finds it with related query
curl -X POST http://localhost:4444/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "programming language syntax"}'
# ✅ Returns the Python memory (semantic match)

# Keyword search requires exact match
curl -X POST http://localhost:4444/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "syntax", "search_type": "keyword"}'
# ❌ Won't find it unless "syntax" appears in content
```

---

## 🧩 MCP Integration Pattern

Typical agent flow:

```
/search → select result.url
      ↓
/scrape(url) → extract content
      ↓
/memory/store → save important facts
      ↓
/memory/retrieve → semantic recall
      ↓
LLM reasoning / synthesis
```

This mirrors Anthropic-style browser MCP tools closely with added persistent memory.

---

## 🔒 Security Considerations

* Do **not** expose this server publicly without:
  * URL allowlists
  * Authentication
  * Rate limiting
* Chrome debugging gives **full browser access**
* Vector embeddings are stored locally (no external API calls)
* Treat this as a trusted internal service

---

## 🛠 Troubleshooting

### FastAPI error: `Field required (body)`
* Ensure `Content-Type: application/json`
* Ensure `-d` is passed in curl

### Playwright cannot connect
* Verify Chrome is running on port `9222`
* Check firewall / localhost access

### Empty extracted text
* Page may be JS-heavy
* Add `wait_for_selector()` for article content

### ChromaDB initialization slow
* First run downloads the `all-MiniLM-L6-v2` model (~80MB)
* Subsequent runs are fast (model is cached)

### Out of memory during embedding
* The embedding model runs on CPU by default
* For large batches, consider using a GPU or smaller model

---

## 🗺 Roadmap / Ideas

* ~~Embeddings + semantic search~~ ✅ Done
* Page reuse pool
* Content hashing + caching
* Streaming summaries
* Screenshot capture
* PDF extraction
* Unified MCP tool schema
* Hybrid search (combine semantic + keyword)
* Reranking with cross-encoders

---

## 📄 License

MIT License

---

## 🙌 Acknowledgements

Inspired by:

* Browserless
* LangChain WebLoader
* Mozilla Readability
* Anthropic MCP browser tools
* ChromaDB
* sentence-transformers

---

If you're building an **LLM agent, RAG pipeline, or research assistant**, this server is meant to be extended—not locked down.

Happy hacking 🚀
