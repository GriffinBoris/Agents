from dataclasses import dataclass
from pathlib import Path

from agents.codegen.profile import Profile
from agents.codegen.resource import ResourceSpec


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    content: str
    merge: bool = False
    note: str = ''


class BaseGenerator:
    """One target language or framework.

    A generator turns a framework-neutral ResourceSpec into files. It owns its own
    templates, its own section of the project profile, and its own output root, so
    adding a target never requires editing the shared core.
    """

    name: str
    templates_root: Path

    def output_root(self, profile: Profile) -> str:
        """Where this target's files land, relative to the repository root."""
        raise NotImplementedError

    def generate(self, spec: ResourceSpec) -> list[GeneratedFile]:
        raise NotImplementedError

    def describe(self, spec: ResourceSpec) -> str:
        """Short label for CLI output."""
        return f'{spec.app}/{spec.feature}'
