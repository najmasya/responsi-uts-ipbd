# Responsi UTS IPBD

Pipeline otomatis untuk scraping artikel Wired.com menggunakan Selenium, FastAPI, Airflow, dan PostgreSQL.

## Arsitektur
```
Selenium → articles.json → FastAPI → Airflow DAG → PostgreSQL
```

## Prasyarat
- Docker Desktop sudah terinstall dan berjalan

## Langkah Menjalankan

### 1. Buka path folder projek
```bash
cd responsi-ipbd
```

### 2. Jalankan semua service
```bash
docker compose up -d
```

### 3. Jalankan scraper
```bash
docker compose run --rm scraper
```
Scraper akan membuka Wired.com dan menyimpan 50+ artikel ke `data/articles.json`

### 4. Trigger DAG di Airflow
- Buka `http://localhost:8080`
- Login: `admin` / `admin`
- Cari DAG `wired_articles_pipeline` → klik tombol ▶ (Trigger DAG)
- Tunggu semua task hijau (success)

### 5. Verifikasi data
```bash
docker exec -it responsi psql -U postgres -d responsi_uts
```
```sql
SELECT COUNT(*) FROM wired_articles;
```

### 6. Jalankan Query
```sql
-- Query 1: Judul + author tanpa kata "By"
SELECT title, TRIM(REPLACE(author, 'By', '')) AS author
FROM wired_articles;

-- Query 2: 3 penulis terbanyak
SELECT TRIM(REPLACE(author, 'By', '')) AS author, COUNT(*) AS jumlah_artikel
FROM wired_articles
WHERE author IS NOT NULL AND author != ''
GROUP BY author
ORDER BY jumlah_artikel DESC
LIMIT 3;

-- Query 3: Artikel dengan keyword AI / Climate / Security
SELECT title, description, author
FROM wired_articles
WHERE title ILIKE '%AI%'
OR title ILIKE '%Climate%'
OR title ILIKE '%Security%'
OR description ILIKE '%AI%'
OR description ILIKE '%Climate%'
OR description ILIKE '%Security%';
```

## Port yang Digunakan
| Service | URL |
|---|---|
| Airflow UI | http://localhost:8080 |
| FastAPI | http://localhost:8000 |
| FastAPI Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5434 |
