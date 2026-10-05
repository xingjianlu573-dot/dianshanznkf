# Project Brief

Status labels used in this document:

- **Implemented**: verified in the current repository.
- **Planned**: included in the project plan but not verified as implemented.
- **TBD / needs verification**: not settled by the project plan or repository.

## 1. Project Summary

The Ecommerce RAG Agent is an AI-assisted customer-support system for an
Etsy-like or Shopify-like store. It combines retrieval-augmented generation
(RAG), structured tool calling, and an escalation route so that each customer
request is handled by an appropriate source of truth.

The MVP is intended to demonstrate a practical support workflow rather than a
general-purpose chatbot:

- Product education, policies, FAQs, and recommendations use grounded RAG.
- Listing counts, order status, and tracking use commerce tools.
- Angry, disputed, high-risk, or explicitly human-directed requests use an
  escalation path.

The current repository implements this as a local portfolio MVP with mock
commerce data. It is not yet a production Etsy or Shopify integration.

## 2. Business Scenario

Small ecommerce teams repeatedly answer questions about products, shipping,
returns, orders, and refunds. The information required to answer those
questions comes from different systems:

- Product descriptions and store policies are relatively stable,
  explanation-heavy knowledge.
- Inventory, listing counts, order status, and tracking are changing
  operational facts.
- Refund disputes, chargebacks, and frustrated customers may require human
  judgement.

A single generative model should not invent answers across all three
categories. This project explores a safer support pattern in which an agent
routes requests to curated knowledge, commerce tools, or a human handoff.

## 3. Target Users

- **Ecommerce store owners** who want a support assistant for common customer
  questions.
- **Customer-support operators** who need repetitive questions handled while
  retaining a human-review path.
- **Store customers** asking about products, policies, listings, or orders.
- **Developers and AI agents** maintaining or extending the implementation.
- **Recruiters and technical reviewers** evaluating the project as an AI
  engineering portfolio example.

## 4. User Problems

- Customers wait for answers to repetitive product and policy questions.
- Static knowledge and changing commerce data are often mixed together,
  increasing the risk of inaccurate responses.
- A normal RAG chatbot cannot reliably answer live order or inventory
  questions.
- A tool-only system is not well suited to semantic questions or product
  explanations.
- High-risk conversations need a clear route to human review.
- Small merchants may not have the resources to build a full support platform.

## 5. MVP Scope

### Implemented

- A FastAPI chat endpoint with structured responses.
- OpenAI tool calling for commerce and escalation decisions.
- A deterministic rules-based router for local development and repeatable
  demos.
- LlamaIndex RAG over product, policy, and FAQ Markdown files.
- Mock listing-count and order-status tools representing future commerce APIs.
- A mock human-escalation result.
- A dependency-free browser chat UI with demo prompts.
- Store URL ingestion that generates `products.md`, `policy.md`, and `faq.md`.
- Downloadable ZIP artifacts for generated store knowledge.
- Source metadata returned with RAG responses.

### Planned

- Demonstrate at least these scenarios:
  - policy or product question through RAG;
  - order-status question through a tool;
  - a product/policy scenario that demonstrates correct source selection;
  - angry customer or refund dispute through escalation.
- Produce a short demo video and a clear architecture diagram.
- Replace or extend mocks with a real Etsy or Shopify integration when the MVP
  contracts are stable.

## 6. Out of Scope for MVP

The following should not be treated as MVP requirements unless the project
owner explicitly reprioritises them:

- A production-grade Etsy or Shopify integration.
- Payment, refund, cancellation, or fulfilment mutations.
- A real help-desk ticket, email, or staff notification integration.
- Conversation memory backed by Redis or another durable store.
- LangChain or LangGraph orchestration.
- A persistent vector database such as FAISS, Chroma, or a hosted service.
- A React/Vite/Tailwind rewrite of the current frontend.
- Multi-tenant merchant accounts and role-based access.
- Production authentication, rate limiting, monitoring, or compliance.
- Fully automated ingestion of every JavaScript-rendered or bot-protected
  ecommerce site.
- Production deployment before external URL fetching has suitable SSRF
  protection.

## 7. Core User Flows

### Product, policy, or FAQ question

1. A customer enters a question in the chat UI.
2. The backend sends the message to the configured router.
3. The request is classified as a knowledge request.
4. LlamaIndex retrieves relevant content from the active Markdown knowledge
   files.
5. The model produces an answer and the API returns source snippets.

### Listing count or order-status question

1. A customer asks for an operational fact.
2. The router selects a structured commerce tool.
3. The tool returns a listing count or order record.
4. The result is formatted into a customer-facing answer.
5. The API also exposes the structured tool result.

The current tools use in-memory mock data.

### Human handoff

1. A customer expresses anger, requests a human, or raises a dispute.
2. The router selects the escalation path.
3. The customer receives a safe handoff response.
4. The current implementation returns only a mock escalation record; no real
   support system is notified.

### Store knowledge setup

1. A user enters a public store URL.
2. The backend extracts available product and policy information.
3. Three Markdown files are generated and saved as the active runtime
   knowledge.
4. The RAG query-engine cache is cleared.
5. The user can download the files as a ZIP and enter the chat experience.

## 8. Success Criteria

The MVP is successful when:

- A product or policy question is answered through RAG with inspectable source
  content.
- A listing-count question is answered through the commerce-tool contract.
- A known order number returns mock status and tracking data through the order
  tool.
- A high-risk or human-review request follows the escalation route.
- The system preserves the boundary between changing operational facts and
  curated knowledge.
- Unknown facts are not invented and remain `Not specified` or produce an
  explicit insufficient-evidence response.
- The local frontend can exercise the documented flows through FastAPI.
- A new developer can install, run, and explain the MVP from repository
  documentation.

Production readiness, live provider integration, and automated quality
evaluation are not part of the current definition of done.

## 9. Portfolio / AI Engineer Value

This project demonstrates:

- **System design judgement**: selecting RAG, tools, or escalation according to
  the type and risk of a request.
- **Grounded generation**: returning source metadata instead of presenting the
  model as an unrestricted authority.
- **Tool calling**: defining JSON schemas, executing functions, and formatting
  structured results.
- **Deterministic fallback design**: preserving a rules router for testing and
  demos.
- **Data-boundary awareness**: separating curated knowledge from live business
  state.
- **End-to-end delivery**: connecting ingestion, retrieval, routing, APIs, and
  a usable frontend.
- **Trade-off awareness**: using mocks and simple in-process infrastructure
  deliberately while identifying what productionisation would require.

## 10. Open Questions

- **TBD / needs verification:** Will the first real provider integration be
  Etsy or Shopify?
- **TBD / needs verification:** Is the primary goal a portfolio demonstration,
  an internal MÙRA tool, or a path toward a production merchant product?
- **TBD / needs verification:** What deployment targets should be used for the
  frontend and backend?
- **TBD / needs verification:** What authentication and merchant-isolation
  model would be required for public use?
- **TBD / needs verification:** What RAG evaluation dataset and quality
  thresholds should define acceptable grounding?
- **TBD / needs verification:** Should low retrieval confidence trigger an
  explicit refusal, a human escalation, or both?
- **TBD / needs verification:** Are conversation memory and observability V2
  priorities?
- **TBD / needs verification:** Should a future frontend remain vanilla or
  adopt React only when UI complexity justifies it?
- **TBD / needs verification:** Should the tolerant store-fetch changes on the
  `pr-7` / `pr-9` branch be merged into the active branch?

## Source Basis

- Planned scope: [Project 2: Etsy AI Agent System](https://app.notion.com/p/37f606dee5e680e1a230d2d0e7cf74aa)
- Implemented state: current repository code, `README.md`, `AGENTS.md`, and
  supporting documents under `docs/`.

