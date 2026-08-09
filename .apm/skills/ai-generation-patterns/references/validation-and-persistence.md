# AI Validation And Persistence

- Validate every generated draft at the service boundary before persistence. Reject empty output, unsupported types, invalid parent references, invalid overrides, duplicate keys, and cross-scope relationships.
- Persist only a complete, validated result. Do not save partial or best-effort generated records merely because a provider returned some usable fields.
- Add focused tests for valid output and representative invalid provider output, including unknown enum values, malformed nested data, invalid references, and duplicate identifiers.
