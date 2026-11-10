"""Where features meet: generics, variance, interfaces, async, iterators and destructors together."""
from probelib import Suite

HEADER = '''using System;
using System.Collections.Generic;
using System.Threading.Tasks;
class Stack<T>
{
    List<T> _items = new List<T>();
    public void Push(T x) { _items.Add(x); }
    public Option<T> Pop() => _items.Pop();
    public readonly int Count => _items.Count;
}
'''
SUITE = Suite('combos', HEADER)
case = SUITE.case
R, O, S = 'reject', 'ok', 'strict'

# A RefMut kept in a generic container: through it, only values that live as long as keep may be stored.
case('refmut_in_container', R, '''static void Put<'b>(ref Stack<RefMut<Ref<'b, int>>> s, Ref<'b, int> r) { mut var m = s.Pop().Unwrap(); m.Value = r; }
static void T1()
{
    int longLived = 1;
    mut Ref<int> keep = Ref<int>.Of(in longLived);
    mut var s = new Stack<RefMut<Ref<int>>>();
    s.Push(RefMut<Ref<int>>.Of(ref keep));
    { int shortLived = 2; Put(ref s, Ref<int>.Of(in shortLived)); }
    Console.WriteLine(keep.Value);
}''')
# The same through an Option: Option<&mut &'b T> is invariant in 'b in Rust.
case('refmut_in_option', R, '''static void Put<'b>(Option<RefMut<Ref<'b, int>>> o, Ref<'b, int> r) { mut var m = o.Unwrap(); m.Value = r; }
static void T1()
{
    int longLived = 1;
    mut Ref<int> keep = Ref<int>.Of(in longLived);
    { int shortLived = 2; Put(Some(RefMut<Ref<int>>.Of(ref keep)), Ref<int>.Of(in shortLived)); }
    Console.WriteLine(keep.Value);
}''')
case('refmut_in_option_ok', O, '''static void Put<'b>(Option<RefMut<Ref<'b, int>>> o, Ref<'b, int> r) { mut var m = o.Unwrap(); m.Value = r; }
static void T1()
{
    int longLived = 1, other = 2;
    mut Ref<int> keep = Ref<int>.Of(in longLived);
    Put(Some(RefMut<Ref<int>>.Of(ref keep)), Ref<int>.Of(in other));
    Console.WriteLine(keep.Value);
}''')
# An object with a lifetime seen through an interface keeps that lifetime.
SRC = "interface ISource<T> { readonly T Get(); }\nclass Src<'a> : ISource<Ref<'a, int>> { Ref<'a, int> _r; public Src(Ref<'a, int> r) { _r = r; } public readonly Ref<'a, int> Get() => _r; }\n"
case('interface_keeps_lifetime', R, '''static void T1() { mut Option<ISource<Ref<int>>> keep = None; { int local = 1; keep = Some<ISource<Ref<int>>>(new Src(Ref<int>.Of(in local))); } Console.WriteLine(keep.IsSome); }''', pre=SRC)
case('interface_in_scope', O, '''static void T1() { int local = 1; ISource<Ref<int>> s = new Src(Ref<int>.Of(in local)); Console.WriteLine(s.Get().Value); }''', pre=SRC)
# async with a generic value: the result lives as long as the argument.
case('async_generic_ok', O, '''static async Task<T> Later<T>(T x) { await Task.Yield(); return x; }
static async Task T1() { int a = 1; var r = await Later(Ref<int>.Of(in a)); Console.WriteLine(r.Value); }''')
case('async_generic_outlives', R, '''static async Task<T> Later<T>(T x) { await Task.Yield(); return x; }
static async Task T1() { mut Option<Ref<int>> k = None; { int a = 1; k = Some(await Later(Ref<int>.Of(in a))); } Console.WriteLine(k.IsSome); }''')
# A generic iterator that hands out its value twice moves it twice.
case('generic_yield_twice', R, '''static IEnumerable<T> Twice<T>(T x) { yield return x; yield return x; }''')
case('generic_yield_once', O, '''static IEnumerable<T> Once<T>(T x) { yield return x; }
static void T1() { foreach (var s in Once("a".Clone())) Console.WriteLine(s); }''')
# A generic type with a destructor uses what it holds when it is dropped (drop check).
LOUD = 'class Loud<T> { public T V; public Loud(T v) { V = v; } ~Loud() { Console.WriteLine("drop"); } }\n'
case('generic_dropck', R, '''static void T1() { Loud<Ref<List<int>>> l; var a = new List<int> { 1 }; l = new Loud<Ref<List<int>>>(Ref<List<int>>.Of(in a)); }''', pre=LOUD)
case('generic_dropck_order_ok', O, '''static void T1() { var a = new List<int> { 1 }; var l = new Loud<Ref<List<int>>>(Ref<List<int>>.Of(in a)); }''', pre=LOUD)
# A lambda capturing a T: Rust allows it while the lambda does not escape; RustSharp asks for 'static.
case('generic_local_capture', S, '''delegate int Fn0();
static int Use<T>(T x) { Fn0 f = () => { var y = x; return 1; }; return f(); }
static void T1() { int a = 1; Console.WriteLine(Use(Ref<int>.Of(in a))); }''')
# A RefMut to an element (AsMut, GetMut) is invariant in what the element borrows: a shorter-lived
# reference may not be stored through it. The container keeps each lifetime of its element apart.
case('option_asmut_inner_invariance', R, '''static void T1()
{
    var longLived = new List<int> { 1 };
    mut Option<Ref<List<int>>> o = Some(Ref<List<int>>.Of(in longLived));
    { var shortLived = new List<int> { 2 }; o.AsMut().Unwrap().Value = Ref<List<int>>.Of(in shortLived); }
    Console.WriteLine(o.Unwrap().Value.Count);
}''')
case('option_asmut_inner_ok', O, '''static void T1()
{
    var longLived = new List<int> { 1 };
    var other = new List<int> { 2 };
    mut Option<Ref<List<int>>> o = Some(Ref<List<int>>.Of(in longLived));
    o.AsMut().Unwrap().Value = Ref<List<int>>.Of(in other);
    Console.WriteLine(o.Unwrap().Value.Count);
}''')
case('list_getmut_inner_invariance', R, '''static void T1()
{
    var longLived = new List<int> { 1 };
    mut var l = new List<Ref<List<int>>> { Ref<List<int>>.Of(in longLived) };
    { var shortLived = new List<int> { 2 }; l.GetMut(0).Unwrap().Value = Ref<List<int>>.Of(in shortLived); }
    Console.WriteLine(l.At(0).Value.Count);
}''')
case('list_getmut_inner_ok', O, '''static void T1()
{
    var longLived = new List<int> { 1 };
    var other = new List<int> { 2 };
    mut var l = new List<Ref<List<int>>> { Ref<List<int>>.Of(in longLived) };
    l.GetMut(0).Unwrap().Value = Ref<List<int>>.Of(in other);
    Console.WriteLine(l.At(0).Value.Count);
}''')
# The borrow of the container and what its element borrows are two lifetimes: using the element's
# referent while the container is no longer borrowed is fine, as in Rust.
case('option_asmut_two_lifetimes_ok', O, '''static void T1()
{
    var a = new List<int> { 1 };
    mut Option<Ref<List<int>>> o = Some(Ref<List<int>>.Of(in a));
    var m = o.AsMut().Unwrap();
    Console.WriteLine(m.Value.Value.Count);
    Console.WriteLine(o.Unwrap().Value.Count);
}''')
# A user generic over a type with two lifetimes keeps them apart: storing into one does not tie the other.
PAIR = "struct Pair<'a, 'b> { public Ref<'a, int> A; public Ref<'b, int> B; public Pair(Ref<'a, int> a, Ref<'b, int> b) { A = a; B = b; } }\nclass Box1<T> { public T V; public Box1(T v) { V = v; } }\n"
case('generic_unfolds_pair_ok', O, '''static void T1()
{
    int a = 1;
    Ref<int> keepA;
    {
        int b = 2;
        var box = new Box1<Pair>(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b)));
        keepA = box.V.A;
    }
    Console.WriteLine(keepA.Value);
}''', pre=PAIR)
case('generic_unfolds_pair_short', R, '''static void T1()
{
    int a = 1;
    Ref<int> keepB;
    {
        int b = 2;
        var box = new Box1<Pair>(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b)));
        keepB = box.V.B;
    }
    Console.WriteLine(keepB.Value);
}''', pre=PAIR)
SPAIR = PAIR + "struct SBox<T> { public T V; public SBox(T v) { V = v; } }\n"
case('struct_unfolds_pair_short', R, '''static void T1()
{
    int a = 1;
    Ref<int> keepB;
    { int b = 2; var box = new SBox<Pair>(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b))); keepB = box.V.B; }
    Console.WriteLine(keepB.Value);
}''', pre=SPAIR)
case('struct_unfolds_pair_ok', O, '''static void T1()
{
    int a = 1;
    Ref<int> keepA;
    { int b = 2; var box = new SBox<Pair>(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b))); keepA = box.V.A; }
    Console.WriteLine(keepA.Value);
}''', pre=SPAIR)
case('unfolded_field_store_short', R, '''static void T1()
{
    int a = 1, c = 3;
    mut var box = new SBox<Pair>(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in a)));
    { int b = 2; box.V = new Pair(Ref<int>.Of(in c), Ref<int>.Of(in b)); }
    Console.WriteLine(box.V.B.Value);
}''', pre=SPAIR)
case('unfolded_field_ref_short', R, '''static void T1()
{
    int a = 1;
    Ref<Ref<int>> keep;
    { int b = 2; var box = new SBox<Pair>(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b))); keep = Ref<Ref<int>>.Of(in box.V.B); }
    Console.WriteLine(keep.Value.Value);
}''', pre=SPAIR)
case('option_pair_unwrap_short', R, '''static void T1()
{
    int a = 1;
    Ref<int> keepB;
    { int b = 2; var o = Some(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b))); keepB = o.Unwrap().B; }
    Console.WriteLine(keepB.Value);
}''', pre=PAIR)
case('option_pair_unwrap_ok', O, '''static void T1()
{
    int a = 1;
    Ref<int> keepA;
    { int b = 2; var o = Some(new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b))); keepA = o.Unwrap().A; }
    Console.WriteLine(keepA.Value);
}''', pre=PAIR)
case('list_pair_short', R, '''static void T1()
{
    int a = 1;
    Ref<int> keepB;
    { int b = 2; var l = new List<Pair> { new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b)) }; keepB = l.At(0).B; }
    Console.WriteLine(keepB.Value);
}''', pre=PAIR)
case('list_pair_ok', O, '''static void T1()
{
    int a = 1;
    mut Ref<int> keepA = Ref<int>.Of(in a);
    { int b = 2; var l = new List<Pair> { new Pair(Ref<int>.Of(in a), Ref<int>.Of(in b)) }; keepA = l.At(0).A; }
    Console.WriteLine(keepA.Value);
}''', pre=PAIR)
