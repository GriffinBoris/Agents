---
name: ai-generation-patterns
description: Design, implement, or review backend AI or LLM generation workflows, including provider configuration, structured output contracts, validation, persistence, and tests.
---

# AI Generation Guidance

## Scope

- Apply backend-owned provider boundaries, typed generation contracts, validation, persistence, and testing rules to AI or LLM generation workflows.
- Keep provider- and product-specific configuration in the consuming repository's `project-architecture` skill or backend settings.
- Apply `python-conventions` and `django-patterns` alongside this skill when their scopes affect the implementation.

## Workflow

1. Inspect the repository's existing provider services, domain contracts, persistence flow, and tests.
2. Identify the affected concerns and read every matching reference below.
3. Define the provider boundary and output contract before implementing persistence.
4. Treat generated output as untrusted input and validate it at the service boundary.
5. Test valid output and representative invalid provider responses.

## Reference Selection

| Work being performed | Read |
| --- | --- |
| Provider credentials, configuration, calls, backend ownership, or trust boundaries | [provider-boundary.md](references/provider-boundary.md) |
| Typed schemas, enums, allowed values, draft models, or structured provider responses | [structured-output-contracts.md](references/structured-output-contracts.md) |
| Generated-data validation, persistence, invalid output, or generation tests | [validation-and-persistence.md](references/validation-and-persistence.md) |

Read every reference whose row matches the task. Most end-to-end generation workflows require all three.

## Example Selection

No packaged AI-generation examples currently exist. Inspect the closest repository-owned provider service, generated-output contract, persistence workflow, and tests before introducing a new pattern.

## Completion Checklist

- Provider secrets and orchestration remain backend-owned.
- Generated output uses a bounded, typed contract.
- Generated data is validated before persistence, execution, or publication.
- Persistence is complete and atomic from the domain workflow's perspective.
- Tests cover valid output and representative invalid provider responses.
