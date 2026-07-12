FROM python:3.13-slim

# 编译依赖(部分 wheel 之外的包需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
WORKDIR /app/backend
EXPOSE 8080
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
