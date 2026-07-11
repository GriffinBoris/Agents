import tempfile
import unittest
from pathlib import Path

from agents.agents_builder.build_runner import build


class BuildTargetsTest(unittest.TestCase):
    def test_all_builds_claude_codex_and_opencode_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)

            build(
                'all',
                output_root,
                clean=True,
                include_examples=False,
                layout='packaged',
            )

            expected_files = {
                'claude': (
                    '.claude/CLAUDE.md',
                    '.claude/commands/pull-guidance-from-agents.md',
                    '.claude/skills/architecture-audit/SKILL.md',
                ),
                'codex': (
                    '.agents/AGENTS.md',
                    '.codex/config.toml',
                    '.agents/skills/full-review/SKILL.md',
                    '.agents/skills/pull-guidance-from-agents/SKILL.md',
                    '.agents/skills/architecture-audit/SKILL.md',
                ),
                'opencode': (
                    'opencode.json',
                    '.opencode/AGENTS.md',
                    '.opencode/commands/full-review.md',
                    '.opencode/skills/architecture-audit/SKILL.md',
                ),
            }

            for target, relative_paths in expected_files.items():
                with self.subTest(target=target):
                    target_root = output_root / target
                    self.assertTrue(target_root.is_dir())

                    for relative_path in relative_paths:
                        generated_file = target_root / relative_path
                        self.assertTrue(
                            generated_file.is_file(),
                            f'{target} did not generate {relative_path}',
                        )
                        self.assertTrue(
                            generated_file.read_text(encoding='utf-8').strip(),
                            f'{target} generated an empty {relative_path}',
                        )

            self.assertFalse((output_root / 'claude' / 'CLAUDE.md').exists())
            self.assertFalse((output_root / 'claude' / 'AGENTS.md').exists())
            self.assertIn('.opencode', {path.name for path in (output_root / 'opencode').iterdir()})
            self.assertNotIn('.OpenCode', {path.name for path in (output_root / 'opencode').iterdir()})
            self.assertNotIn('.Codex', {path.name for path in (output_root / 'codex').iterdir()})
            claude_guidance = (output_root / 'claude' / '.claude' / 'CLAUDE.md').read_text(encoding='utf-8')
            self.assertIn('# Claude Code Guidance', claude_guidance)
            self.assertNotIn('@AGENTS.md', claude_guidance)

            opencode_config = (output_root / 'opencode' / 'opencode.json').read_text(encoding='utf-8')
            self.assertIn('".opencode/AGENTS.md"', opencode_config)

            codex_config = (output_root / 'codex' / '.codex' / 'config.toml').read_text(encoding='utf-8')
            self.assertIn('project_doc_fallback_filenames = [".agents/AGENTS.md"]', codex_config)

            codex_command_skill = (
                output_root / 'codex' / '.agents' / 'skills' / 'full-review' / 'SKILL.md'
            ).read_text(encoding='utf-8')
            self.assertIn('name: full-review', codex_command_skill)
            self.assertIn('the full arguments supplied with this skill', codex_command_skill)

    def test_in_place_targets_keep_guidance_out_of_the_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)

            for target in ('claude', 'opencode', 'codex'):
                build(
                    target,
                    output_root,
                    clean=True,
                    include_examples=False,
                    layout='in-place',
                )

            root_files = {path.name for path in output_root.iterdir() if path.is_file()}
            self.assertEqual({'opencode.json'}, root_files)
            self.assertTrue((output_root / '.claude' / 'CLAUDE.md').is_file())
            self.assertTrue((output_root / '.opencode' / 'AGENTS.md').is_file())
            self.assertTrue((output_root / '.agents' / 'AGENTS.md').is_file())
            self.assertTrue((output_root / '.codex' / 'config.toml').is_file())


if __name__ == '__main__':
    unittest.main()
