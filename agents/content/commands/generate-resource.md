---
kind: command
role: shared-command
description: Generate a resource from one spec across every configured target so backend and frontend match the repository's conventions
---

Generate a resource in the current project from one framework-neutral spec, then finish the parts a generator cannot write.

One spec drives every configured target. The same fields, scope, endpoints, and actions produce the backend model, serializers, views, URLs, admin, and permission tests, and the frontend types, request schema, and API client methods. That is the point: the two sides cannot disagree about a field name, a route, or which fields a form may submit, because they are derived from the same source.

Optional arguments: `$ARGUMENTS`

Interpret the arguments as the resource to create, the app it belongs to, the scope that owns it, or a path to an existing spec. Ask only if the domain is genuinely ambiguous; otherwise infer from the surrounding apps and proceed.

Use this when adding a resource that follows the repository's standard scope, permission, serializer, and test conventions. Do not use it when the resource's value is in bespoke business rules. In that case generate the scaffolding anyway, then replace the generated pieces that do not fit.

## 1. Confirm the generator is available

- Look for `agents/generate_code.py` and `agents/codegen/` in the project. They ship with the Agents `source` target only. If the project installed a built target such as `claude` or `opencode`, the generator is not present. Say so and either install the source package or write the files by hand from the guidance examples.
- Run `python3 agents/generate_code.py --help` to see which targets this checkout supports.
- The generator needs `jinja2` and `pyyaml`. If they are missing, install them or report that the environment cannot run it.

## 2. Establish the project profile

- Look for `.codegen.yaml`, starting at the backend root and walking up.
- If it exists, read it and trust it. Do not silently change repository-wide conventions to make one resource generate more conveniently.
- If it does not exist, create one:

```bash
python3 agents/generate_code.py --init-profile backend
```

- Then replace every placeholder by reading the real code. Open one existing list view, one create view, and one view test and confirm each of these:
  - `base_view`: the shared authenticated API view, and whether it really exposes `resolve_<scope>_scope`, `require_permission`, and `build_serializer_data`
  - `base_model`: the shared base model providing `created_ts` and `updated_ts`
  - `fixtures` and `random_string`: the shared test fixture factory and its random helper
  - `permission_module`, `default_permission`, `permission_scope`
  - `scopes`: the exact URL kwargs each resolver takes, in order
  - `namespaces`: the route namespace prefix each scope contributes
  - `membership_models`: the models whose `RoleChoices` the tests reference
  - `roles`: the real permission matrix, including at least one `403` role and one `404` role
  - `indent`, `layout`, `model_layout`, `detail_lookup`
- Fill in a section per target. `scopes`, `namespaces`, and `api_prefix` are shared because both the backend route and the frontend API path are built from them; everything else belongs to one target's section.
- Delete any target section the project does not use and remove that target from `targets`.
- Set `detail_lookup: resource_resolver` only if per-resource `resolve_<resource>_scope` helpers actually exist. Otherwise leave it as `scoped_queryset`.
- Treat a wrong profile as the main failure mode. A profile that names helpers the repository does not have produces code that imports cleanly and fails at runtime.

## 3. Write the resource spec

- Put the spec beside the app it belongs to, such as `backend/item/item.yaml`.
- Declare only domain facts. Everything the Django guidance examples make mechanical is derived: verbose names, choice labels and defaults, related names, route names, admin configuration, serializer field tuples, and the permission test matrix.
- Keep it small. If a value can be derived, do not write it down.
- Model the resource against the real domain: correct scope, correct field types, real choice members in a sensible order, and a `unique` constraint where one genuinely exists.
- Use `actions` only for simple field assignments such as `archive: status=INACTIVE`. Anything with real business rules is written by hand afterward.
- Put target-only options under a target key such as `django:` or `vue:`. The top level is for domain facts that every target consumes.
- Read `agents/codegen/examples/item.yaml` and `contact.yaml` for a scoped feature package and a flat app respectively.

## 4. Preview before writing

```bash
python3 agents/generate_code.py backend/item/item.yaml --diff
python3 agents/generate_code.py backend/item/item.yaml --diff --target vue
```

- Read the diff as a reviewer, not as a formality. Check that the scope chain, permission scope, route names, and serializer fields match what the surrounding apps do.
- Check the frontend output against an existing type file and API segment for the same reasons.
- If the output is wrong in the same way for every file, the profile is wrong. Fix the profile, not the generated files.

## 5. Generate and complete the work

```bash
python3 agents/generate_code.py backend/item/item.yaml
```

- Existing files are never overwritten. Anything reported as `EXISTS` needs a manual merge; that normally means `admin.py`, the app `urls.py`, and `tests/fixtures.py`.
- Merge those by hand, matching the surrounding file's ordering and import style.
- Wire the new feature URL module into the parent hub if the route family is new.
- Then write what the generator deliberately does not:
  - domain validation in `validate_<field>()` and `validate()`
  - service or task boundaries for anything with side effects
  - real business rules behind action endpoints
  - any test case specific to this domain, beyond the generated permission matrix
  - route folders, views, and stores on the frontend, which compose sections and own workflow state
- Create migrations with the project's own command. The generator never writes migrations.

## 6. Verify

- Run the project's checks, not just the generator's:

```bash
python manage.py makemigrations
python manage.py check
pytest backend/<app>
ruff check backend/<app>
```

- Generated tests reference fixture builders and membership models that must exist. A failure there usually means the profile named something the repository does not have.
- Confirm the ownership-boundary tests actually fail when scoping is removed. A green isolation test that would pass regardless proves nothing.

## 7. Report

- State the spec created, the targets generated, the files that needed manual merges, and the business logic still outstanding.
- Call out any profile value you had to infer rather than confirm, so a reviewer can check it.
- If you changed the profile, say what changed and why, since it affects every future resource.
