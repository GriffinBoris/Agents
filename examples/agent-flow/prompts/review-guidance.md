# Objective

Perform a strict, evidence-backed one-to-one compliance review of the current diff against every relevant guidance source identified in `context.md`.

Re-open the actual governing documents and current diff; do not rely only on summaries. For each applicable guidance-matrix row, identify the exact implementation or test evidence that satisfies it. Report missing, partial, contradictory, or unverifiable compliance as a finding. Check nested `AGENTS.md` scope, repository conventions, architecture documentation, public API rules, and primary upstream framework/API documentation.

Do not make code changes. Do not report style preferences without an applicable source or concrete correctness/maintenance consequence. A pass requires positive evidence for every applicable requirement, not merely an absence of obvious problems.

If the guidance sources conflict or their applicability is ambiguous, send the smallest useful question to the Desktop parent and mark the verdict `blocked`.

# Output

Return only JSON conforming to the provided review schema. Put a source path/URL and section in every finding and verified-requirement entry.
