"""飞书机器人对接桥。

让 AI Customer Service Platform 可以作为飞书自建应用/机器人接收用户消息。

工作方式：
1. 飞书开放平台配置「事件订阅」，把回调地址指向 POST /feishu/webhook
2. 飞书推送事件（im.message.receive_v1），本模块解析消息文本
3. 文本交给 agent_router.answer_message() 处理
4. 回复方式二选一：
   - mock 模式（默认）：不配凭证，直接把回复返回给飞书（需飞书侧配置"返回文本"模式，或用于演示/调试）
   - api 模式：配置 FEISHU_APP_ID + FEISHU_APP_SECRET 后，通过飞书
     开放平台 API（POST /open-apis/im/v1/messages）主动发消息到会话

环境变量：
- FEISHU_APP_ID      飞书自建应用 App ID（api 模式必填）
- FEISHU_APP_SECRET  飞书自建应用 App Secret（api 模式必填）
- FEISHU_VERIFY_TOKEN 事件订阅校验 token（可选，用于 URL 验证）

参考飞书文档：https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-guide-preview
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict, deque
from typing import Optional

import requests

from agent_router import answer_message

# 飞书渠道会话：chat_id -> [{role, content}, ...]（与 api.py 同样 maxlen=8）
# 独立维护，避免 api.py ↔ feishu_bridge.py 循环 import
_feishu_conversations: dict[str, deque] = defaultdict(lambda: deque(maxlen=8))


def _extract_text_from_content(content: str) -> str:
    """飞书消息 content 是 JSON 字符串，text 消息形如 {"text":"你好"}。"""
    try:
        data = json.loads(content)
        return data.get("text", "")
    except Exception:
        return content or ""


def _extract_message(event: dict) -> dict:
    """从飞书事件体里提取 (chat_id, text, message_id)。"""
    msg = event.get("message", {})
    chat_id = msg.get("chat_id", "")
    message_id = msg.get("message_id", "")
    content = msg.get("content", "")
    text = _extract_text_from_content(content)
    return {"chat_id": chat_id, "message_id": message_id, "text": text}


def _is_url_verification(payload: dict) -> bool:
    """飞书首次配置事件订阅时用 challenge 校验 URL。"""
    return payload.get("type") == "url_verification"


def _send_via_feishu_api(chat_id: str, text: str) -> bool:
    """通过飞书开放平台 API 发消息（需要 app_id/app_secret）。"""
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        return False

    # 获取 tenant_access_token
    token_resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    token_data = token_resp.json()
    token = token_data.get("tenant_access_token")
    if not token:
        return False

    # 发送文本消息
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
        timeout=10,
    )
    return resp.status_code == 200


def handle_feishu_event(payload: dict) -> dict:
    """处理飞书事件订阅回调，返回飞书要求的响应体。

    返回结构：
    - 状态 ok：{code:0, msg:"success", reply: "给客户的话术"}（mock 模式 reply 直接返回给飞书）
    - 状态 skipped：非文本消息/无内容，{code:0, msg:"skipped"}
    """
    # 0. 安全校验：若配置了 FEISHU_VERIFY_TOKEN，则校验事件体中的 token 字段
    expected_token = os.getenv("FEISHU_VERIFY_TOKEN", "")
    if expected_token:
        got_token = payload.get("token", "")
        if got_token != expected_token:
            return {"code": 0, "msg": "forbidden"}

    # 1. URL 验证：返回 challenge
    if _is_url_verification(payload):
        return {"code": 0, "msg": "success", "challenge": payload.get("challenge", "")}

    # 2. 事件推送：im.message.receive_v1
    event = payload.get("event", {})
    if event.get("type") != "im.message.receive_v1":
        return {"code": 0, "msg": "skipped"}

    info = _extract_message(event)
    text = info["text"].strip()
    if not text:
        return {"code": 0, "msg": "skipped"}

    # 3. 交给客服 Agent 处理（以 chat_id 为 session，飞书渠道同样支持多轮上下文）
    chat_id = info["chat_id"]
    history = list(_feishu_conversations[chat_id]) if chat_id else None
    result = answer_message(text, platform="feishu", history=history)
    reply = result.get("answer", "")
    if chat_id:
        _feishu_conversations[chat_id].append({"role": "user", "content": text})
        _feishu_conversations[chat_id].append({"role": "agent", "content": reply})

    # 4. api 模式：主动发消息回飞书
    if _send_via_feishu_api(chat_id, reply):
        return {"code": 0, "msg": "success", "delivered": "feishu_api"}
    return {"code": 0, "msg": "success", "reply": reply}
