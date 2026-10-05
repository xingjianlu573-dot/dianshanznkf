# 国内容器构建：默认使用阿里云 pip 镜像加速
FROM python:3.11-slim

WORKDIR /app

# 先装依赖（利用层缓存），使用阿里云 PyPI 镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set global.trusted-host mirrors.aliyun.com

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 业务代码
COPY . .

EXPOSE 8010

ENV HOST=0.0.0.0 \
    PORT=8010 \
    MODEL_PROVIDER=local

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8010"]
