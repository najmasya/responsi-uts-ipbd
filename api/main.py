import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

DATA_FILE = "/app/data/articles.json"

app = FastAPI(
    title="Wired Articles API",
    description="API untuk menyajikan data artikel hasil scraping Wired.com",
    version="1.0.0",
)

def load_articles() -> list[dict]:
    if not os.path.exists(DATA_FILE):
        raise HTTPException(
            status_code=404,
            detail=f"File data tidak ditemukan: {DATA_FILE}. Jalankan scraper terlebih dahulu."
        )

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        sessions = data
    else:
        sessions = [data]
    all_articles = []
    for session in sessions:
        articles = session.get("articles", [])
        for article in articles:
            article["session_id"] = session.get("session_id", "unknown")
        all_articles.extend(articles)

    return all_articles


@app.get("/")
def root():
    """Health check — cek apakah API berjalan."""
    return {
        "status": "running",
        "message": "Wired Articles API is up!",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "GET /articles": "Ambil semua artikel",
            "GET /articles?limit=10": "Ambil N artikel pertama",
            "GET /health": "Health check detail",
        }
    }


@app.get("/articles")
def get_articles(
    limit: Optional[int] = Query(default=None, description="Batasi jumlah artikel yang dikembalikan"),
):
    articles = load_articles()

    if limit is not None:
        articles = articles[:limit]

    return JSONResponse(content={
        "status":   "success",
        "count":    len(articles),
        "articles": articles,
    })


@app.get("/health")
def health_check():
    file_exists = os.path.exists(DATA_FILE)
    article_count = 0

    if file_exists:
        try:
            articles = load_articles()
            article_count = len(articles)
        except Exception:
            article_count = -1

    return {
        "status":        "healthy" if file_exists else "degraded",
        "data_file":     DATA_FILE,
        "file_exists":   file_exists,
        "article_count": article_count,
        "timestamp":     datetime.now().isoformat(),
    }