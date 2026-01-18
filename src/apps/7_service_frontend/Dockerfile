FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY src/apps/7_service_frontend/requirements.txt /app/requirements.txt
COPY src/apps/7_service_frontend/.env.example /app/.env.example

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8002

CMD ["python", "-m", "src.apps.7_service_frontend.main"]
