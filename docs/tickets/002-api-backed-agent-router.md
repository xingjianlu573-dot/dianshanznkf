# Ticket 002: API-Backed Agent Router MVP

## Status

Implemented

## Goal

Move product-count and order-status questions away from local document parsing and into mock commerce tools that represent Etsy or Shopify APIs.

## Scope

- Add a FastAPI `/chat` endpoint.
- Add an intent router with `PRODUCT_COUNT`, `ORDER_STATUS`, `RAG`, and `ESCALATE`.
- Add mock commerce API tools for listing count and order lookup.
- Keep LlamaIndex RAG for policy, FAQ, and product recommendation questions.
- Keep human escalation as a clear handoff response.

## Acceptance Criteria

- `how many products do you have?` returns a listing count from the commerce tool.
- `where is order #1001?` returns order status from the commerce tool.
- `can I return my purchase?` is routed to RAG.
- Angry or refund-dispute messages are routed to escalation.
- The CLI can still be used for local manual testing.

## Future Work

- Replace mock commerce data with real Etsy Listings API or Shopify Admin API calls.
- Replace the rule-based router with OpenAI tool calling once the API contracts are stable.
- Add a React chat UI for demo scenarios.
