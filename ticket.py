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
    "物流异常": [
        "没收到", "没到货", "没签收", "显示签收", "快递丢", "丢件", "停滞",
        "一直不动", "卡在", "破损", "外包装", "箱子破", "压扁", "变形",
    ],
    "少发漏发错发": [
        "少发", "漏发", "没给我", "缺", "少了", "没收到配件", "发错",
        "颜色不对", "型号不对", "数量不对",
    ],
    "退款退货": [
        "退款", "退货", "退钱", "退我", "7天", "七天无理由", "不想要了", "拍错",
        "多拍", "换货", "退订单", "价保", "退差价",
    ],
    "产品质量/故障": [
        "坏了", "故障", "开不了机", "没声音", "失灵", "死机", "质量问题",
        "刺耳", "杂音", "漏电", "发烫", "无法连接", "连不上", "配对不上",
        "充不进", "充不进电", "按键", "按键没反应", "降噪没用", "不准",
    ],
    "订单变更": [
        "改地址", "修改地址", "换地址", "取消订单", "我要取消", "还没发",
        "催发货", "怎么还不发", "什么时候发",
    ],
    "支付与发票": [
        "发票", "抬头", "开票", "重复扣款", "扣了两次", "支付失败", "付不了钱",
        "账号", "登录", "密码", "解绑", "绑定",
    ],
    "售前咨询": [
        "多少钱", "价格", "参数", "区别", "推荐", "哪个好", "对比", "续航",
        "防水", "兼容", "支持吗", "能连", "配件", "送什么", "尺寸", "多大",
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
    "充不进", "没反应", "失灵", "断连", "断联",
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
    if category == "物流异常":
        return "调用订单/物流接口拉最新轨迹；要求客户提供面单/包裹照片；24h 无更新则推送仓储与快递核查工单。"
    if category == "少发漏发错发":
        return "核对订单应发清单与仓库发货记录；要求客户拍开箱图与缺件位置；确认后 48h 内补发，运费商家承担。"
    if category == "退款退货":
        return "校验订单状态是否在 7 天无理由窗口内；自动生成退货地址与短信通知，金额原路退回；质量问题先取证再定责。"
    if category == "产品质量/故障":
        return "采集 SN/订单号，按故障排查手册引导（重置/清洁触点/换线）；若复现则转售后维修组并安排换货。"
    if category == "订单变更":
        return "核对订单是否已出库；未出库走改地址/取消流程；已出库则告知无法改单，提供拒收重拍或转寄方案。"
    if category == "支付与发票":
        return "引导客户在 App 自助开票；重复扣款核实银行流水后 3-7 工作日原路退回；涉及账号安全转账户组。"
    if category == "售前咨询":
        return "优先由 RAG 知识库自动回复；命中商品 SKU 时附带价格/库存/配件信息。"
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
