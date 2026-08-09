# AI Provider Boundary

- Keep provider credentials and provider configuration in backend-owned settings or secret stores. Never expose them to browser code.
- Put provider calls behind a focused backend service boundary. Keep views, serializers, and UI components responsible for request handling and presentation rather than provider orchestration.
- Treat provider output as untrusted input. Do not persist, execute, or publish it until it passes the same domain validation as human-authored input.
