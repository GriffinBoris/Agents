import tempfile
import unittest
from pathlib import Path

from agents.rules.python.rules import RULES
from agents.rules.python.runner import analyze_source, discover_python_files, fix_source, run_paths


class PythonRulesTest(unittest.TestCase):
    def test_rule_registry_has_unique_consistent_ids(self) -> None:
        rule_ids = [rule.id for rule in RULES]

        self.assertEqual(len(rule_ids), len(set(rule_ids)))
        self.assertTrue(all(rule.id == rule.visitor.rule_id for rule in RULES))

    def test_future_annotations_reports_precise_diagnostic(self) -> None:
        diagnostics = analyze_source(
            'from __future__ import annotations\n\nvalue = 1\n',
            Path('example.py'),
        )

        self.assertEqual(1, len(diagnostics))
        self.assertEqual('AGPY001', diagnostics[0].rule_id)
        self.assertEqual(1, diagnostics[0].line)
        self.assertEqual(1, diagnostics[0].column)
        self.assertEqual('error', diagnostics[0].severity)
        self.assertFalse(diagnostics[0].fixable)

    def test_rule_specific_noqa_suppresses_diagnostic(self) -> None:
        diagnostics = analyze_source(
            'value = getattr(record, field_name)  # noqa: AGPY003\n',
            Path('example.py'),
        )

        self.assertEqual((), diagnostics)

    def test_dynamic_attribute_rule_allows_literal_attribute_names(self) -> None:
        source = "literal = getattr(record, 'name')\ndynamic = getattr(record, field_name)\n"

        diagnostics = analyze_source(source, Path('example.py'))

        self.assertEqual(['AGPY003'], [diagnostic.rule_id for diagnostic in diagnostics])
        self.assertEqual(2, diagnostics[0].line)

    def test_concrete_requests_verb_rule_is_fixable_and_idempotent(self) -> None:
        source = "response = requests.request('POST', url, json=payload)\n"

        diagnostics = analyze_source(source, Path('client.py'))
        fixed_source = fix_source(source)

        self.assertEqual(['AGPY005'], [diagnostic.rule_id for diagnostic in diagnostics])
        self.assertTrue(diagnostics[0].fixable)
        self.assertEqual('response = requests.post(url, json=payload)\n', fixed_source)
        self.assertEqual(fixed_source, fix_source(fixed_source))
        self.assertEqual((), analyze_source(fixed_source, Path('client.py')))

    def test_concrete_requests_verb_fixer_handles_keyword_method(self) -> None:
        source = "response = requests.request(url=url, method='PATCH', json=payload)\n"

        fixed_source = fix_source(source)

        self.assertEqual('response = requests.patch(url=url, json=payload)\n', fixed_source)

    def test_fix_mode_writes_safe_refactors_then_rechecks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / 'client.py'
            source_path.write_text("response = requests.request('GET', url)\n", encoding='utf-8')

            results = run_paths((source_path,), fix=True)

            self.assertEqual(1, len(results))
            self.assertTrue(results[0].changed)
            self.assertEqual((), results[0].diagnostics)
            self.assertEqual('response = requests.get(url)\n', source_path.read_text(encoding='utf-8'))

    def test_file_discovery_ignores_virtual_environments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            included_path = root / 'backend' / 'views.py'
            ignored_path = root / '.venv' / 'lib' / 'library.py'
            included_path.parent.mkdir(parents=True)
            ignored_path.parent.mkdir(parents=True)
            included_path.write_text('value = 1\n', encoding='utf-8')
            ignored_path.write_text('value = 2\n', encoding='utf-8')

            discovered_paths = discover_python_files((root,))

            self.assertEqual((included_path.resolve(),), discovered_paths)


if __name__ == '__main__':
    unittest.main()
