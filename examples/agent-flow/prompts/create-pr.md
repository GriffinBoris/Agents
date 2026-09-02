# Objective

Publish the explicitly approved, validated change as a GitHub pull request.

First inspect git status, the current branch, remotes, and the repository's default branch. Refuse to include unrelated user changes. If necessary, create a non-default branch named with the `codex/` prefix and the issue number plus a short slug. Never force-push and never rewrite unrelated history.

Stage only files belonging to this issue, create a clear commit, push the branch with upstream tracking, and create a pull request with `gh pr create`. The PR title and body must:

- reference and close the GitHub issue when appropriate;
- summarize behavior and implementation, not the orchestration process;
- list the exact validation commands and results from `final-validation.json`;
- call out migrations, compatibility risks, follow-ups, or blocked checks;
- avoid claiming checks passed when they were skipped or blocked.

If authentication is missing, the remote is ambiguous, the checkout contains inseparable unrelated changes, or the target base cannot be determined safely, ask the Desktop parent and wait. Do not guess or publish partial work.

After creation, query the PR to verify its URL, number, base, head branch, head SHA, title, and open state.

# Output

Return only JSON conforming to the provided PR schema.
