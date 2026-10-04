#!/usr/bin/env python3
"""Audit an explicit public file allowlist; optionally screen local private terms."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

PATTERNS = {
    'personal_path': r'/(?:Users|home)/[A-Za-z0-9_.-]+(?:/|\b)',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'ipv4': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'private_key': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'api_token': r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',
}
ALLOWED_SUFFIXES = {'.md', '.py', '.json', '.yaml', '.toml'}


def audit(root, denylist=()):
    declared = json.loads((root / 'PUBLIC_FILES.json').read_text(encoding='utf-8'))['files']
    problems = []
    if len(declared) != len(set(declared)):
        problems.append({'kind': 'duplicate_allowlist_member'})
    known = set(declared)
    actual = set()
    for directory, dirs, files in os.walk(root):
        # Exclude only this repository's administrative directory.
        if Path(directory) == root and '.git' in dirs:
            dirs.remove('.git')
        for filename in files:
            path = Path(directory) / filename
            actual.add(path.relative_to(root).as_posix())
    for name in sorted(actual - known):
        problems.append({'kind': 'unexpected_file', 'file': name})
    for name in sorted(known - actual):
        problems.append({'kind': 'missing_file', 'file': name})
    checksums = {}
    for name in declared:
        path = root / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            problems.append({'kind': 'unsafe_member', 'file': name})
            continue
        if not path.is_file():
            continue
        if path.suffix not in ALLOWED_SUFFIXES and name != '.gitignore':
            problems.append({'kind': 'unexpected_type', 'file': name})
            continue
        content = path.read_bytes()
        checksums[name] = hashlib.sha256(content).hexdigest()
        text = content.decode('utf-8')
        for label, pattern in PATTERNS.items():
            if re.search(pattern, text):
                problems.append({'kind': label, 'file': name})
        for index, private in enumerate(denylist):
            if private and private.casefold() in (name+'\n'+text).casefold():
                problems.append({'kind': 'private_term', 'file': name, 'term_index': index})
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if link.startswith(('https://', 'http://', '#', 'mailto:')):
                    continue
                linked = (path.parent / link.split('#')[0]).resolve()
                if not linked.is_relative_to(root.resolve()) or not linked.is_file():
                    problems.append({'kind': 'invalid_local_link', 'file': name})
    return dict(public_files=len(declared), problems=problems, all_checks_pass=not problems,
                checksums=checksums, limitations='Pattern scans cannot prove absence of semantic disclosure.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--denylist', type=Path)
    a = p.parse_args()
    terms = a.denylist.read_text(encoding='utf-8').splitlines() if a.denylist else []
    report = audit(a.root.resolve(), terms)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['all_checks_pass'] else 1)


if __name__ == '__main__':
    main()
