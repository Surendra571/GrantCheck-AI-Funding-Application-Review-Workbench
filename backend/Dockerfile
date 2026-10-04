FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get update \
    && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
