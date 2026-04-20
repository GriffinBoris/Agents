from pathlib import Path

from .constants import GUIDANCE_ROOT, ROOT
from .document_types import Assets, ContentAsset, GuidancePackage, GuidanceTree, MarkdownDocument
from .frontmatter import parse_frontmatter, validate_frontmatter
from .guidance_renderer import derive_title, normalize_body, sort_key


def load_markdown_document(path: Path, *, expected_kind: str, expected_scope: str, expected_name: str) -> MarkdownDocument:
    raw_text = path.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(raw_text, path)
    validate_frontmatter(frontmatter, path)

    if frontmatter.get('kind') not in {None, expected_kind}:
        raise ValueError(f'Frontmatter kind does not match file location in {path.relative_to(ROOT).as_posix()}')

    if frontmatter.get('scope') not in {None, expected_scope}:
        raise ValueError(f'Frontmatter scope does not match file location in {path.relative_to(ROOT).as_posix()}')

    if frontmatter.get('name') not in {None, expected_name}:
        raise ValueError(f'Frontmatter name does not match file location in {path.relative_to(ROOT).as_posix()}')

    return MarkdownDocument(
        id=frontmatter.get('id') or '-'.join(path.relative_to(GUIDANCE_ROOT).with_suffix('').parts),
        title=frontmatter.get('title') or derive_title(path, body),
        description=str(frontmatter.get('description') or ''),
        kind=expected_kind,
        scope=expected_scope,
        name=expected_name,
        tags=list(frontmatter.get('tags') or []),
        applies_to=list(frontmatter.get('applies_to') or []),
        status=frontmatter.get('status') or 'active',
        order=frontmatter.get('order'),
        path=path,
        raw_text=raw_text,
        body=normalize_body(body),
    )


def load_guidance_tree(root: Path) -> GuidanceTree:
    global_guidance = None
    global_path = root / 'guidance.md'
    if global_path.exists():
        global_guidance = load_markdown_document(
            global_path,
            expected_kind='guidance',
            expected_scope='global',
            expected_name='global',
        )

    language_packages = load_packages(root / 'languages', 'language')
    framework_packages = load_packages(root / 'frameworks', 'framework')

    project_package = None
    project_root = root / 'project'
    if project_root.exists():
        project_package = load_package(project_root, 'project')

    return GuidanceTree(
        global_guidance=global_guidance,
        language_packages=language_packages,
        framework_packages=framework_packages,
        project_package=project_package,
    )


def load_packages(parent: Path, scope: str) -> list[GuidancePackage]:
    if not parent.exists():
        return []

    packages = [
        load_package(path, scope)
        for path in sorted(item for item in parent.iterdir() if item.is_dir())
    ]

    return sorted(packages, key=lambda package: sort_key(package.guidance.order if package.guidance else None, package.root))


def load_package(package_root: Path, scope: str) -> GuidancePackage:
    name = package_root.name
    guidance = None
    guidance_path = package_root / 'guidance.md'

    if guidance_path.exists():
        guidance = load_markdown_document(
            guidance_path,
            expected_kind='guidance',
            expected_scope=scope,
            expected_name=name,
        )

    examples_root = package_root / 'examples'
    examples = []

    if examples_root.exists():
        for example_path in sorted(path for path in examples_root.glob('*.md') if path.is_file()):
            examples.append(
                load_markdown_document(
                    example_path,
                    expected_kind='example',
                    expected_scope=scope,
                    expected_name=name,
                )
            )

    return GuidancePackage(
        scope=scope,
        name=name,
        root=package_root,
        guidance=guidance,
        examples=sorted(examples, key=lambda document: sort_key(document.order, document.path)),
    )


def load_content_assets(root: Path) -> Assets:
    return Assets(
        commands=load_assets(root / 'commands', default_kind='command'),
        skills=load_assets(root / 'skills', default_kind='skill'),
    )


def load_assets(directory: Path, *, default_kind: str) -> list[ContentAsset]:
    if not directory.exists():
        return []

    assets = []

    for path in sorted(candidate for candidate in directory.glob('*.md') if candidate.is_file()):
        raw_text = path.read_text(encoding='utf-8')
        frontmatter, body = parse_frontmatter(raw_text, path)
        validate_frontmatter(frontmatter, path)

        assets.append(
            ContentAsset(
                kind=str(frontmatter.get('kind') or default_kind),
                name=str(frontmatter.get('name') or path.stem),
                description=str(frontmatter.get('description') or ''),
                role=frontmatter.get('role'),
                path=path,
                raw_text=raw_text,
                body=normalize_body(body),
            )
        )

    return assets
