# Objective

Validate the current checkout against the GitHub issue, approved plan, and applicable repository guidance.

Inspect the diff before selecting commands. Run the repository-native formatter or format check, linter, type checker, unit tests, integration tests, and build steps that apply to the changed surface. Start focused, then run the broadest practical suite defined by repository guidance or CI. You may allow tools to create normal caches or build products, but do not change source code to make checks pass in this step.

Record every command exactly, its exit code, and a concise result. Treat missing dependencies, credentials, services, or unsupported environments as blocked—not passed. Check the final diff for unintended generated files or unrelated modifications.

If choosing between validation paths would materially change confidence or cost, ask the Desktop parent.

# Output

Return one Markdown report containing the overall status, every command with its exit code and result, failures or blocked checks, the diff-scope check, and unresolved questions.
