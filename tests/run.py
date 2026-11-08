#!/usr/bin/env python3
"""RustSharp test runner. With --asan, run-pass tests also run under AddressSanitizer and LeakSanitizer.
run-pass/x.rscs + x.expected: must compile, and stdout must equal x.expected (exit 0 unless `// exit: N`).
# An optional x.stderr must equal stderr; panics print there, as in Rust. An optional x.stdin is the input.
compile-fail/x.rscs: every `// error: CSxxxx` must be reported on that line, and nothing else.
Usage: tests/run.py [filter] [-v]
"""
import os,re,subprocess,sys,tempfile,concurrent.futures as cf
root=os.path.dirname(os.path.abspath(__file__)); rustsharp=os.path.join(root,'..','rustsharp')
args=[a for a in sys.argv[1:] if a not in('-v','--asan')]; verbose='-v' in sys.argv; asan='--asan' in sys.argv
flt=args[0] if args else ''
out=tempfile.mkdtemp(prefix='rustsharptest')
def run_pass(p):
    name=os.path.basename(p)[:-5]; exe=os.path.join(out,name); src=open(p).read()
    c=subprocess.run([rustsharp,p,'-o',exe]+(['--asan'] if asan else []),capture_output=True,text=True)
    if c.returncode: return f'compile failed\n{c.stderr}{c.stdout}'
    stdin=open(p[:-5]+'.stdin').read() if os.path.exists(p[:-5]+'.stdin') else ''
    r=subprocess.run([exe],input=stdin,capture_output=True,text=True,timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:exitcode=99'))
    if asan and ('AddressSanitizer' in r.stderr or 'LeakSanitizer' in r.stderr): return 'sanitizer report\n'+r.stderr[:1800]
    want=open(p[:-5]+'.expected').read()
    m=re.search(r'// exit: (\d+)',src); code=int(m.group(1)) if m else 0
    if r.stdout!=want: return f'stdout differs\n--- want\n{want}--- got\n{r.stdout}--- stderr\n{r.stderr}'
    if r.returncode!=code: return f'exit {r.returncode}, want {code}\n{r.stderr}'
    if os.path.exists(p[:-5]+'.stderr') and not asan and r.stderr!=open(p[:-5]+'.stderr').read(): return f'stderr differs\n--- want\n{open(p[:-5]+".stderr").read()}--- got\n{r.stderr}'
def compile_fail(p):
    want=set()
    for i,l in enumerate(open(p),1):
        for code in re.findall(r'// error: (CS\d+)',l): want.add((i,code))
    c=subprocess.run([rustsharp,p,'--check'],capture_output=True,text=True)
    text=c.stderr+c.stdout
    got=set()
    for code,line in re.findall(r'error\[(CS\d+)\]:.*\n\s+--> [^\n]*?:(\d+):\d+',text):
        got.add((int(line),code))
    if c.returncode==0 and want: return 'compiled, but errors were expected'
    if got!=want: return f'missing {sorted(want-got)} unexpected {sorted(got-want)}\n{text}'
jobs=[]
for kind,fn in (('run-pass',run_pass),('compile-fail',compile_fail)):
    d=os.path.join(root,kind)
    for f in sorted(os.listdir(d)):
        if f.endswith('.rscs') and flt in f: jobs.append((kind+'/'+f[:-5],fn,os.path.join(d,f)))
fails=0
with cf.ThreadPoolExecutor(6) as ex:
    for (name,_,_),res in zip(jobs,ex.map(lambda j:j[1](j[2]),jobs)):
        print(('ok    ' if res is None else 'FAIL  ')+name)
        if res: fails+=1; print('   '+res.replace('\n','\n   ')[:2500 if verbose else 900])
print(f'\n{len(jobs)-fails}/{len(jobs)} passed'); sys.exit(1 if fails else 0)
