"""Variance, as in Rust: derived per slot from the fields; &mut T is invariant in T."""
from probelib import Suite

HEADER = '''using System;
using System.Collections.Generic;
'''
SUITE = Suite('variance', HEADER)
case = SUITE.case

# Rust: fn assign<'a>(m: &'a mut &'a i32, s: &'a i32) { *m = s; } -- the call with a shorter s is rejected,
# because &mut T is invariant in T: keep's type would have to carry the inner block's lifetime.
case('rej_refmut_inner_invariance', 'reject', '''static void Assign<'a>(RefMut<'a, Ref<'a, List<int>>> m, Ref<'a, List<int>> s) { m.Value = s; }
static void T1()
{
    var longLived = new List<int> { 1 };
    mut Ref<List<int>> keep = Ref<List<int>>.Of(in longLived);
    {
        var shortLived = new List<int> { 1, 2, 3 };
        Assign(RefMut<Ref<List<int>>>.Of(ref keep), Ref<List<int>>.Of(in shortLived));
    }
    Console.WriteLine(keep.Value.Count);
}''')
# With one 'a for both, keep stays borrowed exclusively for all of 'a, so reading it later is rejected,
# as Rust rejects `&'a mut &'a T` here (E0502).
case('rej_refmut_same_lifetime', 'reject', '''static void Assign<'a>(RefMut<'a, Ref<'a, List<int>>> m, Ref<'a, List<int>> s) { m.Value = s; }
static void T1()
{
    var longLived = new List<int> { 1 };
    var other = new List<int> { 1, 2 };
    mut Ref<List<int>> keep = Ref<List<int>>.Of(in longLived);
    Assign(RefMut<Ref<List<int>>>.Of(ref keep), Ref<List<int>>.Of(in other));
    Console.WriteLine(keep.Value.Count);
}''')
# Rust: fn assign<'a, 'b>(m: &'a mut &'b i32, s: &'b i32) -- the borrow of keep ends with the call.
case('ok_refmut_two_lifetimes', 'ok', '''static void Assign<'a, 'b>(RefMut<'a, Ref<'b, List<int>>> m, Ref<'b, List<int>> s) { m.Value = s; }
static void T1()
{
    var longLived = new List<int> { 1 };
    var other = new List<int> { 1, 2 };
    mut Ref<List<int>> keep = Ref<List<int>>.Of(in longLived);
    Assign(RefMut<Ref<List<int>>>.Of(ref keep), Ref<List<int>>.Of(in other));
    Console.WriteLine(keep.Value.Count);
}''')
# Two lifetimes, but s still lives too short for keep: rejected.
case('rej_refmut_two_lifetimes_short', 'reject', '''static void Assign<'a, 'b>(RefMut<'a, Ref<'b, List<int>>> m, Ref<'b, List<int>> s) { m.Value = s; }
static void T1()
{
    var longLived = new List<int> { 1 };
    mut Ref<List<int>> keep = Ref<List<int>>.Of(in longLived);
    {
        var shortLived = new List<int> { 1, 2, 3 };
        Assign(RefMut<Ref<List<int>>>.Of(ref keep), Ref<List<int>>.Of(in shortLived));
    }
    Console.WriteLine(keep.Value.Count);
}''')
# Ref is covariant: a longer-lived Ref may stand in for a shorter one.
case('ok_ref_covariant', 'ok', '''static int Both<'a>(Ref<'a, int> x, Ref<'a, int> y) => x.Value + y.Value;
static void T1() { int a = 1; { int b = 2; Console.WriteLine(Both(Ref<int>.Of(in a), Ref<int>.Of(in b))); } }''')

# A cell that changes its value through a shared reference must hold it in an UnsafeCell, which makes it
# invariant: Rust's Cell<T>. Through `in MyCell<Ref<'a, …>>` only an 'a as long as the cell's own may go in.
MYCELL = '''class MyCell<T>
{
    UnsafeCell<T> _v;
    public MyCell(T x) { _v = new UnsafeCell<T>(x); }
    public readonly unsafe void Set(T x) { *_v.Get() = x; }
    public readonly unsafe ref readonly T Peek() => ref *_v.Get();
}
'''
case('rej_unsafecell_invariance', 'reject', '''static void Put<'a>(in MyCell<Ref<'a, List<int>>> c, Ref<'a, List<int>> r) { c.Set(r); }
static void T1()
{
    var longLived = new List<int> { 1 };
    var cell = new MyCell<Ref<List<int>>>(Ref<List<int>>.Of(in longLived));
    {
        var shortLived = new List<int> { 1, 2, 3 };
        Put(in cell, Ref<List<int>>.Of(in shortLived));
    }
    Console.WriteLine(cell.Peek().Value.Count);
}''', pre=MYCELL)
case('ok_unsafecell_same_scope', 'ok', '''static void Put<'a>(in MyCell<Ref<'a, List<int>>> c, Ref<'a, List<int>> r) { c.Set(r); }
static void T1()
{
    var longLived = new List<int> { 1 };
    var other = new List<int> { 1, 2 };
    var cell = new MyCell<Ref<List<int>>>(Ref<List<int>>.Of(in longLived));
    Put(in cell, Ref<List<int>>.Of(in other));
    Console.WriteLine(cell.Peek().Value.Count);
}''', pre=MYCELL)
# A collection is covariant, like Vec: a Stack of longer-lived references may be read as a shorter one.
STACK = 'class Stack<T> { List<T> _items = new List<T>(); public void Push(T x) { _items.Add(x); } public readonly int Count => _items.Count; }\n'
case('ok_collection_covariant', 'ok', '''static int Count<'a>(in Stack<Ref<'a, int>> s, Ref<'a, int> extra) => s.Count + extra.Value;
static void T1() { int a = 1; mut var s = new Stack<Ref<int>>(); s.Push(Ref<int>.Of(in a)); { int b = 2; Console.WriteLine(Count(in s, Ref<int>.Of(in b))); } Console.WriteLine(s.Count); }''', pre=STACK)
# A struct holding `ref 'a T` is invariant in T, as &'a mut T is.
case('rej_ref_field_invariance', 'reject', '''static void Assign<'a, 'b>(mut MutView<'a, Ref<'b, List<int>>> v, Ref<'b, List<int>> s) { v.Target = s; }
static void T1()
{
    var longLived = new List<int> { 1 };
    mut Ref<List<int>> keep = Ref<List<int>>.Of(in longLived);
    {
        var shortLived = new List<int> { 1, 2, 3 };
        Assign(new MutView<'_, Ref<List<int>>>(ref keep), Ref<List<int>>.Of(in shortLived));
    }
    Console.WriteLine(keep.Value.Count);
}''', pre="ref struct MutView<'a, T> { public ref 'a T Target; public MutView(ref 'a T t) { Target = ref t; } }\n")
