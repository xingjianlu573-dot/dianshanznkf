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
    return bool(os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# 生产路径：LlamaIndex + OpenAI Embeddings / LLM
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_openai_query_engine():
    from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
    from llama_index.core.node_parser import TokenTextSplitter
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.llms.openai import OpenAI

    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.llm = OpenAI(model="gpt-4o-mini")

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
    """返回 (chunks, df, avgdl)。chunks: list of {file, text, tokens: Counter}。"""
    from collections import Counter

    chunks = []
    df: Counter = Counter()
    for path_str in get_knowledge_files():
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")
        # 按段落切分（空行）
        for block in re.split(r"\n\s*\n", text):
            block = block.strip()
            if len(block) < 20:
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
    scored = sorted(
        ((_bm25_score(message, c, df, avgdl), c) for c in chunks),
        key=lambda x: x[0],
        reverse=True,
    )[:top_k]

    sources = []
    if not scored or scored[0][0] <= 0:
        return {
            "answer": "抱歉，我在客服知识库里没有找到完全匹配的答案。已为您生成工单，人工客服将跟进。",
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
