"""Ownership and borrowing basics: the first audit's cases, with the verdict Rust would give."""
from probelib import Suite

HEADER = '''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
class C { public int V; public C? Next = None; public readonly int Get() => V; }
[Copy] struct Pt { public int X; }
'''
SUITE = Suite('basics', HEADER)
case = SUITE.case
R, O = 'reject', 'ok'

# Moves
case('loop_move', R, 'static void Take(C c){} static void T1(){ var c=new C(); mut int i=0; while(i<2){ Take(c); i++; } }')
case('branch_move', R, 'static void Take(C c){} static void T1(){ var c=new C(); if(Console.ReadLine().IsSome) Take(c); Console.WriteLine(c.Get()); }')
case('double_arg', R, 'static void Two(C a, C b){} static void T1(){ var c=new C(); Two(c,c); }')
case('generic_dup', R, 'static T Dup<T>(in T x) => x;')
case('generic_dup2', R, 'static (T,T) Dup<T>(T x) => (x,x);')
case('self_into_field', R, 'static void T1(){ mut var c=new C(); c.Next = Some(c); }')
case('drop_then_use', R, 'static void T1(){ var c=new C(); Mem.Drop(c); Console.WriteLine(c.V); }')
case('closure_move_then_use', R, 'delegate int F(); static void T1(){ var c=new C(); F f = move () => c.V; Console.WriteLine(c.V); f(); }')
case('tuple_partial', R, 'static void T1(){ var t=(new C(), 1); var a=t.Item1; var b=t; }')
case('array_move_out', R, 'static void T1(){ C[] a=new C[]{new C()}; var c=a[0]; }')
case('interface_move', R, 'interface I { move void Eat(); } class K : I { public move void Eat(){} } static void T1(){ I k=new K(); k.Eat(); k.Eat(); }')
case('goto_move', R, 'static void Take(C c){} static void T1(){ var c=new C(); mut int i=0; again: Take(c); i++; if(i<2) goto again; }')
case('pattern_move_out', R, 'static void Take(C c){} static void T1(){ object o=new C(); if(o is C c) Take(c); }')
case('fnonce_twice', R, '[Once] delegate C O(); static void T1(){ var c=new C(); O f = move () => c; var a=f(); var b=f(); }')
case('move_in_closure_twice', R, 'delegate void G(); static void Take(C c){} static void T1(){ var c=new C(); G g = move () => Take(c); }')

# Borrows and mutation
case('swap_self', R, 'static void T1(){ mut int a=1; Mem.Swap(ref a, ref a); }')
case('out_alias', R, 'static void F(out int a, out int b){ a=1;b=2; } static void T1(){ mut int x; F(out x, out x); }')
case('ref_reassign', R, 'static void T1(){ mut int a=1; mut int b=2; ref int r=ref a; r = ref b; a=5; r=6; b=7; int z=r; }')
case('array_elem_two_refs', R, 'static void T1(){ mut int[] a=new int[]{1,2}; ref int x=ref a[0]; ref int y=ref a[1]; x=1; y=2; }')
case('dict_get_insert', R, 'static void T1(){ mut var d=new Dictionary<int,C>(); d.Insert(1,new C()); var r=d.Get(1); d.Insert(2,new C()); Console.WriteLine(r.Unwrap().Value.V); }')
case('list_get_push', R, 'static void T1(){ mut var l=new List<C>(); l.Push(new C()); var r=l.Get(0); l.Push(new C()); Console.WriteLine(r.Unwrap().Value.V); }')
case('linq_then_add', R, 'static void T1(){ mut var l=new List<int>(); l.Add(1); var q=l.Where(x=>x>0); l.Add(2); foreach(var x in q) Console.WriteLine(x); }')
case('foreach_add', R, 'static void T1(){ mut var l=new List<int>(); l.Add(1); foreach(var x in l) l.Add(x); }')
case('while_borrow_loop', R, 'static void T1(){ mut var l=new List<int>(); l.Add(1); mut int i=0; ref int r = ref l[0]; while(i<2){ l.Add(i); r=i; i++; } }')
case('readonly_mutate_field', R, 'class K { public int V; public readonly void Bump(){ V++; } }')
case('readonly_call_mut', R, 'class K { public int V; public void Inc(){V++;} public readonly void Bad(){ Inc(); } }')
case('in_param_mutate_inner', R, 'static void F(in C c){ c.Next = None; }')
case('in_param_call_mut', R, 'class K { public int V; public void Inc(){V++;} } static void F(in K k){ k.Inc(); }')
case('iter_this_mutate', R, 'static void T1(){ mut var w=new W(); foreach(var x in w.Items()){ w.V=1; } }', pre='class W { public int V; public IEnumerable<int> Items(){ yield return V; } }\n')
case('using_moved', R, 'class D : IDisposable { public void Dispose(){} } static void Take(D d){} static void T1(){ var d=new D(); Take(d); using(d){} }')

# Lifetimes and escapes
case('copy_struct_str', R, 'static Holder Make(){ var s = "abc".Clone(); return new Holder{ S = s.Trim() }; }', pre='[Copy] struct Holder { public str S; }\n')
case('struct_str', R, 'static Holder Make(){ var s = "abc".Clone(); return new Holder{ S = s.Trim() }; }', pre='struct Holder { public str S; }\n')
case('class_str', R, 'static Holder Make(){ var s = "abc".Clone(); var h = new Holder(s.Trim()); return h; }', pre='class Holder { public str S; public Holder(str s){ S=s; } }\n')
case('class_ref', R, 'static Holder Make(){ int x=1; return new Holder(Ref<int>.Of(in x)); }', pre='class Holder { public Ref<int> R; public Holder(Ref<int> r){ R=r; } }\n')
case('static_str', R, 'static str G = "x"; static unsafe void T1(){ var s="abc".Clone(); G = s.Trim(); }')
case('return_slice_local', R, 'static str F(){ var s="abc".Clone(); return s.Trim(); }')
case('slice_then_mutate', R, "static void T1(){ mut var s=\"abc \".Clone(); str t = s.Trim(); s.Push('x'); Console.WriteLine(t); }")
case('slice_then_reassign', R, 'static void T1(){ mut var s="abc ".Clone(); str t = s.Trim(); s = "q".Clone(); Console.WriteLine(t); }')
case('generic_id_ref', R, 'static T Id<T>(T x) => x; static Ref<int> Bad(){ int x=1; return Id(Ref<int>.Of(in x)); }')
case('generic_wrap_str', R, 'static Wrap<str> Bad(){ var s="a ".Clone(); return new Wrap<str>{ V = s.Trim() }; }', pre='struct Wrap<T> { public T V; }\n')
case('generic_class_str', R, 'static W<str> Bad(){ var s="a ".Clone(); return new W<str>(s.Trim()); }', pre='class W<T> { public T V; public W(T v){ V=v; } }\n')
case('tuple_str', R, 'static (str,int) Bad(){ var s="a ".Clone(); return (s.Trim(),1); }')
case('option_str', R, 'static Option<str> Bad(){ var s="a ".Clone(); return Some(s.Trim()); }')
case('async_str', R, 'static async Task<str> Bad(){ var s="a ".Clone(); await Task.Yield(); return s.Trim(); } static async Task T1(){ var r = await Bad(); }')
case('out_str', R, 'static void F(out str r){ var x="a ".Clone(); r = x.Trim(); }')
case('ref_str', R, 'static void F(ref str r){ var x="a ".Clone(); r = x.Trim(); }')
case('ref_list_str', R, 'static void F(ref List<str> l){ var x="a ".Clone(); l.Add(x.Trim()); }')
case('list_outlive', R, 'static void T1(){ mut var l=new List<str>(); { var x="a ".Clone(); l.Add(x.Trim()); } Console.WriteLine(l[0]); }')
case('wrap_outlive', R, 'static void T1(){ mut var w=new Wrap<str>{ V="z" }; { var x="a ".Clone(); w.V = x.Trim(); } Console.WriteLine(w.V); }', pre='struct Wrap<T> { public T V; }\n')
case('span_escape', R, 'static Span<int> F(){ Span<int> s = stackalloc int[3]; return s; }')
case('lifetime_escape_scoped', R, 'static ref int F(ref int x, scoped ref int y) => ref y;')
case('ref_struct_set_short', R, 'static void T1(){ mut int outer=1; mut var v=new View(ref outer); { mut int inner=2; v.Set(ref inner); } Console.WriteLine(v.Read()); }', pre='ref struct View { ref int _p; public View(ref int p){ _p = ref p; } public void Set(ref int p){ _p = ref p; } public readonly int Read() => _p; }\n')
case('self_ref_struct', R, 'static void T1(){ mut var w=new W(); w.Set(); }', pre='class W { public int V; public Option<Ref<int>> R = None; public void Set(){ R = Some(Ref<int>.Of(in V)); } }\n')
case('enum_match_reassign', R, 'static void T1(){ mut Shape s = Shape.Circle(new C()); if (s is Shape.Circle(var c)) { s = Shape.Empty; Console.WriteLine(c.V); } }', pre='enum Shape { Circle(C c), Empty }\n')
case('indexer_ref', R, 'static void T1(){ mut var w=new W(); ref int r=ref w[0]; w=new W(); r=1; }', pre='class W { int[] _a = new int[]{1}; public ref int this[int i] => ref _a[i]; }\n')
case('switch_some_move', R, 'static void T1(){ C? o=Some(new C()); var n = o switch { Some(var v) => v.V, None => 0 }; Console.WriteLine(o.IsSome); }')
case('with_record', R, 'record R(C X); static void T1(){ var r=new R(new C()); var x=r.X; var s = r with { }; }')

# Guards
case('mutex_guard_escape', R, 'static ref int F(in Mutex<int> m){ mut var g=m.Lock(); return ref g.Value; }')
case('guard_outlives_lock', R, 'static void T1(){ var m=new Mutex<int>(0); ref int r = ref Dummy(); { mut var g2=m.Lock(); r = ref g2.Value; } r=5; } static ref int Dummy(){ return ref Box0.X; }', pre='static class Box0 { public static int X; }\n')
case('refcell_borrow_replaced', R, 'static void T1(){ var c=new RefCell<int>(1); mut var b=c.BorrowMut(); ref int r=ref b.Value; b = c.BorrowMut(); r=2; }')

# Closures
case('closure_escape_list', R, 'delegate int F(); static void T1(){ mut var l=new List<F>(); { int x=1; l.Add(() => x); } foreach(ref readonly var f in l) Console.WriteLine(f()); }')
case('closure_return', R, 'delegate int F(); static F Make(){ int x=1; return () => x; }')
case('closure_field', R, 'delegate int F(); static void T1(){ int x=1; var h=new Holder(() => x); }', pre='delegate int G(); class Holder { public G F; public Holder(G f){F=f;} }\n')
case('async_lambda_local', R, 'delegate Task<int> AF(); static AF Make(){ int x=1; AF f = async () => x; return f; }')
case('fnmut_reentrant', R, '[Mut] delegate void M(); static void T1(){ mut int a=0; mut M f = () => { a++; }; ref int r = ref a; f(); r=3; }')
case('static_delegate_capture', R, 'static void T1(){ int x=1; unsafe { Holder.G = Some<F>(() => x); } }', pre='public delegate int F(); class Holder { public static Option<F> G = None; }\n')

# Threads and Send/Sync
case('refcell_arc', R, 'static void T1(){ var a=new Arc<RefCell<int>>(new RefCell<int>(1)); var t=Thread.Run(move () => a.Count); }')
case('thread_nonmove', R, 'static void T1(){ mut int a=0; var t=Thread.Run(() => { a=1; return 0; }); }')
case('scope_two_mut', R, 'static void T1(){ mut int a=0; { mut var s=new ThreadScope(); s.Run(() => { a=1; }); s.Run(() => { a=2; }); } }')
case('send_cell_scope', R, 'static void T1(){ var c=new RefCell<int>(1); { mut var s=new ThreadScope(); s.Run(() => { var b=c.Borrow(); }); s.Run(() => { mut var b=c.BorrowMut(); }); } }')
case('atomic_share', O, 'static void T1(){ var a=new Arc<AtomicInt>(new AtomicInt(0)); var b=a.Clone(); var t=Thread.Run(move () => { b.Value.Add(1); return 0; }); t.Join().Unwrap(); }')
case('generic_send', R, 'static void Spawn<T>(T x){ var t=Thread.Run(move () => { var y=x; return 0; }); } static void T1(){ Spawn(new Rc<int>(1)); }')
case('generic_send_inner', R, 'static void Spawn<T>(T x){ var t=Thread.Run(move () => { var y=x; return 0; }); }')
case('generic_task_send', R, 'static async Task Spawn<T>(T x){ var h=Task.Run(move () => Task.FromResult(x)); await h; } static async Task T1(){ await Spawn(new Rc<int>(1)); }')
case('mutex_rc_arc', R, 'static void T1(){ var a=new Arc<Mutex<Rc<int>>>(new Mutex<Rc<int>>(new Rc<int>(1))); var t=Thread.Run(move () => a.Count); }')
case('channel_rc', R, 'static void T1(){ var (tx, rx) = Channel.Create<Rc<int>>(); var t=Thread.Run(move () => { var v = rx.Receive(); return 0; }); tx.Send(new Rc<int>(1)); }')
case('clone_rc_send', R, 'static void T1(){ var rc=new Rc<int>(1); var b=new Box<Rc<int>>(rc); var t=Thread.Run(move () => b.Value.Value); }')
case('weak_arc_cell', R, 'static void T1(){ var a=new Arc<Cell<int>>(new Cell<int>(1)); var t=Thread.Run(move () => a.Value.Get()); }')
case('list_of_iface_send', R, 'interface I { readonly int X(); } static void T1(){ var l=new List<I>(); var t=Thread.Run(move () => l.Count); }')
case('ptr_struct_send', R, 'unsafe struct Raw { public int* P; } static void T1(){ var r=new Raw(); var t=Thread.Run(move () => { var q=r; return 0; }); }')
case('lazy_used', R, 'static readonly Lazy<Rc<int>> G = new Lazy<Rc<int>>(() => new Rc<int>(1)); static void T1(){ var t=Thread.Run(move () => G.Value.Count); Console.WriteLine(G.Value.Count); t.Join(); }')
case('cell_used', R, 'static readonly Cell<int> G = new Cell<int>(1); static void T1(){ var t=Thread.Run(move () => { G.Set(2); return 0; }); G.Set(3); t.Join(); }')
case('generic_static_sync', R, 'static void T1(){ Console.WriteLine(H<Rc<int>>.Count()); }', pre='class H<T> { public static readonly List<T> L = new List<T>(); public static int Count() => L.Count; }\n')
case('readonly_static_refcell', R, 'static readonly RefCell<int> G = new RefCell<int>(1); static void T1(){ Console.WriteLine(G.Borrow().Value); }')
case('static_mut_no_unsafe', R, 'static int G; static void T1(){ G = 1; }')

# async
case('async_ref_local', R, 'static async Task<int> F(C c) { await Task.Yield(); return c.V; } static async Task T1(){ var c=new C(); var t=F(c); Console.WriteLine(c.V); await t; }')
case('async_this_borrow', R, 'static async Task T1(){ mut var w=new W(); var t=w.Run(); w.V=5; await t; }', pre='class W { public int V; public async Task<int> Run(){ await Task.Yield(); return V; } }\n')
case('task_run_borrow', R, 'static async Task T1(){ mut int x=1; var h=Task.Run(() => { x=2; return Task.FromResult(0); }); await h; }')
case('rc_into_task', R, 'static async Task T1(){ var rc=new Rc<int>(1); var h=Task.Run(move () => Task.FromResult(rc.Value)); await h; }')

# unsafe gating
case('transmute_safe', R, 'static void T1(){ var x = Mem.Transmute<int,float>(1); }')
case('ptr_safe', R, 'static void T1(){ int x=1; int* p=&x; }')
case('mem_take_nodefault', R, 'static void T1(){ mut var c=new C(); var d=Mem.Take(ref c); }')

# Gaps found and closed in later rounds
case('reborrow_field_buffer', R, 'static void T1(){ mut var k = new List<int> { 1, 2, 3 }; mut var v = new View(ref k); ref View t = ref v; ref int e = ref t.P[0]; k = new List<int> { 9 }; e = 5; }', pre='ref struct View { public ref List<int> P; public View(ref List<int> p) { P = ref p; } }\n')
case('option_pattern_scope', R, 'static void T1(){ mut var keep = new List<Ref<List<int>>>(); { var inner = new List<int> { 1 }; Option<Ref<List<int>>> o = Option<Ref<List<int>>>.Some(Ref<List<int>>.Of(in inner)); if (o is Some(var w)) keep.Add(w); } Console.WriteLine(keep.Count); }')
case('iter_ref_outlives_list', R, 'static void T1(){ mut Option<Ref<int>> keep = None; { mut var l = new List<int> { 1 }; foreach (var x in l.Iter()) keep = Some(x); } Console.WriteLine(keep.IsSome); }')
case('iter_ref_list_changed', R, 'static void T1(){ mut var l = new List<int> { 1 }; var first = l.Where(x => x > 0).First(); l.Add(2); Console.WriteLine(first.Unwrap().Value); }')
case('select_items_owned', O, 'static void T1(){ mut var l = new List<int> { 1, 2 }; mut var keep = new List<int>(); foreach (var x in l.Select(v => v * 10)) keep.Add(x); Console.WriteLine(keep[0]); }')
case('where_refs_kept', O, 'static void T1(){ mut var l = new List<int> { 1, 2 }; mut var keep = new List<Ref<int>>(); foreach (var x in l.Where(v => v > 0)) keep.Add(x); Console.WriteLine(keep.Count); }')
case('loop_carried_some', O, 'static void T1(){ mut var l = new List<int> { 1, 2, 3 }; mut Option<Ref<int>> prev = None; foreach (var x in l.Iter()) { if (prev is Some(var p)) Console.Write(p.Value); prev = Some(x); } }')
case('delegate_result_outlives_capture', R, 'delegate Ref<int> Get(); static void T1(){ mut Option<Ref<int>> keep = None; { int y = 1; Get g = () => Ref<int>.Of(in y); keep = Some(g()); } Console.WriteLine(keep.IsSome); }')
case('fnmut_result_twice', R, '[Mut] delegate Ref<int> Bump(); static void T1(){ mut int counter = 0; mut Bump f = () => { counter++; return Ref<int>.Of(in counter); }; var a = f(); var b = f(); Console.WriteLine(a.Value + b.Value); }')
case('orderby_ref_key', O, 'static void T1(){ mut var names = new List<string> { "b", "a" }; var sorted = names.Iter().OrderBy(s => s).ToList(); Console.WriteLine(sorted.Count); }')
case('elided_result_keeps_input', R, "static ref readonly 'a int First<'a, 'b>(in Pair<'a, 'b> p) => ref p.X; static Pair Make(ref readonly int x) => new Pair(in x, in x); static void T1(){ mut int x = 1; var p = Make(in x); ref readonly int r = ref First(in p); x = 2; Console.WriteLine(r); }", pre="ref struct Pair<'a, 'b> { public ref readonly 'a int X; public ref readonly 'b int Y; public Pair(ref readonly 'a int x, ref readonly 'b int y) { X = ref x; Y = ref y; } }\n")

# Documented differences
# A struct's default value counts as empty and runs no destructor (documented in LANGUAGE.md).
case('default_struct_no_dtor', O, 'static void T1(){ var d=default(D); }', pre='struct D { public int V; ~D(){ Console.WriteLine("drop"); } }\n')
