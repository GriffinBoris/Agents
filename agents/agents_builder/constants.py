from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_ROOT = ROOT / 'agents'
GUIDANCE_ROOT = AGENTS_ROOT / 'guidance'
CONTENT_ROOT = AGENTS_ROOT / 'content'
TOOLS_ROOT = AGENTS_ROOT / 'tools'


SUPPORTED_FRONTMATTER_FIELDS = {
    'id',
    'title',
    'description',
    'kind',
    'scope',
    'name',
    'tags',
    'applies_to',
    'status',
    'order',
    'role',
}

ALLOWED_STATUSES = {'active', 'draft', 'deprecated'}
BUILD_TARGETS = ('opencode', 'claude', 'copilot', 'codex', 'gemini')
ALL_TARGETS = ('source', *BUILD_TARGETS)
DEFAULT_OPENCODE_JSON = '{\n  "$schema": "https://opencode.ai/config.json",\n  "instructions": [\n    "AGENTS.md"\n  ]\n}\n'
