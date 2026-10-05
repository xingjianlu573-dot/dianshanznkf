# Setup And Run Notes

Last verified: 2026-06-18 (Australia/Sydney)

These notes describe the current local MVP. Treat commands as repository
defaults and verify them against current code before changing infrastructure.

## Runtime Versions

- Project requirement: Python `>=3.10`.
- Recommended: Python 3.11.
- Verified interpreter: `venv/bin/python3.11` reports Python `3.11.15`.
- Warning: `venv/bin/python` currently reports Python `3.9.6`; the existing
  virtual environment is inconsistent and should be rebuilt.
- Frontend has no Node dependency or package manager.
- Node is only useful for optional JavaScript syntax checking. Node `v24.14.0`
  was available through the Codex bundled runtime during verification.

## Clean Installation

From the repository root:

```bash
python3.11 --version
python3.11 -m venv venv
source venv/bin/activate
python --version
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Confirm that `python --version` reports Python 3.11.x. Do not continue with
Python 3.9.

## Environment Variables

Create a local `.env` file:

```dotenv
OPENAI_API_KEY=your_openai_api_key
# Optional deterministic routing:
# AGENT_ROUTER=rules
```

`.env` is ignored by Git and must not be committed.

Router behaviour:

- `OPENAI_API_KEY` present and `AGENT_ROUTER` unset or `openai`: OpenAI tool
  router.
- `OPENAI_API_KEY` absent: deterministic rules router.
- `AGENT_ROUTER=rules`: deterministic router even when a key is present.

RAG still requires a valid OpenAI key because it uses OpenAI embeddings and
`gpt-4o-mini`.

## Run The Backend

```bash
source venv/bin/activate
uvicorn api:app --reload
```

- API: `http://127.0.0.1:8000`
- OpenAPI UI: `http://127.0.0.1:8000/docs`

Optional CLI:

```bash
source venv/bin/activate
python app.py
```

## Run The Frontend

In another terminal:

```bash
cd frontend
python3 -m http.server 5173
```

Open `http://127.0.0.1:5173`.

The frontend defaults to `http://127.0.0.1:8000`. CORS currently permits only
`http://localhost:5173` and `http://127.0.0.1:5173`.

## Knowledge And Runtime Files

Default RAG knowledge:

```text
data/products.md
data/policy.md
data/faq.md
```

After successful store generation, RAG prioritises:

```text
runtime_knowledge/current/products.md
runtime_knowledge/current/policy.md
runtime_knowledge/current/faq.md
```

Download artifacts are written under `generated_knowledge/`. Both runtime
directories are ignored by Git.

The commerce data in `commerce_api.py` is local mock data. It is not connected
to Etsy or Shopify.

## Minimum Test Commands

Python compilation:

```bash
python -m py_compile \
  app.py api.py agent_router.py openai_tool_router.py \
  commerce_api.py rag_service.py store_knowledge.py
```

Frontend syntax, if Node is available:

```bash
node --check frontend/app.js
```

Deterministic route smoke test:

```bash
AGENT_ROUTER=rules python - <<'PY'
from agent_router import answer_message

result = answer_message("how many products do you have?", platform="etsy")
assert result["intent"] == "PRODUCT_COUNT"
assert result["tool_result"]["active_listing_count"] == 12
print("rule router smoke test ok")
PY
```

No committed `pytest` suite currently exists.

## Example API Requests

Health:

```bash
curl http://127.0.0.1:8000/health
```

Listing count:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"how many products do you have?","platform":"etsy"}'
```

Order status:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"where is order #1001?","platform":"etsy"}'
```

RAG policy question:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"can I return my purchase?","platform":"etsy"}'
```

Escalation:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"this is unacceptable, I need a human","platform":"etsy"}'
```

Generate store knowledge:

```bash
curl -X POST http://127.0.0.1:8000/knowledge/generate \
  -H "Content-Type: application/json" \
  -d '{"store_url":"https://example-store.com","output_format":"markdown"}'
```

Download the ZIP using the response's `download_url`:

```bash
curl -OJ http://127.0.0.1:8000/knowledge/download/<artifact-id>
```

## Common Errors And Fixes

### Python 3.9 Union-Type Error

```text
TypeError: unsupported operand type(s) for |: 'ModelMetaclass' and 'NoneType'
```

Cause: newer LlamaIndex dependency code running under Python 3.9.

Fix: rebuild the virtual environment with Python 3.11 and verify the activated
interpreter.

### NLTK SSL Errors

```text
CERTIFICATE_VERIFY_FAILED
Error loading stopwords
Error loading punkt_tab
```

Current code uses `TokenTextSplitter` and should not download these resources.
Confirm that the latest `rag_service.py` is running.

### Pydantic Warning

```text
UnsupportedFieldAttributeWarning: 'validate_default' ...
```

This warning was observed from the dependency stack and did not block the
verified smoke test.

### Tools Work But RAG Fails

Likely cause: the rules router can run without OpenAI, but RAG requires OpenAI
embeddings and LLM access.

Fix: verify `OPENAI_API_KEY`, `.env` loading, and outbound network access.

### Store Generation Returns Placeholder Files

Likely cause: the target store is JavaScript-rendered, bot-protected,
unavailable, or not parseable by the deterministic extractor.

Inspect the response `warning` field and generated files. Do not present
`Not specified` values as real facts.

### Store Generation Returns 400

PR #9 contains tolerant fetch fallback and is not yet merged into `main` as of
2026-06-18. On older `main`, inspect the response JSON `detail`. Empty or
invalid URLs should still return 400.

### Browser CORS Error

Serve the frontend on port `5173`, or intentionally update the CORS allowlist in
`api.py`.

## Local And Mock Limitations

- Listing and order tools are in-memory mocks.
- Human escalation does not create a real support ticket.
- Vector storage is in process and not persistent.
- Generated knowledge is local filesystem state.
- There is no authentication, rate limiting, CI, deployment configuration, or
  committed automated test suite.
- Store URL fetching lacks SSRF protection and must not be exposed publicly
  before that is fixed.

## TBD / Needs Verification

- Production hosting target.
- First real provider integration: Etsy or Shopify.
- Required Etsy/Shopify credentials and permission scopes.
- Whether a Node version should be standardised if the frontend later gains a
  build system.
- Whether LangGraph will be explored in V2.
