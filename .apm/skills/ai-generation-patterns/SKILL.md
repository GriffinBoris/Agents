---
name: ai-generation-patterns
description: Design, implement, or review backend AI or LLM generation workflows, including provider configuration, structured output contracts, validation, persistence, and tests.
---

# AI Generation Patterns

## Provider Boundary

- Keep provider credentials and provider configuration in backend-owned settings or secret stores. Never expose them to browser code.
- Put provider calls behind a focused backend service boundary. Keep views, serializers, and UI components responsible for request handling and presentation rather than provider orchestration.
- Treat provider output as untrusted input. Do not persist, execute, or publish it until it passes the same domain validation as human-authored input.

## Structured Output Contracts

- Define bounded, typed output schemas that the provider can express reliably. Prefer explicit nested models, primitives, and enums over arbitrary `object` or free-form dictionary fields.
- Derive allowed values and output constraints from backend-owned sources—such as domain enums, Django choices, registries, or typed draft models—rather than duplicating a second schema in prompts.
- Keep model-output contracts separate from persisted models when generation needs a draft or review step.

## Validation And Persistence

- Validate every generated draft at the service boundary before persistence. Reject empty output, unsupported types, invalid parent references, invalid overrides, duplicate keys, and cross-scope relationships.
- Persist only a complete, validated result. Do not save partial or best-effort generated records merely because a provider returned some usable fields.
- Add focused tests for valid output and representative invalid provider output, including unknown enum values, malformed nested data, invalid references, and duplicate identifiers.
