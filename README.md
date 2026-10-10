# AI Customer Service Platform

> 企业级电商智能客服 Agent・基于 RAG + Function Calling + Workflow 编排
> 改造自开源项目
>
> [lingyun1010/ecommerce-rag-agent](https://github.com/lingyun1010/ecommerce-rag-agent)
>
> ，模拟一家销售消费电子的企业「星澜数码 NovaTech」的真实客服系统。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)]()
[![LLM](https://img.shields.io/badge/LLM-OpenAI%2FDeepSeek%2FQwen%2FGLM%2FKimi-orange)]()
[![China Ready](https://img.shields.io/badge/国内部署-开箱即用-success)]()

**国产模型一键切换**：`MODEL_PROVIDER=deepseek|qwen|zhipu|kimi|openai`，默认 `local` 本地 BM25 零外部依赖。
国内部署详见 [README_CN.md](./README_CN.md)。

## 在线体验

启动后访问以下三个页面（默认端口 8010，部署到公网后替换成你的域名）：

| 页面 | 链接 | 作用 |
|---|---|---|
| 💬 **客服工作台** | [http://localhost:8010/](http://localhost:8010/) | 实际功能演示：售前 / 售后 / 工单全流程，点侧边栏按钮一键体验 |
| 📊 **项目介绍页** | [http://localhost:8010/showcase](http://localhost:8010/showcase) | 作品集展示：架构图、能力卡片、业务场景、一键启动命令 |
| 🛎 **SDK 嵌入演示页** | [http://localhost:8010/sdk-demo.html](http://localhost:8010/sdk-demo.html) | 模拟第三方网站：一行代码嵌入客服浮窗，多轮对话直连后端 |

![客服工作台](docs/screenshots/06-workbench-presale.png)
![售前 RAG 对话](docs/screenshots/02-presale-rag.png)
![订单物流查询](docs/screenshots/03-order-logistics.png)
![投诉转人工工单](docs/screenshots/04-escalation-ticket.png)



***

## 新能力（本轮升级）

| 能力 | 说明 | 入口 |
|---|---|---|
| **多轮上下文** | 同一 `session_id` 保留最近 8 轮对话：意图分类只看当前消息（避免历史词污染），订单号可从历史回退（"那退款呢"能自动关联上一单），RAG 支持"那它防水吗"这类指代 | 前端自动携带随机 `session_id` |
| **飞书对接** | `POST /feishu/webhook` 事件订阅：`url_verification` 挑战回显、`im.message.receive_v1` 消息解析，配 `FEISHU_APP_ID/FEISHU_APP_SECRET` 后可主动回复 | 飞书开放平台 |
| **引用阅读器** | RAG 回复附带逐条引用卡片：文件 + 相关度得分 + 原文，点击展开 | 工作台消息下方 |
| **SDK 浮窗** | 零依赖 `novatech-chat.js`：一行 `<script>` 即可给任意网站加客服浮窗，支持多轮会话、思考中/网络异常兜底 | `/novatech-chat.js` + `/sdk-demo.html` |
| **情绪话术库** | 联网收集真实客服话术：angry/anxious/disappointed/neutral 四类各多句随机；愤怒且无业务意图直接转人工 + P0 工单 | `agent_router.py` |

## 业务定位

一家销售消费电子（耳机 / 手表 / 键盘 / 充电器）的直营电商，客服需要同时覆盖：



| 场景       | 客户问题              | 系统处理方式                       |
| -------- | ----------------- | ---------------------------- |
| **售前咨询** | 产品参数、型号对比、配件、使用场景 | RAG 检索产品手册 + FAQ，命中商品时附带商品卡片 |
| **售后支持** | 订单状态、物流轨迹、退款流程    | 调用模拟订单 / 物流 / 退款业务接口         |
| **智能工单** | 投诉、升级人工、RAG 未命中   | 自动生成问题分类 / 优先级 / 处理建议        |



***

## 业务流程图



```mermaid
flowchart TD
    U[客户进入聊天] --> R{意图识别<br/>Intent Router}

    R -->|产品咨询/参数/对比| P[模块1 售前咨询]
    P --> RAG[RAG 知识库检索<br/>products.md / faq.md / manuals/]
    P --> SEARCH[商品库模糊搜索<br/>search_products]
    RAG --> A1[带引用的自然语言答复]
    SEARCH --> A1

    R -->|订单/物流/退款| O[模块2 售后支持]
    O --> DB[(模拟订单库<br/>orders.json)]
    O --> LG[物流轨迹<br/>carrier + events]
    O --> RF[退款流程<br/>状态机校验]
    DB --> A2[订单卡片 + 最新轨迹]

    R -->|投诉/人工/RAG未命中| T[模块3 智能工单]
    T --> CLS[问题分类<br/>物流/退款/质量/售前/发票]
    CLS --> PRI[优先级判定<br/>P0 紧急 / P1 高 / P2 常规]
    PRI --> SUG[处理建议生成]
    SUG --> A3[答复 + 工单卡片]

    A1 --> OUT[返回客户]
    A2 --> OUT
    A3 --> OUT
```



***

## 系统架构图



```mermaid
flowchart LR
    subgraph FE[前端]
        UI[vanilla JS 聊天工作台<br/>侧边栏 + 消息气泡 + 工单卡片]
    end

    subgraph API[FastAPI 层 :8010]
        CHAT[POST /chat]
        PROD[GET /products]
        ORD[GET /orders/:id]
        RF[POST /orders/:id/refund]
        TK[POST /tickets]
    end

    subgraph AGENT[Agent 编排层]
        IR[意图路由<br/>agent_router.py]
        TR[工具集<br/>commerce_api]
        RAG[RAG 服务<br/>rag_service.py]
        TKT[工单引擎<br/>ticket.py]
    end

    subgraph DATA[数据与知识]
        PDB[(商品库<br/>5 款电子产品)]
        ODB[(订单库<br/>4 笔订单 + 物流轨迹)]
        KB[(知识库<br/>products.md / faq.md / policy.md / manuals/)]
    end

    UI -->|HTTP| CHAT & PROD & ORD & RF & TK
    CHAT --> IR
    IR -->|PRE_SALE / RAG| RAG
    IR -->|ORDER / REFUND| TR
    IR -->|ESCALATE / 未命中| TKT
    TR --> PDB & ODB
    RAG --> KB
    TKT --> KB
```



***

## 技术栈



| 层            | 技术                                | 说明                                                                                                           |
| ------------ | --------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Agent**    | 规则路由 + LLM Function Calling 双路 | `llm_provider.py` 统一适配 OpenAI / DeepSeek / 通义 / 智谱 / Kimi；无 Key 时走规则兜底 |
| **RAG**      | LlamaIndex（生产）/ 自研 BM25（演示）       | 语料为产品手册 + FAQ + 售后政策；中文按 bigram 分词                                                                           |
| **API**      | FastAPI + Uvicorn                 | RESTful 接口，CORS 开放前端域                                                                                        |
| **Workflow** | 状态机路由                             | `PRE_SALE → RAG` / `ORDER_STATUS → commerce_api` / `REFUND → refund_state_machine` / `ESCALATE → ticket(P0)` |
| **前端**       | 原生 HTML/CSS/JS                    | 无框架，侧边栏工作台布局                                                                                                 |
| **数据**       | 纯 Python dataclass 模拟             | 商品库 / 订单库 / 物流轨迹 / 退款状态全部内存化                                                                                 |



***

## 目录结构



```
ecommerce-rag-agent/
├── api.py                # FastAPI 入口：/chat /products /orders /refund /tickets /feishu/webhook
├── agent_router.py       # 意图路由 + Agent 编排（保留原文件，扩展中文意图 + 多轮上下文）
├── openai_tool_router.py # OpenAI tool calling 路由（生产路径）
├── rag_service.py        # RAG 服务：LlamaIndex 生产路径 + BM25 本地兜底
├── commerce_api.py       # 模拟商品库 + 订单库 + 物流 + 退款（已替换为电子产品）
├── ticket.py             # 新增：智能工单（分类/优先级/处理建议）
├── feishu_bridge.py      # 新增：飞书 webhook 事件解析 + 主动回复
├── store_knowledge.py    # 保留：URL → Markdown 知识抽取工具
├── app.py                # 保留：CLI REPL
├── data/
│   ├── products.md       # 产品手册语料
│   ├── faq.md            # 客服 FAQ（40 条，覆盖售前/履约/售后）
│   ├── policy.md         # 售后政策（7天无理由/退款/保修）
│   └── manuals/
│       └── air100_manual.md  # 单品使用手册
├── frontend/             # 聊天工作台 UI + SDK 浮窗（novatech-chat.js / sdk-demo.html）
└── docs/screenshots/     # 运行截图
```



***

## 快速启动

### 方式 A：本地一键启动（推荐）

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
uvicorn api:app --host 0.0.0.0 --port 8010
```

浏览器直接打开 **http://localhost:8010** ，前后端一体。

> 默认 `MODEL_PROVIDER=local`，走规则路由 + BM25 RAG，零外网依赖。
> 想接国产大模型，复制 `.env.example` 为 `.env`，填一个 `DEEPSEEK_API_KEY`（或通义/智谱/Kimi）即可，详见 [README_CN.md](./README_CN.md)。

### 方式 B：Docker 启动

```bash
docker compose up -d --build
```

访问 http://localhost:8010 。

### 方式 C：开发模式（前后端分离）

```bash
uvicorn api:app --port 8010 --reload
cd frontend && python -m http.server 5173
```

访问 http://localhost:5173 。



***

## 演示场景



| 你问                          | 路由             | 看到什么                   |
| --------------------------- | -------------- | ---------------------- |
| Air100 和 Studio200 怎么选？     | `RAG`          | faq.md 答案 + 3 条知识库引用   |
| Watch30 防水吗？支持 iPhone 吗？    | `PRE_SALE`     | products.md 参数 + 商品卡片  |
| 我的订单 SO20260912001 物流到哪了？   | `ORDER_STATUS` | 订单状态 + 顺丰单号 + 3 条轨迹    |
| 我想退货，订单 SO20260930004 怎么退款？ | `REFUND`       | 退款受理 / 已在审核中等状态机校验     |
| 你们一般多久发货？运费多少？              | `RAG`          | faq.md 物流政策答案          |
| 这质量也太差了，我要投诉，转人工！           | `ESCALATE`     | 人工升级文案 + **P0 紧急工单卡片** |
| （先问 Air100）→ 那它防水吗？          | 多轮上下文 `RAG`   | 自动关联上一轮产品，命中 IPX5 防水参数 |
| （先报订单）→ 那退款呢？               | 多轮上下文 `REFUND` | 自动回退历史订单号，直接走退款状态机 |



***

## 核心 API



```
# 健康检查
curl http://127.0.0.1:8010/health

# 商品库
curl http://127.0.0.1:8010/products

# 订单详情（含物流轨迹 + 退款状态）
curl http://127.0.0.1:8010/orders/SO20260912001

# 提交退款
curl -X POST http://127.0.0.1:8010/orders/SO20260930004/refund \
  -H "Content-Type: application/json" \
  -d '{"reason":"不想要了"}'

# 聊天（多轮：同一 session_id 共享上下文）
curl -X POST http://127.0.0.1:8010/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Air100 和 Studio200 怎么选？","session_id":"demo-001"}'

# 飞书事件订阅（url_verification 挑战回显）
curl -X POST http://127.0.0.1:8010/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"xxxx"}'

# 飞书收到客户消息（mock 模式直接返回 reply）
curl -X POST http://127.0.0.1:8010/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"schema":"2.0","event":{"type":"im.message.receive_v1","message":{"chat_id":"oc_xxx","message_id":"om_1","content":"{\"text\":\"Air100 防水吗？\"}"}}}'

# 手动建工单
curl -X POST http://127.0.0.1:8010/tickets \
  -H "Content-Type: application/json" \
  -d '{"message":"耳机连不上蓝牙","order_id":"SO20260912001"}'
```



***

## 运行截图



| 初始工作台                                            | 售前 RAG 答复                                       |
| ------------------------------------------------ | ----------------------------------------------- |
| ![initial](docs/screenshots/01-initial-chat.png) | ![presale](docs/screenshots/02-presale-rag.png) |



| 订单物流卡片                                            | 智能工单（P0 升级）                                          |
| ------------------------------------------------- | ---------------------------------------------------- |
| ![order](docs/screenshots/03-order-logistics.png) | ![ticket](docs/screenshots/04-escalation-ticket.png) |



| 多轮上下文 + 引用阅读器                                      | SDK 浮窗嵌入演示（第三方网站视角）                          |
| ------------------------------------------------- | --------------------------------------------- |
| ![multiturn](docs/screenshots/07-workbench-multiturn.png) | ![sdk](docs/screenshots/08-sdk-demo.png) |



| SDK 浮窗内多轮对话                                        | 项目介绍页（作品集展示）                                    |
| ------------------------------------------------- | --------------------------------------------- |
| ![sdkchat](docs/screenshots/09-sdk-chat.png)       | ![showcase](docs/screenshots/05-showcase-page.png) |



***

## 设计取舍：为什么 API + RAG + Agent 要拆开



* **精确业务数据走 API**：订单状态、物流轨迹、退款金额、库存、价格 —— 这些是动态、强一致的事实，必须从业务库读，不能让 LLM 编。

* **解释性知识走 RAG**：产品手册、FAQ、售后政策 —— 这些是文本，会更新，需要带引用可追溯。

* **路由走 Agent**：同一句话「我想退钱」可能是售前问政策、也可能是售后真要退某单，Agent 根据是否带订单号、是否有情绪词来决定走哪条路。

* **不确定的问题自动转工单**：RAG 没命中 / 用户提投诉 / 情绪激烈，立即生成结构化工单交给人。

这就是一个最小可用、但流程完整的企业客服自动化闭环。



***

## Credits



* 基础架构：[lingyun1010/ecommerce-rag-agent](https://github.com/lingyun1010/ecommerce-rag-agent)

* RAG 框架：[LlamaIndex](https://github.com/run-llama/llama_index)

* Web 框架：[FastAPI](https://fastapi.tiangolo.com/)