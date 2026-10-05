from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent_router import answer_message
from commerce_api import get_order, list_products, request_refund
from rag_service import clear_query_engine_cache
from ticket import create_ticket


app = FastAPI(title="AI Customer Service Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
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


class ChatResponse(BaseModel):
    intent: str
    answer: str
    tool_result: Optional[dict] = None
    sources: list[dict] = Field(default_factory=list)
    ticket: Optional[dict] = None


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
    return {"status": "ok", "service": "ai-customer-service-platform"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> dict:
    return answer_message(req.message, platform=req.platform)


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


# 兼容原项目的 store knowledge 接口（保留架构，但默认直接用 data/ 下的语料）
@app.post("/knowledge/refresh")
def refresh_knowledge() -> dict:
    clear_query_engine_cache()
    return {"status": "ok", "message": "RAG index reloaded."}
