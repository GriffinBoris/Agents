---
kind: skill
name: context-gatherer
description: >
  Systematically gather and document context about a feature, component,
  subsystem, or codebase area before making changes or writing documentation.
---

# Context Gatherer

## When to use
- Learning how a feature works before changing it
- Mapping data flow through backend and frontend code
- Understanding route structure, APIs, services, or background jobs
- Creating onboarding notes or implementation context for future work

## Boundary
- This skill gathers context; it does not replace a review or rewrite workflow.
- Use `full-review` for the final comprehensive scoped review workflow.

## Goals
- Build a clear map of the area before drawing conclusions
- Show both structure and behavior
- Use concrete file paths everywhere
- Separate durable patterns from repo-specific quirks

## Suggested workflow

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

## Living document note
- If context gathering reveals missing or misplaced guidance, update the authored modular tree under `agents/guidance/`, `agents/reference/`, or `agents/content/`.
