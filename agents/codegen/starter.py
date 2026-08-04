STARTER_PROFILE = """# Code generator profile.
#
# This declares repository conventions once so resource specs stay small. Every
# value below is a placeholder taken from the bundled example. Replace each one with
# the real name from this repository before generating anything, then check it in.
#
# The fastest way to fill it in: open one existing list view, one create view, one
# view test, and one frontend type file.

# Which generators run when a spec does not name its own targets.
targets:
  - django
  - vue

# The API prefix both sides agree on. The backend routes it; the frontend calls it.
api_prefix: /api/

# Default indentation. Any target may override it in its own section.
indent: tab

# Each scope lists the URL identifiers its resolver consumes, in order. A resource
# names one scope and inherits the whole chain. This drives backend view signatures,
# reverse() kwargs in tests, and the frontend API path arguments, so it lives here
# rather than in a single target's section.
scopes:
  organization:
    - organization_id
  workspace:
    - organization_id
    - workspace_id

# Route namespace prefix contributed by each scope. The resource appends its app.
namespaces:
  organization: ''
  workspace: workspace

django:
  backend_root: backend

  # Dotted paths to the shared helpers generated code will call. base_view must
  # expose resolve_<scope>_scope, require_permission, and build_serializer_data.
  base_view: common.access.base_views.AuthenticatedAccessAPIView
  base_model: core.base_models.BaseModel
  fixtures: tests.fixtures.FixtureFactory
  random_string: core.utility.random_string
  permission_module: common.permissions
  default_permission: WORKSPACE_MANAGE

  # The scope that owns permission checks, such as workspace or organization.
  permission_scope: workspace

  on_delete: DO_NOTHING

  # feature_package puts views, serializers, urls, and tests in views/<feature>/.
  # flat keeps them at the app root.
  layout: feature_package

  # module writes app/models.py. package writes app/models/<Model>.py.
  model_layout: module

  # resource_resolver generates self.resolve_<resource>_scope(...) and requires that
  # helper to exist. scoped_queryset uses get_object_or_404 against the scoped parent
  # queryset instead, which works without per-resource resolvers.
  detail_lookup: scoped_queryset

  # Dotted paths to the membership models whose RoleChoices the tests reference.
  membership_models:
    organization: tenancy.models.OrganizationMembership
    workspace: workspace.models.WorkspaceMembership

  # The permission matrix every generated view test proves.
  # expect is the status a role should get from a mutating endpoint:
  #   200 allowed, 403 in scope but unauthorized, 404 outside the ownership boundary.
  # Include at least one 403 role and one 404 role or the isolation tests are hollow.
  roles:
    organization_admin:
      memberships:
        - organization:ADMIN
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

vue:
  frontend_root: frontend

  # TypeScript is conventionally two spaces, so this target overrides the default.
  indent: space2

  types_dir: src/types
  api_client: src/utils/api.ts
  api_client_name: apiClient
"""
