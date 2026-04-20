import shutil
from pathlib import Path

from .constants import ROOT


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')

    print(f'OK: wrote {display_path(path)}')


def should_copy_file(path: Path, source_root: Path) -> bool:
    if not path.is_file():
        return False

    relative_parts = path.relative_to(source_root).parts
    if '__pycache__' in relative_parts:
        return False

    if path.suffix == '.pyc':
        return False

    return True


def copy_tree(source_root: Path, destination_root: Path) -> None:
    for source_path in sorted(path for path in source_root.rglob('*') if should_copy_file(path, source_root)):
        relative_path = source_path.relative_to(source_root)
        destination_path = destination_root / relative_path

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

        print(f'OK: wrote {display_path(destination_path)}')


def clean_output_dir(path: Path) -> None:
    if not path.exists():
        return

    shutil.rmtree(path)

    print(f'OK: removed {display_path(path)}')


def remove_output_path(path: Path) -> None:
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()

    print(f'OK: removed {display_path(path)}')
