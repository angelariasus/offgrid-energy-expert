FROM python:3.11-slim

# Dependencias de sistema necesarias para compilar clipspy, que embebe el
# motor CLIPS original (escrito en C) y requiere un compilador C disponible
# durante `pip install`.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Se copian primero los requirements para aprovechar el cache de capas de
# Docker: solo se reinstalan dependencias si requirements.txt cambia.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
