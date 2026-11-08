#!/usr/bin/env python3
"""Adds `mut` where the compiler asks for it. Usage: tools/migrate_mut.py file.rscs ..."""
import re, subprocess, sys

ERROR = re.compile(r'^error\[CS99(?:28|29)\]')
NOTE = re.compile(r'declare it with `mut` at line (\d+), column (\d+)')

for path in sys.argv[1:]:
    added = 0
    for _ in range(40):
        out = subprocess.run(['./rustsharp', path, '--check'], capture_output=True, text=True).stderr
        sites = set()
        wanted = False
        for line in out.splitlines():
            if line.startswith('error'): wanted = bool(ERROR.match(line))
            m = NOTE.search(line)
            if m and wanted: sites.add((int(m[1]), int(m[2])))
        if not sites: break
        lines = open(path, encoding='utf-8').read().split('\n')
        for row, col in sorted(sites, reverse=True):
            text = lines[row - 1]
            lines[row - 1] = text[:col - 1] + 'mut ' + text[col - 1:]
            added += 1
        open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'{path}: {added}')
