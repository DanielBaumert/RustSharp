"""Rust parity: everyday Rust patterns with rustc's verdict. Mostly programs Rust accepts (to find where
RustSharp is stricter), and classic rejections no other suite covers. Comments name the Rust equivalent."""
from probelib import Suite

HEADER = '''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
class C { public int V; public readonly int Get() => V; }
struct Two { public List<int> A; public List<int> B; }
'''
SUITE = Suite('parity', HEADER)
case = SUITE.case
R, O, S = 'reject', 'ok', 'strict'

# NLL: a borrow ends at its last use.
case('nll_last_use', O, 'static void T1(){ mut var l = new List<int>{1}; var r = Ref<List<int>>.Of(in l); Console.WriteLine(r.Value.Count); l.Add(2); }')
case('nll_use_after_mut', R, 'static void T1(){ mut var l = new List<int>{1}; var r = Ref<List<int>>.Of(in l); l.Add(2); Console.WriteLine(r.Value.Count); }')  # E0502
# Two-phase borrows: v.push(v.len()).
case('two_phase_push_len', O, 'static void T1(){ mut var l = new List<int>{1}; l.Add(l.Count); Console.WriteLine(l.Count); }')
# Disjoint fields: &mut a.x and &mut a.y at once.
case('disjoint_fields_mut', O, 'static void T1(){ mut var t = new Two { A = new List<int>(), B = new List<int>() }; ref var a = ref t.A; ref var b = ref t.B; a.Add(1); b.Add(2); Console.WriteLine(t.A.Count + t.B.Count); }')
case('same_field_mut_twice', R, 'static void T1(){ mut var t = new Two { A = new List<int>(), B = new List<int>() }; ref var a = ref t.A; ref var b = ref t.A; a.Add(1); b.Add(2); }')  # E0499
# Partial move, then reinitialise the field (Rust allows).
case('partial_move_reinit', O, 'static void Take(List<int> l){} static void T1(){ mut var t = new Two { A = new List<int>(), B = new List<int>() }; Take(t.A); t.A = new List<int>(); Console.WriteLine(t.A.Count + t.B.Count); }')
case('partial_move_use_whole', R, 'static void Take(List<int> l){} static void Whole(Two t){} static void T1(){ var t = new Two { A = new List<int>(), B = new List<int>() }; Take(t.A); Whole(t); }')  # E0382
# Move in a loop that leaves right after.
case('move_in_loop_break', O, 'static void Take(C c){} static void T1(){ var c = new C(); while (true) { Take(c); break; } }')
# Move in one branch, assign in the other, then use: Rust tracks initialisation per path.
case('move_then_reassign', O, 'static void Take(C c){} static void T1(){ mut var c = new C(); Take(c); c = new C(); Console.WriteLine(c.V); }')
# Copy types are copied, not moved.
case('copy_int_reuse', O, 'static int Id(int x) => x; static void T1(){ int a = 1; var b = Id(a); Console.WriteLine(a + b); }')
# Reborrow: passing &mut on, then using it again.
case('reborrow_mut_twice', O, 'static void Push(ref List<int> l){ l.Add(1); } static void T1(){ mut var l = new List<int>(); ref var r = ref l; Push(ref r); Push(ref r); Console.WriteLine(l.Count); }')
# Elision: a &self method returns a reference to a field.
case('elided_self_field', O, 'class H { public List<int> Items = new(); public readonly Ref<List<int>> Peek() => Ref<List<int>>.Of(in Items); } static void T1(){ var h = new H(); var p = h.Peek(); Console.WriteLine(p.Value.Count); }')
case('elided_self_field_outlives', R, 'class H { public List<int> Items = new(); public readonly Ref<List<int>> Peek() => Ref<List<int>>.Of(in Items); } static void T1(){ mut Option<Ref<List<int>>> k = None; { var h = new H(); k = Some(h.Peek()); } Console.WriteLine(k.IsSome); }')  # E0597
# Index loop that mutates: Rust allows `for i in 0..v.len() { v[i] += 1 }`.
case('index_loop_mutate', O, 'static void T1(){ mut var l = new List<int>{1,2}; for (mut int i = 0; i < l.Count; i++) l[i] += 1; Console.WriteLine(l.At(0)); }')
case('iterate_while_push', R, 'static void T1(){ mut var l = new List<int>{1,2}; foreach (var x in l) l.Add(1); }')  # E0502
# Closures: FnMut borrows uniquely while alive.
case('fnmut_then_read', O, '[Mut] delegate void F(); static void T1(){ mut int n = 0; mut F inc = () => { n++; }; inc(); inc(); Console.WriteLine(n); }')
case('fnmut_read_while_alive', R, '[Mut] delegate void F(); static void T1(){ mut int n = 0; mut F inc = () => { n++; }; Console.WriteLine(n); inc(); }')  # E0503
# Closure capturing a local by reference while it does not escape (Rust: fine).
case('closure_local_ref_capture', O, 'delegate int F(); static void T1(){ var l = new List<int>{1}; F f = () => l.Count; Console.WriteLine(f()); Console.WriteLine(l.Count); }')
# Shadowing a moved value.
case('shadow_after_move', O, 'static void Take(C c){} static void T1(){ var c = new C(); Take(c); var c2 = new C(); Console.WriteLine(c2.V); }')
# Option::take and replace.
case('option_take', O, 'static void T1(){ mut Option<C> o = Some(new C()); var t = o.Take(); Console.WriteLine(t.IsSome); Console.WriteLine(o.IsSome); }')
# Swap two locals.
case('mem_swap', O, 'static void T1(){ mut var a = new C(); mut var b = new C { V = 2 }; Mem.Swap(ref a, ref b); Console.WriteLine(a.V); }')
# Returning a reference into a parameter.
# Rust's Index (&self) vs IndexMut: l[i] is `ref T` here, so a shared borrow of it through `in` fails (STATUS: List indexer).
case('return_ref_into_param', S, "static Ref<'a, int> First<'a>(in 'a List<int> l) => Ref<int>.Of(in l[0]); static void T1(){ var l = new List<int>{5}; Console.WriteLine(First(in l).Value); }")
case('return_ref_into_local', R, 'static Ref<int> Bad(){ var l = new List<int>{5}; return Ref<int>.Of(in l[0]); }')  # E0515
# Match on a borrowed Option without moving out (match ergonomics).
case('match_moves_option', R, 'static void T1(){ Option<C> o = Some(new C()); if (o is Some(var c)) Console.WriteLine(c.V); Console.WriteLine(o.IsSome); }')
# Returning one of two borrows needs a shared lifetime.
case('longest_same_lifetime', O, "static Ref<'a, int> Longest<'a>(Ref<'a, int> x, Ref<'a, int> y) => x.Value > y.Value ? x : y; static void T1(){ int a = 1, b = 2; Console.WriteLine(Longest(Ref<int>.Of(in a), Ref<int>.Of(in b)).Value); }")
case('longest_outlives_one', R, "static Ref<'a, int> Longest<'a>(Ref<'a, int> x, Ref<'a, int> y) => x.Value > y.Value ? x : y; static void T1(){ int a = 1; mut Option<Ref<int>> k = None; { int b = 2; k = Some(Longest(Ref<int>.Of(in a), Ref<int>.Of(in b))); } Console.WriteLine(k.IsSome); }")  # E0597
# Generic with T: Clone used twice via Clone.

# Rust: String, Option<T>, i32, tuples are Clone; mem::take works on Option (Default). Missing impls in the corelib.
case('clone_bound_string', S, 'static T Dup<T>(in T x) where T : IClone<T> => x.Clone(); static void T1(){ Console.WriteLine(Dup("x".Clone())); }')
case('clone_bound_int', S, 'static T Dup<T>(in T x) where T : IClone<T> => x.Clone(); static void T1(){ Console.WriteLine(Dup(1)); }')
case('mem_take_option', S, 'static void T1(){ mut Option<C> o = Some(new C()); var t = Mem.Take(ref o); Console.WriteLine(t.IsSome); }')
case('ord_bound_int', S, 'static T Max2<T>(T a, T b) where T : IOrd<T> => a.Compare(in b) >= 0 ? a : b; static void T1(){ Console.WriteLine(Max2(1, 2)); }')
case('eq_bound_string', S, 'static bool Same<T>(in T a, in T b) where T : IEq<T> => a.Eq(in b); static void T1(){ Console.WriteLine(Same("a".Clone(), "a".Clone())); }')
# A struct holding a reference, used after the referent's scope.
case('struct_ref_outlives', R, "ref struct View<'a> { public Ref<'a, int> R; public View(Ref<'a, int> r) { R = r; } } static void T1(){ mut Option<int> k = None; View v; { int a = 1; v = new View(Ref<int>.Of(in a)); } Console.WriteLine(v.R.Value); }")  # E0597
# Moving a value into a thread and joining (std::thread::spawn with move).
case('thread_move_join', O, 'static void T1(){ var l = new List<int>{1}; mut var h = Thread.Run(move () => l.Count); Console.WriteLine(h.Join().Unwrap()); }')
# Scoped threads borrow locals (std::thread::scope).
case('thread_scope_borrow', O, 'static void T1(){ var l = new List<int>{1}; mut int n = 0; { mut var scope = new ThreadScope(); scope.Run(() => { n = l.Count; }); } Console.WriteLine(n + l.Count); }')
# Generic function holding a T in a local closure, not escaping: Rust accepts.
case('generic_closure_local_T', O, 'delegate int F(); static int Use<T>(T x) { F f = () => 1; return f(); } static void T1(){ int a = 1; Console.WriteLine(Use(Ref<int>.Of(in a))); }')
# A value of a type with two lifetimes through Id keeps both (structured lifetimes).
case('id_keeps_two_lifetimes', O, "struct HP<'a, 'b> { public Ref<'a, int> X; public Ref<'b, int> Y; public HP(Ref<'a, int> x, Ref<'b, int> y) { X = x; Y = y; } } static T Id<T>(T x) => x; static void T1(){ int a = 1; mut int b = 2; var h = Id(new HP(Ref<int>.Of(in a), Ref<int>.Of(in b))); var r = h.X; b = 5; Console.WriteLine(r.Value); }")
# Tuples hold borrows, each element for its own lifetime: let t = (&a, &b); keep = t.0.
case('tuple_holds_refs', O, 'static void T1(){ int a = 1; var t = (Ref<int>.Of(in a), 1); Console.WriteLine(t.Item1.Value); }')
case('tuple_return_ref', O, 'static (Ref<int>, int) F(Ref<int> x) => (x, 1); static void T1(){ int a = 1; Console.WriteLine(F(Ref<int>.Of(in a)).Item1.Value); }')
case('tuple_generic', O, 'static (T, int) F<T>(T x) => (x, 1); static void T1(){ int a = 1; Console.WriteLine(F(Ref<int>.Of(in a)).Item1.Value); }')
case('tuple_item_own_lifetime', O, 'static void T1(){ int a = 1; mut Ref<int> keep = Ref<int>.Of(in a); { int b = 2; var t = (Ref<int>.Of(in a), Ref<int>.Of(in b)); keep = t.Item1; } Console.WriteLine(keep.Value); }')
case('tuple_item_short', R, 'static void T1(){ int a = 1; mut Ref<int> keep = Ref<int>.Of(in a); { int b = 2; var t = (Ref<int>.Of(in a), Ref<int>.Of(in b)); keep = t.Item2; } Console.WriteLine(keep.Value); }')  # E0597
case('tuple_outlives', R, 'static void T1(){ int z = 0; mut var k = (Ref<int>.Of(in z), 0); { int a = 1; k = (Ref<int>.Of(in a), 1); } Console.WriteLine(k.Item1.Value); }')  # E0597
case('tuple_deconstruct_short', R, 'static void T1(){ int a = 1; mut Ref<int> keep = Ref<int>.Of(in a); { int b = 2; var (x, y) = (Ref<int>.Of(in a), Ref<int>.Of(in b)); keep = y; } Console.WriteLine(keep.Value); }')  # E0597
case('tuple_move_twice', R, 'static void Take(C c){} static void T1(){ var t = (new C(), 1); Take(t.Item1); Take(t.Item1); }')  # E0382
# A clone owns its value: the borrow for clone() ends at once.
case('clone_then_move', O, 'static (T, T) Dup<T>(T x) where T : IClone<T> => (x.Clone(), x); static void T1(){ var (a, b) = Dup(new List<int>{1}); Console.WriteLine(a.Count + b.Count); }')
case('clone_keeps_inner_lifetime', R, 'static T Copy1<T>(in T x) where T : IClone<T> => x.Clone(); static void T1(){ mut Option<List<Ref<int>>> k = None; { int a = 1; var l = new List<Ref<int>>{ Ref<int>.Of(in a) }; k = Some(Copy1(in l)); } Console.WriteLine(k.IsSome); }')  # E0597
# let mut k: (&i32, i32): `mut` before a tuple type does not parse yet.
case('mut_tuple_type', S, 'static void T1(){ int z = 0; mut (Ref<int>, int) k = (Ref<int>.Of(in z), 0); k = (Ref<int>.Of(in z), 1); Console.WriteLine(k.Item2); }')
