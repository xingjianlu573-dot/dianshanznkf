# Ticket 005: Store URL to Markdown Knowledge Flow

## Status

Implemented

## Goal

Turn the store2knowledge workflow into a reusable Python utility inside this repo and expose it through the local UI.

## Scope

- Add `store_knowledge.py` as an importable utility module.
- Support `generate_store_knowledge(store_url, output_format="markdown")`.
- Generate Markdown with Products, Policy, and FAQ sections.
- Add `POST /knowledge/generate`.
- Add `GET /knowledge/download/{artifact_id}`.
- Save generated Markdown as a runtime artifact and refresh the RAG cache.
- Add a frontend setup step: enter store URL, generate Markdown, download it, then enter chat.

## Acceptance Criteria

- A public store URL can be submitted from the UI.
- The backend returns Markdown by default.
- The UI shows a completion message and download link.
- The user can enter the chat flow after knowledge generation.
- The Python utility can be imported directly by backend code or future scripts.

## Future Work

- Add richer extraction for JavaScript-rendered stores.
- Add first-class Etsy and Shopify API ingestion.
- Add PDF and plain text export formats after Markdown is stable.
