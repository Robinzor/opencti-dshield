FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"] 