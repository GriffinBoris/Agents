# Python Verification And Testing

## Contents

- Verification
- HTTP, adapters, and debugging
- Testing

## Verification

- Run `ruff check` on modified Python files before completing a task.
- Prefer targeted `pytest` runs first when shared infrastructure is unchanged.
- When changing formatter or lint settings in new Python projects, prefer a 120-character-friendly line length unless repository constraints require something else.
- Keep local formatting and import ordering aligned with the repository's active lint and formatter configuration.

## HTTP, Adapters, And Debugging

- Use concrete HTTP verb helpers such as `requests.get` and `requests.post` when the method is already known.
- Do not hide straightforward request flow or one-off logic behind tiny wrapper helpers that only shuffle arguments around.
- Prefer built-in logging or framework error paths over ad hoc print debugging in committed code.

## Testing

- Keep Python tests explicit and readable.
- Prefer explicit fixture builders and helper methods over catch-all `**kwargs` patterns.
