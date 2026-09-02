# Objective

Review whether the tests and validation evidence provide proportionate confidence for the current change.

Inspect changed production code, changed tests, existing adjacent tests, and `validation.json`. Look for untested branches, false-positive assertions, excessive mocking, missing negative cases, nondeterminism, platform differences, integration gaps, and commands that were skipped or blocked. Confirm tests assert externally meaningful behavior and would fail before the fix where practical.

Do not modify the repository or rerun the entire implementation. Cite concrete file and test locations. Ask the Desktop parent only when a material validation decision requires user input.

# Output

Return only JSON conforming to the provided review schema.
