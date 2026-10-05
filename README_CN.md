# AI Customer Service Platform · 国内部署指南

> 本文面向中国大陆开发者，所有步骤无需翻墙即可完成。

## 一、本地运行（最快 30 秒）

```bash
git clone https://github.com/xingjianlu573-dot/dianshanznkf.git
cd dianshanznkf

# 建议使用阿里云 PyPI 镜像加速
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 本地模式（默认，零外部 API Key）
python -m uvicorn api:app --host 0.0.0.0 --port 8010
```

浏览器打开 http://localhost:8010 即可，前后端一体。

## 二、切换国产大模型

复制 `.env.example` 为 `.env`，按需填写一项即可：

| MODEL_PROVIDER | 厂商 | 需要的环境变量 | 申请地址 |
|---|---|---|---|
| `deepseek` | DeepSeek 深度求索 | `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ |
| `qwen` | 通义千问 | `DASHSCOPE_API_KEY` | https://dashscope.console.aliyun.com/ |
| `zhipu` | 智谱 GLM | `ZHIPU_API_KEY` | https://open.bigmodel.cn/ |
| `kimi` | 月之暗面 Kimi | `MOONSHOT_API_KEY` | https://platform.moonshot.cn/ |
| `openai` | OpenAI 官方 | `OPENAI_API_KEY`（需海外网络） | https://platform.openai.com/ |

示例（切到 DeepSeek）：

```bash
# .env
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

重启服务即可，所有国产厂商均为 OpenAI 兼容接口，代码无需改动。

## 三、Docker 部署

```bash
docker compose up -d --build
```

容器已配置阿里云 pip 镜像加速构建。访问 http://localhost:8010 。

> 如果 `docker pull python:3.11-slim` 慢，请在 `/etc/docker/daemon.json`（Linux）或 Docker Desktop 设置里加国内镜像加速器：
> ```json
> { "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"] }
> ```

## 四、云服务器部署方案

### 方案 A：阿里云 / 腾讯云轻量应用服务器（推荐）

1. 买一台 2C2G 以上的轻量应用服务器，系统选 Ubuntu 22.04。
2. 安全组放行 8010 端口（或 80/443）。
3. SSH 上去后：
   ```bash
   git clone https://github.com/xingjianlu573-dot/dianshanznkf.git
   cd dianshanznkf
   docker compose up -d --build
   ```
4. 用 Nginx 反代 8010 到 80 并配 HTTPS（certbot）。

### 方案 B：阿里云函数计算 / 腾讯云 CloudBase（Serverless）

把 `api:app` 作为 ASGI 应用上传，无服务器运维，按调用计费。

### 方案 C：本地 Docker 演示

适合作品展示、答辩、客户现场演示，一条命令起服务。

## 五、国内访问优化清单

| 项 | 处理方式 |
|---|---|
| 前端 CDN | 无外部 CDN，HTML/CSS/JS 全部自托管 |
| 字体 | 系统字体栈，不引 Google Fonts |
| 图片 | 无外链图片 |
| pip 源 | Dockerfile 默认阿里云镜像 |
| Docker Hub | 文档提供 USTC 加速器 |
| 大模型 | 抽象层支持 DeepSeek/通义/智谱/Kimi，无需 OpenAI |
| 向量库 | 默认 BM25 本地检索，不依赖 Pinecone/Weaviate |
| Embedding | 切国产模型时用 DashScope text-embedding-v3 或智谱 embedding-3 |

## 六、常见问题

**Q：不配任何 API Key 能用吗？**
A：能。默认走本地规则路由 + BM25 RAG，所有 FAQ 都能答，仅无法用 LLM 做自然语言意图泛化。

**Q：切换模型后需要重建向量库吗？**
A：默认 BM25 模式不需要。切到 LLM 模式时，启动会自动用对应厂商的 embedding 建索引。

**Q：8010 端口被占用？**
A：改启动命令 `--port 你的端口`，或改 docker-compose.yml 的端口映射。

**Q：Windows 下中文乱码？**
A：PowerShell 里先执行 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`。
