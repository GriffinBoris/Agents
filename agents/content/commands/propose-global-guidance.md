---
kind: command
role: shared-command
description: Filter and push reusable guidance from a third-party project to Agents through a pull request
---

Push reusable guidance from the third-party project in the current working directory to the global Agents repository through a pull request.

Optional arguments: `$ARGUMENTS`

Canonical Agents repository: `https://github.com/GriffinBoris/Agents`

Interpret the arguments as extra context, a requested scope, or an explicit Agents checkout path. Always use `https://github.com/GriffinBoris/Agents` as the global repository unless the user explicitly provides a different fork or checkout. A discovered remote is supporting evidence, not permission to substitute another repository. Do not require arguments when the candidate changes can be discovered safely.

This is a cross-repository workflow with two strict roles:

- Source: the third-party project in the current working directory.
- PR destination: the global Agents repository.

The third-party project is evidence for a general rule. It is never the destination for this command's PR, and this command must not open a PR against it.

## 1. Discover the candidate guidance

- Inspect the current branch diff, recent commits, local guidance files, review artifacts, and relevant code or tests.
- Identify only guidance changes that the user appears to want to contribute.
- Read the global Agents repository's current authored content before drafting anything:
  - `agents/guidance/guidance.md`
  - relevant `agents/guidance/languages/<name>/guidance.md`
  - relevant `agents/guidance/frameworks/<name>/guidance.md`
  - relevant examples under those packages
- Check whether the rule already exists, conflicts with current guidance, or belongs as a refinement to an existing rule or example.

## 2. Apply the global-guidance test

Every proposed change must pass all of these checks:

- It is useful across multiple repositories or teams, not just this project's current layout or product domain.
- It can be stated without private names, customer details, internal URLs, secrets, organization-specific processes, or repository-only terminology.
- It is not merely a local preference, temporary migration constraint, one-off workaround, or description of the current implementation.
- It fits the correct global, language, or framework package.
- There is enough evidence to explain when the rule applies, why it helps, and important exceptions.

Treat content under `agents/guidance/project/` in the current project as project-specific by default. Never copy that package wholesale. A rule found there may only be promoted after rewriting it into a portable principle that passes the tests above.

If no candidate passes, stop without creating a branch or PR. Report which candidates were rejected and why, and recommend keeping them in project guidance.

## 3. Draft the smallest upstream change

- Work in a clean temporary clone or git worktree of the global Agents repository so the third-party project is not mutated.
- Start from the repository's default branch and create a focused branch.
- Edit authored files under `agents/guidance/`, `agents/content/`, or supporting builder code only when required. Never edit `dist/` as the source of truth.
- Put universal rules in global guidance, ecosystem rules in the matching language or framework package, and detailed demonstrations in examples.
- Generalize names and snippets. Preserve the lesson, not the source project's identifiers.
- Prefer updating an existing document over adding a near-duplicate.
- Do not include unrelated local changes.

## 4. Verify and self-review

- Build all targets with `python3 agents/build_agents.py --target all --out dist --clean`.
- Run any additional focused checks available in the global repository.
- Review the complete upstream diff for portability, duplication, contradictions, accidental project details, generated-file noise, and secrets.
- Clearly distinguish facts observed in the source project from the generalized recommendation.

## 5. Publish through a PR

- Commit only the approved upstream guidance change.
- Push the branch and open a pull request against the global repository's default branch.
- The PR body must include:
  - the reusable problem or pattern
  - why it belongs in global guidance
  - the evidence used, described without sensitive project details
  - what was deliberately left project-specific
  - files changed and verification run
- Return the PR URL, branch, changed files, and verification results.

Do not push or create the required PR until the classification and diff review show that every included change is genuinely reusable. Never commit project-specific material to Agents. If authentication, repository access, or a consequential ambiguity blocks publication, preserve the prepared diff and ask for the minimum needed input.
