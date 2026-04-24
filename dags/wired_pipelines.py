import json
import logging
import os
from datetime import datetime, timedelta

import psycopg2
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

API_URL     = os.getenv("API_URL",     "http://api:8000")
DB_HOST     = os.getenv("DB_HOST",     "postgres")
DB_PORT     = int(os.getenv("DB_PORT", "5432"))
DB_NAME     = os.getenv("DB_NAME",     "postgres")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2346")

log = logging.getLogger(__name__)

def get_connection():
    """Return psycopg2 connection ke wired_db."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )

def create_table(**context):
    log.info("Membuat tabel wired_articles (jika belum ada)...")

    sql = """
        CREATE TABLE IF NOT EXISTS wired_articles (
            id          SERIAL PRIMARY KEY,
            session_id  VARCHAR(100),
            title       TEXT NOT NULL,
            url         TEXT,
            description TEXT,
            author_raw  TEXT,
            author      TEXT,
            scraped_at  TIMESTAMP,
            source      VARCHAR(100) DEFAULT 'Wired.com',
            inserted_at TIMESTAMP DEFAULT NOW()
        );
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        log.info("Tabel wired_articles siap.")
    finally:
        conn.close()

def fetch_from_api(**context):
    """
    Hit GET /articles ke FastAPI.
    Simpan hasilnya ke XCom supaya bisa dipakai task berikutnya.
    """
    url = f"{API_URL}/articles"
    log.info(f"Mengambil data dari: {url}")

    response = requests.get(url, timeout=30)
    response.raise_for_status()  # raise exception kalau status bukan 2xx

    data     = response.json()
    articles = data.get("articles", [])

    log.info(f"Berhasil mengambil {len(articles)} artikel dari API.")

    context["ti"].xcom_push(key="raw_articles", value=articles)

def transform_data(**context):
    articles = context["ti"].xcom_pull(key="raw_articles", task_ids="fetch_from_api")

    if not articles:
        log.warning("Tidak ada artikel untuk ditransformasi.")
        context["ti"].xcom_push(key="transformed_articles", value=[])
        return

    log.info(f"Mentransformasi {len(articles)} artikel...")
    transformed = []

    for article in articles:
        author_raw = article.get("author") or ""
        author_clean = author_raw

        scraped_at_raw = article.get("scraped_at") or ""
        try:
            dt = datetime.fromisoformat(scraped_at_raw)
            scraped_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.warning(f"Format scraped_at tidak valid '{scraped_at_raw}', diganti dengan waktu sekarang.")

        transformed.append({
            "session_id":  article.get("session_id") or "unknown",
            "title":       (article.get("title") or "").strip(),
            "url":         (article.get("url")   or "").strip(),
            "description": (article.get("description") or "").strip(),
            "author_raw":  author_raw,
            "author":      author_clean,
            "scraped_at":  scraped_at,
            "source":      article.get("source") or "Wired.com",
        })

    log.info(f"Transformasi selesai. {len(transformed)} artikel siap dimasukkan ke database.")

    context["ti"].xcom_push(key="transformed_articles", value=transformed)

def load_to_postgres(**context):
    articles = context["ti"].xcom_pull(
        key="transformed_articles",
        task_ids="transform_data"
    )

    if not articles:
        log.warning("Tidak ada artikel untuk dimasukkan ke database.")
        return

    log.info(f"Memasukkan {len(articles)} artikel ke PostgreSQL...")

    add_constraint_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'wired_articles_url_key'
            ) THEN
                ALTER TABLE wired_articles ADD CONSTRAINT wired_articles_url_key UNIQUE (url);
            END IF;
        END $$;
    """

    insert_sql = """
        INSERT INTO wired_articles
            (session_id, title, url, description, author_raw, author, scraped_at, source)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
    """

    conn = get_connection()
    inserted = 0
    skipped  = 0

    try:
        with conn.cursor() as cur:
            cur.execute(add_constraint_sql)

            for article in articles:
                cur.execute(insert_sql, (
                    article["session_id"],
                    article["title"],
                    article["url"],
                    article["description"],
                    article["author_raw"],
                    article["author"],
                    article["scraped_at"],
                    article["source"],
                ))
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1

        conn.commit()
        log.info(f"Selesai. Inserted: {inserted}, Skipped (duplikat): {skipped}")

    finally:
        conn.close()

default_args = {
    "owner":            "mahasiswa",
    "retries":          1,                        
    "retry_delay":      timedelta(minutes=2),    
    "email_on_failure": False,
}

with DAG(
    dag_id="wired_articles_pipeline",
    description="Pipeline: FastAPI → Transform → PostgreSQL",
    default_args=default_args,
    start_date=datetime(2026, 4, 1),
    schedule_interval="@daily",          
    catchup=False,                       
    tags=["wired", "scraping", "bigdata"],
) as dag:

    t1_create_table = PythonOperator(
        task_id="create_table",
        python_callable=create_table,
    )

    t2_fetch = PythonOperator(
        task_id="fetch_from_api",
        python_callable=fetch_from_api,
    )

    t3_transform = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data,
    )

    t4_load = PythonOperator(
        task_id="load_to_postgres",
        python_callable=load_to_postgres,
    )

    t1_create_table >> t2_fetch >> t3_transform >> t4_load