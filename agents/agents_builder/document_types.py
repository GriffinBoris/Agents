from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class MarkdownDocument:
    id: str
    title: str
    description: str
    kind: str
    scope: str
    name: str
    tags: list[str]
    applies_to: list[str]
    status: str
    order: Optional[int]
    path: Path
    raw_text: str
    body: str


@dataclass(frozen=True)
class GuidancePackage:
    scope: str
    name: str
    root: Path
    guidance: Optional[MarkdownDocument]
    examples: list[MarkdownDocument]


@dataclass(frozen=True)
class GuidanceTree:
    global_guidance: Optional[MarkdownDocument]
    language_packages: list[GuidancePackage]
    framework_packages: list[GuidancePackage]
    project_package: Optional[GuidancePackage]


@dataclass(frozen=True)
class ContentAsset:
    kind: str
    name: str
    description: str
    role: Optional[str]
    path: Path
    raw_text: str
    body: str


@dataclass(frozen=True)
class Assets:
    commands: list[ContentAsset]
    skills: list[ContentAsset]


@dataclass(frozen=True)
class BuildContext:
    guidance_tree: GuidanceTree
    assets: Assets
    example_mode: str
