# Ticket 004: Minimal Chat UI

## Status

Implemented

## Goal

Add a small frontend demo surface for the ecommerce support agent so Project 2 can be demonstrated as a product flow, not only a backend API.

## Scope

- Create a dependency-free frontend under `frontend/`.
- Add chat input and message history.
- Add demo prompt buttons for the main MVP scenarios.
- Add an Etsy / Shopify platform selector.
- Show detected intent, tool results, and RAG sources.
- Keep styling minimal and operational.

## Acceptance Criteria

- The UI can call `POST /chat`.
- Product count, order lookup, RAG, and escalation scenarios can be triggered from visible demo prompts.
- Responses display the route/intent returned by the backend.
- Tool result and source details are inspectable without overwhelming the main chat.

## Future Work

- Add streaming responses.
- Add React or another UI framework if the interface grows beyond the MVP.
- Add deployment configuration for Vercel or similar hosting.
- Add richer source citation UI after RAG evaluation is stable.
