# AI Structured Output Contracts

- Define bounded, typed output schemas that the provider can express reliably. Prefer explicit nested models, primitives, and enums over arbitrary `object` or free-form dictionary fields.
- Derive allowed values and output constraints from backend-owned sources—such as domain enums, Django choices, registries, or typed draft models—rather than duplicating a second schema in prompts.
- Keep model-output contracts separate from persisted models when generation needs a draft or review step.
