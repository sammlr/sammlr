"""Export only explicitly reviewed release files; never read a user database."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/R5_RELEASE_FILES.json'


def assemble(destination: Path) -> None:
    destination = destination.resolve()
    if not destination.is_relative_to(Path('/private/tmp')):
        raise ValueError('Candidate must be isolated under /private/tmp')
    entries = json.loads(MANIFEST.read_text())
    # Validate the entire allowlist before copying anything.
    for relative in entries:
        path = ROOT / relative
        current = ROOT
        for part in Path(relative).parts:
            if part not in {entry.name for entry in current.iterdir()}:
                raise ValueError(f'Non-canonical release path spelling: {relative}')
            current = current / part
        if (not path.is_file() or path.is_symlink()
                or not path.resolve().is_relative_to(ROOT)
                or any(part in relative.split('/') for part in (
                    '.git', '.venv', '__pycache__', 'uploads', 'Backups', 'screens'))
                or path.suffix in ('.db', '.sqlite', '.sqlite3', '.pyc', '.log')
                or path.name.startswith('.env')
                or path.name == '.DS_Store'
                or 'valentin-portrait' in relative):
            raise ValueError(f'Unsafe or missing release file: {relative}')
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for relative in sorted(entries):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        hashes[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
    # Evidence lives beside the candidate, not in its versionable file set.
    destination.with_suffix('.sha256.json').write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + '\n')
    print(f'Exported {len(hashes)} allowlisted files')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    assemble(parser.parse_args().destination)
