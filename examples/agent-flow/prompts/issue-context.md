# Objective

Build an evidence-backed implementation brief for the GitHub issue in `request.md`. Do not modify the repository.

Use bounded native subagents for distinct context-gathering assignments. At minimum cover:

1. The issue's current body, comments, linked work, acceptance criteria, and unresolved decisions. Use `gh` read-only commands when the source URL is available.
2. The repository architecture, relevant execution paths, analogous implementations, ownership boundaries, and likely files to change.
3. Every applicable repository guidance source: all governing `AGENTS.md` files, `README`, `CONTRIBUTING`, architecture documents, ADRs, package documentation, CI configuration, formatting rules, and test conventions.
4. Relevant upstream documentation for frameworks or APIs implicated by the issue. Prefer primary official documentation and record the exact URL or repository path and section.

For every material instruction, create a guidance matrix row with:

- source and section;
- a precise paraphrase of the requirement;
- why it applies;
- affected files or behaviors;
- how implementation and review can prove compliance.

Distinguish facts from inferences. Include exact repository paths and symbols. Do not invent requirements that are absent from the issue or guidance.

If ambiguity could materially change behavior, architecture, public API, data handling, compatibility, or scope, send a concise blocking question to the Desktop parent immediately. State the options and impact, then wait for the parent's answer. Record answered and still-open questions in the artifact.

# Output

Return a complete Markdown document with these sections:

- Issue interpretation and acceptance criteria
- Issue history and linked context
- Repository map and analogous code
- Test and validation commands
- Guidance matrix
- Risks and edge cases
- Decisions already established
- Open questions
