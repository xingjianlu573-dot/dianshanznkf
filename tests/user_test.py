# -*- coding: utf-8 -*-
"""用户视角全场景测试脚本（模拟真实用户提问）"""
import json
import urllib.request
import time

BASE = "http://127.0.0.1:8010"

def chat(message, sid=None, platform="novatech"):
    body = json.dumps({"message": message, "platform": platform, "session_id": sid or "t-" + str(int(time.time()*1000))}).encode("utf-8")
    req = urllib.request.Request(BASE + "/chat", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def show(tag, r):
    ans = (r.get("answer") or "")[:70].replace("\n", " ")
    intent = r.get("intent", "?")
    srcs = r.get("sources") or []
    tk = r.get("ticket")
    tkinfo = f"[工单:{tk['category']}/{tk['priority']}]" if tk else ""
    print(f"  {tag}: intent={intent} {tkinfo} | {ans} | sources={len(srcs)}")

print("======== 1. 售前咨询 ========")
sid = "u1"
show("产品参数", chat("Air100 的续航和重量是多少", sid))
show("产品对比", chat("Air100 和 Studio200 哪个好", sid))
show("使用方法", chat("Watch30 怎么开启运动模式", sid))
show("配件", chat("Air100 包装里有什么配件", sid))
show("价格", chat("GaN65 充电器多少钱", sid))

print("\n======== 2. 售后支持 ========")
sid = "u2"
show("订单查询", chat("帮我查下订单 SO20260920002 到哪了", sid))
show("物流", chat("订单 SO20260912001 现在什么物流状态", sid))
show("退款流程", chat("我要退 SO20260930004 这单，怎么退", sid))
show("售后政策", chat("7天无理由退货政策是什么", sid))

print("\n======== 3. 多轮上下文 ========")
sid = "u3"
show("第一问", chat("Air100 怎么样", sid))
show("指代-防水", chat("那它防水吗", sid))
show("指代-续航", chat("续航多久", sid))
show("追问订单", chat("我要查订单 SO20260912001", sid))
show("追问退款", chat("那退款呢", sid))

print("\n======== 4. 智能工单/升级 ========")
sid = "u4"
show("投诉", chat("你们东西质量太差，我要投诉", sid))
show("骂人", chat("什么垃圾产品，再也不买了", sid))
show("知识库外问题", chat("你们公司什么时候上市的", sid))
show("模糊问题", chat("今天天气怎么样", sid))

print("\n======== 5. 边界/刁钻输入 ========")
sid = "u5"
try:
    show("空消息", chat("", sid))
except Exception as e:
    print(f"  空消息: 被拒绝 {e}（预期：422 校验）")
show("纯符号", chat("？？？！！！", sid))
show("英文", chat("How much is the Air100?", sid))
show("乱码", chat("asdfghjkl;", sid))
show("订单号错", chat("查订单 SO99999999999", sid))
show("极长消息", chat("你好" * 300, sid))

print("\n======== 6. 飞书 webhook ========")
payload = json.dumps({"schema": "2.0", "event": {"type": "im.message.receive_v1", "message": {"chat_id": "oc_t", "message_id": "om_t", "content": '{"text":"Watch30 多少钱？"}'}}}).encode("utf-8")
req = urllib.request.Request(BASE + "/feishu/webhook", data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    resp = json.loads(r.read().decode("utf-8"))
print(f"  code={resp.get('code')} reply={(resp.get('reply') or '')[:50]}")

print("\n======== 7. 工单独立接口 ========")
req = urllib.request.Request(BASE + "/tickets", data=json.dumps({"message": "耳机连不上蓝牙"}).encode("utf-8"), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print("  OK:", json.loads(r.read().decode("utf-8")))
except Exception as e:
    print("  ERR:", e)

print("\n======== 8. 商品/订单接口 ========")
for path in ["/products", "/orders/SO20260912001"]:
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    print(f"  {path}: {type(data).__name__} 条目={len(data) if isinstance(data, list) else 'ok'}")
