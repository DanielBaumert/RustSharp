#!/usr/bin/env python3
"""Generates a decimal test program: `gen_decimal.py seed count [dotnet|rustsharp]`. Outputs must match."""
import random,sys
r=random.Random(int(sys.argv[1]) if len(sys.argv)>1 else 1); n=int(sys.argv[2]) if len(sys.argv)>2 else 1500
def lit():
    k=r.randrange(8)
    if k==0: return r.choice(['0m','1m','-1m','0.0m','1.00m','0.5m','-0.5m','2m','10m','0.1m','3m','7m','79228162514264337593543950335m','-79228162514264337593543950335m','0.0000000000000000000000000001m','1.5m','2.5m','0.25m'])
    digits=r.randrange(1,30); s=''.join(r.choice('0123456789') for _ in range(digits)).lstrip('0') or '0'
    if len(s)>28: s=s[:28]
    sc=r.randrange(0,min(len(s)+3,28))
    if sc: 
        s=s.rjust(sc+1,'0'); s=s[:-sc]+'.'+s[-sc:]
    return ('-' if r.random()<.4 else '')+s+'m'
# The body is the same for both targets; only the helpers differ. .NET reports errors as exceptions,
# RustSharp has none and uses Rust's checked operations instead.
mode=sys.argv[3] if len(sys.argv)>3 else 'dotnet'
print('using System;\nclass P {')
if mode=='rustsharp':
    print('''  static string Show(Option<decimal> v) => v.IsSome ? v.Unwrap().ToString() : "overflow";
  static string T(char op, decimal a, decimal b)
  {
    if ((op == '/' || op == '%') && b == 0m) return "div0";
    if (op == '+') return Show(decimal.CheckedAdd(a, b));
    if (op == '-') return Show(decimal.CheckedSub(a, b));
    if (op == '*') return Show(decimal.CheckedMul(a, b));
    if (op == '/') return Show(decimal.CheckedDiv(a, b));
    return Show(decimal.CheckedRem(a, b));
  }
  static string L(decimal a) { var v = decimal.CheckedToInt64(a); return v.IsSome ? v.Unwrap().ToString() : "overflow"; }''')
else:
    print('''  static string T(char op, decimal a, decimal b)
  {
    try
    {
      if (op == '+') return (a + b).ToString();
      if (op == '-') return (a - b).ToString();
      if (op == '*') return (a * b).ToString();
      if (op == '/') return (a / b).ToString();
      return (a % b).ToString();
    }
    catch (OverflowException) { return "overflow"; }
    catch (DivideByZeroException) { return "div0"; }
  }
  static string L(decimal a) { try { return ((long)a).ToString(); } catch (OverflowException) { return "overflow"; } }''')
print(' static void Main() {')
ops=['+','-','*','/','%']
for i in range(n):
    a,b=lit(),lit(); op=r.choice(ops)
    print(f"  {{ decimal a = {a}, b = {b}; Console.WriteLine(T('{op}', a, b)); }}")
    if i%7==0: print(f'  {{ decimal a = {a}, b = {b}; Console.WriteLine((a < b).ToString() + (a == b).ToString() + (a >= b).ToString()); }}')
    if i%11==0:
        print(f'  {{ decimal a = {a}; Console.WriteLine(L(a)); }}')
        print(f'  {{ decimal a = {a}; Console.WriteLine(-a); }}')
print(' }\n}')
