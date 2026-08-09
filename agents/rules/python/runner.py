from dataclasses import dataclass
from pathlib import Path

import libcst as cst
from libcst.metadata import MetadataWrapper

from agents.rules.python.api import Diagnostic, PythonRule
from agents.rules.python.rules import RULES

IGNORED_DIRECTORY_NAMES = frozenset({'.git', '.mypy_cache', '.pytest_cache', '.ruff_cache', '.venv', '__pycache__'})


@dataclass(frozen=True)
class FileResult:
    path: Path
    diagnostics: tuple[Diagnostic, ...]
    changed: bool


def analyze_source(
    source: str,
    path: Path = Path('<memory>'),
    rules: tuple[PythonRule, ...] = RULES,
) -> tuple[Diagnostic, ...]:
    module = cst.parse_module(source)
    wrapper = MetadataWrapper(module)
    source_lines = tuple(source.splitlines())
    diagnostics: list[Diagnostic] = []

    for rule in rules:
        visitor = rule.visitor(path, source_lines)
        wrapper.visit(visitor)
        diagnostics.extend(visitor.diagnostics)

    return tuple(sorted(diagnostics, key=lambda item: (item.line, item.column, item.rule_id)))


def fix_source(source: str, rules: tuple[PythonRule, ...] = RULES) -> str:
    module = cst.parse_module(source)

    for rule in rules:
        if rule.transformer is not None:
            module = module.visit(rule.transformer())

    return module.code


def run_paths(paths: tuple[Path, ...], *, fix: bool) -> tuple[FileResult, ...]:
    results: list[FileResult] = []

    for path in discover_python_files(paths):
        source = path.read_text(encoding='utf-8')
        fixed_source = fix_source(source) if fix else source
        changed = fixed_source != source

        if changed:
            path.write_text(fixed_source, encoding='utf-8')

        diagnostics = analyze_source(fixed_source, path)
        results.append(FileResult(path=path, diagnostics=diagnostics, changed=changed))

    return tuple(results)


def discover_python_files(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    discovered_paths: set[Path] = set()

    for path in paths:
        resolved_path = path.resolve()
        if resolved_path.is_file() and resolved_path.suffix == '.py':
            discovered_paths.add(resolved_path)
            continue

        if not resolved_path.is_dir():
            continue

        for candidate in resolved_path.rglob('*.py'):
            relative_parts = candidate.relative_to(resolved_path).parts
            if any(part in IGNORED_DIRECTORY_NAMES for part in relative_parts):
                continue

            discovered_paths.add(candidate)

    return tuple(sorted(discovered_paths))
