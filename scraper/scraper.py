"""
scraper.py
1. Ambil daftar artikel dari halaman utama Wired.com
2. Masuk ke tiap artikel untuk ambil author dan description
Output: /app/data/articles.json
"""

import json
import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

TARGET_URL   = "https://www.wired.com"
MIN_ARTICLES = 50
OUTPUT_DIR   = "/app/data"
OUTPUT_FILE  = os.path.join(OUTPUT_DIR, "articles.json")
SCROLL_PAUSE = 2.5
MAX_SCROLLS  = 15


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        driver = webdriver.Chrome(options=options)
    return driver


def scroll_to_load(driver, target):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(MAX_SCROLLS):
        found = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/story/']"))
        print(f"  [Scroll {i+1}] Artikel: {found}")
        if found >= target:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def get_article_detail(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
        )
        time.sleep(1)

        description = ""

        try:
            meta = driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
            description = meta.get_attribute("content") or ""
        except NoSuchElementException:
            pass

        if not description:
            for sel in [
                "[class*='SubDek']",
                "[class*='Dek']",
                "[class*='dek']",
                "[class*='lead']",
                "[class*='intro']",
            ]:
                try:
                    description = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                    if description:
                        break
                except NoSuchElementException:
                    continue

        author = ""
        for sel in [
            "[class*='BylineName']",
            "[class*='byline']",
            "[class*='Byline']",
            "[class*='author']",
            "[class*='Author']",
            "a[href*='/author/']",
            "a[href*='/contributor/']",
        ]:
            try:
                author = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                if author:
                    break
            except NoSuchElementException:
                continue

        if author and not author.lower().startswith("by"):
            author = "By" + author

        return author or None, description or None

    except TimeoutException:
        print(f"    [TIMEOUT] {url}")
        return None, None
    except Exception as e:
        print(f"    [ERROR] {url}: {e}")
        return None, None


def scrape_wired():
    session_id = f"wired_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    scraped_at = datetime.now().isoformat()
    articles   = []
    seen_urls  = set()

    print(f"Session: {session_id}")
    driver = build_driver()

    try:
        print("\nMembuka halaman utama Wired.com")
        driver.get(TARGET_URL)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/story/']"))
        )

        print(f"Scrolling untuk kumpulkan {MIN_ARTICLES}+ URL")
        scroll_to_load(driver, MIN_ARTICLES)

        cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/story/']")
        urls = []
        for card in cards:
            try:
                url   = card.get_attribute("href") or ""
                title = card.text.strip()
                if url and title and url not in seen_urls:
                    seen_urls.add(url)
                    urls.append({"url": url, "title": title})
            except StaleElementReferenceException:
                continue

        print(f"URL unik terkumpul: {len(urls)}")
        print(f"\nMengambil detail tiap artikel (author + description)")
        for i, item in enumerate(urls[:MIN_ARTICLES + 5]):
            print(f"  [{i+1}/{min(len(urls), MIN_ARTICLES+5)}] {item['url'][-60:]}")
            author, description = get_article_detail(driver, item["url"])

            articles.append({
                "title":       item["title"],
                "url":         item["url"],
                "description": description,
                "author":      author,
                "scraped_at":  scraped_at,
                "source":      "Wired.com",
            })

            time.sleep(0.5)

    finally:
        driver.quit()
        print("Browser ditutup")

    result = {
        "session_id":     session_id,
        "timestamp":      scraped_at,
        "articles_count": len(articles),
        "articles":       articles,
    }
    return result


def save_to_json(data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    existing = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = [existing]
        except json.JSONDecodeError:
            existing = []

    existing.append(data)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\nDisimpan ke: {OUTPUT_FILE}")
    print(f"Total session: {len(existing)}")


if __name__ == "__main__":
    print("\nMemulai scraping Wired.com\n")
    result = scrape_wired()

    author_count = sum(1 for a in result["articles"] if a.get("author"))
    desc_count   = sum(1 for a in result["articles"] if a.get("description"))

    print(f"\nHasil:")
    print(f"  Total artikel : {result['articles_count']}")
    save_to_json(result)