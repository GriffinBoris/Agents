import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Optional

from agents.agents_linter.config import LintConfig, ToolConfig

RunStatus = Literal['passed', 'failed', 'skipped', 'missing']


@dataclass(frozen=True)
class RunResult:
    tool: str
    phase: Literal['check', 'fix']
    status: RunStatus
    command: tuple[str, ...]
    cwd: str
    return_code: Optional[int] = None
    output: str = ''
    reason: str = ''


def run_tools(
    config: LintConfig,
    action: Literal['check', 'fix'],
    profiles: set[str],
    *,
    keep_going: bool,
) -> list[RunResult]:
    selected_tools = [tool for tool in config.tools if _matches_profiles(tool, profiles)]
    results: list[RunResult] = []

    if action == 'fix':
        results.extend(_run_phase(selected_tools, 'fix', keep_going=keep_going))

        if _has_blocking_failure(results):
            return results

    results.extend(_run_phase(selected_tools, 'check', keep_going=keep_going))
    return results


def print_results(results: list[RunResult], output_format: Literal['text', 'json']) -> None:
    if output_format == 'json':
        print(json.dumps([asdict(result) for result in results], indent=2))
        return

    for result in results:
        label = result.status.upper().ljust(7)
        print(f'{label} {result.phase.ljust(5)} {result.tool}')

        if result.reason:
            print(f'        {result.reason}')

        if result.output and result.status == 'failed':
            for line in result.output.rstrip().splitlines():
                print(f'        {line}')


def exit_code_for(results: list[RunResult]) -> int:
    return 1 if _has_blocking_failure(results) else 0


def _run_phase(
    tools: list[ToolConfig],
    phase: Literal['check', 'fix'],
    *,
    keep_going: bool,
) -> list[RunResult]:
    results: list[RunResult] = []

    for tool in tools:
        command = tool.fix if phase == 'fix' else tool.check

        if command is None:
            results.append(_skipped_result(tool, phase, (), 'no automatic fix is configured'))
            continue

        result = _run_tool(tool, phase, command)
        results.append(result)

        if not keep_going and result.status in ('failed', 'missing'):
            break

    return results


def _run_tool(
    tool: ToolConfig,
    phase: Literal['check', 'fix'],
    raw_command: tuple[str, ...],
) -> RunResult:
    command = tuple(_expand_argument(argument) for argument in raw_command)
    missing_paths = [path for path in tool.required_paths if not path.exists()]

    if missing_paths:
        relative_paths = ', '.join(str(path) for path in missing_paths)
        return _skipped_result(tool, phase, command, f'required paths are absent: {relative_paths}')

    executable = command[0]
    if not _executable_exists(executable):
        status: RunStatus = 'skipped' if tool.optional else 'missing'
        return RunResult(
            tool=tool.name,
            phase=phase,
            status=status,
            command=command,
            cwd=str(tool.cwd),
            reason=f'executable is unavailable: {executable}',
        )

    completed_process = subprocess.run(  # noqa: S603 - commands come from the checked-in project manifest.
        command,
        cwd=tool.cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    combined_output = '\n'.join(
        output.strip() for output in (completed_process.stdout, completed_process.stderr) if output.strip()
    )

    return RunResult(
        tool=tool.name,
        phase=phase,
        status='passed' if completed_process.returncode == 0 else 'failed',
        command=command,
        cwd=str(tool.cwd),
        return_code=completed_process.returncode,
        output=combined_output,
    )


def _skipped_result(
    tool: ToolConfig,
    phase: Literal['check', 'fix'],
    command: tuple[str, ...],
    reason: str,
) -> RunResult:
    return RunResult(
        tool=tool.name,
        phase=phase,
        status='skipped',
        command=command,
        cwd=str(tool.cwd),
        reason=reason,
    )


def _matches_profiles(tool: ToolConfig, profiles: set[str]) -> bool:
    return not profiles or 'all' in tool.profiles or bool(profiles.intersection(tool.profiles))


def _expand_argument(argument: str) -> str:
    return argument.replace('{python}', sys.executable)


def _executable_exists(executable: str) -> bool:
    if Path(executable).is_absolute():
        return Path(executable).is_file()

    return shutil.which(executable) is not None


def _has_blocking_failure(results: list[RunResult]) -> bool:
    return any(result.status in ('failed', 'missing') for result in results)
