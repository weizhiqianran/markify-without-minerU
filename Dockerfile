FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

ENV HF_ENDPOINT="https://hf-mirror.com"

# 设置工作目录
WORKDIR /app

# 将 requirements.txt 复制到容器中
COPY requirements.txt .

# 安装依赖
RUN pip install --upgrade -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple pip && \
    pip install --no-cache-dir -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt

# 将应用代码复制到容器中
COPY . .

# 暴露应用服务端口
EXPOSE 20926

# 定义启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "20926"]
