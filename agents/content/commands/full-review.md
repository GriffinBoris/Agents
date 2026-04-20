---
kind: command
role: opencode-command
description: Perform a comprehensive scoped review of code or guidance in the repository
---

Perform a comprehensive scoped review.

Scope comes from `$ARGUMENTS`.
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
- discover nearby named examples under `agents/guidance/**/examples/`
- use both diff context and example frontmatter to decide applicability
- check frontmatter fields when present, including filename, title, `description`, `tags`, and `applies_to`
- treat examples as applicable when the scope touches the same concern, even if the stack match is broad and the filename is the strongest signal
- do not stop at one matching example if multiple examples cover different concerns in the same scope, such as structure, routing, models, serializers, views, services, tests, forms, or state management
- if an example appears plausibly relevant, include it in the review map and mark it `matched`, `partially_matched`, `not_matched`, or `not_applicable`
- if a reviewed example produced no findings, keep it in the review map with `matched` or `not_applicable`; do not silently omit it
- prefer over-including plausible examples in the review map rather than under-including them; if unsure, include the example and explain the uncertainty in the applicability reason

Build the review map in this order:
1. Determine the concrete concerns in scope from the diff or requested review area.
2. Load the mandatory guidance files for the active stack.
3. Find candidate examples by path, filename, title, tags, and `applies_to` frontmatter.
4. Cross-reference each candidate example against the in-scope concerns, touched files, and changed behaviors.
5. Record why each reviewed example does or does not apply before finalizing findings.

When examples are applicable, check them explicitly against the scope rather than vaguely citing them:
- identify the concern each example teaches, such as layout, boundaries, routing, API shape, persistence, validation, testing, loading states, dialogs, or shell structure
- compare each in-scope area to the examples for the same concern, not just to one broad stack example
- when a single change touches multiple concerns, include all matching examples in the review map rather than choosing only the closest filename
- when an example is the clearest standard for one part of the scope, say so explicitly in the review map or findings

Use the modular guidance tree as the source of truth:
- `agents/guidance/guidance.md`
- relevant language, framework, and project guidance
- nearby named examples under `agents/guidance/**/examples/`
- `agents/reference/review/architecture-rubric.md`

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
