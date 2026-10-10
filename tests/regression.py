import json
import uuid
import urllib.request

BASE = "http://127.0.0.1:8010"


def chat(msg, sid=None):
    sid = sid or ("s-" + uuid.uuid4().hex[:8])
    body = json.dumps({"message": msg, "platform": "novatech", "session_id": sid}).encode()
    req = urllib.request.Request(BASE + "/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def feishu(payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + "/feishu/webhook", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def show(tag, ok, detail):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {tag}: {detail}")


# ========== 1. 售前 ==========
r = chat("Air100 核心参数是什么")
show("售前-参数", r["intent"] in ("RAG", "PRE_SALE") and len(r["answer"]) > 20, f"{r['intent']} | {r['answer'][:40]}")

r = chat("Air100 和 Studio200 怎么选")
show("售前-对比", "Q2" in r["answer"] or "Studio200" in r["answer"], f"{r['intent']} | {r['answer'][:40]}")

r = chat("Air100 怎么配对蓝牙")
show("售前-使用方法", "配对" in r["answer"] or "Q18" in r["answer"], f"{r['intent']} | {r['answer'][:40]}")

# ========== 2. 售后 ==========
r = chat("我的订单 SO20260912001 物流到哪了")
show("售后-订单物流", r["intent"] == "ORDER_STATUS" and "顺丰" in r["answer"], f"{r['intent']} | {r['answer'][:40]}")

r = chat("我想退货，订单 SO20260930004 怎么退款")
show("售后-退款", r["intent"] == "REFUND", f"{r['intent']} | {r['answer'][:40]}")

r = chat("查一下订单 SO99999999999")
show("售后-假订单号", r["intent"] == "ORDER_STATUS" and "没有找到" in r["answer"], f"{r['intent']} | {r['answer'][:40]}")

# ========== 3. 多轮 ==========
sid = "mt-test-1"
chat("Air100 怎么样", sid)
r = chat("那它防水吗", sid)
show("多轮-指代防水", "IPX5" in r["answer"] or "防水" in r["answer"], f"{r['intent']} | {r['answer'][:45]}")

sid2 = "mt-test-2"
chat("我要查订单 SO20260912001 物流", sid2)
r = chat("那退款呢", sid2)
show("多轮-指代退款", r["intent"] == "REFUND" and "SO20260912001" in r["answer"], f"{r['intent']} | {r['answer'][:45]}")

# ========== 4. 情绪 / 兜底 ==========
r = chat("你们这个什么垃圾玩意！再也不买了！")
show("情绪-愤怒转人工", r["intent"] == "ESCALATE" and r.get("ticket", {}).get("priority", "").startswith("P0"), f"{r['intent']} P0={r.get('ticket',{}).get('priority')}")

r = chat("帮我推荐生日礼物")
tk = r.get("ticket") or {}
show("兜底-知识库外转人工", r.get("ticket") is not None, f"ticket={tk.get('category')}")

r = chat("你们老板姓什么")
tk = r.get("ticket") or {}
show("兜底-噪声转人工", r.get("ticket") is not None, f"ticket={tk.get('category')}")

r = chat("How much is Air100?")
show("兜底-英文问题", len(r["answer"]) > 10, f"{r['intent']} | {r['answer'][:40]}")

# ========== 5. 引用 sources ==========
r = chat("Watch30 收不到手机通知怎么办")
show("RAG-引用数量", len(r.get("sources", [])) >= 1, f"sources={len(r.get('sources',[]))}")

# ========== 6. 飞书 ==========
fr = feishu({"type": "url_verification", "challenge": "ch_abc123"})
show("飞书-挑战回显", fr.get("challenge") == "ch_abc123", f"challenge={fr.get('challenge')}")

fsid = "oc_chat_test"
r1 = feishu({"schema": "2.0", "event": {"type": "im.message.receive_v1", "message": {"chat_id": fsid, "message_id": "om_1", "content": json.dumps({"text": "Air100 怎么样"})}}})
r2 = feishu({"schema": "2.0", "event": {"type": "im.message.receive_v1", "message": {"chat_id": fsid, "message_id": "om_2", "content": json.dumps({"text": "那它防水吗"})}}})
show("飞书-多轮指代", "防水" in r2.get("reply", ""), f"reply1={r1.get('reply','')[:30]} | reply2={r2.get('reply','')[:45]}")

# ========== 7. 空消息 ==========
import urllib.error
try:
    body = json.dumps({"message": "  ", "platform": "novatech"}).encode()
    req = urllib.request.Request(BASE + "/chat", data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)
    show("边界-空消息", False, "空消息竟然通过了")
except urllib.error.HTTPError as e:
    show("边界-空消息", e.code == 422, f"HTTP {e.code}（422 校验拒绝）")

print("\n==== 后端回归完成 ====")
