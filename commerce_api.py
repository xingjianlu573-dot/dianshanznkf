"""模拟电商业务后端（商品库 + 订单库 + 物流 + 退款）。

保留原项目的 dataclass 风格，扩充字段以支撑：
- 商品参数 / 价格 / 配件 / 库存
- 订单状态机：pending_pay → paid → shipped → in_transit → delivered → (refund_applied / completed)
- 物流轨迹（carrier + tracking_no + events[]）
- 退款申请状态（none / reviewing / approved / rejected / refunded）
"""
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 商品库（企业电子产品）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price: float           # CNY
    stock: int
    params: dict = field(default_factory=dict)
    accessories: tuple = ()
    usage: str = ""
    warranty: str = ""


PRODUCTS = [
    Product(
        sku="NT-AIR100",
        name="智能降噪耳机 Air100",
        category="音频设备",
        price=899.00,
        stock=128,
        params={
            "驱动单元": "10mm 动圈",
            "主动降噪": "-42dB",
            "蓝牙版本": "5.3",
            "单次续航": "8 小时",
            "总续航": "32 小时（含充电盒）",
            "防水": "IPX5",
            "单耳重量": "4.6g",
        },
        accessories=("Type-C 充电线", "S/M/L 硅胶耳帽", "收纳袋", "说明书"),
        usage="开盖即连；双击左耳切换降噪；长按左耳 2 秒切换通透/强降噪。",
        warranty="主机 2 年 / 配件 6 个月",
    ),
    Product(
        sku="NT-STUDIO200",
        name="头戴式空间音频耳麦 Studio200",
        category="音频设备",
        price=1599.00,
        stock=45,
        params={
            "驱动单元": "40mm 生物纤维振膜",
            "主动降噪": "-48dB",
            "蓝牙版本": "5.4",
            "续航": "45 小时（降噪开）",
            "重量": "258g",
            "麦克风": "双 AI 通话降噪",
        },
        accessories=("3.5mm 音频线", "Type-C 充电线", "硬壳收纳包", "飞机转接头"),
        usage="右侧滚轮调音量；电源键长按 3 秒开关；有线/蓝牙双模切换。",
        warranty="主机 2 年 / 配件 6 个月",
    ),
    Product(
        sku="NT-WATCH30",
        name="智能手表 Watch30",
        category="智能穿戴",
        price=1299.00,
        stock=76,
        params={
            "屏幕": "1.43 英寸 AMOLED",
            "电池": "420mAh，典型使用 7 天",
            "防水": "5ATM + IP68",
            "传感器": "心率/血氧/加速度/陀螺仪",
            "GPS": "双频 GNSS",
            "兼容": "Android 9.0+ / iOS 14+",
        },
        accessories=("磁吸充电线", "备用硅胶表带", "说明文档"),
        usage="扫码下载 HealthGo App 配对；长按表盘切换表盘；右上下滑控制中心。",
        warranty="主机 1 年 / 表带 3 个月",
    ),
    Product(
        sku="NT-GAAN65",
        name="65W 氮化镓快充充电器 Pro",
        category="配件",
        price=149.00,
        stock=320,
        params={
            "功率": "65W 单口 / 45W+20W 双口",
            "接口": "1×USB-C + 1×USB-A",
            "协议": "PD3.0 / QC4+ / PPS",
            "折叠插脚": "是",
            "尺寸": "31×31×33mm",
        },
        accessories=("充电器本体", "说明书（不含线材）"),
        usage="插入墙面插座即可；C 口支持笔记本 65W 满速。",
        warranty="1 年",
    ),
    Product(
        sku="NT-KEY87",
        name="机械键盘 Key87 三模",
        category="电脑外设",
        price=399.00,
        stock=58,
        params={
            "配列": "87 键 TKL",
            "连接": "蓝牙 5.1 / 2.4G / Type-C 有线",
            "轴体": "线性红轴 / 段落茶轴可选",
            "电池": "4000mAh，RGB 关闭约 4 周",
            "热插拔": "五脚热插拔",
        },
        accessories=("拔键器", "拔轴器", "Type-C 线", "2.4G 接收器"),
        usage="Fn+1/2/3 切换蓝牙设备；Fn+灯光键调节亮度。",
        warranty="1 年",
    ),
]


# ---------------------------------------------------------------------------
# 订单库
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OrderItem:
    sku: str
    name: str
    qty: int
    price: float


@dataclass(frozen=True)
class LogisticsEvent:
    time: str
    desc: str


@dataclass(frozen=True)
class Order:
    order_id: str
    user_id: str
    items: tuple
    total: float
    status: str           # paid / shipped / in_transit / delivered / refund_applied
    created_at: str
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    carrier: str = "未分配"
    tracking_no: str = "待分配"
    events: tuple = ()
    refund_status: str = "none"   # none / reviewing / approved / rejected / refunded
    refund_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    refund_updated_at: Optional[str] = None


ORDERS = {
    "SO20260912001": Order(
        order_id="SO20260912001",
        user_id="U1001",
        items=(OrderItem("NT-AIR100", "智能降噪耳机 Air100", 1, 899.00),),
        total=899.00,
        status="in_transit",
        created_at="2026-09-12 10:23",
        shipped_at="2026-09-13 09:00",
        carrier="顺丰速运",
        tracking_no="SF318876543210",
        events=(
            LogisticsEvent("2026-09-13 09:00", "商家已发货，包裹到达【广州番禺集散中心】"),
            LogisticsEvent("2026-09-14 08:30", "快件到达【杭州萧山集散点】"),
            LogisticsEvent("2026-09-14 14:12", "派送中，快递员张师傅 138****1234"),
        ),
    ),
    "SO20260920002": Order(
        order_id="SO20260920002",
        user_id="U1001",
        items=(OrderItem("NT-WATCH30", "智能手表 Watch30", 1, 1299.00),),
        total=1299.00,
        status="delivered",
        created_at="2026-09-20 20:11",
        shipped_at="2026-09-21 11:00",
        delivered_at="2026-09-23 18:42",
        carrier="京东物流",
        tracking_no="JD009988776655",
        events=(
            LogisticsEvent("2026-09-21 11:00", "商家已发货"),
            LogisticsEvent("2026-09-23 18:42", "已签收，签收人：本人"),
        ),
    ),
    "SO20260928003": Order(
        order_id="SO20260928003",
        user_id="U1002",
        items=(
            OrderItem("NT-KEY87", "机械键盘 Key87 三模", 1, 399.00),
            OrderItem("NT-GAAN65", "65W 氮化镓快充充电器 Pro", 1, 149.00),
        ),
        total=548.00,
        status="in_transit",
        created_at="2026-09-28 15:40",
        shipped_at="2026-09-29 10:00",
        carrier="中通快递",
        tracking_no="ZT776655443322",
        events=(
            LogisticsEvent("2026-09-29 10:00", "商家已发货"),
            LogisticsEvent("2026-10-01 09:20", "快件到达【北京朝阳分拨中心】"),
        ),
    ),
    "SO20260930004": Order(
        order_id="SO20260930004",
        user_id="U1001",
        items=(OrderItem("NT-STUDIO200", "头戴式空间音频耳麦 Studio200", 1, 1599.00),),
        total=1599.00,
        status="refund_applied",
        created_at="2026-09-30 09:00",
        shipped_at="2026-10-01 09:00",
        delivered_at="2026-10-03 12:00",
        carrier="顺丰速运",
        tracking_no="SF318800001122",
        events=(
            LogisticsEvent("2026-10-01 09:00", "商家已发货"),
            LogisticsEvent("2026-10-03 12:00", "已签收"),
        ),
        refund_status="reviewing",
        refund_reason="耳罩夹头，申请 7 天无理由退货",
        refund_amount=1599.00,
        refund_updated_at="2026-10-04 20:10",
    ),
}


# ---------------------------------------------------------------------------
# 商品相关工具
# ---------------------------------------------------------------------------
def list_products() -> list[dict]:
    return [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "price": p.price,
            "stock": p.stock,
            "params": p.params,
            "accessories": list(p.accessories),
            "warranty": p.warranty,
        }
        for p in PRODUCTS
    ]


def get_product_by_sku(sku: str) -> Optional[Product]:
    for p in PRODUCTS:
        if p.sku.lower() == sku.lower():
            return p
    return None


def search_products(keyword: str) -> list[dict]:
    """按关键词在品名/品类中模糊搜索。"""
    kw = (keyword or "").lower().strip()
    if not kw:
        return list_products()
    hits = []
    for p in PRODUCTS:
        blob = f"{p.name} {p.category} {' '.join(p.params.keys())} {' '.join(p.params.values())}".lower()
        if kw in blob:
            hits.append({
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "stock": p.stock,
            })
    return hits


# ---------------------------------------------------------------------------
# 订单 / 物流 / 退款工具
# ---------------------------------------------------------------------------
def _order_to_dict(order: Order) -> dict:
    return {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "items": [
            {"sku": it.sku, "name": it.name, "qty": it.qty, "price": it.price}
            for it in order.items
        ],
        "total": order.total,
        "status": order.status,
        "created_at": order.created_at,
        "shipped_at": order.shipped_at,
        "delivered_at": order.delivered_at,
        "logistics": {
            "carrier": order.carrier,
            "tracking_no": order.tracking_no,
            "events": [{"time": e.time, "desc": e.desc} for e in order.events],
        },
        "refund": {
            "status": order.refund_status,
            "reason": order.refund_reason,
            "amount": order.refund_amount,
            "updated_at": order.refund_updated_at,
        },
    }


def get_order(order_id: str) -> Optional[dict]:
    order = ORDERS.get((order_id or "").strip().upper()) or ORDERS.get((order_id or "").strip())
    return _order_to_dict(order) if order else None


def list_orders_by_user(user_id: str) -> list[dict]:
    return [_order_to_dict(o) for o in ORDERS.values() if o.user_id == user_id]


def request_refund(order_id: str, reason: str) -> dict:
    order = ORDERS.get((order_id or "").strip().upper())
    if order is None:
        return {"ok": False, "error": f"订单 {order_id} 不存在"}
    if order.status not in ("delivered", "shipped", "in_transit", "refund_applied"):
        return {"ok": False, "error": f"当前订单状态 {order.status} 不支持退款"}
    if order.refund_status == "reviewing":
        return {"ok": False, "error": "该订单已有退款申请在审核中，请等待处理"}
    if order.refund_status == "refunded":
        return {"ok": False, "error": "该订单已完成退款"}

    # 模拟写库：在这个 mock 里我们返回一条已受理的记录，不真改 frozen dataclass
    return {
        "ok": True,
        "order_id": order.order_id,
        "status": "reviewing",
        "reason": reason,
        "amount": order.total,
        "estimated_next_step": "客服将在 2 小时内审核，审核通过后请按短信地址寄回商品，仓库签收后 48 小时内原路退款。",
    }


def escalate_to_human(reason: str, platform: str = "novatech") -> dict:
    return {
        "platform": platform,
        "escalated": True,
        "reason": reason or "customer_support_review",
        "next_step": "已为您转接人工客服（工作时间 9:00-21:00），非工作时间将在次日 10 点前回访。",
    }
