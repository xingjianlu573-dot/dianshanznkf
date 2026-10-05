# Technical Decision Log

This log records architecture decisions visible in the current code or project
documentation. Dates use 2026-06-18 when the exact original decision date is
not recorded.

## 2026-06-18 — Use FastAPI For The Backend

Decision:
Use FastAPI as the HTTP API framework, with Uvicorn for local serving.

Reason:
The project needs a small typed API for chat, knowledge generation, health
checks, and artifact downloads. FastAPI provides Pydantic validation, generated
API documentation, and a direct path from Python agent logic to a frontend.

Trade-offs:
The current synchronous handlers and URL fetching are simple but can block
workers. Production use will require security, authentication, rate limiting,
and deployment configuration.

Status:
Implemented.

## 2026-06-18 — Separate Operational State From RAG Knowledge

Decision:
Route listing count, order status, tracking, and other changing business state
through commerce tools/APIs. Use RAG for product education, policies, FAQs, and
recommendations.

Reason:
Operational facts change frequently and need authoritative API responses.
Explanation-heavy store knowledge is better suited to semantic retrieval.

Trade-offs:
The system has multiple execution paths and needs routing tests. The current
commerce implementation is mock data, so it demonstrates the contract but not
production accuracy.

Status:
Implemented as an MVP; real Etsy/Shopify adapters are deferred.

## 2026-06-18 — Use OpenAI Tool Calling With A Rules Fallback

Decision:
Use OpenAI Chat Completions tool calling to select commerce and escalation
tools, while preserving `AGENT_ROUTER=rules`.

Reason:
Tool schemas make operational actions explicit and auditable. The deterministic
fallback supports local development, predictable demos, and testing without an
extra router model call.

Trade-offs:
Tool routing depends on OpenAI when enabled. The current implementation handles
only the first returned tool call and lacks committed mocked tool-calling tests.

Status:
Implemented.

## 2026-06-18 — Use LlamaIndex For RAG

Decision:
Use LlamaIndex for document loading, token splitting, OpenAI embeddings,
in-memory vector indexing, retrieval, source nodes, and answer synthesis.

Reason:
The project started as a LlamaIndex RAG application, and the framework provides
the required RAG primitives with little orchestration code.

Trade-offs:
The vector index is rebuilt in process and is not persisted. OpenAI is required
for embeddings and answer generation. Strict grounding and evaluation still
need to be implemented.

Status:
Implemented.

## 2026-06-18 — Defer LangChain And LangGraph In V1

Decision:
Do not introduce LangChain or LangGraph into the current V1.

Reason:
The current workflow has a small number of routes and tools that can be
explained with direct Python orchestration. A graph framework would add
complexity before durable state, retries, approvals, or multi-step workflows
are required.

Trade-offs:
Direct orchestration may become harder to maintain if the agent grows into a
stateful multi-step workflow. LangGraph remains a possible V2 option.

Status:
Deferred. Neither dependency is present in the repository.

## 2026-06-18 — Keep The Frontend Dependency-Free For The MVP

Decision:
Implement the frontend with vanilla HTML, CSS, and JavaScript.

Reason:
The UI currently needs only store setup, chat, demo prompts, intent display,
tool results, and RAG sources. A build system or framework is not necessary for
the MVP.

Trade-offs:
State management and component reuse will become less convenient if the UI
grows. React or another framework may be justified later.

Status:
Implemented.

## 2026-06-18 — Generate Three Store Knowledge Files

Decision:
Generate `products.md`, `policy.md`, and `faq.md`, package them as a ZIP, and
make them the runtime RAG knowledge set.

Reason:
Separate files preserve clear knowledge ownership, match the store2knowledge
workflow, improve source attribution, and are easier to inspect or replace.

Trade-offs:
The deterministic extractor cannot reliably handle every dynamic or
bot-protected store. Unknown values must remain explicit placeholders.

Status:
Implemented. Fetch-tolerance improvements are currently in open PR #9.

## 2026-06-18 — Use TokenTextSplitter Instead Of Runtime NLTK Downloads

Decision:
Use LlamaIndex `TokenTextSplitter` with a 256-token chunk size and 20-token
overlap.

Reason:
Previous NLTK-based chunking attempted to download resources and failed on
local SSL certificate verification.

Trade-offs:
Token splitting does not use sentence boundaries. Retrieval quality should be
evaluated before changing chunk strategy.

Status:
Implemented.

## 2026-06-18 — Prefer MVP-First, Portfolio-Explainable Changes

Decision:
Prioritise a working, demonstrable vertical slice over broad framework
adoption or production-scale infrastructure.

Reason:
The project is an AI Engineer portfolio project and should clearly demonstrate
RAG, tool calling, data boundaries, fallbacks, and human escalation.

Trade-offs:
Authentication, persistence, deployment, CI, provider integrations, and
evaluation remain unfinished.

Status:
Active project convention.
