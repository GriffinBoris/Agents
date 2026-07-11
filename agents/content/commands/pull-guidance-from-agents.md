---
kind: command
role: shared-command
description: Pull and intelligently merge Agents guidance into a third-party project through a pull request
---

Pull newer guidance from the global Agents repository, merge it into the third-party project in the current working directory, and deliver the result through a focused pull request.

Optional arguments: `$ARGUMENTS`

Canonical Agents repository: `https://github.com/GriffinBoris/Agents`

Interpret the arguments as a source ref, target agent, requested package scope, or explicit Agents checkout path. Always pull global guidance from `https://github.com/GriffinBoris/Agents` unless the user explicitly provides a different fork or checkout. A discovered remote is supporting evidence, not permission to substitute another repository. If no ref is supplied, use the canonical repository's default branch.

This is a cross-repository workflow with two strict roles:

- Source: the global Agents repository.
- PR destination: the third-party project in the current working directory.

The PR must target the third-party project. This command must not open a PR against Agents. The update is a semantic merge, not a blind overwrite.

## 1. Establish provenance and scope

- Require a git repository with a clean enough working tree to isolate this work. Preserve all unrelated user changes.
- Discover how guidance was installed and which target is in use by inspecting files such as `agents/`, `AGENTS.md`, harness-specific directories, git history, and installer metadata.
- Resolve the requested upstream ref to an immutable commit and record that commit in the PR body.
- Fetch or clone the upstream repository into a temporary location. Do not execute scripts downloaded from an untrusted fork without explicit approval.
- Compare authored source when the project contains `agents/`. If it only contains a built target, build or obtain the matching target from the trusted upstream source before comparing.

## 2. Classify local and upstream content

Treat these categories differently:

- Upstream-owned global content: global, language, and framework guidance; shared commands and skills; builder or target assets installed from Agents.
- Project-owned content: `agents/guidance/project/`, local additions explicitly marked as project-specific, and repository-specific instructions in root or harness files.
- Diverged content: upstream-owned files that have also been edited locally.
- Generated content: files such as `AGENTS.md` and harness-specific command or skill output that should be regenerated from authored source when possible.

Use git history or an installed provenance marker as the merge base when available. Otherwise compare the local files with plausible upstream versions and state the inferred base. Never assume every difference is either an upstream update or a local customization.

## 3. Plan a three-way semantic merge

- Summarize upstream additions, removals, and changed recommendations before editing.
- Preserve project-owned guidance.
- Bring in compatible upstream improvements.
- For locally modified upstream files, reconcile intent section by section instead of replacing the file.
- Do not reintroduce upstream rules that the project intentionally overrides. Keep the local exception close to the relevant project guidance and make the relationship explicit.
- Flag substantive conflicts where upstream and local guidance prescribe incompatible behavior. Resolve only when repository evidence makes the right choice clear; otherwise leave the conflict out of the PR and report it for user decision.
- Remove obsolete generated material only when the upstream source and current builder clearly supersede it.
- Avoid unrelated dependency, formatting, or code changes.

Before applying changes, present or record a concise merge plan containing:

- upstream commit and inferred local base
- packages and assets that will change
- local customizations that will be preserved
- conflicts, overrides, or skipped upstream changes

## 4. Apply on a branch and regenerate

- Create a focused branch from the third-party project's default integration point. Do not commit directly to the default branch.
- Update authored source first when it exists.
- Regenerate only the target artifacts used by this project with the repository's existing builder workflow.
- If only built artifacts are installed, merge the matching upstream target while retaining project-specific root and harness instructions.
- Add or update a lightweight provenance record only if the project already has a convention for one; do not invent a new tracking format during a routine sync.

## 5. Verify the result

- Review the full diff for lost local guidance, duplicated sections, stale generated output, broken imports, secret material, and changes outside the planned scope.
- Run the relevant Agents build and any repository checks that validate instruction or configuration files.
- Confirm that project guidance still appears in the final generated instructions and that newly selected upstream guidance appears exactly once.
- If verification fails, fix the merge or stop before publication with a precise report.

## 6. Publish through a PR

- Commit the isolated sync, push the branch, and open the required pull request against the third-party project's default branch.
- The PR body must include:
  - upstream repository, ref, and resolved commit
  - previous or inferred base
  - upstream changes adopted
  - local customizations preserved
  - conflicts resolved, deferred, or intentionally skipped
  - generated outputs and verification run
- Return the PR URL, branch, upstream commit, changed files, preserved customizations, and any follow-ups.

Do not force-push, overwrite unrelated work, or silently choose between incompatible local and upstream rules. If there are no meaningful upstream changes after semantic comparison, do not create an empty PR; report that the project is already current.
