FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY fixtures /app/fixtures

ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["uvicorn", "southpole_pipeline.api:app", "--host", "0.0.0.0", "--port", "8080"]
