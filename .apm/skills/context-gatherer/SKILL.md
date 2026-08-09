---
name: context-gatherer
description: Build an evidence-backed map of an unfamiliar feature, component, subsystem, or codebase area. Use when explicitly asked to gather context, explain data flow, create onboarding or implementation context, or when a named review workflow requires context gathering; do not trigger for ordinary implementation.
---

# Context Gatherer

## Scope

- Map relevant structure, behavior, data flow, dependencies, and integration points with concrete file references.
- Separate durable patterns, repository-specific quirks, and unresolved questions without turning the context pass into a review or rewrite.

### Boundaries

- This skill gathers context; it does not replace a review or rewrite workflow.
- Use `full-review` for the final comprehensive scoped review workflow.

## Workflow

### 1. Define the scope
- What is being investigated?
- Backend, frontend, or both?
- Folder-level overview or implementation-level detail?

### 2. Map the structure
- Identify key directories and important files
- Note whether frontend code is organized by route folders under `src/views/`
- Note whether backend code is flat, feature-foldered, or split into domain app plus `api/` transport

### 3. Identify key components
- Backend: models, views, serializers, services, tasks, commands, middleware
- Frontend: route views, local route components, route-local `store.ts`, shared stores, composables, services, shared UI

### 4. Trace the flow
- entrypoint -> validation -> business logic -> persistence -> response
- user action -> route view -> store/composable -> API client -> backend endpoint -> response handling

### 5. Compare to guidance
- Note where the code matches modular guidance and examples
- Note missing guidance coverage or example gaps worth promoting later

## Reference Selection

- Read the [engineering baseline](../../instructions/engineering-baseline.instructions.md).
- Read the relevant language and framework guidance skills.
- Read the consumer-owned `project-architecture` skill when repository-specific structure or behavior matters.
- Open only examples that match the feature, component, or workflow being mapped.

## Review Criteria

### Goals

- Build a clear map of the area before drawing conclusions
- Show both structure and behavior
- Use concrete file paths everywhere
- Separate durable patterns from repo-specific quirks

## Output

### Summary
- what was investigated
- what it does
- key patterns used
- main complexity drivers

### Structure
- directory tree or inventory with purpose notes

### Key Components
- purpose, location, main methods, dependencies

### Data Flow
- concrete request or action flow with file references

### Integration Points
- APIs, stores, services, tasks, external systems

### Guidance Notes
- reusable patterns worth promoting
- repo-specific quirks that should not become general guidance

### Open Questions
- anything unclear, inconsistent, or lightly checked

## Completion Checklist

- The investigated scope and depth are explicit.
- Structure, key components, data flow, integration points, and open questions are covered where applicable.
- Concrete file references support the context map.

## Maintenance

- If context gathering reveals missing or misplaced guidance, update the relevant `.apm/` source file.
