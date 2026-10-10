from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_router import answer_message
from commerce_api import get_order, list_products, request_refund
from rag_service import clear_query_engine_cache
from ticket import create_ticket
from llm_provider import describe as describe_llm


app = FastAPI(title="AI Customer Service Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 作品集演示：允许任意来源访问
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARTIFACT_DIR = Path("generated_knowledge")
RAG_RUNTIME_DIR = Path("runtime_knowledge/current")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    platform: str = "novatech"
    session_id: str = "default"


class ChatResponse(BaseModel):
    intent: str
    answer: str
    tool_result: Optional[dict] = None
    sources: list[dict] = Field(default_factory=list)
    ticket: Optional[dict] = None
    session_id: str = "default"


# 内存会话存储：session_id -> [{role, content}, ...]（多轮上下文）
# 生产环境可替换为 Redis / PostgreSQL
from collections import defaultdict, deque
_conversations: dict[str, deque] = defaultdict(lambda: deque(maxlen=8))


def _get_history(session_id: str) -> list[dict]:
    return list(_conversations[session_id])


class RefundRequest(BaseModel):
    order_id: str
    reason: str = ""


class TicketRequest(BaseModel):
    message: str = Field(..., min_length=1)
    order_id: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "ai-customer-service-platform",
        "llm": describe_llm(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> dict:
    history = _get_history(req.session_id)
    result = answer_message(req.message, platform=req.platform, history=history)
    # 记录本次对话，供多轮上下文使用
    _conversations[req.session_id].append({"role": "user", "content": req.message})
    _conversations[req.session_id].append({"role": "agent", "content": result.get("answer", "")})
    result["session_id"] = req.session_id
    return result


@app.get("/products")
def products() -> dict:
    """模拟商品数据库接口。"""
    return {"products": list_products(), "total": len(list_products())}


@app.get("/orders/{order_id}")
def order_detail(order_id: str) -> dict:
    """模拟订单数据库接口：订单状态 + 物流轨迹 + 退款状态。"""
    order = get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"order {order_id} not found")
    return order


@app.post("/orders/{order_id}/refund")
def order_refund(order_id: str, req: RefundRequest) -> dict:
    """模拟退款申请接口。"""
    return request_refund(order_id, reason=req.reason)


@app.post("/tickets")
def tickets(req: TicketRequest) -> dict:
    """手动创建智能工单。"""
    return create_ticket(req.message, order_id=req.order_id)


@app.post("/feishu/webhook")
def feishu_webhook(payload: dict) -> dict:
    """飞书事件订阅回调：接收用户消息 → 客服 Agent 处理 → 回复。"""
    from feishu_bridge import handle_feishu_event
    return handle_feishu_event(payload)


# 兼容原项目的 store knowledge 接口（保留架构，但默认直接用 data/ 下的语料）
@app.post("/knowledge/refresh")
def refresh_knowledge() -> dict:
    clear_query_engine_cache()
    return {"status": "ok", "message": "RAG index reloaded."}


# ---------------------------------------------------------------------------
# 托管前端静态文件（生产/单容器部署模式）
# ---------------------------------------------------------------------------
_FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/showcase", include_in_schema=False)
async def showcase_page():
    # 新版 Starlette 的 StaticFiles html 模式不再支持"无扩展名自动补 .html"，
    # 这里显式路由，保证 README 里的 http://host/showcase 链接可用。
    return FileResponse(_FRONTEND_DIR / "showcase.html")


if _FRONTEND_DIR.exists():
    # 把前端目录挂到根路径（API 路由已在上方注册，优先匹配）
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="static")
