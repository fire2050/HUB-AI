FROM docker.m.daocloud.io/library/python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FINANCE_WUKONG_DB=/data/finance_wukong.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
RUN mkdir -p /data

EXPOSE 8000
CMD ["sh", "-c", "python scripts/init_db.py && python scripts/init_hubai_db.py && python scripts/init_hubai_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
