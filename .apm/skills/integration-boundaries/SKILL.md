---
name: integration-boundaries
description: Apply resource-lifecycle testing and outbound-request security guidance. Use when code manages hardware devices, operating-system services, network streams, child processes, replaceable external resources, or requests to user-configurable destinations, including SSRF-sensitive HTTP integrations.
---

# Integration Boundary Guidance

## Scope

- Keep fragile external-resource ownership replaceable and testable without abstracting ordinary pure code.
- Treat user-configurable outbound destinations as security boundaries.

## Workflow

1. Identify where the application acquires, uses, and releases the external resource or resolves and connects to an outbound destination.
2. Inspect the closest repository integration and test patterns before introducing a new boundary.
3. Keep the boundary small, explicit, and owned by a production adapter or service.
4. Verify lifecycle failure paths or destination validation paths appropriate to the change.

## Resource Lifecycle Guidance

- When a workflow owns a hardware device, operating-system service, network stream, child process, or another resource that is impractical to exercise in ordinary tests, keep the acquire-and-release boundary small and replaceable.
- Test the workflow lifecycle with a fake resource: successful start, invalid concurrent start, pause or resume when applicable, cleanup on stop, failed startup, and a subsequent retry.
- Keep production adapters responsible for the real integration and resource cleanup. Do not introduce a broad abstraction for pure code or a single straightforward call that needs no isolated lifecycle testing.

## Outbound Request Security

- Treat requests to user-configurable destinations as an SSRF boundary. Restrict schemes and ports, reject credentials and non-public network ranges, and disable redirects unless every hop is independently validated.
- Do not validate a hostname and then let the HTTP client resolve it again. Resolve once, validate every returned address, connect to a validated address, and preserve the original hostname for the HTTP `Host` header and TLS SNI and certificate verification.
- Test literal blocked addresses, DNS-rebinding behavior, redirects, invalid ports, and any intentional destination exceptions.

## Completion Checklist

- The external boundary and its owner are explicit.
- Resource cleanup and retry behavior are verified where applicable.
- User-configurable destinations cannot bypass address validation through resolution or redirects.
- Any public-network or destination exceptions are deliberate, narrow, and tested.
