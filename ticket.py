"""智能工单模块。

用户问题进来后，根据关键词 + 上下文自动生成：
- 问题分类（category）
- 优先级（priority: P0/P1/P2）
- 处理建议（suggested_action）

产出一张工单 ticket，可被客服后台接管。
"""
from datetime import datetime
from itertools import count


_ticket_seq = count(1001)


# 分类 → 触发关键词（中文为主）
CATEGORY_RULES: dict[str, list[str]] = {
    "物流问题": [
        "没收到", "没到货", "物流", "快递", "运单", "一直不发", "没发货",
        "卡", "停滞", "丢件", "破损", "外包装", "箱子",
    ],
    "退款退货": [
        "退款", "退货", "退钱", "退我", "7天", "七天无理由", "不想要了", "拍错",
        "多拍", "换货", "退订单",
    ],
    "产品质量": [
        "坏了", "故障", "开不了机", "没声音", "失灵", "死机", "质量问题",
        "刺耳", "杂音", "漏电", "发烫", "无法连接", "连不上", "配对不上",
    ],
    "售前咨询": [
        "多少钱", "价格", "参数", "区别", "推荐", "哪个好", "对比", "续航",
        "防水", "兼容", "支持吗", "能连", "配件", "送什么",
    ],
    "账户与发票": [
        "发票", "抬头", "开票", "账号", "登录", "密码", "解绑", "绑定",
    ],
}

# 高优先级触发词
P0_TERMS = [
    "投诉", "起诉", "12315", "消协", "媒体", "曝光", "总理", "人工",
    "经理", "主管", "退货退款马上", "立刻退", "马上退", "315",
]
P1_TERMS = [
    "没收到", "丢件", "坏了", "故障", "质量", "开不了机", "没声音",
    "破损", "漏发", "少发", "充电器烧", "起火",
]


def classify(message: str) -> tuple[str, str, str]:
    """返回 (category, priority, suggested_action)。"""
    text = (message or "").lower()

    # 1) 分类
    category = "其他咨询"
    best_hits = 0
    for cat, kws in CATEGORY_RULES.items():
        hits = sum(1 for kw in kws if kw.lower() in text)
        if hits > best_hits:
            best_hits = hits
            category = cat

    # 2) 优先级
    if any(term in text for term in P0_TERMS):
        priority = "P0-紧急"
    elif any(term in text for term in P1_TERMS):
        priority = "P1-高"
    elif category in ("退款退货", "产品质量", "物流问题"):
        priority = "P1-高"
    else:
        priority = "P2-常规"

    # 3) 处理建议
    suggested_action = _suggest(category, priority, text)

    return category, priority, suggested_action


def _suggest(category: str, priority: str, text: str) -> str:
    if category == "物流问题":
        return "调用订单/物流接口拉取最新轨迹；若 24h 无更新则推送仓储核查工单。"
    if category == "退款退货":
        return "校验订单状态是否在 7 天无理由窗口内；自动生成退货地址与短信通知，金额原路退回。"
    if category == "产品质量":
        return "采集 SN/订单号，引导恢复出厂设置/重置；若复现则转售后维修组并安排换货。"
    if category == "售前咨询":
        return "优先由 RAG 知识库自动回复；命中商品 SKU 时附带价格/库存/配件信息。"
    if category == "账户与发票":
        return "引导用户在 App「订单详情」自助开票；涉及账号安全转账户组。"
    if priority == "P0-紧急":
        return "立即转人工客服主管，10 分钟内电话回访。"
    return "常规排期，下个工作日内回复。"


def create_ticket(message: str, order_id: str = "") -> dict:
    category, priority, action = classify(message)
    ticket_id = f"TK{next(_ticket_seq)}"
    return {
        "ticket_id": ticket_id,
        "category": category,
        "priority": priority,
        "suggested_action": action,
        "order_id": order_id or None,
        "summary": message[:80],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "open",
    }
