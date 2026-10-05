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


def classify_intent(message: str) -> str:
    text = message.lower()

    if any(term in text for term in ESCALATION_TERMS):
        return "ESCALATE"

    # 退款类问题：只有当消息里带订单号，或明确说"我的订单/我买的那个"时，才真的走退款流程；
    # 否则像"7天无理由""退款多久到账"是在问售后政策，走 RAG。
    has_order_id = bool(extract_order_id(message))
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


def _answer_pre_sale(message: str) -> dict:
    """售前：先看是否命中具体商品，命中就带商品卡片；否则 RAG。"""
    hits = search_products(message)
    from rag_service import answer_with_rag
    rag = answer_with_rag(message)

    if hits:
        card_lines = ["在售相关商品："]
        for h in hits[:5]:
            card_lines.append(f"  · {h['name']}（{h['sku']}）¥{h['price']:.0f}，库存 {h['stock']}")
        rag["answer"] = rag["answer"] + "\n\n" + "\n".join(card_lines)
        rag["tool_result"] = {"products": hits}
    return rag


def answer_message_rule_based(message: str, platform: str = "novatech") -> dict:
    intent = classify_intent(message)
    ticket = None

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

    # 退款：先抽订单号
    if intent == "REFUND":
        order_id = extract_order_id(message)
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
        order_id = extract_order_id(message)
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

    # 售前 / RAG
    rag = _answer_pre_sale(message)
    out = {
        "intent": intent,
        "answer": rag["answer"],
        "tool_result": rag.get("tool_result"),
        "sources": rag["sources"],
    }
    # RAG 未命中 → 自动建工单转人工
    if not rag.get("matched", True):
        out["ticket"] = create_ticket(message)
    else:
        # RAG 命中但问题属于售后/履约类（非纯售前咨询），自动建工单让人工跟进
        from ticket import classify as classify_ticket
        category, priority, _ = classify_ticket(message)
        if category not in ("售前咨询", "其他咨询"):
            out["ticket"] = create_ticket(message)
    return out


def should_use_openai_tool_router() -> bool:
    mode = os.getenv("AGENT_ROUTER", "openai").lower()
    return mode == "openai" and bool(os.getenv("OPENAI_API_KEY"))


def answer_message(message: str, platform: str = "novatech") -> dict:
    if should_use_openai_tool_router():
        from openai_tool_router import answer_message_with_tools
        return answer_message_with_tools(message=message, platform=platform)
    return answer_message_rule_based(message=message, platform=platform)
