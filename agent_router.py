"""意图路由 + Agent 编排。

保留原项目的双路结构（规则兜底 / OpenAI tool calling），扩充：
- 售前咨询（RAG + 商品库）
- 售后支持（订单状态 / 物流 / 退款）
- 智能工单（自动分类 / 优先级 / 处理建议）
"""
import os
import re

from commerce_api import (
    escalate_to_human,
    get_order,
    list_products,
    request_refund,
    search_products,
)
from ticket import create_ticket


# 高敏感 / 升级人工
ESCALATION_TERMS = (
    "投诉", "起诉", "12315", "消协", "曝光", "媒体",
    "经理", "主管", "人工客服", "转人工",
)


# ---------- 情绪识别 + 兜底话术 ----------
# 知识库未命中时，根据客户语气匹配不同承接话术
EMOTION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("angry", (
        "气死", "什么垃圾", "什么玩意", "破玩意", "骗子", "差劲", "太差",
        "再也不买", "什么态度", "服务差", "差评", "曝光", "举报",
        "退一赔三", "赔我", "什么破", "火大", "受不了",
    )),
    ("anxious", (
        "快点", "尽快", "加急", "急死", "着急", "赶时间", "马上",
        "来不及", "怎么办", "救命", "今天必须", "今天要用", "航班",
        "出差", "急用", "怎么还没",
    )),
    ("disappointed", (
        "失望", "不值", "浪费钱", "不好用", "难用", "垃圾", "后悔",
        "根本不是", "骗人", "虚假宣传", "差劲", "再也",
    )),
]

FALLBACK_REPLIES: dict[str, list[str]] = {
    "angry": [
        "非常抱歉让您这么生气，我已经第一时间为您升级到客服主管加急处理，10 分钟内会有专人电话联系您，请稍等。",
        "真的很抱歉给您带来这么糟糕的体验，我已为您转接人工客服主管并标记最高优先级，会第一时间回电处理。",
        "对不起让您受委屈了，我立刻为您接通人工客服，主管正在排队接入，请您稍等片刻。",
        "请您消消气，您的问题我们都会尽力帮您解决。非常抱歉这次没有给您带来愉快的体验，我们非常重视您的反馈，一定会改善问题。",
        "宝子消消气！您反馈的问题我一字不落记下了，真的超抱歉让您烦心，我现在立刻升级处理，必须给您一个满意的答复！",
    ],
    "anxious": [
        "别着急，我马上为您转接人工客服并标记加急，会优先处理您的问题，请稍等。",
        "理解您赶时间的心情，已为您登记加急，人工客服正在快速接入，请稍等。",
        "收到，已为您跳过排队直接转接人工，请稍等片刻。",
        "非常理解您着急使用的心情，这边马上为您加急备注、优先安排，您可以放心等待反馈。",
        "亲，请别着急，非常理解您的心情，我们一定会竭尽全力为您解决，已为您加急处理。",
    ],
    "disappointed": [
        "抱歉没能一次帮您解决，我已为您转接人工客服，会有专人跟进到底。",
        "抱歉让您失望了，已为您登记并转接人工，会给您一个明确的处理方案。",
        "理解您的感受，我马上为您转人工客服跟进，请稍等。",
        "发生这样的事给您带来不便了，非常抱歉。我们一定会查证清楚，给您一个满意的答复。",
        "您的反馈我们都记下了，我们会认真核实并给出负责任的处理结果，已转人工跟进。",
    ],
    "neutral": [
        "已为您申请人工客服服务，请稍等。",
        "这个问题我帮您转接人工客服处理，请稍等片刻。",
        "好的，已为您登记并转接人工客服，稍后会有专人回复您。",
        "收到，我马上为您接通人工客服，请稍等。",
    ],
}


def _detect_emotion(text: str) -> str:
    for emotion, keywords in EMOTION_RULES:
        if any(k in text for k in keywords):
            return emotion
    return "neutral"


def _fallback_reply(message: str) -> str:
    emotion = _detect_emotion(message)
    import random
    return random.choice(FALLBACK_REPLIES[emotion])

# 售后意图关键词
ORDER_TERMS = (
    "订单", "我的订单", "查到", "发货", "物流", "快递", "运单", "到哪",
    "在哪", "送到", "签收", "没收到", "没到货",
    "改地址", "修改地址", "换地址", "取消订单", "我要取消",
    "催发货", "怎么还不发", "什么时候发",
)
REFUND_TERMS = (
    "退款", "退货", "退钱", "不想要了", "拍错", "多拍", "7天无理由", "七天无理由",
    "换货", "退订单",
)
PRODUCT_TERMS = (
    "多少钱", "价格", "参数", "区别", "推荐", "对比", "哪个好", "续航",
    "防水", "兼容", "配件", "送什么", "怎么样", "如何选", "对比一下",
)

# 订单号正则：SO20260912001 这种格式，或纯数字
ORDER_ID_RE = re.compile(r"(SO\d{10,}|#?\d{6,})", re.IGNORECASE)


def classify_intent(message: str, history: list[dict] | None = None) -> str:
    text = message.lower()

    if any(term in text for term in ESCALATION_TERMS):
        return "ESCALATE"

    # 退款类问题：只有当消息里带订单号（或历史对话中有），或明确说"我的订单/我买的那个"时，
    # 才真的走退款流程；否则像"7天无理由""退款多久到账"是在问售后政策，走 RAG。
    has_order_id = bool(_extract_order_id_with_history(message, history))
    own_order_hint = any(term in text for term in (
        "我的订单", "我的包裹", "我的快递", "我买的", "我拍的", "刚买的", "刚收到",
    ))
    if any(term in text for term in REFUND_TERMS):
        if has_order_id or own_order_hint:
            return "REFUND"
        return "RAG"

    # 订单/物流类：必须带订单号或指向自己的订单
    if has_order_id or own_order_hint:
        if any(term in text for term in ORDER_TERMS):
            return "ORDER_STATUS"

    if any(term in text for term in PRODUCT_TERMS):
        return "PRE_SALE"

    return "RAG"


def extract_order_id(message: str) -> str:
    m = ORDER_ID_RE.search(message or "")
    if not m:
        return ""
    raw = m.group(1).lstrip("#").upper()
    return raw


def _format_order(order: dict) -> str:
    item_strs = [f"{it['name']} x{it['qty']}" for it in order["items"]]
    lines = [
        f"订单 {order['order_id']} 当前状态：{order['status']}。",
        f"商品：{'；'.join(item_strs)}",
        f"合计：¥{order['total']:.2f}",
    ]
    lg = order.get("logistics") or {}
    if lg.get("carrier") and lg.get("carrier") != "未分配":
        lines.append(f"承运：{lg['carrier']}，运单号 {lg['tracking_no']}")
        events = lg.get("events") or []
        if events:
            lines.append("最新物流轨迹：")
            for ev in events[-3:]:
                lines.append(f"  · [{ev['time']}] {ev['desc']}")
    rf = order.get("refund") or {}
    if rf.get("status") and rf["status"] != "none":
        lines.append(f"退款状态：{rf['status']}（{rf.get('reason') or ''}，¥{rf.get('amount') or 0}）")
    return "\n".join(lines)


def _answer_pre_sale(message: str, context: str | None = None) -> dict:
    """售前：先看是否命中具体商品，命中就带商品卡片；否则 RAG。
    检索顺序：当前消息优先（避免历史词污染）；当前消息未命中且有多轮上下文时，
    再用带历史的 context 兜底（支持'那它呢'这类指代）。"""
    hits = search_products(message)
    from rag_service import _detect_products, _product_chunk, answer_with_rag
    rag = answer_with_rag(message)
    if not rag.get("matched", True) and context and context != message:
        # 兜底 1：从历史中提取产品名注入当前问题，支持"那它防水吗"这类指代
        products_in_context = _detect_products(context)
        if products_in_context:
            rag2 = answer_with_rag(message + " " + " ".join(products_in_context))
            if rag2.get("matched", True):
                rag = rag2
        # 兜底 2：仍未命中再尝试完整上下文
        if not rag.get("matched", True):
            rag_context = answer_with_rag(context)
            if rag_context.get("matched", True):
                rag = rag_context
    if not rag.get("matched", True):
        # 兜底 3：查询/历史提到具体产品 → 直接返回该产品手册 chunk（确定性兜底）
        products = _detect_products(message) or (
            _detect_products(context) if context else set()
        )
        if products:
            pc = _product_chunk(next(iter(products)))
            if pc:
                rag = {
                    "answer": "根据知识库（products.md）：\n\n" + re.sub(r"^#+\s*", "", pc["text"]).strip(),
                    "sources": [pc],
                    "matched": True,
                    "tool_result": None,
                }

    if hits:
        card_lines = ["在售相关商品："]
        for h in hits[:5]:
            card_lines.append(f"  · {h['name']}（{h['sku']}）¥{h['price']:.0f}，库存 {h['stock']}")
        rag["answer"] = rag["answer"] + "\n\n" + "\n".join(card_lines)
        rag["tool_result"] = {"products": hits}
    return rag


def _extract_order_id_with_history(message: str, history: list[dict] | None) -> str:
    """订单号提取：当前消息优先，没有则从最近历史里找（支持'那退款呢'这类指代）。"""
    oid = extract_order_id(message)
    if oid:
        return oid
    if history:
        for h in reversed(history[-4:]):
            if h.get("role") == "user":
                oid = extract_order_id(h.get("content", ""))
                if oid:
                    return oid
    return ""


def answer_message_rule_based(
    message: str,
    platform: str = "novatech",
    history: list[dict] | None = None,
    context: str | None = None,
) -> dict:
    # 意图分类只基于当前消息（订单号可从历史回退），避免历史里的"退款/订单号"污染判断
    intent = classify_intent(message, history)
    ticket = None

    # 情绪拦截：愤怒/极度不满且没有明确业务意图（无订单号、无产品词）→ 直接转人工 + P0 工单
    emotion = _detect_emotion(message)
    if (
        emotion == "angry"
        and intent in ("RAG", "PRE_SALE")
        and not extract_order_id(message)
    ):
        product_hint = any(p in message.lower() for p in (
            "air100", "studio200", "watch30", "key87", "gaan65",
            "充电", "耳机", "手表", "键盘", "充电器", "降噪",
        ))
        if not product_hint:
            ticket = create_ticket(message)
            ticket["priority"] = "P0-紧急"
            return {
                "intent": "ESCALATE",
                "answer": _fallback_reply(message),
                "tool_result": escalate_to_human(reason=message[:60], platform=platform),
                "sources": [],
                "ticket": ticket,
            }

    # 升级人工 → 同时生成 P0 工单
    if intent == "ESCALATE":
        result = escalate_to_human(reason=message[:60], platform=platform)
        ticket = create_ticket(message)
        ticket["priority"] = "P0-紧急"
        return {
            "intent": "ESCALATE",
            "answer": (
                "非常抱歉给您带来不好的体验。我已为您转接人工客服主管，"
                "并同步生成紧急工单。工作时间 10 分钟内将有专人电话回访；"
                "非工作时间将在次日 10 点前联系您。"
            ),
            "tool_result": result,
            "sources": [],
            "ticket": ticket,
        }

    # 退款：先抽订单号（支持从历史回退）
    if intent == "REFUND":
        order_id = _extract_order_id_with_history(message, history)
        if not order_id:
            ticket = create_ticket(message)
            return {
                "intent": "REFUND",
                "answer": (
                    "您可以在订单详情页直接申请退款，或告诉我订单号（形如 SO2026xxxxxx），"
                    "我帮您查一下是否在 7 天无理由窗口内。退款原路退回，仓库签收后 48 小时内到账。"
                ),
                "tool_result": None,
                "sources": [],
                "ticket": ticket,
            }
        refund = request_refund(order_id, reason=message[:80])
        if not refund.get("ok"):
            return {
                "intent": "REFUND",
                "answer": f"退款申请未受理：{refund.get('error')}。",
                "tool_result": refund,
                "sources": [],
                "ticket": create_ticket(message, order_id=order_id),
            }
        return {
            "intent": "REFUND",
            "answer": (
                f"已为订单 {order_id} 提交退款申请，金额 ¥{refund['amount']:.2f}。\n"
                f"{refund['estimated_next_step']}"
            ),
            "tool_result": refund,
            "sources": [],
            "ticket": create_ticket(message, order_id=order_id),
        }

    # 订单 / 物流
    if intent == "ORDER_STATUS":
        order_id = _extract_order_id_with_history(message, history)
        if not order_id:
            return {
                "intent": "ORDER_STATUS",
                "answer": "请提供您的订单号（形如 SO2026xxxxxx），我帮您查询物流与状态。",
                "tool_result": None,
                "sources": [],
            }
        order = get_order(order_id)
        if order is None:
            return {
                "intent": "ORDER_STATUS",
                "answer": f"没有找到订单 {order_id}，请核对订单号后重试。",
                "tool_result": None,
                "sources": [],
                "ticket": create_ticket(message, order_id=order_id),
            }
        return {
            "intent": "ORDER_STATUS",
            "answer": _format_order(order),
            "tool_result": order,
            "sources": [],
        }

    # 售前 / RAG（context 含多轮历史，帮助理解"那它呢"这类指代）
    rag = _answer_pre_sale(message, context)
    out = {
        "intent": intent,
        "answer": rag["answer"],
        "tool_result": rag.get("tool_result"),
        "sources": rag["sources"],
    }
    # RAG 未命中 → 按情绪匹配兜底话术 + 自动建工单转人工
    if not rag.get("matched", True):
        out["answer"] = _fallback_reply(message)
        out["ticket"] = create_ticket(message)
    else:
        # RAG 命中但问题属于售后/履约类（非纯售前咨询），自动建工单让人工跟进
        from ticket import classify as classify_ticket
        category, priority, _ = classify_ticket(message)
        if category not in ("售前咨询", "其他咨询"):
            out["ticket"] = create_ticket(message)
    return out


def should_use_openai_tool_router() -> bool:
    """当 MODEL_PROVIDER 不是 local 且配置了对应 API key 时，启用 LLM tool calling。"""
    from llm_provider import get_config
    cfg = get_config()
    mode = os.getenv("AGENT_ROUTER", "auto").lower()
    if mode == "rules":
        return False
    return cfg.available


def answer_message(message: str, platform: str = "novatech", history: list[dict] | None = None) -> dict:
    # 多轮上下文：把最近对话拼成 RAG 检索上下文，帮助理解指代；
    # 但意图分类仍只用当前消息，避免历史词污染路由。
    context = message
    if history:
        recent = history[-4:]
        turns = []
        for h in recent:
            role = "客户" if h.get("role") == "user" else "客服"
            turns.append(f"{role}：{h.get('content', '')[:120]}")
        if turns:
            context = "【最近对话】\n" + "\n".join(turns) + "\n\n【当前问题】" + message

    if should_use_openai_tool_router():
        from openai_tool_router import answer_message_with_tools
        return answer_message_with_tools(message=context, platform=platform)
    return answer_message_rule_based(
        message=message, platform=platform, history=history, context=context
    )
