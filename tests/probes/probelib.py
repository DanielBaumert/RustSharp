"""Probe suites: small programs with the verdict Rust would give, 'ok' or 'reject'.
'strict' marks a program Rust accepts but RustSharp deliberately rejects (sound, a known limitation).
Each suite module defines HEADER and calls case(); run them with tests/probes/run.py.
"""
import os, re, subprocess, concurrent.futures as cf

ROOT = os.path.dirname(os.path.abspath(__file__))
RUSTSHARP = os.path.join(ROOT, '..', '..', 'rustsharp')

class Suite:
    def __init__(self, name, header):
        self.name, self.header, self.cases = name, header, {}

    def case(self, name, expect, body, pre=''):
        assert expect in ('ok', 'reject', 'strict'), expect
        self.cases[name] = (expect, self.header + pre + 'class P {\n' + body + '\n    static void Main() { }\n}\n')

    def run(self, out, flt='', verbose=False):
        os.makedirs(out, exist_ok=True)
        def one(n):
            expect, src = self.cases[n]
            f = os.path.join(out, f'{self.name}_{n}.rscs')
            open(f, 'w').write(src)
            c = subprocess.run([RUSTSHARP, f, '--check'], capture_output=True, text=True)
            codes = sorted(set(re.findall(r'error\[(CS\d+)\]', c.stderr + c.stdout)))
            got = 'ok' if c.returncode == 0 else 'reject'
            want = 'reject' if expect == 'strict' else expect
            return n, expect, want, got, codes, c.stderr + c.stdout
        bad = 0
        with cf.ThreadPoolExecutor(8) as ex:
            for n, expect, want, got, codes, text in ex.map(one, [k for k in self.cases if flt in k]):
                fine = want == got
                bad += not fine
                print(f'{"  " if fine else "XX"} {self.name}/{n:28} want {expect:6} got {got:6} {" ".join(codes)}')
                if verbose and not fine: print('   ' + text[:1500].replace('\n', '\n   '))
        return len([k for k in self.cases if flt in k]) - bad, len([k for k in self.cases if flt in k])
