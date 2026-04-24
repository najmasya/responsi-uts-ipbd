FROM selenium/standalone-chrome:latest

USER root

RUN apt-get update && apt-get install -y python3 python3-pip --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

COPY scraper.py .

RUN mkdir -p /app/data

CMD ["python3", "scraper.py"]