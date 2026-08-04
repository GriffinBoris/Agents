import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from agents.django_codegen.fields import SpecError


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parent.parent
LINKS_PATH = PACKAGE_ROOT / 'guidance_links.yaml'
TEMPLATES_ROOT = PACKAGE_ROOT / 'templates'
GUIDANCE_EXAMPLES_ROOT = REPOSITORY_ROOT / 'agents' / 'guidance' / 'frameworks' / 'django' / 'examples'

ACCEPT_COMMAND = 'python3 agents/scripts/update_codegen_golden.py --accept-guidance'


@dataclass(frozen=True)
class GuidanceLink:
    example: str
    digest: str
    templates: tuple[str, ...]

    @property
    def example_path(self) -> Path:
        return GUIDANCE_EXAMPLES_ROOT / self.example

    def template_paths(self) -> tuple[Path, ...]:
        return tuple(TEMPLATES_ROOT / name for name in self.templates)

    def current_digest(self) -> str:
        return digest_for(self.example_path)

    @property
    def has_drifted(self) -> bool:
        return self.digest != self.current_digest()

    def drift_message(self) -> str:
        templates = ', '.join(self.templates)
        return (
            f'{self.example} changed since the generator templates were last reviewed against it.\n'
            f'  Review these templates and confirm they still match the example: {templates}\n'
            f'  Then record the new baseline with: {ACCEPT_COMMAND}'
        )


def digest_for(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_links(path: Path = LINKS_PATH) -> tuple[GuidanceLink, ...]:
    raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}

    if not isinstance(raw, dict):
        message = f'{path} must contain a mapping of guidance example to templates.'
        raise SpecError(message)

    links: list[GuidanceLink] = []

    for example, entry in raw.items():
        if not isinstance(entry, dict) or 'templates' not in entry:
            message = f'{example} needs a mapping with a templates list in {path.name}.'
            raise SpecError(message)

        links.append(
            GuidanceLink(
                example=example,
                digest=str(entry.get('digest', '')),
                templates=tuple(entry['templates']),
            )
        )

    return tuple(links)


def linked_template_names(links: tuple[GuidanceLink, ...]) -> set[str]:
    return {name for link in links for name in link.templates}


def drifted_links(links: tuple[GuidanceLink, ...]) -> tuple[GuidanceLink, ...]:
    return tuple(link for link in links if link.has_drifted)


def record_digests(path: Path = LINKS_PATH) -> tuple[GuidanceLink, ...]:
    """Re-record every linked example's digest. Only call this after reviewing the templates."""
    links = load_links(path)
    payload = {
        link.example: {'digest': link.current_digest(), 'templates': list(link.templates)}
        for link in links
    }
    header = (
        '# Which Django guidance example defines the shape of which generator template.\n'
        '#\n'
        '# The digest is the sha256 of the example at the time the templates were last\n'
        '# reviewed against it. When an example changes, the generator test suite fails and\n'
        '# names the templates to re-check, so guidance edits cannot silently outrun the\n'
        '# code they are supposed to produce.\n'
        '#\n'
        f'# After reviewing the listed templates, record the new baseline with:\n'
        f'#   {ACCEPT_COMMAND}\n\n'
    )
    path.write_text(header + yaml.safe_dump(payload, sort_keys=True), encoding='utf-8')
    return load_links(path)
