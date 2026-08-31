---
name: ste-writing
description: Write, rewrite, or review technical prose in clear, controlled English. Use for READMEs, documentation, runbooks, pull-request descriptions, release notes, comments, error messages, tool descriptions, and agent prompts when asked for plain language, Simplified Technical English, or less "AI slop"; do not apply its prose rules to source code, identifiers, commands, or quoted literals.
---

# Simplified Technical Writing Guidance

## Scope

- Apply a consistent plain-language system to technical prose without changing its facts or scope.
- Use `flavored` mode by default so ordinary engineering writing stays natural.
- Use `strict` mode for procedures, runbooks, safety text, and terse user-facing messages that benefit from controlled language.
- Do not use this skill for marketing copy, essays, or other writing whose voice is part of the requirement.

## Workflow

1. Identify whether the task is to write, rewrite, or review prose.
2. Select `flavored` or `strict` mode from the artifact and the user's request.
3. Read every reference whose row matches the task.
4. Preserve the source's meaning while applying the selected rules.
5. Perform one focused review pass and return only the requested artifact or review.

## Reference Selection

| Work being performed | Read |
| --- | --- |
| Any technical-prose writing, rewrite, or review | [plain technical writing](references/plain-technical-writing.md) |
| Procedures, runbooks, safety text, strict error messages, or an explicit request for Simplified Technical English | [strict controlled writing](references/strict-controlled-writing.md), in addition to the plain rules |

## Output Modes

- **Write:** Produce the requested prose with no process commentary unless the user asks for it.
- **Rewrite:** Keep every fact, condition, number, qualifier, and technical literal. Change only the prose needed for clarity.
- **Review:** Do not rewrite the artifact. Report each issue as `Rule | Original | Suggested`, then note any intentional exception.

## Boundaries

- Do not claim that controlled wording makes incorrect or empty content true.
- Do not change code, identifiers, command syntax, part numbers, units, error strings, quotations, or required legal and safety wording.
- Do not force strict word limits or dictionary substitutions into ordinary prose unless strict mode applies.
- Do not invent facts to make a sentence more concrete.
- If the source already satisfies the selected rules, leave it unchanged and say so when the task is a review or rewrite.

## Completion Checklist

- The selected mode matches the artifact.
- Terminology stays consistent and each sentence has a clear purpose.
- Facts, conditions, scope qualifiers, and technical literals are unchanged.
- Ordered procedures use numbered steps with one primary action per step.
- The response contains only the requested prose or review.
