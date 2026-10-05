"""RAG 服务层。

保留原项目的 LlamaIndex 生产路径；当未配置 OPENAI_API_KEY 时，
自动降级为本地 BM25 关键词检索，保证 demo 无需外网即可运行。
"""
import math
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


RUNTIME_KNOWLEDGE_DIR = Path("runtime_knowledge/current")
DEFAULT_KNOWLEDGE_DIR = Path("data")
MANUALS_DIR = Path("data/manuals")


def get_knowledge_files() -> list[str]:
    runtime_files = sorted(RUNTIME_KNOWLEDGE_DIR.glob("*.md"))
    if runtime_files:
        return [str(p) for p in runtime_files]

    files = sorted(DEFAULT_KNOWLEDGE_DIR.glob("*.md"))
    # 产品手册子目录也纳入语料
    if MANUALS_DIR.exists():
        files += sorted(MANUALS_DIR.glob("*.md"))
    return [str(p) for p in files]


def _use_openai_llm() -> bool:
    from llm_provider import get_config
    return get_config().available


# ---------------------------------------------------------------------------
# 生产路径：LlamaIndex + 国产/海外 LLM & Embeddings
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_openai_query_engine():
    from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
    from llama_index.core.node_parser import TokenTextSplitter
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.llms.openai import OpenAI
    from llm_provider import get_config

    cfg = get_config()
    Settings.embed_model = OpenAIEmbedding(
        model=cfg.embedding_model or "text-embedding-3-small",
        api_base=cfg.base_url,
        api_key=cfg.api_key,
    )
    Settings.llm = OpenAI(
        model=cfg.chat_model,
        api_base=cfg.base_url,
        api_key=cfg.api_key,
    )

    documents = SimpleDirectoryReader(input_files=get_knowledge_files()).load_data()
    parser = TokenTextSplitter(chunk_size=400, chunk_overlap=40)
    nodes = parser.get_nodes_from_documents(documents)
    index = VectorStoreIndex(nodes)
    return index.as_query_engine(similarity_top_k=3)


# ---------------------------------------------------------------------------
# 本地兜底：纯 Python BM25 检索（中文按 bigram 切分）
# ---------------------------------------------------------------------------
_CN_RE = re.compile(r"[\u4e00-\u9fa5]")


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    # 英文/数字按词
    en_tokens = re.findall(r"[a-z0-9]+", text)
    # 中文按 bigram
    cn_chars = re.findall(r"[\u4e00-\u9fa5]+", text)
    cn_tokens: list[str] = []
    for run in cn_chars:
        if len(run) == 1:
            cn_tokens.append(run)
        else:
            cn_tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return en_tokens + cn_tokens


@lru_cache(maxsize=1)
def _local_index():
    """按 ## 标题切分；每个标题下的内容是一个 chunk。
    返回 (chunks, df, avgdl)。"""
    from collections import Counter

    chunks = []
    df: Counter = Counter()
    for path_str in get_knowledge_files():
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")

        # 按 ## 或 ### 标题切分（每个 Q&A / 每个政策小节独立成 chunk）
        if re.search(r"^##{1,3}\s", text, re.MULTILINE):
            blocks = _split_by_heading(text)
        else:
            blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]

        for block in blocks:
            block = block.strip()
            if len(block) < 15:
                continue
            tokens = _tokenize(block)
            if not tokens:
                continue
            chunks.append({
                "file_name": path.name,
                "text": block,
                "tokens": Counter(tokens),
            })
            for t in set(tokens):
                df[t] += 1

    avgdl = sum(len(c["tokens"]) for c in chunks) / max(len(chunks), 1)
    return chunks, df, avgdl


def _split_by_heading(text: str) -> list[str]:
    """按 ## 或 ### 标题切分，每个标题块独立成 chunk；丢掉文件级 # 标题。"""
    parts = re.split(r"(?=^#{2,3}\s)", text, flags=re.MULTILINE)
    out = []
    for p in parts:
        p = p.strip()
        if re.match(r"^#{2,3}\s", p):
            out.append(p)
    return out


# 产品名 → 别名，用于 query 里提到产品时给 chunk 加权
PRODUCT_ALIASES = {
    "air100": ["air100", "air 100", "耳机 air", "蓝牙耳机", "tws"],
    "studio200": ["studio200", "studio 200", "头戴", "耳麦"],
    "watch30": ["watch30", "watch 30", "手表", "智能手表"],
    "key87": ["key87", "key 87", "键盘", "机械键盘"],
    "gaan65": ["gaan65", "65w", "充电器", "氮化镓"],
}


def _detect_products(query: str) -> set[str]:
    q = query.lower()
    hit = set()
    for canon, aliases in PRODUCT_ALIASES.items():
        if any(a in q for a in aliases):
            hit.add(canon)
    return hit


def _bm25_score(query: str, chunk: dict, df: Counter, avgdl: float, k1=1.5, b=0.75) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    n = sum(df.values()) or 1
    score = 0.0
    dl = sum(chunk["tokens"].values()) or 1
    for qt in q_tokens:
        tf = chunk["tokens"].get(qt, 0)
        if tf == 0:
            continue
        idf = math.log(1 + (n - df[qt] + 0.5) / (df[qt] + 0.5))
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score


def _local_retrieve(message: str, top_k: int = 3) -> dict:
    chunks, df, avgdl = _local_index()
    query_products = _detect_products(message)

    scored = []
    for c in chunks:
        s = _bm25_score(message, c, df, avgdl)
        # 产品名命中加权：query 提到某产品，chunk 也提到 → ×1.6
        if query_products:
            blob = c["text"].lower()
            for p in query_products:
                aliases = PRODUCT_ALIASES[p]
                if any(a in blob for a in aliases):
                    s *= 1.6
                    break
        scored.append((s, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    scored = scored[:top_k]

    sources = []
    # 分数阈值：实测好匹配 55+，弱噪声 7-16，25 分以下视为未命中走人工
    if not scored or scored[0][0] < 25:
        return {
            "answer": "",  # 由 agent_router 按情绪匹配兜底话术
            "sources": [],
            "matched": False,
        }

    best_score, best_chunk = scored[0]
    # 把 top 3 作为引用，答案取 top1 的段落（去掉 markdown 标题符号）
    for s, c in scored:
        sources.append({
            "file_name": c["file_name"],
            "file_path": c["file_name"],
            "text": c["text"],
            "score": round(s, 3),
        })

    answer_lines = [
        f"根据知识库（{best_chunk['file_name']}）：",
        "",
        re.sub(r"^#+\s*", "", best_chunk["text"]).strip(),
    ]
    return {
        "answer": "\n".join(answer_lines),
        "sources": sources,
        "matched": True,
        "score": round(best_score, 3),
    }


# ---------------------------------------------------------------------------
# 对外统一入口
# ---------------------------------------------------------------------------
def answer_with_rag(message: str) -> dict:
    if _use_openai_llm():
        response = _get_openai_query_engine().query(message)
        sources = [
            {
                "file_name": node.metadata.get("file_name"),
                "file_path": node.metadata.get("file_path"),
                "text": node.text,
            }
            for node in response.source_nodes
        ]
        return {"answer": str(response), "sources": sources, "matched": True}

    return _local_retrieve(message)


def clear_query_engine_cache() -> None:
    _get_openai_query_engine.cache_clear()
    _local_index.cache_clear()
