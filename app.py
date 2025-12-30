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



load_dotenv()

LANGSEARCH_API_KEY = os.getenv("LANGSEARCH_API_KEY")
LANGSEARCH_URL = "https://api.langsearch.com/v1/web-search"

app = FastAPI(title="MCP Search Server")

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


"""
uvicorn app:app --reload --port 4444
"""