FROM python:3.11-slim

WORKDIR /app

# Python 依赖(根目录 requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制全部源码
COPY . .

# 后端工作目录 + 启动(Railway 注入 PORT)
WORKDIR /app/backend
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
