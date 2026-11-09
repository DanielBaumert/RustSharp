#!/usr/bin/env python3
"""Runs the probe suites. Usage: tests/probes/run.py [filter] [-v]"""
import importlib, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if a != '-v']
flt = args[0] if args else ''
out = tempfile.mkdtemp(prefix='rustsharpprobes')
total = good = 0
for mod in ('generics', 'variance'):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), mod + '.py')
    if not os.path.exists(path): continue
    g, t = importlib.import_module(mod).SUITE.run(out, flt, '-v' in sys.argv)
    good += g; total += t
print(f'\n{good}/{total} as Rust')
sys.exit(0 if good == total else 1)
