# Ticket 003: OpenAI Tool Calling Router

## Status

Implemented

## Goal

Upgrade the MVP router from keyword-only routing to OpenAI tool calling while keeping the deterministic rule-based router available for local testing.

## Scope

- Define OpenAI tool schemas for listing count, order lookup, and human escalation.
- Let the model choose when to call a commerce or escalation tool.
- Route non-tool questions to the existing LlamaIndex RAG path.
- Keep `AGENT_ROUTER=rules` as a no-network fallback.

## Acceptance Criteria

- Product-count questions can call `get_listing_count`.
- Order-status questions can call `get_order`.
- Angry or refund-dispute messages can call `escalate_to_human`.
- Policy, FAQ, and recommendation questions can still fall back to RAG.
- Local tests can still force rule-based routing without an OpenAI API call.

## Notes

This is the first step from "router + tools" toward a true tool-augmented AI agent. The commerce tools still use mock data, but the integration shape now mirrors Etsy or Shopify API calls.
