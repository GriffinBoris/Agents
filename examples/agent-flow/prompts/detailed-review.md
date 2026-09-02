# Objective

Produce one rigorous, evidence-backed review of the current diff. Do not modify the repository.

Delegate three disjoint reviews, then synthesize and deduplicate their results:

1. Guidance compliance: re-open every applicable source from `context.md` and verify each requirement against exact implementation or test evidence.
2. Issue acceptance and tests: trace every criterion through behavior and tests, including errors, edge cases, compatibility, integration gaps, and skipped or blocked checks.
3. Maintainability and safety: inspect architectural fit, unnecessary complexity, security, error handling, scope creep, documentation, and observability where relevant.

Ground every finding in an applicable source, acceptance criterion, or concrete failure mode. Include exact paths, symbols, commands, or URLs. Do not report unsupported style preferences. A pass requires positive evidence for every applicable requirement, not merely an absence of obvious defects.

If ambiguity prevents a defensible verdict, ask the Desktop parent and mark the result `blocked`.

# Output

Return one Markdown report with a clear verdict, prioritized findings, verified requirements, supporting evidence, and unresolved questions.
