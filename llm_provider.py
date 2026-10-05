"""国产/海外大模型统一接入层。

通过环境变量 ``MODEL_PROVIDER`` 切换：

- ``local``（默认）：不调用任何外部模型，走本地规则路由 + BM25 RAG，
  零网络依赖，适合作品演示与离线部署。
- ``openai``：官方 OpenAI（api.openai.com）
- ``deepseek``：DeepSeek 深度求索（api.deepseek.com）
- ``qwen``：通义千问 DashScope 兼容模式（dashscope.aliyuncs.com）
- ``zhipu``：智谱 GLM（open.bigmodel.cn）
- ``kimi``：月之暗面 Moonshot（api.moonshot.cn）

所有国产厂商均提供 OpenAI 兼容接口，因此客户端统一用 ``openai`` SDK，
只换 base_url / api_key / model 三个参数。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str | None
    api_key: str | None
    chat_model: str
    embedding_model: str | None
    available: bool  # 是否配置了可用的 API key


_PROVIDERS: dict[str, dict] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "chat_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "embedding_model": "text-embedding-3-small",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "chat_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "embedding_model": None,  # DeepSeek 暂未开放 embedding
    },
    "qwen": {
        # 通义千问 OpenAI 兼容模式
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "chat_model": "qwen-plus",
        "env_key": "DASHSCOPE_API_KEY",
        "embedding_model": "text-embedding-v3",
    },
    "zhipu": {
        # 智谱 GLM OpenAI 兼容接口
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "chat_model": "glm-4-flash",
        "env_key": "ZHIPU_API_KEY",
        "embedding_model": "embedding-3",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "chat_model": "moonshot-v1-8k",
        "env_key": "MOONSHOT_API_KEY",
        "embedding_model": None,
    },
}


def get_config() -> LLMConfig:
    provider = (os.getenv("MODEL_PROVIDER") or "local").strip().lower()
    if provider == "local":
        return LLMConfig(
            provider="local",
            base_url=None,
            api_key=None,
            chat_model="",
            embedding_model=None,
            available=False,
        )
    if provider not in _PROVIDERS:
        raise ValueError(
            f"未知 MODEL_PROVIDER={provider!r}，可选: local/openai/deepseek/qwen/zhipu/kimi"
        )
    meta = _PROVIDERS[provider]
    api_key = os.getenv(meta["env_key"]) or os.getenv("OPENAI_API_KEY")
    return LLMConfig(
        provider=provider,
        base_url=meta["base_url"],
        api_key=api_key,
        chat_model=os.getenv("CHAT_MODEL") or meta["chat_model"],
        embedding_model=os.getenv("EMBEDDING_MODEL") or meta["embedding_model"],
        available=bool(api_key),
    )


def get_openai_client():
    """返回 OpenAI 兼容客户端；local 或未配置 key 时返回 None。"""
    cfg = get_config()
    if not cfg.available:
        return None
    from openai import OpenAI  # 延迟导入，本地模式不需要装 openai 包

    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)


def describe() -> str:
    cfg = get_config()
    if cfg.provider == "local":
        return "本地规则路由 + BM25 RAG（无外部模型依赖）"
    if not cfg.available:
        return f"{cfg.provider}（未配置 API_KEY，已回退本地模式）"
    return f"{cfg.provider} · {cfg.chat_model}"
