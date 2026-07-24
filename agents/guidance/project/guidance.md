---
id: project-guidance
title: Project Guidance
description: Repository-specific guidance, tooling, and architecture decisions for Project.
kind: guidance
scope: project
name: project
tags:
  - project
applies_to:
  - project
status: active
order: 0
---

# Project Guidance

## Purpose

- Capture repository-specific conventions, local tooling, and product architecture decisions.
- Keep general development rules in `agents/guidance/guidance.md`.
- Use this file for decisions tied to this repo's structure, migration state, or product direction.

## Guidance Authoring And Migration

### Authored Guidance

- Update authored guidance under `agents/guidance/` instead of editing generated `AGENTS.md` output directly.

### Guidance Map

| File | Scope |
|---|---|
| `agents/guidance/guidance.md` | Shared development guidance |
| `agents/guidance/languages/python/guidance.md` | Python guidance |
| `agents/guidance/frameworks/django/guidance.md` | Django, DRF, and Celery guidance |
| `agents/guidance/frameworks/vue/guidance.md` | Vue, TypeScript, Pinia, and frontend API guidance |
| `agents/guidance/project/guidance.md` | Project-specific guidance |
| `agents/reference/` | Anti-pattern catalog, review rubric, and reporting templates; ships as the `guidance-reference` skill |

### Skills And Commands

- Authored command and skill content lives under `agents/content/`.

## Local Verification And Tooling

When the repository exposes a `Taskfile`, prefer its entrypoints over raw commands; `task --list` shows what is available. Everything else — pytest, Ruff, `manage.py`, and the frontend `npm` scripts — follows the standard invocation for the tool and is discoverable from `pyproject.toml` and `package.json`.

### Tooling Notes

- If the repo exposes a context7 MCP server or web search, use them only when needed and within repo rules.
- If the repo has custom CLI tooling, prefer it over ad hoc scripts.
- Python tooling is centralized in the repo-root `pyproject.toml` even when hooks run from `backend/`; keep formatter and import-sorter indentation aligned there to avoid Ruff and isort reformat loops.
- For repo-local machine automation, keep Task entrypoints in `tasks/*.yml`, put scripts in `scripts/<feature>/`, and write runtime PID, log, and state files to a gitignored repo-root dot directory.

## Current Architecture Decisions

### Django Repository Conventions

- Base backend classes live in `core/`, with `ProjectBaseModel` and `ProjectBaseAPIView` currently provided through `core/common.py`.
- Backend views should inherit from `ProjectBaseAPIView`, use `check_has_permission` for permission checks, and call `require_fields` when explicit payload-field validation is needed before serializer validation.
- For custom permissions, use `ProjectBaseModel.get_custom_permission(...)` instead of indexing `_meta.permissions` or hand-building permission strings.
- Models should continue extending `ProjectBaseModel`.
- When model audit tracking is needed, use `history_log_fields` or `history_log_private_fields` and pass `log_user_id` into `save()`.
- Existing backend relationships in this repo follow `on_delete=models.DO_NOTHING`; keep that convention unless you are making a deliberate migration with a clear data-integrity plan.
- `core/common.py` is already overloaded. Do not add new unrelated concerns there, and prefer extracting focused modules such as `core/base_models.py`, `core/base_views.py`, `core/auth_backends.py`, `core/encryption.py`, `core/email.py`, `core/admin_widgets.py`, or `core/test_fixtures.py` when touching one concern deeply.
- When the base view exposes helpers such as `create_options_from_choices`, use them instead of rebuilding choice-option payloads ad hoc.
- This repo uses `drf-standardized-errors`; in views, raise `rest_framework.exceptions.ValidationError`, and in serializers, keep field validation in `serializers.ValidationError` so responses stay in the standardized shape.
- Shared backend fixture builders belong in `core/test_fixtures.py`, and tests should mirror those helpers instead of creating one-off builders in each module.
- When view tests need model permissions, resolve them through the model helper methods the repo already uses and grant them explicitly.
- The Django settings chain in this repo is `base.py -> dev_local.py -> dev_pytest.py -> dev_docker.py -> dev_github.py -> production.py`.
- Background task wiring follows the task-app pattern already used in the repo: add behavior on the task model or task class, register it in the task map, expose a Celery entrypoint, schedule it when needed, and add tests in the task app.
- When the task framework supports progress reporting, use `self.set_message_and_percent(...)` instead of inventing parallel progress tracking.

### Frontend Repository Conventions

- The canonical frontend API client in this repo is `ApiClient`; keep Axios imports there and route domain modules through it.
- In this repository, `ApiClient` lives in `src/utils/api.ts` rather than a top-level `src/services/` folder.
- Use `buildParamsConfig` with camelCase params and let the API client handle casing conversion.
- Reuse the repo's shared loading, error, markdown, recent-run, and assistant-state components before adding view-local replacements.
- Do not render a second empty optimistic assistant bubble while a waiting-state card is already visible.
- Use `useClipboard` for copy interactions instead of direct `navigator.clipboard` calls.

