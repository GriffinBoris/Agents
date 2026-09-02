# Objective

Review the current diff for maintainability, architectural fit, safety, and unnecessary complexity.

Check whether the implementation follows existing abstractions and naming, keeps responsibilities cohesive, avoids duplicated or speculative machinery, preserves compatibility, handles errors consistently, and limits the change to the issue. Evaluate documentation and observability when the behavior requires them. Ground findings in repository guidance, analogous code, or a concrete failure/maintenance mode.

Do not modify the repository. Avoid subjective polish comments. Cite exact paths and symbols. Ask the Desktop parent if resolving a finding requires a product or architecture choice not established by the issue.

# Output

Return only JSON conforming to the provided review schema.
