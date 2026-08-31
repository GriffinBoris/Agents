# Vue Testing

## Behavioral Test Design

- Follow the consuming repository's established test runner, Vue mounting utilities, browser-test framework, file placement, naming, setup files, and commands. Do not introduce another test stack for one feature.
- Test the narrowest boundary that owns the behavior. Use unit tests for pure helpers, composables, and isolated stores; component tests for rendering, input, events, and visible states; router tests for navigation policy; and end-to-end tests for cross-page or browser-session behavior.
- Express each scenario as preconditions and inputs, one user or program action, and concrete observable outcomes. Keep each test about one behavior; multiple assertions may jointly describe that outcome.
- Cover the normal positive outcome and meaningful negative, failure, and boundary outcomes. Choose cases from the contract and risk rather than adding permutations that prove nothing new.
- Derive expected values from the requirement or user-visible contract. Do not reproduce the production computation in the test and then compare the implementation with itself.
- Keep production transport, browser API, timer, and storage ownership intact. Tests may use lower-level APIs to prepare state, but application behavior must still flow through the canonical production boundary.
- Reuse established test helpers when they make setup clearer. Keep route scope, identity, inputs, expected state, and assertions visible instead of hiding the scenario in broad fixtures.

## Contract Coverage

- Cover the success path and the failure or boundary states that change user-visible behavior.
- For asynchronous stores, composables, and route views, assert loading transitions, error state, retry behavior, cleanup, and protection against stale responses when those contracts apply.
- For forms and dialogs, assert input state, validation messages, submit gating, server-error mapping, emitted events, and reset or close behavior relevant to the feature.
- For shared components and wrappers, test the shared contract once: props, slots, emitted events, disabled or loading behavior, accessible labels, and stable test identifiers when the repository uses them.
- For routing and authentication, cover anonymous, authenticated, guest-only, permission-denied, bootstrap-failure, redirect-preservation, and public-route behavior that applies to the changed flow.
- For browser boundaries such as clipboard, storage, location, or timers, mock the boundary deterministically and cover rejection or cleanup behavior.
- For API and error helpers, assert the shared helper behavior instead of repeating raw transport-payload assertions in every component.

## Test Quality

- Require every test to fail when the intended behavior is removed, reversed, or produces the wrong result. A test that still passes against a broken implementation is not protecting the contract.
- Assert observable output and state rather than private implementation details.
- Do not add tests merely to increase coverage, mount a component, call a composable, prove that a value exists, or verify one mock called another mock. Those checks are useful only when that exact fact is a meaningful public contract.
- Assert collaborator calls only when the interaction is itself observable behavior, such as emitting once, navigating to a route, sending one request, or making no request after validation fails.
- Mock transport, browser APIs, time, randomness, and other nondeterministic boundaries when they are not the subject of the test. Do not mock away the state transition, validation, rendering, routing, or error behavior being proved.
- Prefer focused assertions over broad snapshots. Use snapshots only where the repository already uses them and the snapshot expresses a stable, reviewable contract.
- Control time, timers, browser APIs, network responses, and generated values deterministically.
- Prove cleanup for polling, subscriptions, event listeners, and timers when components or composables own lifecycle work.
- Avoid duplicating the same helper contract across every consuming component test.
- Treat coverage as a way to find unexamined behavior, not as evidence that the behavior is tested correctly.

## Verification

- Run the smallest test file, case, or project target that covers the change first.
- Run the repository's frontend linter and typecheck when test or production TypeScript changes.
- Expand to the relevant suite or end-to-end flow when shared state, routing, authentication, API helpers, or reusable UI contracts change.
- Report verification that was not run and the exact command needed when the environment blocks it.
