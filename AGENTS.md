# Codex Working Instructions

This file contains persistent instructions for Codex agents working in this
repository. Do not assume access to previous Codex threads or chat history.

## Start Here

Before making changes:

1. Run `git status --short --branch`.
2. Read `docs/CONTEXT.md`.
3. Read `README.md`.
4. Read `docs/setup-notes.md` when running or testing the project.
5. Read `docs/decision-log.md` when changing architecture.
6. Inspect only the source files relevant to the current task.

Treat repository files and current Git state as the source of truth. If a
document conflicts with code, verify the code and update the document.

## Project Goal

Build an explainable ecommerce customer-support agent that routes each request
to the correct source of truth:

- Live or changing business state, such as listing counts and order tracking,
  goes through commerce tools/APIs.
- Product education, policies, FAQs, and recommendations go through grounded
  RAG over store knowledge files.
- High-risk, angry, chargeback, refund-dispute, or human-review requests go
  through an escalation path.

The current MVP uses mock commerce data. Do not describe it as a production
Etsy or Shopify integration until real provider APIs are implemented.

## Current Stack

- Python 3.10+; use Python 3.11 locally.
- FastAPI and Uvicorn backend.
- OpenAI tool calling with a deterministic rules fallback.
- LlamaIndex RAG with OpenAI embeddings and `gpt-4o-mini`.
- Dependency-free HTML, CSS, and JavaScript frontend.
- Markdown knowledge in `data/` or generated under `runtime_knowledge/`.

LangChain and LangGraph are not currently implemented. Mention them only as
possible future V2 options unless the repository changes.

## Coding Rules

- Keep changes small, focused, and testable.
- Follow existing Python and vanilla frontend patterns.
- Do not perform unrelated refactors.
- Do not invent product, policy, inventory, order, refund, or tracking facts.
- Preserve structured API response contracts unless a task explicitly changes
  them.
- Preserve `AGENT_ROUTER=rules` as a deterministic development fallback.
- Preserve RAG source metadata in `/chat` responses.
- Keep secrets out of Git. Never commit `.env`, credentials, generated ZIPs,
  or runtime knowledge artifacts.
- Validate external input carefully. Store URL fetching currently needs SSRF
  protection before public deployment.
- Do not silently turn placeholder knowledge into asserted facts.

## Context Management

- Do not assume previous Codex thread context unless it is written in the repo.
- Do not read the whole repo unnecessarily.
- Start with `docs/CONTEXT.md`, then inspect only files required for the task.
- Re-check branch and working-tree state before editing or committing.
- Preserve user changes and unrelated uncommitted work.
- When context risk becomes high, suggest a checkpoint and update
  `docs/CONTEXT.md`.

## Testing Expectations

Run the smallest meaningful checks for every change:

- Python syntax:
  `python -m py_compile app.py api.py agent_router.py openai_tool_router.py commerce_api.py rag_service.py store_knowledge.py`
- Frontend syntax when JavaScript changes:
  `node --check frontend/app.js`
- Deterministic router smoke test:

```bash
AGENT_ROUTER=rules python - <<'PY'
from agent_router import answer_message

result = answer_message("how many products do you have?", platform="etsy")
assert result["intent"] == "PRODUCT_COUNT"
print("rule router smoke test ok")
PY
```

No committed automated test suite currently exists. Add focused tests when
changing routing, tools, ingestion, API contracts, or RAG behaviour. Mock
OpenAI and external network calls.

If a test cannot run, state the exact reason. Do not present an unrun test as
passing.

## Documentation Expectations

- Update `docs/CONTEXT.md` after meaningful milestones, changed architecture,
  new integrations, changed commands, or resolved blockers.
- Add important technical decisions to `docs/decision-log.md`.
- Update `docs/setup-notes.md` when dependencies, environment variables, run
  commands, or troubleshooting steps change.
- Keep README public-facing and concise; keep detailed handoff information in
  `docs/CONTEXT.md`.
- After each task, summarise:
  - files changed;
  - commands/tests run;
  - results;
  - how the user can verify the change.

## Constraints That Must Not Break

- Do not remove existing working MVP behaviour without explicit approval.
- RAG answers must be grounded in knowledge files.
- Live/order/refund/business-state queries must use tools/APIs, not RAG
  hallucination.
- Human-review cases must retain an escalation route.
- Store knowledge remains split into `products.md`, `policy.md`, and `faq.md`.
- Missing facts must remain `Not specified` or produce an explicit
  insufficient-evidence response.
- The frontend must continue to support the documented local API flow.
- Keep implementation practical and portfolio-explainable; avoid unnecessary
  framework complexity.
