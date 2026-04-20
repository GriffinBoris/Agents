from pathlib import Path

from .constants import BUILD_TARGETS, CONTENT_ROOT, GUIDANCE_ROOT
from .content_loader import load_content_assets, load_guidance_tree
from .document_types import BuildContext
from .targets import ClaudeTarget, CodexTarget, CopilotTarget, GeminiTarget, OpenCodeTarget, SourceTarget

TARGETS = {
    'source': SourceTarget(),
    'opencode': OpenCodeTarget(),
    'claude': ClaudeTarget(),
    'copilot': CopilotTarget(),
    'codex': CodexTarget(),
    'gemini': GeminiTarget(),
}


def build(target: str, out_root: Path, *, clean: bool, include_examples: bool, layout: str) -> None:
    context = BuildContext(
        guidance_tree=load_guidance_tree(GUIDANCE_ROOT),
        assets=load_content_assets(CONTENT_ROOT),
        example_mode='full' if include_examples else 'metadata',
    )

    if target == 'source':
        if layout == 'in-place':
            raise ValueError('The source target does not support --layout in-place.')

        TARGETS['source'].build(context, out_root / 'source', clean=clean)
        return

    targets = BUILD_TARGETS if target == 'all' else (target,)

    if layout == 'in-place' and len(targets) != 1:
        raise ValueError('The in-place layout only supports a single non-source target.')

    for selected_target in targets:
        build_target(selected_target, out_root, context, clean=clean, layout=layout)


def build_target(target: str, out_root: Path, context: BuildContext, *, clean: bool, layout: str) -> None:
    if layout == 'packaged':
        TARGETS[target].build(context, out_root / target, clean=clean)
        return

    TARGETS[target].build_in_place(context, out_root, clean=clean)
