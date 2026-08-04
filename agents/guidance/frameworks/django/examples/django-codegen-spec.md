---
id: framework-django-example-codegen-spec
title: Django Codegen Spec Example
description: Example spec-driven generation of Django models, serializers, views, URLs, admin, fixtures, and the permission test matrix from one YAML resource file.
kind: example
scope: framework
name: django
tags:
  - example
  - django
  - codegen
  - scaffolding
  - testing
applies_to:
  - django
status: active
order: 20
---

# Django Codegen Spec Example

## Scenario

- Use this shape when adding a new CRUD resource that follows the repository's existing view, serializer, URL, admin, and test conventions.
- Use this shape when a resource needs the standard nested scope, route-owned field enforcement, and permission test matrix rather than bespoke behavior.
- Use this shape when auditing whether an existing app still matches the conventions the other Django examples describe.
- Do not use this shape for resources whose value is in their business rules. Generate the scaffolding, then write the domain logic by hand.

## Why This Shape Exists

- The Django examples describe one consistent house style. Route names, admin field lists, serializer field tuples, and the security test matrix are mechanical consequences of a few facts about a resource.
- Writing those files by hand is where conventions drift. A missing `raw_id_fields`, a `list_display` without `created_ts`, or a create endpoint with no spoofed-payload test are the failures that show up in review.
- The parts most often skipped under deadline are the security parts: route-owned scope enforcement, cross-scope validation, and the 403/404 isolation tests. Those are also the most mechanical, so they should exist by default rather than by discipline.
- A spec makes the resource's shape reviewable in one screen. A reviewer can check the spec against the domain instead of reading six generated files.
- Generation is reversible in review because the generator can report drift instead of writing.

## Recommended Shape

### Project Profile

The profile declares repository conventions once so resource specs stay small. It lives at the backend root as `.codegen.yaml`.

```yaml
backend_root: backend
api_prefix: /api/

base_view: common.access.base_views.AuthenticatedAccessAPIView
base_model: core.base_models.BaseModel
fixtures: tests.fixtures.FixtureFactory
random_string: core.utility.random_string
permission_module: common.permissions
default_permission: WORKSPACE_MANAGE
permission_scope: workspace

on_delete: DO_NOTHING
indent: tab
layout: feature_package
detail_lookup: resource_resolver

scopes:
  organization:
    - organization_id
  workspace:
    - organization_id
    - workspace_id
  catalog_entry:
    - organization_id
    - workspace_id
    - catalog_entry_id

namespaces:
  organization: ''
  workspace: workspace
  catalog_entry: workspace:catalog_entry

membership_models:
  organization: tenancy.models.OrganizationMembership
  workspace: workspace.models.WorkspaceMembership

roles:
  organization_admin:
    memberships:
      - organization:ADMIN
    expect: 200
  workspace_admin:
    memberships:
      - organization:MEMBER
      - workspace:ADMIN
    expect: 200
  workspace_operator:
    memberships:
      - organization:MEMBER
      - workspace:OPERATOR
    expect: 403
  other_organization_admin:
    memberships:
      - other_organization:ADMIN
    expect: 404
```

The `scopes` map is the important part. It defines the `resolve_<scope>_scope(...)` chain, the URL kwargs, the `reverse(...)` kwargs in tests, and the nested route prefix. A resource names one scope and inherits the whole chain.

The `roles` map is the permission matrix every generated view test proves. `expect` is the status a role should receive from a mutating endpoint: `200` allowed, `403` in scope but unauthorized, `404` outside the ownership boundary.

### Resource Spec

```yaml
app: item
model: Item
scope: catalog_entry

choices:
  status:
    - ACTIVE
    - INACTIVE

fields:
  catalog_entry: fk catalog_entry.CatalogEntry
  name: text
  code: text
  status: choice status
  summary: text blank
  sort_order: positive_int default=0

unique:
  - catalog_entry
  - code

filters:
  - search=name
  - status

actions:
  archive: status=INACTIVE
```

Every line is a decision a human has to make. Nothing else is declared because everything else is derived.

### What Gets Derived

| Not declared | Derived as |
| --- | --- |
| `verbose_name` | Title Case of the field name, so `sort_order` becomes `Sort Order` |
| Choice labels | Title Case of the member, so `ACTIVE` becomes `Active` |
| Choice class name | `{field}Choices`, so `status` becomes `StatusChoices` |
| Choice default | The first declared member, unless the field sets `no_default` |
| `related_name` | Plural snake case of the model, so `Item` becomes `items` |
| `null` and `blank` | `null=False, blank=False` unless the field declares the flag |
| `on_delete` | The profile default |
| Constraint name | `unique_{model}_{field}_per_{parent}` |
| Feature, path segment, lookup kwarg | `item`, `items/`, `item_id` |
| Route names | `item-list`, `item-create`, `item-detail`, `item-archive` |
| Route-owned field, spoofed-payload test target | The scope foreign key |
| Admin configuration | Relations become `raw_id_fields`, choice and boolean fields become `list_filter`, identity text fields become `search_fields`, long-form text stays off the grid |
| Serializer field tuples | Input is every field, output adds the timestamps, `id` stays first |
| Blocked update fields | Any field an action writes |
| `history_log_fields` | The same action-driven fields |

### Field Declarations

A field is `type [flags] [key=value]`, with a mapping form as the escape hatch.

```yaml
fields:
  catalog_entry: fk catalog_entry.CatalogEntry
  email: email unique
  summary: text blank
  sort_order: positive_int default=0
  is_primary: bool default=false
  parent_node: {type: fk, to: survey.ComponentNode, null: true, related_name: child_nodes}
  legacy_column: {type: text, raw: "models.TextField(db_column='legacy', null=True, blank=True)"}
```

### One Action Line Produces Five Artifacts

```yaml
actions:
  archive: status=INACTIVE
```

That single line generates the action view, the action route, `history_log_fields = ('status',)` on the model, the guard in the generic update serializer, and the test proving the guard holds. The lifecycle rule from the transition-endpoint example cannot be forgotten because it is not written by hand.

### Running The Generator

```bash
python3 agents/generate_code.py --init-profile backend
python3 agents/generate_code.py backend/item/item.yaml --diff
python3 agents/generate_code.py backend/item/item.yaml
python3 agents/generate_code.py backend/**/*.yaml --check
```

`--init-profile` writes a commented starter profile. Every value in it is a placeholder; replace each one by reading the repository's real base view, base model, fixture factory, and scope resolvers before generating anything.

The default mode writes files that do not exist and leaves everything else alone. `--diff` prints a unified diff for each file that differs. `--check` exits non-zero on any drift, which makes it usable in CI as a conformance gate.

### Guidance Examples Are Linked To Templates

`guidance_links.yaml` records which example defines the shape of which template, with a digest of each example at the time the templates were last reviewed against it.

```yaml
django-view.md:
  digest: 7398f4d0515c86cdbc02863a6f51fae83dbb3cbc033704166450e8e37a46277c
  templates:
    - views.py.jinja
    - urls.py.jinja
```

Editing a linked example fails the generator test suite and names the templates to re-check. Review them, update what actually changed, then record the new baseline with `--accept-guidance`. Accepting a digest is a claim that the templates still match the guidance, not a way to silence the failure.

This is the mechanism that stops the guidance and the generated code from drifting apart. Without it, an example can be improved and every future generated resource silently keeps the old shape.

## Things To Notice

- The profile holds repository conventions; the spec holds domain facts. Neither file repeats the other.
- The spec never names a file path. Layout comes from the profile so an app can move from flat files to feature packages without touching the resource spec.
- Generated code is indentation-configurable through `indent`, so the generator does not force a style change on an existing repository.
- Existing files are never overwritten by default. Merge targets such as `admin.py`, `urls.py`, and `tests/fixtures.py` are reported rather than rewritten.
- The generated view tests create out-of-scope records on purpose so isolation is actually exercised.
- The generated create test and the spoofed-payload test both look the resource up by scope, so a route-scope regression fails the test rather than silently passing.
- The generator is not a framework. Its output is ordinary Django code that a reviewer reads and edits like any other file.
- The generator ships with the Agents `source` target only. A repository that installed a built target has the guidance but not the tool.

## Rules To Follow

- Keep the profile at the backend root and check it in. A generator whose conventions live only on one machine is worse than no generator.
- Declare only domain facts in a resource spec. If a value can be derived from the guidance examples, do not write it down.
- Generate first, then edit. Do not add spec keys to express business logic that belongs in a serializer, service, or model method.
- Write actions with real rules by hand. The `actions` key is for simple field assignments only.
- Run `--check` in CI once specs exist so convention drift shows up as a failing job.
- Re-run the generator with `--diff` after changing a template so the effect on every resource is visible before it lands.
- Update the golden files and review them whenever a template or derivation rule changes.
- When editing a Django guidance example, review the templates it governs before recording a new digest. A guidance change is also a question about the generator.
- Add a `guidance_links.yaml` entry for every new template so it cannot escape the drift check.
- Do not generate migrations. Let Django produce them from the generated models.
- Treat the generated permission tests as the floor, not the ceiling. Add domain-specific cases beside them.

## Refactor Signals

- A new resource's `admin.py` omits `created_ts` or `updated_ts`, or leaves a high-cardinality foreign key as a dropdown.
- A create endpoint has no test proving the URL scope wins over a spoofed payload field.
- Route names drift from `{resource}-list`, `{resource}-create`, and `{resource}-detail`.
- A lifecycle field can be changed through the generic update serializer because no action guard was written.
- Two resources in the same repository resolve nested scope in visibly different ways.
- A resource spec grows conditionals, computed values, or business vocabulary that belongs in Python.
- The generator's golden files change in a commit that does not explain why every future resource should change too.

## Verification

- Run the generator test suite after changing templates or derivation rules:

```bash
python3 -m unittest tests.test_codegen
```

- Refresh and review the golden files when output changes on purpose:

```bash
python3 agents/scripts/update_codegen_golden.py
```

- Confirm generated output still matches the guidance examples. The conformance tests assert that literal snippets from `django-view.md`, `django-model.md`, and `django-admin.md` appear in generated files, so a guidance edit that changes those shapes fails the suite.
- After generating into a real backend, run the app's own checks:

```bash
python manage.py check
python manage.py makemigrations --check
pytest backend/item
ruff check backend/item
```

## Why It Helps

- Convention compliance stops depending on whether the author remembered the checklist.
- The security-critical, boilerplate-heavy files exist before anyone is under deadline pressure.
- Review shifts from reading six generated files to reading one spec, which is where the real decisions are.
- Guidance and generated code cannot drift apart silently, because the examples are asserted by the generator's own tests.
- `--check` turns the mechanical half of a backend homogeneity audit into a job that runs in seconds, leaving reviewer attention for the judgment half.
