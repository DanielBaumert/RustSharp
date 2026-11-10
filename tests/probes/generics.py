"""Generic code with lifetimes: every type parameter carries a lifetime of its own, as in Rust."""
from probelib import Suite

HEADER = '''using System;
using System.Collections.Generic;
using System.Threading;
class Stack<T>
{
    List<T> _items = new List<T>();
    public void Push(T x) { _items.Add(x); }
    public Option<T> Pop() => _items.Pop();
    public readonly int Count => _items.Count;
}
class Pair<K, V> { public K Key; public V Val; public Pair(K k, V v) { Key = k; Val = v; } }
interface IStore<U> { void Store(U x); }
class Acc<V> : IStore<V> { public List<V> Items = new List<V>(); public void Store(V x) { Items.Add(x); } }
class Static<T> { public static Option<T> Slot = None; }
class G { public static readonly int V = 7; }
'''
SUITE = Suite('generics', HEADER)
case = SUITE.case
HP = "class HP<'a, 'b> { public Ref<'a, int> X; public Ref<'b, int> Y; public HP(Ref<'a, int> x, Ref<'b, int> y) { X = x; Y = y; } }\n"
WRAPPER = 'class Wrapper<T, U> where T : IStore<U> { T _inner; public Wrapper(T i) { _inner = i; } public void Put(U u) { _inner.Store(u); } public readonly int Count() => 0; }\n'
OUTER = 'class Outer<T> { Stack<T> _inner = new Stack<T>(); public void Add(T x) { _inner.Push(x); } public readonly int N() => _inner.Count; }\n'

case('ok_stack', 'ok', '''static void T1() { int a = 1; mut var s = new Stack<Ref<int>>(); s.Push(Ref<int>.Of(in a)); Console.WriteLine(s.Count); }''')
case('ok_id', 'ok', '''static T Id<T>(T x) => x;
static void T1() { int a = 1; var r = Id(Ref<int>.Of(in a)); Console.WriteLine(r.Value); }''')
case('ok_static_bound', 'ok', '''static void Keep<T>(T x) where T : 'static { unsafe { Static<T>.Slot = Some(x); } }
static void T1() { Keep(Ref<int>.Of(in G.V)); }''')
case('ok_plain', 'ok', '''static void T1() { mut var s = new Stack<int>(); s.Push(1); Console.WriteLine(s.Count); }''')
case('ok_generic_calls_generic', 'ok', '''static void PushAll<T>(ref Stack<T> s, T a, T b) { s.Push(a); s.Push(b); }
static void T1() { int a = 1, b = 2; mut var s = new Stack<Ref<int>>(); PushAll(ref s, Ref<int>.Of(in a), Ref<int>.Of(in b)); Console.WriteLine(s.Count); }''')
case('ok_pop', 'ok', '''static void T1() { int a = 1; mut var s = new Stack<Ref<int>>(); s.Push(Ref<int>.Of(in a)); if (s.Pop() is Some(var r)) Console.WriteLine(r.Value); }''')
case('ok_pair', 'ok', '''static void T1() { int a = 1; string b = "x".Clone(); var p = new Pair<Ref<int>, str>(Ref<int>.Of(in a), b); Console.WriteLine(p.Key.Value); }''')
case('ok_acc', 'ok', '''static void T1() { int a = 1; mut var acc = new Acc<Ref<int>>(); acc.Store(Ref<int>.Of(in a)); Console.WriteLine(acc.Items.Count); }''')
case('ok_bound_store', 'ok', '''static void F<T, U>(ref T a, U b) where T : IStore<U> { a.Store(b); }
static void T1() { int x = 1; mut var acc = new Acc<Ref<int>>(); F(ref acc, Ref<int>.Of(in x)); Console.WriteLine(acc.Items.Count); }''')
case('ok_type_bound', 'ok', '''static void T1() { int a = 1; mut var w = new Wrapper<Acc<Ref<int>>, Ref<int>>(new Acc<Ref<int>>()); w.Put(Ref<int>.Of(in a)); Console.WriteLine(w.Count()); }''', pre=WRAPPER)
case('ok_nested_field', 'ok', '''static void T1() { int a = 1; mut var o = new Outer<Ref<int>>(); o.Add(Ref<int>.Of(in a)); Console.WriteLine(o.N()); }''', pre=OUTER)
case('ok_local_closure', 'ok', '''delegate int Fn0();
static int Use<T>(T x) { Fn0 f = () => 1; return f(); }
static void T1() { int a = 1; Console.WriteLine(Use(Ref<int>.Of(in a))); }''')
case('ok_type_level_static', 'ok', '''static void T1() { mut var r = new Registry<Ref<int>>(); r.Add(Ref<int>.Of(in G.V)); }''', pre="class Registry<T> where T : 'static { public void Add(T x) { unsafe { Static<T>.Slot = Some(x); } } }\n")

case('rej_static_store', 'reject', '''static void Keep<T>(T x) { unsafe { Static<T>.Slot = Some(x); } }''')
case('rej_static_bound_call', 'reject', '''static void Keep<T>(T x) where T : 'static { unsafe { Static<T>.Slot = Some(x); } }
static void T1() { int a = 1; Keep(Ref<int>.Of(in a)); }''')
case('rej_mutate_held', 'reject', '''static void T1() { mut int a = 1; mut var s = new Stack<Ref<int>>(); s.Push(Ref<int>.Of(in a)); a = 2; Console.WriteLine(s.Count); }''')
case('rej_outlive_stack', 'reject', '''static void T1() { mut var s = new Stack<Ref<int>>(); { int a = 1; s.Push(Ref<int>.Of(in a)); } Console.WriteLine(s.Count); }''')
case('rej_outlive_id', 'reject', '''static T Id<T>(T x) => x;
static void T1() { mut Option<Ref<int>> k = None; { int a = 1; k = Some(Id(Ref<int>.Of(in a))); } Console.WriteLine(k.IsSome); }''')
case('rej_pop_outlive', 'reject', '''static void T1() { mut Option<Ref<int>> k = None; { int a = 1; mut var s = new Stack<Ref<int>>(); s.Push(Ref<int>.Of(in a)); k = s.Pop(); } Console.WriteLine(k.IsSome); }''')
case('rej_class_static', 'reject', '''static void T1() { }''', pre='class Leak<T> { public static Option<T> Slot = None; public void Put(T x) { unsafe { Slot = Some(x); } } }\n')
case('rej_thread', 'reject', '''static void Send<T>(T x) { var t = Thread.Run(move () => { var y = x; return 0; }); }''')
case('rej_bound_store', 'reject', '''static void F<T, U>(ref T a, U b) where T : IStore<U> { a.Store(b); }
static void T1() { mut var acc = new Acc<Ref<int>>(); { int x = 1; F(ref acc, Ref<int>.Of(in x)); } Console.WriteLine(acc.Items.Count); }''')
case('rej_via_interface', 'reject', '''static void T1() { mut var acc = new Acc<Ref<int>>(); { int x = 1; mut IStore<Ref<int>> i = acc; i.Store(Ref<int>.Of(in x)); acc = (Acc<Ref<int>>)i; } Console.WriteLine(acc.Items.Count); }''')
case('rej_pair_key', 'reject', '''static void T1() { mut Option<Ref<int>> k = None; string b = "x".Clone(); { int a = 1; var p = new Pair<Ref<int>, str>(Ref<int>.Of(in a), b); k = Some(p.Key); } Console.WriteLine(k.IsSome); }''')
case('rej_closure_escape', 'reject', '''delegate T Mk<T>();
static Mk<T> Make<T>(T x) => move () => x;
static void T1() { mut Option<Mk<Ref<int>>> k = None; { int a = 1; k = Some(Make(Ref<int>.Of(in a))); } Console.WriteLine(k.IsSome); }''')
case('rej_out_param', 'reject', '''static void Out<T>(T x, out Option<T> o) { o = Some(x); }
static void T1() { mut Option<Ref<int>> k = None; { int a = 1; Out(Ref<int>.Of(in a), out k); } Console.WriteLine(k.IsSome); }''')
case('rej_ref_param', 'reject', '''static void Put<T>(ref Option<T> slot, T x) { slot = Some(x); }
static void T1() { mut Option<Ref<int>> k = None; { int a = 1; Put(ref k, Ref<int>.Of(in a)); } Console.WriteLine(k.IsSome); }''')
case('rej_wrap', 'reject', '''static Option<T> Wrap<T>(T x) => Some(x);
static void T1() { mut Option<Ref<int>> k = None; { int a = 1; k = Wrap(Ref<int>.Of(in a)); } Console.WriteLine(k.IsSome); }''')
case('rej_return_container', 'reject', '''static Stack<T> One<T>(T x) { mut var s = new Stack<T>(); s.Push(x); return s; }
static void T1() { mut var keep = new Stack<Ref<int>>(); { int a = 1; keep = One(Ref<int>.Of(in a)); } Console.WriteLine(keep.Count); }''')
case('rej_into_interface_param', 'reject', '''static void Into<T>(ref IStore<T> st, T x) { st.Store(x); }
static void T1() { mut IStore<Ref<int>> st = new Acc<Ref<int>>(); { int a = 1; Into(ref st, Ref<int>.Of(in a)); } Console.WriteLine(st is Acc<Ref<int>>); }''')
case('rej_struct_generic', 'reject', '''static SBox<Ref<int>> Make() { int a = 1; return new SBox<Ref<int>> { V = Ref<int>.Of(in a) }; }''', pre='struct SBox<T> { public T V; }\n')
case('rej_type_bound', 'reject', '''static void T1() { mut var w = new Wrapper<Acc<Ref<int>>, Ref<int>>(new Acc<Ref<int>>()); { int a = 1; w.Put(Ref<int>.Of(in a)); } Console.WriteLine(w.Count()); }''', pre=WRAPPER)
case('rej_nested_field', 'reject', '''static void T1() { mut var o = new Outer<Ref<int>>(); { int a = 1; o.Add(Ref<int>.Of(in a)); } Console.WriteLine(o.N()); }''', pre=OUTER)
case('rej_generic_thread_field', 'reject', '''static void T1() { int a = 1; mut var s = new Stack<Ref<int>>(); s.Push(Ref<int>.Of(in a)); var t = Thread.Run(move () => s.Count); }''')
case('rej_slots_through_T', 'reject', '''static T Id<T>(T x) => x;
static Ref<'a, int> FirstOf<'a, 'b>(in HP<'a, 'b> p) => p.X;
static void T1() { mut int a = 1; int b = 2; var h = Id(new HP(Ref<int>.Of(in a), Ref<int>.Of(in b))); var r = FirstOf(in h); a = 5; Console.WriteLine(r.Value); }''', pre=HP)
case('rej_bound_concrete', 'reject', '''static void G<T>(ref T a, Ref<int> r) where T : IStore<Ref<int>> { a.Store(r); }''')
case('rej_type_level_static', 'reject', '''static void T1() { int a = 1; mut var r = new Registry<Ref<int>>(); r.Add(Ref<int>.Of(in a)); }''', pre="class Registry<T> where T : 'static { public void Add(T x) { unsafe { Static<T>.Slot = Some(x); } } }\n")
# One lifetime per type parameter: Rust keeps 'a and 'b apart through a T, RustSharp merges them.
# Through T each lifetime stays its own, as Rust substitutes T (structured lifetimes).
case('slots_through_T', 'ok', '''static T Id<T>(T x) => x;
static Ref<'a, int> FirstOf<'a, 'b>(in HP<'a, 'b> p) => p.X;
static void T1() { int a = 1; mut int b = 2; var h = Id(new HP(Ref<int>.Of(in a), Ref<int>.Of(in b))); var r = FirstOf(in h); b = 5; Console.WriteLine(r.Value); }''', pre=HP)
