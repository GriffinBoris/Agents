---
description: Perform a comprehensive scoped review of code or guidance in the repository.
input: [scope]
---

Perform a comprehensive scoped review.

Scope comes from `${input:scope}`.
If no scope is provided, review the current branch changes.

Supported scopes include:
- current branch diff
- selected files
- a folder, app, feature, route, or module
- a concept or workflow across multiple files
- a guidance package, examples folder, or selected guidance files

Keep this command specific to full code review.
Do not turn it into a generic command chooser or a language-by-language checklist.
Treat it as one integrated review of the in-scope material against:
- the relevant guidance rules
- the nearby named examples that teach the expected shapes
- the closest established implementation patterns already in the repo

Systematically work through the scope:
- inspect every in-scope file or changed area
- identify which guidance and example sources apply to that scope
- build an explicit review map for both guidance files and named examples before writing findings
- compare each in-scope area to both the rules and the examples
- compare structure and organization to the closest real repo patterns
- list every verifiable in-scope deviation, not just a short curated subset

Guidance and example applicability is required, not optional:
- start with the owning skill's example-selection routing, then discover additional candidates under its `references/examples/` directory only when the scope exposes an uncovered concern
- use the diff or requested scope, filename, H1 title, Scenario section, and heading list to decide applicability
- for long examples, inspect the Scenario section and headings first, then read only the sections relevant to the in-scope concern
- treat an example as applicable when it teaches the same concrete concern, not merely because it uses the same broad stack
- do not stop at one matching example if multiple examples cover different concerns in the same scope, such as structure, routing, models, serializers, views, services, tests, forms, or state management
- include each reviewed example in the review map and mark it `matched`, `partially_matched`, `not_matched`, or `not_applicable`
- if a reviewed example produced no findings, keep it in the review map with `matched` or `not_applicable`; do not silently omit it
- do not load or list examples solely because they are in the active stack; record uncertainty only when a concrete in-scope concern makes the example plausibly relevant

Build the review map in this order:
1. Determine the concrete concerns in scope from the diff or requested review area.
2. Load the mandatory guidance files for the active stack.
3. Find candidate examples through the owning skill's routing, then compare their filename, H1 title, Scenario section, and headings to the in-scope concerns.
4. Cross-reference each candidate example against the in-scope concerns, touched files, and changed behaviors.
5. Record why each reviewed example does or does not apply before finalizing findings.

When examples are applicable, check them explicitly against the scope rather than vaguely citing them:
- identify the concern each example teaches, such as layout, boundaries, routing, API shape, persistence, validation, testing, loading states, dialogs, or shell structure
- compare each in-scope area to the examples for the same concern, not just to one broad stack example
- when a single change touches multiple concerns, include all matching examples in the review map rather than choosing only the closest filename
- when an example is the clearest standard for one part of the scope, say so explicitly in the review map or findings

Use the modular guidance tree as the source of truth:
- `.apm/instructions/engineering-baseline.instructions.md`
- relevant language, framework, and project guidance
- matching examples under the relevant guidance skill's `references/examples/` directory
- `.apm/skills/review-workflows/references/architecture-rubric.md`

Use these skills as relevant:
- `architecture-audit`
- `backend-homogeneity-audit`
- `frontend-homogeneity-audit`
- `context-gatherer`

Use `context-gatherer` first when the scope is broad, unfamiliar, or concept-based.
Use `architecture-audit` for file, folder, module, and code-structure review.
Use the backend or frontend homogeneity audits when those stacks are in scope.

In the final review:
- state the review scope clearly
- list all guidance and example sources reviewed
- include a guidance and example review map with applicability verdicts and a short reason for each reviewed example
- list all verifiable guidance deviations within scope, or explicitly say none were found
- make clear that findings come from systematically comparing the scope to guidance, examples, and real patterns
- report verification status and blind spots
