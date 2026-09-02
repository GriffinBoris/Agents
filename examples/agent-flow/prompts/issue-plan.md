# Objective

Produce an implementation plan for the snapshotted GitHub issue using `context.md`. Do not modify the repository.

Map every issue acceptance criterion and every applicable guidance-matrix requirement to concrete implementation and verification work. Include exact files or symbols where evidence supports them. Preserve existing behavior unless the issue explicitly changes it.

The plan must include:

- the intended behavior and explicit non-goals;
- ordered implementation steps;
- data, API, migration, compatibility, security, and rollback considerations where applicable;
- tests at the appropriate unit, integration, and end-to-end boundaries;
- the repository-native commands that should be run;
- a traceability table from each acceptance criterion and guidance requirement to code and tests;
- uncertainties and the smallest question needed to resolve each one.

If a decision would materially affect the result and is not established by the issue or repository guidance, ask the Desktop parent before finalizing. Do not silently choose a product or architectural direction.

# Output

Return one actionable Markdown plan. It must be detailed enough that a fresh implementation worker can execute it without reconstructing the research.
