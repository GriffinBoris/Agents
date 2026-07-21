import io
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.agents_builder.build_runner import build
from agents.agents_linter.cli import main
from agents.agents_linter.config import LintConfig, ToolConfig, load_config
from agents.agents_linter.runner import exit_code_for, print_results, run_tools
from agents.rules.django_checks.policy import missing_admin_audit_fields


class AgentsLinterTest(unittest.TestCase):
    def test_load_config_reads_commands_relative_to_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = root / '.agents-lint.toml'
            config_path.write_text(
                """\
version = 1

[[tools]]
name = "example"
profiles = ["backend"]
cwd = "backend"
required_paths = ["backend/pyproject.toml"]
check = ["{python}", "-c", "raise SystemExit(0)"]
optional = true
""",
                encoding='utf-8',
            )

            config = load_config(config_path, root)

            self.assertEqual(1, len(config.tools))
            self.assertEqual(root / 'backend', config.tools[0].cwd)
            self.assertEqual((root / 'backend' / 'pyproject.toml',), config.tools[0].required_paths)
            self.assertIsNone(config.tools[0].fix)

    def test_fix_runs_safe_fixes_then_verifies_with_check_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            marker = root / 'formatted.txt'
            tool = ToolConfig(
                name='formatter',
                profiles=('backend',),
                check=(
                    '{python}',
                    '-c',
                    "from pathlib import Path; raise SystemExit(Path('formatted.txt').read_text() != 'fixed')",
                ),
                fix=(
                    '{python}',
                    '-c',
                    "from pathlib import Path; Path('formatted.txt').write_text('fixed')",
                ),
                cwd=root,
                required_paths=(),
                optional=False,
            )
            config = LintConfig(path=root / '.agents-lint.toml', tools=(tool,))

            results = run_tools(config, 'fix', {'backend'}, keep_going=True)

            self.assertEqual(['fix', 'check'], [result.phase for result in results])
            self.assertEqual(['passed', 'passed'], [result.status for result in results])
            self.assertEqual('fixed', marker.read_text(encoding='utf-8'))
            self.assertEqual(0, exit_code_for(results))

    def test_absent_project_area_skips_its_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tool = ToolConfig(
                name='frontend-eslint',
                profiles=('frontend',),
                check=('eslint', '.'),
                fix=None,
                cwd=root,
                required_paths=(root / 'frontend' / 'package.json',),
                optional=False,
            )
            config = LintConfig(path=root / '.agents-lint.toml', tools=(tool,))

            results = run_tools(config, 'check', set(), keep_going=True)

            self.assertEqual('skipped', results[0].status)
            self.assertIn('required paths are absent', results[0].reason)
            self.assertEqual(0, exit_code_for(results))

    def test_json_output_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tool = ToolConfig(
                name='python-check',
                profiles=('backend',),
                check=('{python}', '-c', "print('checked')"),
                fix=None,
                cwd=root,
                required_paths=(),
                optional=False,
            )
            config = LintConfig(path=root / '.agents-lint.toml', tools=(tool,))
            results = run_tools(config, 'check', {'backend'}, keep_going=True)

            output = io.StringIO()
            with patch('sys.stdout', output):
                print_results(results, 'json')

            payload = json.loads(output.getvalue())
            self.assertEqual('python-check', payload[0]['tool'])
            self.assertEqual('passed', payload[0]['status'])
            self.assertEqual('checked', payload[0]['output'])

    def test_cli_uses_project_manifest_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / '.agents-lint.toml').write_text(
                f"""\
version = 1

[[tools]]
name = "python-check"
profiles = ["backend"]
cwd = "."
check = ["{sys.executable}", "-c", "raise SystemExit(0)"]
""",
                encoding='utf-8',
            )

            self.assertEqual(0, main(['check', '--root', str(root), '--output', 'json']))

    def test_source_build_includes_runner_and_rule_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)

            build(
                'source',
                output_root,
                clean=True,
                include_examples=False,
                layout='packaged',
            )

            source_root = output_root / 'source'
            expected_paths = (
                'agents/lint_agents.py',
                'agents/agents_linter/runner.py',
                'agents/rules/catalog.toml',
                'agents/rules/config/agents-lint.toml',
                'agents/rules/eslint-plugin-agents/index.js',
            )

            for relative_path in expected_paths:
                with self.subTest(path=relative_path):
                    self.assertTrue((source_root / relative_path).is_file())


class RuleCatalogTest(unittest.TestCase):
    def test_catalog_has_unique_ids_and_existing_guidance(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        catalog_path = repository_root / 'agents' / 'rules' / 'catalog.toml'

        with catalog_path.open('rb') as catalog_file:
            catalog = tomllib.load(catalog_file)

        rules = catalog['rules']
        ids = [rule['id'] for rule in rules]
        self.assertEqual(len(ids), len(set(ids)))

        for rule in rules:
            with self.subTest(rule=rule['id']):
                self.assertRegex(rule['id'], r'^AG(?:PY|DJ|VUE)\d{3}$')
                guidance_path = rule['guidance'].split('#', maxsplit=1)[0]
                self.assertTrue((repository_root / guidance_path).is_file())
                self.assertIn(rule['fix'], {'safe', 'unsafe', 'none'})
                self.assertIn(rule['status'], {'active', 'experimental', 'planned'})


class DjangoCheckPolicyTest(unittest.TestCase):
    def test_audited_admin_requires_all_audit_fields(self) -> None:
        missing_fields = missing_admin_audit_fields(
            {'id', 'name', 'created_ts', 'updated_ts'},
            ('id', 'name'),
        )

        self.assertEqual(('created_ts', 'updated_ts'), missing_fields)

    def test_non_audited_model_is_outside_the_rule(self) -> None:
        missing_fields = missing_admin_audit_fields(
            {'id', 'name'},
            ('name',),
        )

        self.assertEqual((), missing_fields)


if __name__ == '__main__':
    unittest.main()
