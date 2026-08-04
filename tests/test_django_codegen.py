import ast
import tempfile
import unittest
from pathlib import Path

from agents.django_codegen.fields import SpecError, parse_field, render_declaration
from agents.django_codegen.generator import generate
from agents.django_codegen.naming import class_case, kebab_case, plural_snake, snake_case, title_case
from agents.django_codegen.profile import load_profile
from agents.django_codegen.spec import build_spec, load_spec
from agents.django_codegen.writer import MATCHES, WRITTEN, apply_files


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = ROOT / 'agents' / 'django_codegen' / 'examples'
GOLDEN_ROOT = ROOT / 'tests' / 'golden' / 'django_codegen'
GUIDANCE_EXAMPLES_ROOT = ROOT / 'agents' / 'guidance' / 'frameworks' / 'django' / 'examples'


def load_example_spec(name: str = 'item'):
    profile = load_profile(EXAMPLES_ROOT / '.django-codegen.yaml')
    return load_spec(EXAMPLES_ROOT / f'{name}.yaml', profile)


def load_item_spec():
    return load_example_spec('item')


def generated_by_path(name: str = 'item') -> dict[str, str]:
    return {generated.path: generated.content for generated in generate(load_example_spec(name))}


def bundled_spec_names() -> list[str]:
    return sorted(path.stem for path in EXAMPLES_ROOT.glob('*.yaml') if not path.name.startswith('.'))


class NamingTest(unittest.TestCase):
    def test_snake_case_splits_camel_case(self) -> None:
        self.assertEqual('catalog_entry', snake_case('CatalogEntry'))
        self.assertEqual('survey_form_version', snake_case('SurveyFormVersion'))

    def test_kebab_case_matches_route_naming(self) -> None:
        self.assertEqual('catalog-entry', kebab_case('CatalogEntry'))
        self.assertEqual('input-binding-mapping', kebab_case('InputBindingMapping'))

    def test_class_case_round_trips(self) -> None:
        self.assertEqual('CatalogEntry', class_case('catalog_entry'))
        self.assertEqual('Item', class_case('item'))

    def test_title_case_builds_verbose_names(self) -> None:
        self.assertEqual('Sort Order', title_case('sort_order'))
        self.assertEqual('Active', title_case('ACTIVE'))
        self.assertEqual('Survey Submitted', title_case('SURVEY_SUBMITTED'))

    def test_pluralize_handles_repository_names(self) -> None:
        self.assertEqual('items', plural_snake('Item'))
        self.assertEqual('catalog_entries', plural_snake('CatalogEntry'))
        self.assertEqual('addresses', plural_snake('Address'))
        self.assertEqual('workspaces', plural_snake('Workspace'))


class FieldDeclarationTest(unittest.TestCase):
    def render(self, name: str, declaration, **kwargs) -> str:
        field = parse_field(name, declaration)
        return render_declaration(
            field,
            model_name=kwargs.get('model_name', 'Item'),
            default_on_delete=kwargs.get('default_on_delete', 'DO_NOTHING'),
            related_name=kwargs.get('related_name', 'items'),
        )

    def test_relation_declaration_matches_the_model_example(self) -> None:
        self.assertEqual(
            "collection = models.ForeignKey('catalog.Collection', related_name='items', null=False, blank=False, "
            "verbose_name=gettext('Collection'), on_delete=models.DO_NOTHING)",
            self.render('collection', 'fk catalog.Collection'),
        )

    def test_text_declaration_matches_the_model_example(self) -> None:
        self.assertEqual(
            "name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))",
            self.render('name', 'text'),
        )

    def test_blank_flag_is_honored(self) -> None:
        self.assertEqual(
            "summary = models.TextField(null=False, blank=True, verbose_name=gettext('Summary'))",
            self.render('summary', 'text blank'),
        )

    def test_numeric_declaration_keeps_argument_order(self) -> None:
        self.assertEqual(
            "sort_order = models.PositiveIntegerField(default=0, null=False, blank=False, "
            "verbose_name=gettext('Sort Order'))",
            self.render('sort_order', 'positive_int default=0'),
        )

    def test_unknown_type_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            parse_field('name', 'stringy')

    def test_relation_without_target_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            parse_field('catalog_entry', 'fk')


class SpecDerivationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_item_spec()

    def test_route_names_follow_the_url_module_example(self) -> None:
        self.assertEqual('item-list', self.spec.route_name('list'))
        self.assertEqual('item-create', self.spec.route_name('create'))
        self.assertEqual('item-detail', self.spec.route_name('detail'))
        self.assertEqual('workspace:catalog_entry:item:item-detail', self.spec.full_route_name('detail'))

    def test_path_and_lookup_names_are_derived(self) -> None:
        self.assertEqual('items', self.spec.path_segment)
        self.assertEqual('item_id', self.spec.id_kwarg)
        self.assertEqual('items', self.spec.related_name)

    def test_scope_chain_comes_from_the_profile(self) -> None:
        self.assertEqual(('organization', 'workspace', 'catalog_entry'), self.spec.scope_chain)
        self.assertEqual(('organization_id', 'workspace_id', 'catalog_entry_id'), self.spec.scope_kwargs)

    def test_choice_fields_default_to_the_first_member(self) -> None:
        status = next(field for field in self.spec.fields if field.name == 'status')
        self.assertEqual('ACTIVE', status.default)

    def test_admin_configuration_is_derived(self) -> None:
        self.assertEqual(
            ('id', 'catalog_entry', 'name', 'code', 'status', 'sort_order', 'created_ts', 'updated_ts'),
            self.spec.admin_list_display,
        )
        self.assertEqual(('name', 'code'), self.spec.search_fields)
        self.assertEqual(('status', 'catalog_entry'), self.spec.list_filter)
        self.assertEqual(('catalog_entry',), self.spec.raw_id_fields)

    def test_long_form_text_stays_out_of_admin_columns_and_search(self) -> None:
        self.assertNotIn('summary', self.spec.admin_list_display)
        self.assertNotIn('summary', self.spec.search_fields)

    def test_actions_drive_blocked_fields(self) -> None:
        self.assertEqual(('status',), self.spec.blocked_fields)
        self.assertEqual('archive', self.spec.action_for_field('status').name)

    def test_serializer_field_tuples_put_id_first(self) -> None:
        self.assertEqual('id', self.spec.input_fields[0])
        self.assertEqual('id', self.spec.output_fields[0])
        self.assertEqual(('created_ts', 'updated_ts'), self.spec.output_fields[-2:])

    def test_unique_constraint_name_is_derived(self) -> None:
        self.assertEqual('unique_item_code_per_catalog_entry', self.spec.unique_name)

    def test_url_prefix_matches_the_nested_route_contract(self) -> None:
        self.assertEqual(
            '/api/organizations/{self.organization.id}/workspaces/{self.workspace.id}'
            '/catalog-entries/{self.catalog_entry.id}/items/',
            self.spec.url_prefix,
        )

    def test_unknown_scope_is_rejected(self) -> None:
        profile = load_profile(EXAMPLES_ROOT / '.django-codegen.yaml')
        spec = build_spec(
            {'app': 'item', 'model': 'Item', 'scope': 'nowhere', 'fields': {'name': 'text'}},
            profile,
        )

        with self.assertRaises(SpecError):
            spec.scope_chain

    def test_undeclared_choice_group_is_rejected(self) -> None:
        profile = load_profile(EXAMPLES_ROOT / '.django-codegen.yaml')

        with self.assertRaises(SpecError):
            build_spec({'app': 'item', 'model': 'Item', 'fields': {'status': 'choice status'}}, profile)

    def test_unknown_spec_key_is_rejected(self) -> None:
        profile = load_profile(EXAMPLES_ROOT / '.django-codegen.yaml')

        with self.assertRaises(SpecError):
            build_spec({'app': 'item', 'model': 'Item', 'fields': {'name': 'text'}, 'colour': 'red'}, profile)


class GeneratedOutputTest(unittest.TestCase):
    def setUp(self) -> None:
        self.generated = generated_by_path()

    def test_every_generated_file_is_valid_python(self) -> None:
        for path, content in self.generated.items():
            with self.subTest(path=path):
                ast.parse(content)

    def test_expected_files_are_generated(self) -> None:
        expected = {
            'item/models.py',
            'item/admin.py',
            'item/urls.py',
            'item/views/item/serializers.py',
            'item/views/item/views.py',
            'item/views/item/urls.py',
            'item/views/item/tests/test_views.py',
            'item/views/item/tests/test_serializers.py',
            'item/tests/test_item_models.py',
            'tests/fixtures.py',
        }
        self.assertTrue(expected.issubset(set(self.generated)))

    def test_generated_code_uses_tabs_by_default(self) -> None:
        views = self.generated['item/views/item/views.py']
        self.assertIn('\n\tdef get(self, request', views)
        self.assertNotIn('\n    def get(self, request', views)

    def test_space_indent_profile_converts_leading_tabs(self) -> None:
        profile_text = (EXAMPLES_ROOT / '.django-codegen.yaml').read_text(encoding='utf-8')

        with tempfile.TemporaryDirectory() as temporary_directory:
            profile_path = Path(temporary_directory) / '.django-codegen.yaml'
            profile_path.write_text(profile_text.replace('indent: tab', 'indent: space'), encoding='utf-8')
            spec = load_spec(EXAMPLES_ROOT / 'item.yaml', load_profile(profile_path))
            views = next(item for item in generate(spec) if item.path.endswith('views/item/views.py'))

        self.assertIn('\n    def get(self, request', views.content)
        self.assertNotIn('\t', views.content)
        ast.parse(views.content)


class GuidanceConformanceTest(unittest.TestCase):
    """The generated output must match the shapes the Django guidance examples prescribe."""

    def setUp(self) -> None:
        self.generated = generated_by_path()

    def assert_example_contains(self, example: str, snippet: str) -> None:
        text = (GUIDANCE_EXAMPLES_ROOT / example).read_text(encoding='utf-8')
        self.assertIn(snippet, text, f'{example} no longer contains the shape the generator targets')

    def test_feature_urls_match_the_url_module_example(self) -> None:
        snippet = "\tpath('list/', views.ItemListView.as_view(), name='item-list'),"
        self.assertIn(snippet, self.generated['item/views/item/urls.py'])
        self.assert_example_contains('django-view.md', snippet)

    def test_detail_route_matches_the_url_module_example(self) -> None:
        snippet = "\tpath('<int:item_id>/', views.ItemDetailView.as_view(), name='item-detail'),"
        self.assertIn(snippet, self.generated['item/views/item/urls.py'])
        self.assert_example_contains('django-view.md', snippet)

    def test_scoped_list_view_matches_the_view_example(self) -> None:
        snippet = (
            '\t\t_, _, catalog_entry = self.resolve_catalog_entry_scope('
            'request, organization_id, workspace_id, catalog_entry_id)'
        )
        self.assertIn(snippet, self.generated['item/views/item/views.py'])
        self.assert_example_contains('django-view.md', snippet)

    def test_create_view_enforces_route_owned_scope_like_the_example(self) -> None:
        snippet = '\t\tedited_data = self.build_serializer_data(request, catalog_entry=catalog_entry.id)'
        self.assertIn(snippet, self.generated['item/views/item/views.py'])
        self.assert_example_contains('django-view.md', snippet)

    def test_permission_check_matches_the_view_example(self) -> None:
        snippet = (
            '\t\tself.require_permission(request, '
            'AppPermission.permission(AppPermissionChoices.WORKSPACE_MANAGE), workspace=workspace)'
        )
        self.assertIn(snippet, self.generated['item/views/item/views.py'])
        self.assert_example_contains('django-view.md', snippet)

    def test_action_view_matches_the_view_example(self) -> None:
        views = self.generated['item/views/item/views.py']
        self.assertIn('\t\titem.status = Item.StatusChoices.INACTIVE', views)
        self.assertIn("\t\titem.save(update_fields=['status', 'updated_ts'])", views)
        self.assert_example_contains('django-view.md', '\t\titem.status = Item.StatusChoices.INACTIVE')

    def test_detail_view_resolves_the_full_nested_path(self) -> None:
        snippet = (
            '\t\t_, workspace, catalog_entry, item = self.resolve_item_scope('
            'request, organization_id, workspace_id, catalog_entry_id, item_id)'
        )
        self.assertIn(snippet, self.generated['item/views/item/views.py'])
        self.assert_example_contains('django-view.md', snippet)

    def test_output_serializer_marks_every_field_read_only(self) -> None:
        serializers = self.generated['item/views/item/serializers.py']
        self.assertIn('\t\tread_only_fields = fields', serializers)

    def test_admin_registration_matches_the_admin_example(self) -> None:
        admin = self.generated['item/admin.py']
        self.assertIn('@admin.register(Item)', admin)
        self.assertIn('class ItemAdmin(admin.ModelAdmin):', admin)
        self.assertIn("\treadonly_fields = ('id', 'created_ts', 'updated_ts')", admin)
        self.assert_example_contains('django-admin.md', "\treadonly_fields = ('id', 'created_ts', 'updated_ts')")

    def test_model_declaration_matches_the_model_example(self) -> None:
        models = self.generated['item/models.py']
        self.assertIn("\t\tACTIVE = 'ACTIVE', gettext('Active')", models)
        self.assertIn("\t\tordering = ('sort_order', 'id')", models)
        self.assert_example_contains('django-model.md', "\t\tACTIVE = 'ACTIVE', gettext('Active')")
        self.assert_example_contains('django-model.md', "\t\tordering = ('sort_order', 'id')")

    def test_view_tests_cover_the_prescribed_security_matrix(self) -> None:
        tests = self.generated['item/views/item/tests/test_views.py']
        required = (
            'def test_item_routes_follow_contract(self):',
            'def test_organization_admin_only_lists_in_scope_items(self, client):',
            'def test_create_keeps_route_catalog_entry_scope_when_payload_includes_other_catalog_entry(self, client):',
            'def test_workspace_operator_cannot_create_item(self, client):',
            'def test_other_organization_admin_cannot_read_item(self, client):',
            'def test_generic_update_cannot_change_status(self, client):',
        )

        for signature in required:
            with self.subTest(signature=signature):
                self.assertIn(signature, tests)

    def test_view_tests_assert_against_the_output_serializer(self) -> None:
        tests = self.generated['item/views/item/tests/test_views.py']
        self.assertIn(
            "expected = ItemOutputSerializer([self.item], many=True, context={'request': response.wsgi_request}).data",
            tests,
        )
        self.assertIn('assert response.json() == expected', tests)

    def test_view_tests_use_reverse_with_route_kwargs(self) -> None:
        tests = self.generated['item/views/item/tests/test_views.py']
        self.assertIn("reverse('workspace:catalog_entry:item:item-list', kwargs=", tests)

    def test_out_of_scope_records_exist_so_isolation_is_provable(self) -> None:
        tests = self.generated['item/views/item/tests/test_views.py']
        self.assertIn('self.other_organization = FixtureFactory.create_organization()', tests)
        self.assertIn('self.other_item = FixtureFactory.create_item(self.other_catalog_entry)', tests)


class FlatLayoutTest(unittest.TestCase):
    """The contact spec is organization-scoped and flat, so it exercises different code paths."""

    def setUp(self) -> None:
        self.spec = load_example_spec('contact')
        self.generated = generated_by_path('contact')

    def test_flat_layout_keeps_transport_files_at_the_app_root(self) -> None:
        self.assertIn('contact/views.py', self.generated)
        self.assertIn('contact/serializers.py', self.generated)
        self.assertIn('contact/urls.py', self.generated)
        self.assertNotIn('contact/views/contact/views.py', self.generated)

    def test_flat_layout_urls_own_the_app_name(self) -> None:
        urls = self.generated['contact/urls.py']
        self.assertIn("app_name = 'contact'", urls)
        self.assertIn('from contact import views', urls)

    def test_flat_layout_does_not_emit_a_second_url_hub(self) -> None:
        paths = [path for path in self.generated if path.endswith('urls.py')]
        self.assertEqual(['contact/urls.py'], paths)

    def test_single_scope_resolves_without_tuple_unpacking(self) -> None:
        self.assertIn(
            '\t\torganization = self.resolve_organization_scope(request, organization_id)',
            self.generated['contact/views.py'],
        )

    def test_multi_field_search_builds_an_or_query(self) -> None:
        self.assertIn(
            'queryset.filter(Q(email__icontains=search) | Q(first_name__icontains=search) '
            '| Q(last_name__icontains=search))',
            self.generated['contact/views.py'],
        )

    def test_boolean_field_declaration(self) -> None:
        self.assertIn(
            "\tis_primary = models.BooleanField(default=False, null=False, blank=False, "
            "verbose_name=gettext('Is Primary'))",
            self.generated['contact/models.py'],
        )

    def test_unique_flag_reaches_the_declaration(self) -> None:
        self.assertIn('unique=True', self.generated['contact/models.py'])

    def test_no_actions_means_no_blocked_fields_or_action_routes(self) -> None:
        self.assertEqual((), self.spec.blocked_fields)
        self.assertNotIn('ArchiveView', self.generated['contact/views.py'])
        self.assertNotIn('def validate(self, attrs):', self.generated['contact/serializers.py'])

    def test_notes_stay_out_of_admin_columns(self) -> None:
        self.assertNotIn("'notes'", self.generated['contact/admin.py'])


class GoldenOutputTest(unittest.TestCase):
    """Checked-in golden files make template drift visible in review."""

    def test_generated_output_matches_the_golden_files(self) -> None:
        golden_paths = sorted(path for path in GOLDEN_ROOT.rglob('*') if path.is_file())
        self.assertTrue(
            golden_paths,
            'golden files are missing; regenerate them with agents/scripts/update_codegen_golden.py',
        )

        for name in bundled_spec_names():
            generated = generated_by_path(name)
            spec_root = GOLDEN_ROOT / name

            for golden in sorted(path for path in spec_root.rglob('*') if path.is_file()):
                relative = golden.relative_to(spec_root).as_posix()
                with self.subTest(spec=name, path=relative):
                    self.assertIn(relative, generated)
                    self.assertEqual(
                        golden.read_text(encoding='utf-8'),
                        generated[relative],
                        f'{name}/{relative} drifted from the golden file',
                    )

    def test_golden_files_cover_every_non_empty_generated_file(self) -> None:
        for name in bundled_spec_names():
            with self.subTest(spec=name):
                generated = {path for path, content in generated_by_path(name).items() if content.strip()}
                spec_root = GOLDEN_ROOT / name
                covered = {
                    path.relative_to(spec_root).as_posix() for path in spec_root.rglob('*') if path.is_file()
                }
                self.assertEqual(generated, covered)

    def test_every_bundled_spec_generates_valid_python(self) -> None:
        for name in bundled_spec_names():
            for path, content in generated_by_path(name).items():
                with self.subTest(spec=name, path=path):
                    ast.parse(content)


class WriterTest(unittest.TestCase):
    def test_write_then_check_reports_no_drift(self) -> None:
        files = generate(load_item_spec())

        with tempfile.TemporaryDirectory() as temporary_directory:
            out_root = Path(temporary_directory)
            written = apply_files(files, out_root, mode='write')
            self.assertTrue(all(result.status == WRITTEN for result in written))

            checked = apply_files(files, out_root, mode='check')
            self.assertTrue(all(result.status == MATCHES for result in checked))

    def test_check_reports_drift_when_a_file_changes(self) -> None:
        files = generate(load_item_spec())

        with tempfile.TemporaryDirectory() as temporary_directory:
            out_root = Path(temporary_directory)
            apply_files(files, out_root, mode='write')
            target = out_root / 'item' / 'admin.py'
            target.write_text(target.read_text(encoding='utf-8').replace('search_fields', 'searchfields'), encoding='utf-8')

            drifted = [result for result in apply_files(files, out_root, mode='check') if result.is_drift]

        self.assertEqual(1, len(drifted))
        self.assertEqual('item/admin.py', drifted[0].file.path)
        self.assertIn('searchfields', drifted[0].diff)

    def test_existing_files_are_never_overwritten_by_default(self) -> None:
        files = generate(load_item_spec())

        with tempfile.TemporaryDirectory() as temporary_directory:
            out_root = Path(temporary_directory)
            target = out_root / 'item' / 'admin.py'
            target.parent.mkdir(parents=True)
            target.write_text('# hand written\n', encoding='utf-8')

            apply_files(files, out_root, mode='write')

            self.assertEqual('# hand written\n', target.read_text(encoding='utf-8'))

    def test_merge_targets_survive_force_mode(self) -> None:
        files = generate(load_item_spec())

        with tempfile.TemporaryDirectory() as temporary_directory:
            out_root = Path(temporary_directory)
            fixtures = out_root / 'tests' / 'fixtures.py'
            fixtures.parent.mkdir(parents=True)
            fixtures.write_text('# hand written fixtures\n', encoding='utf-8')

            apply_files(files, out_root, mode='force')

            self.assertEqual('# hand written fixtures\n', fixtures.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
