import difflib
from dataclasses import dataclass
from pathlib import Path

from agents.django_codegen.generator import GeneratedFile


WRITTEN = 'written'
SKIPPED = 'skipped'
DIFFERS = 'differs'
MATCHES = 'matches'
OVERWRITTEN = 'overwritten'


@dataclass(frozen=True)
class WriteResult:
    file: GeneratedFile
    status: str
    diff: str = ''

    @property
    def is_drift(self) -> bool:
        return self.status == DIFFERS


def apply_files(files: list[GeneratedFile], out_root: Path, *, mode: str) -> list[WriteResult]:
    results: list[WriteResult] = []

    for generated in files:
        results.append(apply_file(generated, out_root, mode=mode))

    return results


def apply_file(generated: GeneratedFile, out_root: Path, *, mode: str) -> WriteResult:
    target = out_root / generated.path

    if not target.exists():
        if mode in {'check', 'diff'}:
            return WriteResult(file=generated, status=DIFFERS, diff=render_diff('', generated.content, generated.path))

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(generated.content, encoding='utf-8')
        return WriteResult(file=generated, status=WRITTEN)

    existing = target.read_text(encoding='utf-8')

    if existing == generated.content:
        return WriteResult(file=generated, status=MATCHES)

    if mode == 'force' and not generated.merge:
        target.write_text(generated.content, encoding='utf-8')
        return WriteResult(file=generated, status=OVERWRITTEN)

    if mode in {'check', 'diff'}:
        return WriteResult(file=generated, status=DIFFERS, diff=render_diff(existing, generated.content, generated.path))

    return WriteResult(file=generated, status=SKIPPED, diff=render_diff(existing, generated.content, generated.path))


def render_diff(existing: str, generated: str, path: str) -> str:
    lines = difflib.unified_diff(
        existing.splitlines(keepends=True),
        generated.splitlines(keepends=True),
        fromfile=f'a/{path}',
        tofile=f'b/{path}',
    )
    return ''.join(lines)
