# MCP Search & Scrape Server

A FastAPI-based **MCP-compatible server** that provides:

1. **Web search** via LangSearch
2. **Live webpage scraping** via an existing Chrome instance (remote debugging)
3. **Readable content extraction** (Reader-mode quality)
4. **Summarization-ready outputs** for LLM pipelines

This server is designed to be used as a **tool backend** for LLM agents (MCP-style), RAG pipelines, or automated research workflows.

---

## ✨ Features

* 🔍 Web search using **LangSearch API**
* 🌐 Attach to a **running Chrome browser** via DevTools (CDP)
* 🔐 Reuse logged-in sessions, cookies, and profiles
* 📰 High-quality article extraction using **Mozilla Readability**
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
┌────────────┐
│  FastAPI   │
│  Server    │
├────────────┤
│ /search    │───▶ LangSearch API
│ /scrape-   │
│ summarize  │───▶ Chrome (CDP 9222)
└────────────┘
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
source venv/bin/activate
```

---

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

If `requirements.txt` is missing, install manually:

```bash
pip install fastapi uvicorn requests python-dotenv playwright readability-lxml beautifulsoup4
```

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
uvicorn main:app --host 0.0.0.0 --port 4444 --reload
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

### 2️⃣ Scrape & Summarize Webpage

**Endpoint**

```
POST /scrape-and-summarize
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
  "summary": "William Anderson was an officer in the Royal Australian Air Force...",
  "extracted_text": "William Anderson was born..."
}
```

---

## 🧠 Summarization Strategy

The server **intentionally decouples scraping from summarization**.

Current implementation uses a placeholder:

```python
def summarize_text(text: str) -> str:
    return text[:500] + "..."
```

### Plug-in options

* OpenAI / Azure OpenAI
* Ollama (local LLMs)
* Gemini
* Claude
* Any MCP-compatible LLM tool

This makes the server ideal as a **tool node** rather than a monolithic AI service.

---

## 🧩 MCP Integration Pattern

Typical agent flow:

```
/search → select result.url
      ↓
/scrape-and-summarize(url)
      ↓
LLM reasoning / synthesis
```

This mirrors Anthropic-style browser MCP tools closely.

---

## 🔒 Security Considerations

* Do **not** expose this server publicly without:

  * URL allowlists
  * Authentication
  * Rate limiting
* Chrome debugging gives **full browser access**
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

---

## 🗺 Roadmap / Ideas

* Page reuse pool
* Content hashing + caching
* Streaming summaries
* Screenshot capture
* PDF extraction
* Unified MCP tool schema

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

---

If you’re building an **LLM agent, RAG pipeline, or research assistant**, this server is meant to be extended—not locked down.

Happy hacking 🚀
