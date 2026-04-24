# responsi-uts-ipbd
Pipeline otomatis untuk scraping artikel Wired.com menggunakan Selenium, FastAPI, Airflow, dan PostgreSQL.
Arsitektur
Selenium → articles.json → FastAPI → Airflow DAG → PostgreSQL

Prasyarat

Docker Desktop sudah terinstall dan berjalan

Langkah Menjalankan
1. Buat folder Project
cd responsi-ipbd

2. Jalankan Semua Service
docker compose up -d

3. Jalankan Scraper
docker compose run --rm scraper
Scraper akan membuka Wired.com dan menyimpan 50+ artikel ke data/articles.json. Proses ini memakan waktu 3-5 menit.

4. Trigger DAG di Airflow
Buka http://localhost:8080
Login: admin / admin
Cari DAG wired_articles_pipeline → klik tombol ▶ (Trigger DAG)
Tunggu semua task hijau (success)

5. Verifikasi Data
docker exec -it responsi psql -U postgres -d responsi_uts
sqlSELECT COUNT(*) FROM wired_articles;

6. Jalankan Query
sql-- Query 1: Judul + author tanpa kata "By"
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
WHERE title ILIKE '%AI%' OR title ILIKE '%Climate%' OR title ILIKE '%Security%'
OR description ILIKE '%AI%' OR description ILIKE '%Climate%' OR description ILIKE '%Security%';

Port yang Digunakan
Airflow UI: http://localhost:8080
FastAPI: http://localhost:8000
FastAPI Docs: http://localhost:8000docs
PostgreSQL: localhost:5434