# 面试速通笔记 · AI Customer Service Platform

> 目标：3 小时掌握，面试能答出来。按时间分三段。

---

## 第 1 小时：项目全景与架构（背熟这一节）

### 1.1 一句话介绍

"这是一个模拟消费电子企业（星澜数码 NovaTech）的 AI 客服系统。客户问售前/售后/退款问题时，系统用 **RAG 检索知识库**回答政策类问题，用 **Function Calling 调业务接口**查订单/物流/退款，回答不了的自动**生成工单转人工**。默认跑本地规则+BM25 零依赖，一行环境变量切 DeepSeek/通义/智谱/Kimi。"

### 1.2 技术栈

| 层 | 技术 | 为什么选它 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | 异步、自带 OpenAPI 文档、轻量 |
| 前端 | 原生 HTML/CSS/JS，无打包 | 作品演示要零构建，单端口托管 |
| 意图路由 | 规则路由（正则+关键词）兜底，OpenAI Function Calling 升级 | 无 Key 也能跑，有 Key 自动变强 |
| RAG | 本地 BM25（中文 bigram）兜底；有 Key 切 LlamaIndex 向量检索 | BM25 零依赖、可解释；向量检索语义更强 |
| 业务接口 | Python dict 模拟商品库/订单库 | 作品演示不需要真数据库 |
| 工单 | 关键词分类 + P0/P1/P2 优先级 | 展示"自动化"能力 |
| 部署 | Docker + docker-compose | 一条命令起服务 |

### 1.3 请求链路（必须能画出来）

```
用户发消息
  ↓
POST /chat
  ↓
agent_router.answer_message()
  ↓
should_use_openai_tool_router()？
  ├─ 是（有 Key）→ openai_tool_router：LLM 自己决定调哪个函数
  └─ 否（默认）  → answer_message_rule_based：规则分类意图
        ↓
  classify_intent(message)
        ↓
  ┌─ ESCALATE  → escalate_to_human() + P0 工单
  ├─ REFUND    → extract_order_id() → request_refund()
  ├─ ORDER_STATUS → extract_order_id() → get_order() → 格式化物流轨迹
  ├─ PRE_SALE  → search_products() + RAG
  └─ RAG 兜底  → answer_with_rag()
        ↓
  RAG 未命中 → 情绪识别 → 兜底话术 + 工单
  RAG 命中但是售后类 → 仍自动建工单让人工跟进
        ↓
返回 {intent, answer, tool_result, sources, ticket}
```

### 1.4 三个核心设计决策（面试加分点）

1. **双路路由**：规则路由和 LLM tool calling 同时存在，通过 `AGENT_ROUTER` 环境变量切换。没有 OpenAI Key 时作品也能跑；有 Key 时自动升级成真正的 Agent。
2. **RAG 双层**：BM25 本地兜底（零依赖、可解释），有 Key 时切 LlamaIndex 向量检索。chunk 按 `##` 标题切分而不是按空行，避免"问 Air100 充电时间"命中保修表。
3. **工单不是只在出错时建**：RAG 命中但问题属于售后类（破损/故障/少发），照样建工单让人工跟进——客户拿到自助答案的同时后台有人接管。

---

## 第 2 小时：核心模块深挖

### 2.1 RAG 模块（rag_service.py）

**问：你的 RAG 怎么实现的？**

- 知识库就是 `data/` 下的 Markdown：`products.md`（5 个产品手册）、`faq.md`（40 条 Q&A）、`policy.md`（售后政策）、`manuals/air100_manual.md`。
- **Chunk 策略**：按 `##`/`###` 二级标题切分，每个 Q&A 独立成 chunk。之前按空行切太粗导致误命中，改成按标题切。
- **中文分词**：bigram（二元切分）。比如"充电仓"切成"充电""电仓"。英文按词。不用 jieba 是为了零依赖。
- **检索算法**：BM25（k1=1.5, b=0.75），纯 Python 实现，不用 Elasticsearch。
- **产品名加权**：query 里提到 Air100，chunk 也提到 → score ×1.6。解决"耳机续航"被通用政策答案抢分的问题。
- **阈值**：score < 25 视为未命中（实测好匹配 55+，噪声 7-16），避免"你们老板姓什么"硬命中"你们卖哪些产品"。
- **有 Key 时**：自动切 LlamaIndex + 对应厂商 embedding（通义 text-embedding-v3 / 智谱 embedding-3）。

**问：为什么不用向量数据库？**
- 作品演示数据量小（4 个 md 文件），BM25 足够；零外部依赖，`pip install -r requirements.txt` 就能跑。生产环境再接 Milvus/PGVector。

### 2.2 意图路由（agent_router.py）

**问：怎么区分"问退款政策"和"我要退款"？**

这是这个项目最关键的一个细节（面试会问）：

- "7 天无理由条件是什么？" → 问政策 → 走 RAG
- "帮我退 SO20260912001" → 真退款 → 走退款流程

实现：`classify_intent` 里，命中 `REFUND_TERMS` 后还要判断：
- 消息里有没有订单号（正则 `SO\d{10,}` 或 `#\d{6,}`）
- 有没有"我的订单/我买的/刚收到"这种指代
- 两个都没有 → 视为问政策，走 RAG

**问：情绪识别怎么做的？**
- 关键词命中：angry（垃圾/骗子/投诉）、anxious（快点/加急/出差）、disappointed（失望/不值/不好用）、neutral。
- 每类 3-4 句兜底话术随机选。不是 LLM 做的，纯关键词——快、可控、零成本。

### 2.3 工单模块（ticket.py）

**问：工单怎么生成的？**

- **分类**：7 类（物流异常/少发漏发/退款退货/产品质量故障/订单变更/支付发票/售前咨询），统计每类关键词命中数，命中最多的赢。
- **优先级**：P0（投诉/12315/主管）> P1（没收到/坏了/破损）> P2。
- **处理建议**：硬编码的 SOP 文案，按分类映射。
- **工单号**：`itertools.count(1001)` 自增，内存态（重启重置，作品演示够用）。

### 2.4 业务接口（commerce_api.py）

- 5 个商品（Air100 ¥899 / Studio200 ¥1599 / Watch30 ¥1299 / GaN65 ¥149 / Key87 ¥399）
- 4 笔订单，每笔有：items、total、status、logistics（carrier/tracking_no/events[]）、refund 状态机
- 退款状态机：`none → requested → approved → refunded`，只有 in_transit/delivered 状态才能退

### 2.5 模型抽象层（llm_provider.py）

**问：怎么切换国产大模型？**

- 环境变量 `MODEL_PROVIDER=deepseek|qwen|zhipu|kimi|openai`
- 所有国产厂商都提供 OpenAI 兼容接口，所以统一用 `openai` SDK，只换 `base_url`：
  - DeepSeek: `https://api.deepseek.com/v1`
  - 通义: `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - 智谱: `https://open.bigmodel.cn/api/paas/v4`
  - Kimi: `https://api.moonshot.cn/v1`
- 这是面试高频：**OpenAI 兼容协议已经事实成为行业标准**，国内厂商全部对齐，所以一套代码切五家。

---

## 第 3 小时：工程化 + 面试高频题

### 3.1 国内化改造（这个项目的特色）

| 风险 | 处理 |
|---|---|
| Google Fonts | 用系统字体栈（PingFang/微软雅黑） |
| 外部 CDN | 无，CSS/JS 全自托管 |
| pip 源 | Dockerfile 写阿里云 mirrors.aliyun.com |
| Docker Hub | 文档给 USTC 加速器 |
| OpenAI 被墙 | 默认 local 模式不调；有 Key 切国产 |
| 向量库 | 默认 BM25 本地，不依赖 Pinecone |

### 3.2 部署

```bash
# 本地
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
uvicorn api:app --port 8010

# Docker
docker compose up -d --build
```

单容器前后端一体，FastAPI 用 `StaticFiles(directory=frontend)` 挂在 `/` 根路径。

### 3.3 面试高频问题（自己答一遍）

1. **这个项目和直接调 ChatGPT 有什么区别？**
   - 直接调 ChatGPT 是无状态的，它不知道用户订单号、不能查物流、不能真的退款。这个项目把 LLM 当路由/推理引擎，真正的业务动作走自己的工具接口，有状态、有边界、有工单兜底。

2. **RAG 为什么需要 BM25 兜底？**
   - 没 Key 也能跑；BM25 对精确术语（订单号、型号）更准；可解释（能看到 score 和 chunk）。

3. **怎么避免乱回答？**
   - 三道闸：① 意图路由先判断是不是售后/订单，问政策不会误走退款；② BM25 阈值 25，低置信度直接转人工；③ 情绪识别后兜底话术不硬答。

4. **为什么 chunk 按标题切？**
   - 按空行切会把"保修政策"和"充电时间"混在一个 chunk，问充电时间返回保修表。按 `##` 标题切每个 Q&A 独立。

5. **生产化要做什么？**
   - 工单入库（SQLite/PG）、接真订单系统、向量库换 Milvus、加对话历史（多轮）、鉴权、限流、日志、A/B 评测。

---

## 练习题（学完自测）

### 选择题

1. 客户说"7 天无理由是什么条件"，系统应该走哪条路？
   - A. REFUND 退款流程
   - B. RAG 知识库
   - C. ESCALATE 转人工
   - D. ORDER_STATUS 查订单

2. BM25 阈值设为 25 的原因是？
   - A. 数字随便选的
   - B. 实测好匹配 55+，噪声 7-16，25 能分开
   - C. 越高越准
   - D. 跟 OpenAI 限制有关

3. 切换到通义千问要改什么？
   - A. 重写整个 LLM 调用层
   - B. 改 `base_url` 为 dashscope 兼容地址
   - C. 用 LangChain
   - D. 必须用 PyTorch

4. 客户问"你们老板姓什么"，系统会？
   - A. 编造一个答案
   - B. BM25 命中"你们卖哪些产品"
   - C. BM25 分数 < 25，走情绪识别兜底话术转人工
   - D. 直接报错

5. 工单 P0 优先级的触发词不包括？
   - A. 投诉
   - B. 12315
   - C. 没收到货
   - D. 主管

### 简答题

6. 画一下一条用户消息从发起到返回的完整链路。

7. 为什么"问退款政策"和"我要退款"要分开处理？怎么实现的？

8. 这个项目的双路路由（规则 vs LLM tool calling）各自优缺点？

9. RAG 的 chunk 策略是什么？为什么不用固定长度切？

10. 如果让你把这个项目接到真的电商系统，第一步改哪个文件？

---

### 答案

1. B（问政策走 RAG，没有订单号和"我的"指代）
2. B
3. B（OpenAI 兼容协议，只换 base_url）
4. C
5. C（没收到货是 P1）
6. 见 1.3
7. 见 2.2（有订单号/指代才走退款，否则视为问政策）
8. 规则：快、可控、零成本但泛化差；LLM tool calling：能理解自然语言但要 Key、有成本、可能幻觉。本项目两者共存，无 Key 跑规则，有 Key 自动切 LLM。
9. 按 `##` 标题切，每个 Q&A 独立；固定长度会把答案和不相关内容切断。
10. `commerce_api.py`：把 LISTINGS/ORDERS 从内存 dict 换成真数据库查询。
