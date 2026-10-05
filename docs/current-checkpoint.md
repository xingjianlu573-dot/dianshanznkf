# Current Checkpoint

Last updated: 2026-06-18 (Australia/Sydney)

## Context Risk

**MEDIUM**

The repository context is understood, but the thread has accumulated project
recovery, Git/PR history, and branch-name ambiguity. Use this file to resume
without relying on chat history.

## Project

- Repository: `https://github.com/lingyun1010/eCommenceRAG.git`
- Local path: `/Users/lingyunzhao/Documents/RAG with llama-index/etsy-ai-agent`
- Current branch: `chore/update-agent-files`
- Working tree was clean when this checkpoint was created.
- Project goal: build an explainable ecommerce support agent that routes live
  operational facts to commerce tools, product/policy knowledge to LlamaIndex
  RAG, and high-risk requests to human escalation.

## Current Implementation

- FastAPI backend with `/health`, `/chat`, `/knowledge/generate`, and knowledge
  ZIP download endpoints.
- OpenAI tool-calling router with `AGENT_ROUTER=rules` fallback.
- LlamaIndex RAG over `products.md`, `policy.md`, and `faq.md`.
- Vanilla HTML/CSS/JavaScript frontend.
- Commerce data and human escalation are mocks.
- Store URL extraction uses Shopify JSON, JSON-LD, links, and policy pages.
- Default checked-in knowledge describes MÙRA products and policies.

## Important Decisions

- Do not route every question to RAG.
- Changing business facts must come from tools/APIs.
- Missing knowledge must remain `Not specified`; do not invent facts.
- Preserve RAG source metadata and deterministic routing fallback.
- Keep V1 practical and portfolio-explainable; LangChain/LangGraph are deferred.
- Generated knowledge remains split into `products.md`, `policy.md`, and
  `faq.md`.

## Git And PR Caveat

Branch names and GitHub PR numbers do not align cleanly:

- GitHub PR #7 merged branch `pr-6`.
- GitHub PR #8 merged the earlier `pr-7` work.
- The current `pr-7` branch contains commit `c877862`, used for later tolerant
  store-fetch work and locally aliased as `pr-9`.

Always identify work by both PR number and commit/branch.

## Current Gap

The checked-out branch does not contain commit `c877862`. Therefore it does
not currently:

- normalize scheme-less store URLs to `https://`;
- return placeholder files plus a warning when store fetching fails;
- expose or display the knowledge-generation warning.

Those changes exist on local branch `pr-7` / `pr-9`.

## Constraints And Risks

- No real Etsy or Shopify integration yet.
- No real support-ticket handoff.
- No persistent vector store, authentication, rate limiting, CI, deployment
  configuration, or committed automated test suite.
- Store URL fetching requires SSRF protection before public deployment.
- RAG still requires OpenAI access even when deterministic routing is enabled.

## Next Step

No implementation task has been selected yet. Before editing, ask which work
should continue: tolerant store fetching/PR #9, real commerce integration, RAG
evaluation, deployment, or another requested task.

## Resume Procedure

1. Read `AGENTS.md`, this file, and `docs/CONTEXT.md`.
2. Run `git status --short --branch`.
3. Confirm the target branch/PR before changing code.
4. Inspect only files relevant to the selected task.
