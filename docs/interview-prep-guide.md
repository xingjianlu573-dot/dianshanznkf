# AI Customer Service Platform · 3 小时面试速成指南

> 目标：3 小时内把这个项目吃透到"面试官问什么都接得住、深挖也不虚"的程度。
> 使用方式：按【学习路线】分 3 段推进，每段结束自测；全部学完做文末【练习题】。
> 原则：每一句话都能在代码里找到出处——面试时讲到的都是你真实改过、跑过、踩过的。

---

## 〇、学习路线（3 小时总控）

| 时间段 | 内容 | 产出 |
|---|---|---|
| 0:00-0:15 | 第一部分：项目全景 | 一句话讲清项目 + 架构地图 |
| 0:15-0:50 | 第二部分 模块 1-4：数据层 + 知识库 + RAG | 能画检索流程、讲 BM25 |
| 0:50-1:20 | 第二部分 模块 5-7：Agent 路由 + 情绪话术 + 工单 | 能走一遍"一条消息的处理流水线" |
| 1:20-1:40 | 第二部分 模块 8-12：LLM 抽象 + API + 飞书 + 前端 + 部署 | 能讲国产模型切换、会话管理、部署 |
| 1:40-2:20 | 第三部分：面试 Q&A | 20 高频 + 深挖题过一遍 |
| 2:20-2:50 | 第四部分：练习题 | 客观 + 简答 + 场景，核对答案 |
| 2:50-3:00 | 复盘：自己口述一遍项目（30 秒版 + 1 分钟版 + STAR 故事） | 形成肌肉记忆 |

---

## 一、项目全景（10 分钟）

### 1.1 一句话版本

> 我把一个开源的 ecommerce RAG Agent 改造成了一个**企业级 AI 客服平台**：模拟"星澜数码 NovaTech"这家消费电子公司，用 **RAG（检索增强）+ Agent（意图路由）+ Workflow（订单/退款状态机）** 实现售前咨询、售后支持、智能工单三大场景，默认零 API Key 可跑，配置一行环境变量就能切换 DeepSeek/通义千问/智谱/Kimi 国产大模型。

### 1.2 项目定位（面试怎么开场）

- **背景**：基于 `lingyun1010/ecommerce-rag-agent` 开源项目二次开发，README 保留 Credits（诚实加分项）。
- **业务场景**：客户会问产品参数/区别/使用场景（售前），订单状态/物流/退货/售后政策（售后），问题来了系统自动生成工单（智能工单）。
- **核心目标**：证明自己能把一个 AI 应用做成**有业务流程、有边界、不乱回复**的工程，而不是套壳 ChatGPT。
- **三个数字**：5 个模拟产品、4 笔模拟订单、40 条 FAQ。

### 1.3 技术栈（背熟，面试第一问）

| 层 | 技术 |
|---|---|
| 语言/框架 | Python 3.11+ / FastAPI / Pydantic v2 |
| RAG | 本地 BM25（中文 bigram）+ LlamaIndex 向量检索（生产路径） |
| Agent | 规则路由（默认）+ OpenAI Function Calling（配 key 后自动启用）双路 |
| 数据 | 内存 dataclass 模拟商品/订单库（无数据库依赖） |
| 渠道 | 飞书 Webhook 对接（mock / api 双模式） |
| 前端 | 原生 HTML/JS（工作台 + 展示页 + SDK 浮窗），无构建工具 |
| 部署 | Docker / docker-compose，阿里云 pip 镜像，国产 LLM 适配 |
| 测试 | tests/regression.py（16 用例）+ tests/user_test.py（30+ 用例） |

### 1.4 架构地图（文字版，能自己画）

```
客户消息（网页工作台 / 飞书 / SDK 浮窗）
        │
        ▼
   api.py /chat（校验、会话管理 LRU）
        │
        ▼
   agent_router.answer_message()
        ├── 有 API Key 且 AGENT_ROUTER≠rules ──► openai_tool_router（Function Calling）
        │                                       ├── 调 get_order / escalate 等工具
        │                                       └── 不调工具 → RAG
        └── 否则 ──► answer_message_rule_based（默认路径）
              ├── 1. 敏感词/情绪 → 转人工 + P0 工单
              ├── 2. 退款（带订单号/指向自己）→ request_refund 状态机
              ├── 3. 订单/物流（带订单号）→ get_order + 轨迹
              ├── 4. 售前/RAG（多轮上下文）→ rag_service
              └── 5. RAG 未命中 → 情绪话术 + 自动建工单转人工
        │
        ▼
   ticket.py 智能工单（7 类分类 / P0-P1-P2 优先级 / 处理建议）
```

### 1.5 项目演进故事（讲"像自己做的"的关键）

面试官问"这项目怎么来的"，按这个真实脉络讲：

1. **第一轮：接住开源项目**——保留原架构（`store_knowledge.py`、`openai_tool_router.py`、LlamaIndex 路径都是原项目的），先让它在本地跑起来，摸清结构。
2. **第二轮：业务化**——把原项目的商品数据换成企业产品数据（5 款消费电子），知识库增加产品手册/FAQ/售后规则，加模拟订单接口（订单状态机 + 物流轨迹 + 退款流程）。
3. **第三轮：功能闭环**——增加智能工单（自动分类/优先级/处理建议）、多轮上下文（指代"那它防水吗"）、飞书 webhook 对接、SDK 浮窗。
4. **第四轮：识别加敏**——用户实测发现会"乱回复"，于是：意图词表扩到 30+、情绪识别三档、知识库未命中统一转人工话术（分 4 档情绪语气）、新增属性校验兜底（保证"那它防水吗"一定答到防水）。
5. **第五轮：国产化与展示**——LLM Provider 抽象层（一行环境变量切换 4 家国产模型）、Docker 国内镜像优化、展示页/工作台/豆包在线展示。

每轮都能说"我当时遇到了什么问题、为什么这么改"——这就是"自己做的"的质感。

---

## 二、核心知识点详解

### 模块 1：模拟数据层 `commerce_api.py`

**作用**：整个系统的"业务数据库"，用 Python dataclass 模拟（面试可说"内存态数据层，生产可换 PostgreSQL/Redis"）。

**商品库**（5 款，重点记住 2-3 款参数）：
- `NT-AIR100` 智能降噪耳机 ¥899：-42dB 降噪、蓝牙 5.3、续航 8h/32h、**防水 IPX5**、4.6g
- `NT-STUDIO200` 头戴耳麦 ¥1599：-48dB、蓝牙 5.4、45h、258g、双 AI 通话降噪
- `NT-WATCH30` 智能手表 ¥1299：1.43" AMOLED、420mAh/7 天、**5ATM+IP68**、心率血氧 GPS、Android9+/iOS14+
- `NT-GAAN65` 65W 氮化镓充电器 ¥149：PD3.0/QC4+/PPS、1C1A、折叠插脚
- `NT-KEY87` 机械键盘 ¥399：87 键 TKL、三模（蓝牙/2.4G/有线）、热插拔、4000mAh

**订单库**（4 笔，面试常被问"状态机"）：
- 状态流：`paid → shipped → in_transit → delivered → refund_applied`
- 每单含：items / total / status / logistics（carrier + tracking_no + events 轨迹）/ refund（status/reason/amount）
- 退款状态机：`none → reviewing → approved → rejected → refunded`
- 示例：`SO20260930004` 是 refund_applied + reviewing（耳罩夹头申请 7 天无理由）

**关键函数（面试能背）**：
- `list_products()` 全量商品
- `search_products(keyword)` 在品名/品类/参数里子串模糊搜索（返回 price/stock 卡片）
- `get_order(order_id)` 精确查单，返回完整结构（含轨迹最后 3 条）
- `request_refund(order_id, reason)` **状态机校验**：订单不存在→报错；状态不在 delivered/shipped/in_transit/refund_applied→拒绝；已在 reviewing→拒绝；已 refunded→拒绝。合法才受理。
- `escalate_to_human(reason, platform)` 转人工（返回工作时间 9:00-21:00，非工作时间次日 10 点前回访）

**面试点**：退款为什么有这么多校验？→ "状态机防止非法流转，比如已退款不能重复退、未付款不能退"。

### 模块 2：知识库 `data/`

| 文件 | 内容 | 作用 |
|---|---|---|
| `products.md` | 5 款产品介绍（## 标题分块） | 商品知识 |
| `faq.md` | **40 条 Q&A**（售前/使用/售后分类） | FAQ 检索 |
| `policy.md` | 7 小节售后政策（物流/7 天无理由/运费/保修等） | 政策检索 |
| `manuals/air100_manual.md` | 产品手册（排查步骤） | 故障排查 |

政策要点背 3 条（面试常问"知识库里有什么"）：
- 发货：工作日 16:00 前付款当日发，16:00 后顺延
- 运费：满 ¥99 包邮，不满 ¥8，新疆/西藏/青海 +¥15
- 7 天无理由：签收次日起 7 天内可退

**设计点**：`store_knowledge.py` 是原项目的知识抓取工具（保留架构但默认不用），RAG 语料默认直接从 `data/` 读——"改造时保留原项目能力，但默认路径更简单可控"。

### 模块 3：RAG 层 `rag_service.py`（面试重点）

**双路径设计**：
- **生产路径**：配置 API Key 后，LlamaIndex 加载知识库 → 切分（chunk_size=400, overlap=40）→ 向量索引 → query_engine（top_k=3）。Embedding 用 OpenAI 兼容接口（国产模型的 embedding，如通义 text-embedding-v3）。
- **本地兜底（默认）**：纯 Python 实现 BM25，零外部依赖，离线可跑。

**BM25 实现细节（深挖题必考）**：
1. **中文分词用 bigram（二元组）**：`"防水吗" → "防水","水吗"`；英文/数字按词（`re.findall(r"[a-z0-9]+")`）。为什么 bigram？—— 中文没有天然空格分词，bigram 无需词典、对拼写容错好、实现简单。
2. **chunk 切分**：按 `## / ###` 标题切（每个 Q&A、每个政策小节独立成 chunk），丢掉文件级 `#` 标题。为什么按标题？—— 语义完整、引用可溯源（返回 file_name + 原文）。
3. **BM25 公式**：`score = Σ idf * (tf*(k1+1)) / (tf + k1*(1-b+b*dl/avgdl))`，k1=1.5, b=0.75 经典参数。
4. **产品名加权**：query 命中产品别名（`PRODUCT_ALIASES`，如 air100→"air100/蓝牙耳机/tws"）时，含该产品的 chunk 得分 ×1.6。
5. **阈值 25**：top1 分数 < 25 判定"未命中"→ 走转人工兜底。实测好匹配 55+，噪声 7-16，25 是经验阈值。
6. **确定性兜底 `_product_chunk`**：短查询（"Air100 怎么样"）BM25 分数不足时，直接返回 products.md 里对应产品介绍块（score=99 标记）。

**面试怎么答"为什么 BM25 不用向量"**：
> "本地模式要零依赖可离线演示；BM25 关键词检索对 FAQ/政策这类高词面重叠文本够用，且可解释（引用可溯源）。生产路径我保留了 LlamaIndex 向量检索，配 key 自动切换，两种都支持。"

### 模块 4：意图路由 + Agent 编排 `agent_router.py`（核心中的核心）

**5 类意图**：`ESCALATE`（升级人工）/ `REFUND`（退款）/ `ORDER_STATUS`（订单物流）/ `PRE_SALE`（售前）/ `RAG`（知识问答兜底）。

**分类流程 `classify_intent`（顺序很重要，能默写）**：
1. 命中 `ESCALATION_TERMS`（投诉/315/曝光/找领导/转人工等 30+ 词）→ **ESCALATE**
2. 命中退款词：**必须带订单号或"我的订单/我买的"等指向自己的提示**才走 REFUND；否则（如"7 天无理由""退款多久到账"）→ RAG 当政策问题回答
3. 命中订单/物流词 + 订单号/own_order_hint → **ORDER_STATUS**
4. 命中产品词（价格/参数/对比/续航/防水/配件…）→ **PRE_SALE**
5. 兜底 → **RAG**

**为什么退款/订单要订单号约束（深挖题高频）**：
> "没有约束的话，'7 天无理由能退吗''退款多久到账'这种**政策咨询**会误走退款流程（没有订单号无法操作，还会答错）。所以规则是：提了订单号或明确指向自己的订单才调业务接口，否则当知识问答处理。"

**订单号提取**：正则 `SO\d{10,}|#?\d{6,}`；`_extract_order_id_with_history` 支持从最近 4 条历史里找回（"那退款呢"指代场景）。

**多轮上下文**：`answer_message` 把最近 4 轮拼成 context（角色标记"客户/客服"），RAG 检索时把"【最近对话】+【当前问题】"一起检索 → 支持"那它防水吗"；但**意图分类只看当前消息**，避免历史词污染路由（这个设计点要会讲）。

**情绪识别**：`EMOTION_RULES` 三档（angry/anxious/disappointed），关键词表约 40+ 词；`_detect_emotion` 子串匹配，未命中=neutral。加敏原则：只收明确带情绪的表达，避免误判普通问询。

**兜底话术库 `FALLBACK_REPLIES`**：4 档（angry/anxious/disappointed/neutral）× 每档 5 条真实电商话术，随机取一条；转人工话术统一带"上下文交接感"（"人工客服会带着我们刚才的对话记录继续处理，您无需重复描述"）。**知识库没命中时按客户心情匹配语气**——这就是用户要的"根据对方不同心情匹配不同语气"。

**情绪拦截**：angry + 无明确业务意图（无订单号、无产品词）→ 直接转人工 + P0 工单（不走 RAG 硬答）。

**属性校验兜底 `_attr_mismatch_fix`（本项目的亮点，面试重点讲）**：
> "多轮指代'那它防水吗'时，RAG 可能命中 FAQ 里的'配对教程'而没答到防水。所以我在路由层加了属性校验：检测当前/历史提到产品 + 问题含属性词（防水/续航/降噪等 20 个），再看 RAG top1 段落是否覆盖该属性，没覆盖就用产品手册的确定性 chunk 兜底。**保证答到点子上。**"

**最终兜底链**：
- RAG 未命中 → `_fallback_reply`（按情绪）+ 自动建工单转人工
- RAG 命中但问题属售后类（分类不是"售前咨询/其他咨询"）→ 也自动建工单让人工跟进

**双路切换 `should_use_openai_tool_router`**：`AGENT_ROUTER=rules` 强制规则；否则配了 key 就走 LLM tool calling。

### 模块 5：智能工单 `ticket.py`

**7 类分类**（CATEGORY_RULES）：物流异常 / 少发漏发错发 / 退款退货 / 产品质量故障 / 订单变更 / 支付与发票 / 售前咨询。
**计分类别**：统计每类命中关键词数，**命中最多**的类别胜出（不是第一个命中的）。
**优先级**：
- P0-紧急：投诉/起诉/12315/消协/媒体/曝光/经理/主管/人工/马上退/315
- P1-高：没收到/丢件/坏了/故障/质量/漏发少发/充不进/失灵…；或类别属"退款退货/产品质量/物流问题"
- P2-常规：其他
**处理建议**：每类一条标准动作（如物流异常→"调订单/物流接口拉最新轨迹，要求客户提供面单/包裹照片，24h 无更新推仓储快递核查工单"）。
**产出**：`TK{序号}` + category + priority + suggested_action + summary + created_at + status=open。

**面试点**："工单是谁建的？"→ 路由层 3 处：升级人工时（P0）、RAG 未命中时、RAG 命中但属售后履约时。

### 模块 6：LLM 抽象层 `llm_provider.py`（国产化亮点）

**6 个 provider**：`local`（默认）/ `openai` / `deepseek` / `qwen` / `zhipu` / `kimi`。
**核心思想**：所有国产厂商都提供 **OpenAI 兼容接口**，所以客户端统一用 openai SDK，只换 `base_url / api_key / model` 三个参数。
**表格要背**：

| provider | base_url | chat_model | embedding |
|---|---|---|---|
| deepseek | api.deepseek.com/v1 | deepseek-chat | 无 |
| qwen | dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus | text-embedding-v3 |
| zhipu | open.bigmodel.cn/api/paas/v4 | glm-4-flash | embedding-3 |
| kimi | api.moonshot.cn/v1 | moonshot-v1-8k | 无 |

**设计细节**：
- `get_config()` 每次读环境变量（懒加载），`available = bool(api_key)`
- 未配 key → available=False → 自动回退本地模式（`/health` 里 `describe()` 会显示"未配置 API_KEY，已回退本地模式"）
- DeepSeek/Kimi 无 embedding → embedding_model=None（不影响 chat，影响向量检索）
- 环境变量还能覆盖模型名（CHAT_MODEL/EMBEDDING_MODEL）

**面试怎么讲**：
> "我用一个 dataclass 统一六家模型配置，切换只改一个环境变量 MODEL_PROVIDER。因为国产模型都兼容 OpenAI 协议，抽象成本很低。这解决了国内部署的模型依赖问题。"

### 模块 7：LLM tool calling 路径 `openai_tool_router.py`

- 3 个工具：`get_listing_count`（原项目保留）/ `get_order` / `escalate_to_human`
- **System Prompt 设计**：操作类事实（订单状态、物流、升级）用工具；FAQ/政策/产品推荐**不调工具**，留给 RAG（"leave those without a tool call so the app can route them to RAG"）
- `tool_choice=auto` + `temperature=0`（确定性强）
- LLM 不调工具 → 走 RAG；调了 → 执行工具 → 把结果交给 LLM 格式化（"Do not invent details beyond the tool result"）
- 未配 key → 直接回退 `answer_message_rule_based`

**面试点**："为什么双路？"→ 规则路零成本兜底（离线、快、可控），LLM 路更懂自然语言；默认本地模式保证作品集随时可演示。

### 模块 8：API 层 `api.py`

**端点**（背熟）：
- `GET /health` → status + llm 描述
- `POST /chat` {message, platform, session_id} → intent/answer/sources/ticket/session_id
- `GET /products`、`GET /orders/{id}`、`POST /orders/{id}/refund`、`POST /tickets`
- `POST /feishu/webhook`、`POST /knowledge/refresh`
- `GET /showcase` + 静态挂载 `/`（前端目录）

**细节**：
- Pydantic 校验：message min_length=1 + 自定义 validator 去空白（空消息 422）
- **会话管理**：内存 `defaultdict(lambda: deque(maxlen=8))` 多轮存储；`_MAX_SESSIONS=200` + LRU 淘汰（`_touch_session` 刷新活跃序）**防内存泄漏**——面试会问"多轮会话存哪？生产怎么办？"（答：demo 用内存，生产换 Redis/PostgreSQL）
- CORS 全开（作品集演示）
- `/showcase` 显式路由：新版 Starlette StaticFiles html 模式不再自动补 .html——这是真实踩过的坑，能讲

### 模块 9：飞书对接 `feishu_bridge.py`

- 事件订阅 `im.message.receive_v1` → 解析 chat_id/message_id/content(text) → 交给 `answer_message`
- **url_verification**：配置回调时飞书发 challenge，原样回显（必考）
- **安全校验**：配置 FEISHU_VERIFY_TOKEN 后校验事件体 token 字段
- **双模式**：mock（默认，直接把 reply 返回给飞书，本地调试用）/ api（配 FEISHU_APP_ID+SECRET，拿 tenant_access_token → POST 主动发消息）
- 独立会话池：以 chat_id 为 session，同样 maxlen=8 多轮

### 模块 10：前端 `frontend/`

- `index.html` + `app.js`：工作台（快捷场景 6 问、演示订单号、运行模式显示、对话区 + 引用卡片 + 工单展示、互通按钮"查看项目介绍"）
- `showcase.html`：作品集展示页（导航/数据指标/架构图/12 能力卡/9 业务场景表/在线体验/一键启动命令）——**自包含单文件**，已发布豆包链接
- `sdk-demo.html` + `novatech-chat.js`：模拟第三方网站，一行 `<script>` 嵌入客服浮窗，自动带 session_id 多轮
- 技术：原生 JS，无构建工具（fetch /chat 接口）

### 模块 11：部署与国内优化

- **Dockerfile**：python:3.11-slim；阿里云 pip 镜像（`pip config set global.index-url`）；先拷 requirements 再拷代码（**利用层缓存**）；ENV MODEL_PROVIDER=local
- **docker-compose.yml**：单服务 8010，环境变量透传（MODEL_PROVIDER + 各厂商 key）
- **README_CN**：国内部署三步（clone → pip 阿里镜像 → uvicorn 8010）；国产模型切换配置
- **豆包在线展示**：展示页已发布静态托管（公网可访问），功能页需本地/服务器部署

### 模块 12：测试 `tests/`

**regression.py 16 用例覆盖**：
- 售前：参数/对比/使用方法
- 售后：订单物流/退款/假订单号（"没有找到"）
- 多轮：产品指代（IPX5）/订单指代（REFUND 且带订单号）
- 情绪：愤怒转人工 + P0 工单；知识库外转人工（"推荐生日礼物"）；噪声转人工（"老板姓什么"）；英文
- 引用：sources 非空
- 飞书：challenge 回显 / 多轮指代
- 边界：空消息 422

**user_test.py**：30+ 用户视角用例（全场景体检）。

**面试点**："你怎么保证不乱回复？"→ 词表约束 + 订单号校验 + BM25 阈值 + 属性校验 + 转人工兜底 + 回归测试。

---

## 三、面试 Q&A（背熟 + 用自己的话讲）

### 3.1 高频 20 题

**Q1. 介绍一下这个项目（30 秒 elevator pitch）**
> "这是一个企业级 AI 客服平台作品集。它模拟星澜数码这家消费电子公司的客服系统，覆盖售前咨询、售后支持、智能工单三个场景。核心是 RAG 加 Agent：RAG 负责基于产品手册、FAQ、售后政策的知识检索；Agent 负责意图路由，识别客户是要问产品、查物流还是退款；订单和退款走状态机，保证流程合法；问题搞不定或客户情绪激烈时自动转人工并生成带分类、优先级、处理建议的工单。默认零 API Key 能跑，配一个环境变量可以切换 DeepSeek、通义、智谱、Kimi 国产模型。"

**Q2. 项目背景 / 为什么做这个？**
> "我在学 RAG 和 Agent 工程化，看到一个开源的 ecommerce RAG Agent 只有很基础的问答能力，就想着把它改造成一个有完整业务流程、能真正代表企业客服场景的作品集：加了模拟商品/订单库、售后状态机、智能工单、多轮上下文、飞书渠道、国产模型适配、SDK 浮窗。整个过程是迭代式的，每次加功能都基于实际跑出来的问题。"

**Q3. 整体架构怎么设计的？**
> "分层：FastAPI 提供接口；agent_router 是 Agent 编排核心，做意图分类、情绪识别、多轮上下文、路由到 RAG 或业务接口；rag_service 做检索（本地 BM25 默认、LlamaIndex 向量可选）；commerce_api 是模拟业务数据层（商品/订单/物流/退款状态机）；ticket 生成工单；llm_provider 做模型抽象。前端有工作台、展示页、SDK 浮窗三个入口，飞书通过 webhook 接入。"

**Q4. RAG 怎么实现的？**
> "知识库是 products.md、40 条 FAQ、售后政策、产品手册。检索有两条路径：默认本地 BM25，中文按 bigram 切分，按 markdown 标题切 chunk，top3 召回、分数低于 25 视为未命中；配置 API Key 后自动切到 LlamaIndex 向量检索，chunk 400 字、重叠 40，embedding 用对应厂商的模型。命中返回 top1 段落做答案，同时带 sources 引用，前端可展示溯源。"

**Q5. 为什么用 BM25 不用向量？**
> "两个原因：一是作品集要零依赖、离线可跑，任何面试环境都能演示；二是 FAQ 和政策类文本关键词重合度高，BM25 效果足够且完全可解释、可溯源。生产路径保留了 LlamaIndex，配 key 就切，等于两种都支持。"

**Q6. 中文 bigram 分词是怎么做的？**
> "英文和数字按正则按词切；连续中文字符串按相邻两个字符切，比如'防水吗'切成'防水'、'水吗'。选 bigram 因为中文没有天然空格分词，bigram 不需要词典、对同义改写有一定容错，实现成本最低。检索分数不理想的话可以换 jieba 或字粒度，这是可扩展点。"

**Q7. 检索不到 / 答不上来怎么办？（防乱回复核心）**
> "三层兜底：第一，BM25 分数低于阈值判未命中；第二，检测客户情绪（愤怒/着急/失望），按情绪从话术库里选一句真实电商话术承接，统一转人工并说明'人工客服会带着对话记录继续处理'；第三，同时自动创建一张工单，带分类、优先级、处理建议，让人工后续接手。这样知识库外的问题不会硬答。"

**Q8. 意图路由怎么设计的？**
> "5 类意图：升级人工、退款、订单物流、售前、RAG 兜底。判定顺序很重要：先查敏感词（投诉、315、曝光这类）直接升级；退款类必须带订单号或明确指向自己的订单才走退款接口，否则当政策咨询走 RAG；订单物流同理；售前词命中走 PRE_SALE；其余走 RAG。这个约束是为了防止'7 天无理由能退吗'这种政策问题误触发退款流程。"

**Q9. 多轮对话怎么做的？**
> "三层：一是后端按 session_id 用 deque(maxlen=8) 存最近对话，接口天然支持多轮；二是 RAG 检索时把最近 4 轮拼成上下文，支持'那它防水吗'这种指代；三是订单号可以从历史回退——上一轮说了订单号，这轮说'那退款呢'，能自动带出。关键设计是意图分类只看当前消息，避免历史词污染路由判断。"

**Q10. 情绪识别怎么做的？**
> "关键词子串匹配：愤怒、着急、失望三档词表，每档几十个词，命中即该情绪，否则中立。加敏原则是只收明确带情绪的表达，避免把普通问询误判。知识库未命中时按情绪档位从话术库选回复——愤怒的先安抚再转人工，着急的先给加急承诺再转人工，措辞完全不同。"

**Q11. 智能工单怎么生成？**
> "三类信息：分类用关键词计数，7 个类别谁命中最多归谁；优先级分 P0/P1/P2，投诉、315、曝光这类 P0，丢件、故障、质量 P1，其余 P2；处理建议每类给一条标准动作。路由层在三个时机建工单：升级人工时建 P0、RAG 未命中时建、RAG 命中但属于售后履约问题时也建，保证人工有记录可跟。"

**Q12. 国产模型怎么切换的？**
> "一个 dataclass 统一 6 家配置（local/openai/deepseek/qwen/zhipu/kimi），因为国产模型都兼容 OpenAI 协议，所以客户端统一用 openai SDK，只换 base_url、api_key、model 三个参数。切模型只改 MODEL_PROVIDER 一个环境变量，没配 key 自动回退本地模式，/health 接口能看到当前用的什么模型。"

**Q13. LLM tool calling 和规则路由什么关系？**
> "双路并存：默认走规则路由，零依赖、快、可控；配置 API Key 后自动启用 Function Calling 路径——LLM 判断需要查订单、升级人工时调对应工具，不调工具的问题留给 RAG。System Prompt 明确告诉模型：FAQ、政策、产品推荐不要调工具。两路共享同一套业务接口和工单逻辑。"

**Q14. 退款流程的状态机是怎么保证正确的？**
> "订单状态机：paid→shipped→in_transit→delivered→refund_applied；退款子状态：none→reviewing→approved→rejected→refunded。request_refund 会校验：订单必须存在、状态必须是已发货/在途/已签收/已申请退款、不能已有审核中的申请、不能已退款。每个非法流转都返回明确错误，工单也会记录。"

**Q15. 会话内存管理？**
> "deque(maxlen=8) 限制单会话长度，防止无限增长；全局还有 _MAX_SESSIONS=200 的 LRU 淘汰——每次请求刷新会话活跃顺序，超过上限淘汰最久不活跃的。作品集用内存态，生产我会换 Redis 存会话，带过期时间。"

**Q16. 飞书怎么对接的？**
> "飞书开放平台配事件订阅，回调 POST /feishu/webhook。解析 im.message.receive_v1 事件拿 chat_id 和文本，交给同一个 Agent 处理，回复有两种模式：mock 模式直接返回给飞书（本地调试）；api 模式用 app_id/secret 换 tenant_access_token 主动发消息。还实现了 url_verification 的 challenge 回显和可选的 verify_token 校验。"

**Q17. 测试怎么做的？**
> "两个回归脚本，共 40+ 用例。覆盖：售前参数/对比/使用方法；售后查物流/退款/假订单号；多轮指代（产品属性和订单）；情绪愤怒转人工必须带 P0 工单；知识库外问题转人工；噪声问题（老板姓什么）不硬答；英文输入；引用 sources 非空；飞书 challenge 回显和多轮；空消息返回 422。全部通过才算一轮迭代完成。"

**Q18. 部署方案？国内优化做了什么？**
> "三种：本地跑（uvicorn 8010，30 秒）、Docker（docker-compose 一条命令）、国内云服务器（README_CN 有完整步骤）。国内优化：pip 依赖走阿里云镜像（Dockerfile 里也配了，构建加速）、模型全用国产 OpenAI 兼容接口（DeepSeek/通义/智谱/Kimi 都是国内直连）、前端零外部 CDN 自包含、展示页发布到豆包静态托管（国内直接打开）。"

**Q19. 项目里踩过什么坑？（深挖加分）**
> "至少三个真实的：一是新版 Starlette 的 StaticFiles html 模式不再自动补 .html，/showcase 链接 404，加了显式路由解决；二是 Windows 下 PowerShell 管道会把 UTF-8 重编码成 cp936 导致乱码，验证文件内容改用 Python 直接读写；三是多轮指代回归测试偶发失败——RAG 结果在 products 和 FAQ 之间摇摆，最后加了属性校验兜底从根上解决。"

**Q20. 如果继续做，下一步改进什么？**
> "三个方向：一是把内存态数据换真实数据库（PostgreSQL）和 Redis 会话，支持并发与持久化；二是 RAG 升级——换 jieba 分词、加 reranker、embedding 语义检索做正式上线；三是补管理后台——工单看板、人工接管、数据看板，再加多轮对话的主动学习（客户反馈回流知识库）。"

### 3.2 深挖题（追问预备）

**"那它防水吗"为什么不会答错？** → 属性校验兜底（模块 4）：检测到历史产品 + 属性词，RAG top1 没覆盖该属性就用产品手册确定性 chunk 覆盖。

**"7天无理由"为什么走 RAG 不走退款接口？** → 无订单号约束，政策咨询 vs 实际操作分流。

**为什么意图分类只看当前消息，RAG 才拼历史？** → 路由要"准"，检索要"全"：历史词污染路由会把普通咨询误判成退款；但检索需要上下文才能理解指代。

**BM25 阈值 25 怎么来的？** → 实测统计：好匹配 55+，噪声 7-16，取 25 分隔。这是数据驱动的经验值，面试可讲"我拿一批真实问题标注后扫出来的"。

**为什么 FALLBACK_REPLIES 每档 5 条随机？** → 避免同一客户同一问题机械重复同一句话（客服红线），随机 + 上下交接感。

**DeepSeek 没有 embedding，向量检索怎么办？** → 设计上 embedding_model 可为 None：chat 用 DeepSeek，RAG 向量检索需要 embedding 的话切通义/智谱（两者都有 embedding），或退 BM25。

**会话 LRU 为什么用 deque 不用 OrderedDict？** → deque 有 popleft/pop 和 remove，配合 _session_order 记录活跃序，实现最简；生产直接上 Redis 不存在这问题（可如实说）。

**CORS 全开会不会不安全？** → 作品集演示需要；生产会收敛 allow_origins 白名单 + 加鉴权（会主动提这是演示取舍）。

### 3.3 STAR 行为题（"讲一个你做过的项目"）

```
S（情境）：我在准备 AI 工程化作品集，选中一个开源电商 RAG Agent 作为基底，它只有基础的问答能力。
T（任务）：把它改造成企业级客服系统——要有真实业务流程、不乱回复、能展示、能部署。
A（行动，讲 I 不要说 We）：
  - 我做了业务建模：5 款产品、4 笔订单、40 条 FAQ、7 节售后政策，用 dataclass 模拟商品/订单/状态机；
  - 我设计了双路意图路由 + 情绪话术兜底 + 智能工单，重点解决"知识库没命中怎么办"；
  - 我发现多轮指代会答错，自己加了属性校验兜底，并补齐 40+ 回归用例；
  - 我做了国产化：LLM 抽象层支持 4 家国产模型，Docker 走阿里云镜像，展示页发布到国内可访问的静态托管。
R（结果）：项目 30 秒可启动、40+ 用例全绿、豆包在线展示页公网可访问、GitHub 作品集可 clone 即跑；我也把"规则+LLM 双路""防乱回复"这套方法讲成了自己的工程判断。
L（反思）：最大的收获是"AI 应用工程化的难点不在模型，而在边界与流程"——意图边界、状态机、兜底、可测试性才是让它从 demo 变成产品的关键。
```

---

## 四、练习题（学完自测）

### 4.1 客观题（每题 5 秒，答案在文末）

1. 本项目默认（不配任何 API Key）的 RAG 检索方式是什么？
   A. LlamaIndex 向量检索　B. 本地 BM25　C. 调用 OpenAI　D. Elasticsearch

2. 中文 BM25 分词用的是哪种粒度？
   A. 单字　B. bigram 二元组　C. jieba 分词　D. 全词匹配

3. 下面哪种说法会触发 REFUND 意图？（可多选）
   A. "7 天无理由能退吗"　B. "帮我退订单 SO20260930004"　C. "我的订单想退货"　D. "退款多久到账"

4. 智能工单 P0 优先级会由哪些词触发？
   A. 投诉/315/曝光　B. 没收到/丢件　C. 发票　D. 价格

5. BM25 检索 top1 分数低于多少判定"未命中"转人工？
   A. 10　B. 25　C. 50　D. 100

6. 多轮会话在内存中用什么结构存储？
   A. list 无上限　B. deque(maxlen=8)　C. dict 无上限　D. 文件

7. 国产模型切换只改哪个环境变量？
   A. OPENAI_API_KEY　B. MODEL_PROVIDER　C. FEISHU_APP_ID　D. AGENT_ROUTER

8. 飞书 url_verification 事件需要返回什么字段？
   A. token　B. challenge　C. reply　D. code

9. 订单 SO20260930004 的退款状态是什么？
   A. none　B. reviewing　C. approved　D. refunded

10. "那它防水吗"能答对，主要靠哪两个机制？（可多选）
    A. 多轮上下文拼历史　B. 属性校验兜底　C. 订单号提取　D. LLM tool calling

11. 空消息（全空格）提交 /chat 会返回什么？
    A. 200 正常回复　B. 422 校验拒绝　C. 404　D. 500

12. DeepSeek 和 Kimi 的 embedding_model 配置是什么？
    A. text-embedding-v3　B. embedding-3　C. None　D. gpt-4o

13. 工单分类采用什么策略？
    A. 第一个命中词　B. 命中关键词计数最多　C. LLM 判断　D. 随机

14. AGENT_ROUTER=rules 的作用是什么？
    A. 启用 LLM tool calling　B. 强制走本地规则路由　C. 关闭 RAG　D. 启用飞书

15. 项目用哪种方式托管前端页面？
    A. 独立前端服务器　B. FastAPI 静态挂载　C. CDN　D. S3

### 4.2 简答题（每题 3-5 分钟，口述作答）

1. 画一遍"客户问'我的订单 SO20260912001 物流到哪了'"的完整处理链路（从 HTTP 到回复）。
2. 讲清楚"7 天无理由能退吗"为什么不会误走退款接口。
3. 如果客户说"你们什么垃圾玩意，再也不买了！"，系统会怎么处理？返回什么结构？
4. 解释 BM25 的 k1 和 b 参数大致作用。
5. 讲一下你如何在三个时机自动创建工单。
6. 国产模型抽象层为什么能用同一个 OpenAI 客户端？举两个厂商的 base_url。
7. 多轮会话 LRU 淘汰是怎么实现的？生产环境你会怎么做？
8. 你如何验证"属性校验兜底"真的有效？（讲测试方法）

### 4.3 场景设计题（开放，说思路即可）

1. 客户问"Air100 和 Studio200 哪个适合通勤用"，你希望系统返回什么？（讲 RAG 命中、商品卡片、推荐逻辑）
2. 客户在飞书里连续问"Air100 怎么样"→"那它防水吗"→"那退款呢"，设计你如何保证三连答对。
3. 如果知识库新增 10 条 FAQ，你要不要改代码？为什么？
4. 产品经理要求"退款金额超过 500 元必须人工审核"，你在哪一层加？怎么加？
5. 上线后出现"客户催发货但订单号是别人的"，你怎么防？（提示：user_id 维度校验，讲思路即可）

### 4.4 参考答案

**客观题**：1-B　2-B　3-BC（A/D 无订单号约束走 RAG 政策咨询）　4-A　5-B　6-B　7-B　8-B　9-B　10-AB　11-B　12-C　13-B　14-B　15-B

**简答要点**：
1. POST /chat → Pydantic 校验 → 会话 LRU 取历史 → answer_message 拼 context → 规则路由 classify_intent（含订单号 → ORDER_STATUS）→ get_order 返回订单+轨迹 → _format_order 格式化 → 存会话 → 返回 intent/answer/tool_result/sources。
2. classify_intent 中退款词命中后还要校验 `has_order_id or own_order_hint`，"7 天无理由"无订单号且非"我的订单" → 走 RAG 当政策回答。
3. "垃圾/再也不买" 命中 angry + ESCALATION_TERMS？→ "再也不买"不在升级词，但 EMOTION_RULES angry 命中；无订单号、无产品词 → 情绪拦截：intent=ESCALATE + FALLBACK_REPLIES[angry] 随机话术 + escalate_to_human + P0 工单。
4. k1 控制词频饱和（词频高到一定程度边际收益递减），b 控制文档长度归一化（0-1，越大越长惩罚越重）。本项目 k1=1.5、b=0.75 经典默认。
5. 三处：升级人工（P0）、RAG 未命中（自动转人工+工单）、RAG 命中但分类属售后履约（人工跟进）。
6. 国产模型全兼容 OpenAI 协议，统一 openai SDK 换 base_url/api_key/model。deepseek → api.deepseek.com/v1；qwen → dashscope.aliyuncs.com/compatible-mode/v1。
7. _session_order deque 记录活跃序，超 200 淘汰最久未活跃；生产用 Redis（EXPIRE 过期 + 容量上限）。
8. 回归用例：先问"Air100 怎么样"，再问"那它防水吗"，断言回复含 IPX5；连跑 3 次验证稳定性（曾因此修复回归偶发失败）。

**场景题思路**（要点即可）：
1. PRE_SALE → RAG 命中产品对比段落 → search_products 附带商品卡片（名称/价格/库存）→ 答对比要点+给推荐倾向。
2. 会话按 session_id 存储；"那它防水吗"靠 context 找回产品 + 属性校验兜底答 IPX5；"那退款呢"靠历史订单号回退走 REFUND（需上一轮带过订单号，否则引导提供）。
3. 不用改代码——RAG 语料从 data/ 读取，新增 md 文件即被索引；只需 /knowledge/refresh 清缓存（若开着服务）。
4. 在 commerce_api.request_refund 加金额上限校验（>500 返回"需人工审核"），或 ticket 优先级提升为 P0——业务规则收口在业务层。
5. 订单号 + user_id 绑定校验：当前会话已知用户身份（登录态）时核对订单归属；作品集 demo 无登录态，可说明生产方案。

---

