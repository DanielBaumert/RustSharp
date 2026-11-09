# RustSharp Language Reference

RustSharp is C# syntax with Rust's rules. This document only describes what differs from C#. It is
written for readers who know C#; knowing Rust helps but is not required.

## Immutable by default

As in Rust, a variable only changes if it is declared `mut`:

```csharp
int a = 1;
a++;                          // CS9928
mut int b = 1;
b++;                          // ok

var list = new List<int>();
list.Add(1);                  // CS9929: Add needs exclusive access
mut var grow = new List<int>();
grow.Add(1);                  // ok
```

`mut` goes before the type and works wherever a variable is introduced: locals, `for`,
`foreach (mut var x in list)`, parameters (`int F(mut int x)`), lambdas (`(mut int v) => ...`) and
patterns. It belongs to the variable, not to the value: moving a value into a `mut` variable makes it
mutable.

- `CS9928`: a second assignment. Late initialization is still allowed: `int x; if (c) x = 1; else x = 2;`
- `CS9929`: a field assignment, an exclusive borrow, or a call to a method that is not `readonly`. This
  applies to classes too: they belong to their variable.
- A closure that changes a variable needs that variable to be `mut`. A `[Mut]` delegate such as
  `Func<A, R>` must itself be `mut` to be called, just like `let mut f` for `FnMut`.
- A parameter `ref int x` is immutable; what it refers to is not. `out` arguments count as the first
  assignment.

The compiler's message gives the line and column where `mut` belongs. `tools/migrate_mut.py` adds it to
existing code automatically.

Shadowing works like Rust's `let`: `var x = 5; var x = x + 1;` declares a new `x`, and the initializer
still sees the old one. This works in the same block, in inner blocks, over parameters, and in
top-level statements.

## Ownership

Every value has exactly one owner. When the owner goes out of scope, the value is dropped. Locals are
dropped in reverse declaration order, temporaries at the end of the statement.

Assigning and passing a value **moves** it. The source can no longer be used:

```csharp
var a = new Foo();
var b = a;          // a is moved
a.Bar();            // CS9901: borrow of moved value
```

A moved `mut` variable can be used again after a new assignment. An assignment drops the old value
first.

### Which types are copied

Copy types are duplicated when read instead of being moved:

- numbers, `bool`, `char`, pointers, and tuples of Copy types
- your own structs and enums marked `[Copy]`, like `#[derive(Copy)]`; all fields must be Copy (`CS9922`)
- type parameters with `where T : unmanaged`

Without `[Copy]`, even a struct made only of numbers is moved, and so is an enum like `Color`.

Everything else is moved: classes, arrays, delegates, interfaces, structs with such fields, and
unconstrained type parameters.

`string` is Rust's `String`: UTF-8, `Length` counts bytes, there is no `s[i]`, `Chars()` yields `Rune`
(Rust's `char`), and `Bytes()` yields the bytes. Slicing in the middle of a character panics. With
`mut`, `Push`, `PushStr`, `Pop`, `Insert`, `Truncate` and `Clear` change the string. A `Clone()` and the
original never affect each other (copy-on-write), and a literal is a string of its own at every use.
More methods: `Find`, `Contains`, `StartsWith`, `EndsWith`, `Trim`, `Split`, `Replace`, `Repeat`,
`ToUpper`, `ToLower`, `AsPtr`. `fixed` on a string is not supported. Assigning, passing and `return`
move a string; `Clone()` copies it.

`str` is Rust's `&str`: a borrowed slice without a copy, Copy, and tracked by the borrow checker. A
`string` converts to `str` implicitly. A literal becomes a `'static str` and may leave a method, even
`"a b".Split(' ')`. `s[a..b]`, `s[..5]`, `s[^3..]`, `Trim`, `Slice`, `Split` and `Lines` return `str`
without copying, and `ToOwned()` turns one into a `string`. The parts from `Split` live as long as both
the text and the separator.

```csharp
static str FirstWord(str s) => s.IndexOf(" ") is var i && i >= 0 ? s.Slice(0, i) : s;
```

`str` takes a lifetime like Rust's `&'a str`, so a signature or a struct can say which text a slice
borrows:

```csharp
static str<'a> Longest<'a>(str<'a> x, str<'a> y) => x.Length >= y.Length ? x : y;

ref struct Parser<'a> { public str<'a> Rest; /* Word() returns str<'a>: words outlive the parser */ }
```

A method that only reads takes `in string` (Rust's `&str`). Core-library methods with a `string`
parameter, `a + b`, `==`, `$"…"` and `switch` only read and consume nothing.

### What cannot be moved out of

| Source | Error | Instead |
|---|---|---|
| behind `ref`, `in` or `this` | CS9902 | `Mem.Replace`, `Option.Take()`, or borrow |
| an array element | CS9903 | `Mem.Replace(ref a[i], replacement)`, or `RemoveAt(i)` on a list |
| a `static` field | CS9904 | `Mem.Replace` or `Option.Take()` in an `unsafe` block |
| a field of a type with a destructor | CS9905 | `Mem.Replace`, or make the field `T?` and call `Take()` |

Like Rust's `mem::take`, `Mem.Take` needs a `Default`: `where T : IDefault<T>` (otherwise `CS0311`). It
leaves `T.Default()` behind, never a null.

Individual fields may be moved out of an object you own (a partial move). The remaining fields are
dropped normally, but the object as a whole can no longer be used.

## Borrows

C# references are borrows:

```csharp
void Read(in Foo x)   { }     // shared: read-only, any number at the same time
void Edit(ref Foo x)  { }     // exclusive: may write, only one at a time
```

Rust's rule applies: **either any number of shared borrows or exactly one exclusive borrow.** This
prevents, for example, a list from growing while a reference points into its buffer:

```csharp
ref int first = ref list[0];
list.Add(2);                  // CS9911
first = 3;
```

A borrow ends at its last use, not at the end of the scope (non-lexical lifetimes). So this code is
valid:

```csharp
ref int r = ref a;
r = 10;
a = 11;                       // ok: r is not used anymore
```

Different fields may be borrowed at the same time. Different array elements, however, count as the
same memory.

Everything behind a shared reference is immutable, however deeply nested: through `in Foo x`,
`x.Bar.Baz = 1` is an error (CS9917).

### The receiver `this`

| Declaration | `this` is | Rust |
|---|---|---|
| `void M()` | an exclusive borrow | `&mut self` |
| `readonly void M()` | a shared borrow | `&self` |
| `move void M()` | a value that is consumed | `self` |

`get` accessors are `readonly` automatically, unless they return `ref T`. Constructors and destructors
borrow `this` exclusively.

Overrides and interface implementations must match their declaration (CS9920). `readonly` may replace
an ordinary method because it promises more. The reverse is not allowed, and `move` must be the same on
both sides.

Arguments are evaluated before the receiver is borrowed, so `list.Add(list.Count)` is valid.

## Lifetimes

Usually no annotations are needed; the rules match Rust's elision:

1. A method that borrows `this` returns a borrow from `this`.
2. Otherwise the result comes from the only input that carries a reference.
3. Several candidates without an annotation are an error (CS9916).

A lifetime is written directly behind the kind of reference, like Rust's `&'a T`: `ref 'a T` is
`&'a mut T`, `in 'a T` and `ref readonly 'a T` are `&'a T`. Inputs the result does not come from can be
excluded with `scoped`. A method may declare its lifetimes after its name, as in Rust, or simply use
them:

```csharp
static ref 'a int Larger<'a>(ref 'a int x, ref 'a int y) { ... }
static ref 'a int Larger(ref 'a int x, ref 'a int y) { ... }       // the same
static ref int First(ref int x, scoped ref int y) => ref x;
static ref 'b int Shorter(ref 'a int x, ref 'b int y) where 'a : 'b => ref x;
```

`'a` is only read as a lifetime when no closing quote follows. `'a'` stays a character literal.

### Lifetime parameters on types

A type may declare lifetime parameters, like Rust's `struct Pair<'a, 'b>`. They come first, before the
type parameters, and a value of the type holds one borrow per lifetime. A field names the lifetime it
borrows for:

```csharp
ref struct Pair<'a, 'b>
{
    public ref readonly 'a int X;
    public ref readonly 'b int Y;
    public Pair(ref readonly 'a int x, ref readonly 'b int y) { X = ref x; Y = ref y; }
}

static ref readonly 'a int First<'a, 'b>(in Pair<'a, 'b> pair) => ref pair.X;

var p = new Pair(in x, in y);
ref readonly int r = ref First(in p);
y = 3;                       // ok: r borrows x only ('a), and p is no longer used
x = 3;                       // CS9907 while r is used
```

- Lifetime arguments come first in a type: `Pair<'a, 'b>`, `Entry<'a, T>`, `Ref<'a, string>`. Left out,
  or written `'_`, a lifetime is elided: `Pair` is `Pair<'_, '_>`, and every elided position is a
  lifetime of its own.
- As in Rust, a live value keeps all its lifetimes alive. Only what is taken out of it through a field,
  or returned under one lifetime's name, is bound to that lifetime alone.
- A field without a lifetime borrows for as long as the whole value.
- Storing into the wrong slot is `CS9915` (`X = ref y` in the constructor above), and so is returning
  `ref pair.Y` as `'a`.
- Through a shared reference, a `ref` field gives no exclusive access (`CS9918`), as Rust gives no
  `&'a mut` through `&Pair`.
- Elided lifetimes in a result come from where the result comes from, as in Rust:
  `static Pair Make(ref readonly int x) => new Pair(in x, in x);` borrows `x` for both.
- The number of lifetime arguments must match the declaration, like Rust's E0107 (`CS9939`):
  `Pair<'a>`, `Ref<'a, 'b, int>` and `Option<'a, int>` are errors.
- The older prefix `'a View` names the one implicit lifetime of a returned ref struct that declares no
  lifetime parameters. It is deprecated; declare `ref struct View<'a>` instead.

`Ref<'a, T>` and `RefMut<'a, T>` are Rust's `&'a T` and `&'a mut T`. A value of a type with one
lifetime lives exactly as long as it, so several references stay independent, in signatures as in
fields:

```csharp
static Ref<'a, int> Pick<'a, 'b>(Ref<'a, int> x, Ref<'b, int> y) => x;   // y => CS9915

ref struct RPair<'a, 'b> { public Ref<'a, int> X; public Ref<'b, int> Y; }
```

Classes and ordinary structs may declare lifetimes too, like a Rust struct in a `Box`. The fields that
name a lifetime may hold borrows; the object's owner keeps them alive, and the object must not outlive
them:

```csharp
class Index<'a>
{
    public List<Ref<'a, int>> Items = new List<Ref<'a, int>>();
    public void Add(Ref<'a, int> r) { Items.Add(r); }
}

mut var idx = new Index();
idx.Add(Ref<int>.Of(in a));
a = 5;                       // CS9907 while idx is used
```

- An object with borrows cannot go where no lifetime is tracked: into a `static`, into an object that
  declares no lifetimes, or to a thread (`CS9914`). The same holds for a variable a lambda captures,
  because it lives in the lambda's environment.
- A destructor may read the borrows, so they must still be alive when the object is dropped, as with
  Rust's drop check: an object declared before what it borrows is `CS9912`.
- A field without a lifetime can only hold `'static` borrows, as before.

### Generics and lifetimes

Generic code is checked as in Rust: a type parameter `T` stands for any type, references included, and
carries a lifetime of its own. A generic container may therefore hold references, and a generic method
may take and return them:

```csharp
class Stack<T> { List<T> _items = new(); public void Push(T x) { _items.Add(x); } }

mut var s = new Stack<Ref<int>>();     // Rust: Vec<&i32>
s.Push(Ref<int>.Of(in a));
a = 2;                                 // CS9907 while s is used

static T Id<T>(T x) => x;              // the result lives as long as x
```

- A body may not store a `T` where no lifetime is tracked, such as a static, a thread or an object
  without lifetimes, unless the method says `where T : 'static` (`CS9915`). Its callers then have to
  pass `'static` values. `where T : 'a` relates `T` to a named lifetime. On a type
  (`class Registry<T> where T : 'static`), the clause holds in all its methods, as does
  `where 'a : 'b` on a type with lifetime parameters.
- A trait bound `where T : IStore<U>` lets `T` hold `U`, so `U` must outlive `T` at every call, as
  Rust's implementation would require.
- Each type parameter has one lifetime. A value with several lifetimes, such as `HP<'a, 'b>`, keeps
  them apart in its own type, but passed as a `T` they act as one, the shorter. That is stricter than
  Rust, never unsound.
- The core library's generic types keep their own rules (`[CarriesBorrows]`), with the same effect for
  `List<T>`, `Option<T>` and the others.

Not yet: variance beyond what the rules above imply.

### Ref structs

A `ref struct` may contain borrows and has an implicit lifetime. It never outlives the data it refers
to:

```csharp
ref struct View
{
    ref int _p;
    public View(ref int p) { _p = ref p; }
    public readonly int Read() => _p;
}

var v = new View(ref k);
k = 2;                 // CS9907 while v is still used
```

A `ref struct` is not Copy; a `readonly ref struct` is.

## Destructors

`~T()` runs deterministically when the owner drops the value, exactly once. For classes, all
destructors run first, from the derived class to the base class. Then the fields are dropped in
declaration order, the base class's fields first.

Structs may have destructors too. One runs only for values created with `new`. A `default(T)` of a
struct without references counts as empty and does not trigger it.

`using` and `IDisposable` work as usual and are independent of destructors.

## No `null`: `Option<T>`

As in Rust, there is no `null`. A `string`, a class or an array always has a value. A value that may be
missing is an `Option<T>`, and `T?` is only a short way to write it, for classes and structs alike:
`string?` is `Option<string>`, `int?` is `Option<int>`.

```csharp
static int? Digit(char c) => c >= '0' && c <= '9' ? Some(c - '0') : None;

static string Show(int? d) => d switch
{
    Some(var v) => "digit " + v.ToString(),
    None => "none",
};

static int? Sum(string s)
{
    mut int sum = 0;
    foreach (var c in s.Chars()) sum += Digit(c)?;   // None is passed on
    return Some(sum);
}
```

- `Some(x)` and `None` come from the prelude (`System.Option`), as in Rust. `None` fits any `Option<T>`;
  written out, it is `Option<T>.None`. `Some(x)` also takes a reference, like `Some(&x)`: the Option
  then lives no longer than what it borrows.
- The value is only reachable after a check: `if (o is Some(var v))`, a `switch` with `Some(var v)` and
  `None` (it must cover both, `CS8509`), or `Unwrap()` and `Expect(msg)`, which panic explicitly on
  `None`. `IsSome`, `IsNone`, `UnwrapOr`, `Map`, `AndThen` and the other methods are listed below.
- `x?` passes `None` on out of a method that itself returns an `Option`. `x?.M()` then calls a member.
- A `T` never turns into an `Option<T>` by itself: `int? i = 5;` is an error; write `Some(5)`.
- Patterns on a borrowed Option go through `AsRef()`: `o.AsRef() is Some(var r)` gives a `Ref<T>`, and
  `o.AsMut()` a `RefMut<T>` that can be written through without `mut`. `Some(var v)` directly on `o`
  moves the value out, like Rust's `match o { Some(v) => ... }`.

Everything that creates or presupposes a `null` is rejected:

| Written | Error | Instead |
|---|---|---|
| `null` | CS9935 | `None`, `Some(x)` |
| `x!`, `a ?? b`, `a ??= b`, `x?.M()` on a reference, `x as T` | CS9937 | `Unwrap()`, `UnwrapOr(b)`, `GetOrInsert(b)`, `.`, `x is T v` |
| `default` for a type that contains references | CS9938 | `None`, or `T.Default()` with `where T : IDefault<T>` |
| `new string[n]`, `new S()` without a constructor of its own | CS9938 | list the elements, `List<T>`, a constructor or an initializer |
| `Mem.Take(ref slot)` without `IDefault<T>` | CS0311 | `RemoveAt(i)`, `Pop()`, `Mem.Replace`, `Option.Take()` |
| `#nullable` | CS9936 | remove the line |

Fields need a value (`CS8618`): in the constructor, as an initializer, or as `T? x = None`. `unsafe`
code may use null pointers (`p == null` on an `int*`), like Rust's `ptr::null`, but no null references.

The same rules apply to the core library: it has no `#nullable`, no `null` except for raw pointers, and
no zeroed values. Where a value may be missing, there is an `Option`: the result of a task, a waiting
`Waker`, the field of a generator. `Result` consists of two `Option` fields, exactly one of which is
`Some`. The empty part of a `None` is uninitialized memory that nobody reads, as in Rust.
`StringBuilder.Append` returns nothing, like Rust's `push_str`.

APIs where a value may be missing return `Option` or `Result`: `Console.ReadLine()` (`None` at the end
of the input), `list.Get(i)`, `list.Pop()`, `dict.Get(k)`, `First()`, `rx.ReceiveAsync()` (`None` once all
senders are gone), `stream.ReadLineAsync()` (`Result<Option<string>, IoError>`) and `int.Parse(s)`
(`Result<int, ParseError>`). Indexers such as `list[i]` panic, as in Rust.

A `switch` expression must cover every case, like Rust's `match` (`CS8509`). A C# `enum` can also hold
unnamed values: if all named values are covered, the expression compiles, and an unnamed value throws
`SwitchExpressionException` at run time.

## Pattern matching

Pattern variables borrow from the value being tested:

```csharp
if (shape is Circle c) c.Radius = 2;   // shape stays the owner
```

As long as `c` is used, `shape` is borrowed. Moving out of `c` is an error. To actually take over the
object, use a cast: `var c = (Circle)shape;`. The cast consumes `shape`. There is no `as` (`CS9937`),
because it would give `null` when it fails.

## Anonymous types

Fields of anonymous types are read directly and follow the normal rules: Copy values and strings can be
read any number of times, and an object is moved out when it is read (`var x = a.Obj;`).

## foreach

`foreach` over arrays and `List<T>` borrows the collection. For Copy elements it works as usual. Other
elements must be iterated by reference, because otherwise they would be moved out of the collection:

```csharp
foreach (ref readonly var node in nodes) Console.WriteLine(node.Value);
```

Or, as in Rust's `for node in nodes.iter()`, with `Ref<T>` items that may be kept as long as the
list lives: `foreach (var node in nodes.Iter()) Console.WriteLine(node.Value);`

## Clone

Nothing is deep-copied implicitly. If you need a copy, call `x.Clone()`. This works for Copy types,
strings, arrays of cloneable elements, and types that allow it:

```csharp
[Clone] class Node { public int V; public Node? Next = None; }   // field by field, like #[derive(Clone)]
class Shape : IClone<Shape> { public readonly Shape Clone() => ...; }   // a custom implementation
```

A type without Clone gives `CS9922`. The dynamic type is always cloned, even behind an interface.

## Records

Records are cloneable and comparable automatically. `with` clones, `==` compares structurally and
borrows both sides, and `ToString` gives `Point { X = 1, Name = a }`.

Properties whose type is not Copy are read like fields: `var y = r.Y;` moves the value out of the
record. A deconstruction `var (a, b) = r;` consumes `r` if one of the fields has to be moved.

## Traits

There is no inheritance (`CS9934`): a class only implements interfaces. Shared behaviour belongs in a
trait with default methods, and a fixed set of cases in an enum with data. `ToString`, `Equals` and
`GetHashCode` may be overridden, like `Display` and `PartialEq`.

Variants are created without `new`, as in Rust: `Abx.A`, `Shape.Circle(2)` (`new` works too).

An enum implements a trait like Rust's `impl Trait for Enum`:
`enum Abx : ICool<int> { A, B, C; public readonly int a() => …; }`. An enum with a trait, with methods
after `;`, or with data is a Rust enum (and is moved); otherwise it is a C# enum with numeric values.

Interfaces are traits. As in Rust, a method states how it takes `self`: `readonly` is `&self`, no
modifier is `&mut self`, and `move` is `self`. Implementations must respect this (`CS9920`).

```csharp
interface IGreet
{
    readonly string Name();
    readonly string Hello() => "Hello " + Name();   // a default method
}
static string Say<T>(in T x) where T : IGreet => x.Hello();   // a bound like `T: Greet`
static T Make<T>() where T : IDefault<T> => T.Default();      // `T::default()`
```

## Lambdas

A lambda borrows what it uses, per variable: shared if it only reads, exclusive if it writes.

```csharp
mut int a = 1, b = 2;
G incA = () => { a++; };
G incB = () => { b++; };       // ok: a different variable
int read = a;                  // CS9908 while incA is still used
```

A closure must not outlive its variables. A `move` lambda therefore takes them over:

```csharp
static F MakeAdder(int n) => move x => x + n;     // without move: CS9925
```

Delegates carry the lifetime of what they borrow. Where a delegate is stored, for example in a field or
a list, it must not borrow anything. The signature says so with `'static`:

```csharp
class Button { F _click; public Button('static F click) { _click = click; } }
```

A `move` lambda may only consume its captures if the delegate type is marked `[Once]`. Calling it then
consumes the delegate itself, and a second call is `CS9900`. This corresponds to `FnOnce`.

A delegate type marked `[Mut]` corresponds to `FnMut`: only such delegates may change their captures,
and calling one needs exclusive access (`CS9927`).

A lambda may return a borrow of what it captures or of the data behind its arguments (`s => s` on a
`Ref<string>`). Every call of a delegate therefore binds the result to all inputs, the delegate
included: the result lives no longer than the arguments and the captures, and the result of a `[Mut]`
delegate keeps the delegate borrowed, so it cannot be called again while the result is used (`CS9911`).

A delegate type may declare lifetimes, like Rust's `for<'a> Fn(&'a i32) -> &'a i32`. They belong to each
call, and the signature says where the result comes from, so callers bind it to that argument only:

```csharp
delegate Ref<'a, int> Id<'a>(Ref<'a, int> x);

Id id = x => x;
var r = id(Ref<int>.Of(in y));   // lives as long as y, also after id is gone
```

Every body behind such a delegate must keep the promise: a lambda that returns something else, such as
its object's field (`x => R`), is `CS9915`, and so is a method group whose result comes from another
parameter (`First f = Right;`).

## LINQ

LINQ works directly on lists and arrays, also in query syntax. It is lazy and monomorphized, and it
follows Rust's iterators. A query on a collection **lends** its elements as `Ref<T>`, like
`v.iter()` gives `&T`. Computed items (`Select`, `Zip`, `Enumerate`, `Range`, `Chars()`, `Split`) are
**owned**. Members and operators reach through a `Ref` by themselves (see auto-deref below), so most
lambdas read as in C#:

```csharp
var names = people.Where(p => p.Age >= 18).Select(p => p.Name).ToList();   // List<string>
foreach (var p in people.Where(p => p.Age > 40)) Console.WriteLine(p.Name); // p is Ref<Person>
var squares = from x in nums where x < 4 select x * x;                       // x is Ref<int>
var evens = nums.Where(x => x % 2 == 0).Copied().ToList();                    // List<int>
```

| Method | Item it hands out | Rust |
|---|---|---|
| `list.Where(...)`, `AsQuery()`, `Iter()`, `Take`, `Skip`, `Order()` on a list | `Ref<T>` | `iter()`, `filter`, ... |
| `Select(f)`, `Map(f)` | what `f` returns, owned | `map` |
| `Zip`, `Enumerate` | owned tuples | `zip`, `enumerate` |
| `Enumerable.Range`, `Chars()`, `Bytes()`, `Split`, `Lines` | `int`, `Rune`, `byte`, `str` | `0..n`, `chars()`, `bytes()`, `split` |
| `Cloned()`, `Copied()` on a `Ref<T>` query | `T` | `cloned()`, `copied()` |

- Consuming methods move the items, they never clone them: `ToList`/`Collect` give a `List<Ref<T>>`
  on a borrowing query, `First`, `Last`, `Max`, `Min`, `Find`, `Nth` give an `Option<Ref<T>>`. Use
  `Cloned()` or `Copied()` for owned values. `list.ToList()` directly on a collection is a copy, like
  `to_vec()`, and needs Clone.
- `Where`, `Any`, `All`, `Count`, `TakeWhile`, `SkipWhile`, `First(f)` and the key of `OrderBy`/`GroupBy`
  look at an item (`in T`, Rust's `&Item`). `Select`, `Aggregate`/`Fold` and `ForEach` take it by value.
- `Max`, `Min`, `Order`, `Distinct`, `Contains` and `GroupBy` compare what a `Ref` points at. Of several
  equal items, `Max` gives the last one and `Min` the first, as in Rust.
- A query may only be iterated once. As long as a query or an item it lent is alive, the collection is
  borrowed: changing it is `CS9909`, letting it die first is `CS9912`. Owned items may be kept freely; a
  `str` from `Split` still points at the text.
- `q.Next()` is Rust's `next()`: `while (q.Next() is Some(var x)) ...` (the query must be `mut`).
- A key or a projection may itself be a reference into the items: `OrderBy(s => s)` and
  `Select(s => s)` on `Ref<string>` items, like Rust's `sort_by_key(|s| *s)`.

Your own iterator implements `IIter<T>` with `Option<T> Next()`. It may lend what it borrows, never
itself: `Some(Ref<int>.Of(in _field))` in `Next` is `CS9915`.

## Iterators

`yield return` works as usual and creates a coroutine. `foreach` consumes the sequence: iterating the
same variable a second time is `CS9900`. An iterator method on an instance borrows `this` as long as the
sequence is alive.

## Threads

```csharp
var counter = new Arc<Mutex<int>>(new Mutex<int>(0));
var c = counter.Clone();
var t = Thread.Run(move () =>
{
    mut var guard = c.Value.Lock();
    guard.Value = guard.Value + 1;
    return 0;
});
t.Join().Unwrap();   // Err if the thread ended with a panic
```

Every type is automatically `Send` (may move to another thread) and `Sync` (may be shared between
threads) if its fields are. Raw pointers, `Rc<T>`, `object` and interfaces are not. Violations give
`CS9923` and `CS9924`. Your own types with `unsafe` inside state their rule with `[SendWhen]` and
`[SyncWhen]`.

A closure for `Thread.Run` or `Task.Run` must be a `move` lambda. A `Mutex<T>` owns its data, which is
only reachable through the guard, and the guard releases the lock at the end of its scope.

Available are `Arc<T>`, `WeakArc<T>`, `Mutex<T>`, `RwLock<T>`, `RefCell<T>`, `Condvar`, `Barrier`,
`Lazy<T>`, `AtomicInt`, `AtomicLong`, `AtomicBool`, `Channel`, and `ThreadScope` for threads that borrow
local data. `lock (x)` only works on `System.Threading.Lock`, which protects no data; prefer `Mutex<T>`.

Mutable `static` fields require `unsafe` because of possible data races (`CS9921`). A `readonly static`
field can be read freely, but it must be `Sync` and is immutable inside as well.

## async and await

```csharp
static async Task<int> Add(int a, int b)
{
    await Task.Delay(10);
    return a + b;
}

var handle = Task.Run(move () => Add(1, 2));
Console.WriteLine(await handle);
```

The syntax is C#, the behaviour is Rust:

- **Tasks are lazy.** An `async` method only runs once something drives it with `await` or `Task.Run`.
- **`await` consumes the task.**
- **Tasks are cancelled by dropping them.** Their locals are dropped along with them.
- **`await handle` gives `Result<T, JoinError>`**, as in Tokio: `Err` if the task ended with a panic or
  was aborted.
- **A task borrows what its method borrows.** An `async` instance method borrows `this` as long as the
  task is alive.
- **`Task.Run` spreads work over worker threads.** Idle workers steal waiting tasks. Only the closure and
  its result must be `Send`: if a task's state holds something that is not `Send`, such as an `Rc<T>`,
  the task stays on its thread from the first poll on.
- **Cooperative budget.** After 128 I/O operations that were ready immediately, a task yields the worker.
- **End of the program.** When `async Main` ends, tasks that are still alive are cancelled and dropped.
- **Locks must not be held across an `await`** (`CS9926`).

There are also `Task.Yield`, `Task.FromResult`, `Task.WhenAll` and `async Task Main`. For your own leaf
futures, `Runtime.CurrentWaker()` is available.

### Tokio building blocks

| Building block | Meaning |
|---|---|
| `Task.Run` | Gives a `JoinHandle<T>`. Dropping it detaches the task; `Abort()` cancels it. |
| `Task.RunBlocking` | Blocking code on a thread of its own |
| `Task.WhenAny`, `Task.Race` | The first one wins, the others are cancelled |
| `Task.Timeout(task, ms)` | Cancels and gives `Err(Elapsed)` |
| `Interval` | A steady tick: `await tick.TickAsync()` |
| `AsyncMutex<T>` | The guard may be held across `await`; clones share the data |
| `Semaphore` | `await s.AcquireAsync()`; dropping the permit returns it |
| `Channel.CreateBounded<T>(n)` | `await tx.SendAsync(v)` waits while the channel is full |
| `rx.ReceiveAsync()` | Gives `Option<T>`, `None` once all senders are gone: `while (await rx.ReceiveAsync() is Some(var v))` |
| `TaskCompletionSource<T>` | A task completed by hand |
| `Notify` | `await n.NotifiedAsync()`; `n.NotifyOne()` wakes one waiter |
| `Watch<T>` | The latest value: `Set`, `Get`, `await w.ChangedAsync()` |
| `Broadcast<T>` | Every `Subscribe()` receiver gets every value; `T` must be Clone |
| `CancellationTokenSource` | `Cancel()`, `IsCancellationRequested`, `await CancelledAsync()` |
| `Signal.WaitAsync(n)` | Waits for an operating-system signal |

`async IAsyncEnumerable<T>` with `yield return`, `await foreach` and `await using` work as in C#, and so
do `async ValueTask` and `async ValueTask<T>`. Leaving an `await foreach` drops the iterator.

### Networking

```csharp
var listener = TcpListener.Bind("127.0.0.1", 8080).Unwrap();
while (true)
{
    var conn = (await listener.AcceptAsync()).Unwrap();
    Task.Run(move () => Handle(conn));
}

static async Task<Result<int, IoError>> Handle(TcpStream s)
{
    mut byte[] buffer = new byte[1024];
    while (true)
    {
        int n = (await s.ReadAsync(ref buffer))?;
        if (n == 0) return Result<int, IoError>.Ok(0);
        (await s.WriteAsync(in buffer, n))?;
    }
}
```

`ReadAsync` and `WriteAsync` borrow the buffer until the task is done. There are also
`TcpStream.ConnectAsync`, `ReadLineAsync`, `WriteAsync(string)` and `ShutdownWrite`. Every operation
returns `Result<_, IoError>`, so a refused connection is an `Err` value. `TcpListener` and `TcpStream`
support IPv6 (`"::1"`), and `ConnectAsync` resolves host names through `Dns.ResolveAsync`. For Unix
sockets there are `UnixListener` and `UnixStream`, and for datagrams `UdpSocket` with `SendToAsync` and
`ReceiveFromAsync`. `File.ReadAllTextAsync` and `WriteAllTextAsync` run on threads of their own.

## typeof and GetType

`typeof(T)` and `x.GetType()` give a `Type` with `Name` and `FullName`, nothing more. Generic parameters
are resolved, so `typeof(T)` in `NameOf<string>()` is `String`. `==` consumes both operands;
`a.Same(in b)` does not. On a type parameter, `GetType` gives the static type.

## Errors: Result, `?` and panics

There are no exceptions. `throw`, `try`, `catch` and `finally` are errors in user code (`CS9930`). As in
Rust, there are two kinds of errors:

**Expected failures are values.** A method that can fail returns `Result<T, E>` or `Option<T>`. `x?`
passes the error on: on `Err` (or `None`) the method returns immediately and drops its locals; otherwise
`x?` is the value inside.

```csharp
static Result<int, ParseError> Sum(List<string> items)
{
    mut int total = 0;
    foreach (var s in items) total += int.Parse(s)?;
    return Result<int, ParseError>.Ok(total);
}

static async Task<Result<string, IoError>> FirstLine(string host)
{
    mut var c = (await TcpStream.ConnectAsync(host, 80))?;
    (await c.WriteAsync("GET / HTTP/1.0\r\n\r\n"))?;
    return Result<string, IoError>.Ok((await c.ReadLineAsync())?.UnwrapOr(""));
}
```

- `f()?;` also works as a statement on its own, and `x?.Name` calls a member after passing the error on.
- If the method has a different error type, `?` converts the error through an `implicit operator`. That
  is Rust's `From`.
- `?` needs a method that returns `Result` or `Option` (`CS9932`) and an operand of that type (`CS9931`).
- A `?` followed by `:` stays the conditional operator. `?.` on other types is an error (`CS9937`),
  because a reference is never `null`.

`Option<T>` has the methods of Rust's `Option`: `IsSome`, `IsNone`, `IsSomeAnd`, `IsNoneOr`, `AsRef`,
`AsMut`, `AsDeref`, `AsDerefMut`, `Unwrap`, `Expect`, `UnwrapOr`, `UnwrapOrElse`, `UnwrapOrDefault`, `Map`,
`MapOr`, `MapOrElse`, `Inspect`, `OkOr`, `OkOrElse`, `Filter`, `And`, `AndThen`, `Or`, `OrElse`, `Xor`,
`Zip`, `Unzip`, `Take`, `TakeIf`, `Replace`, `Insert`, `GetOrInsert`, `GetOrInsertWith`, `Iter`,
`IterMut`, `Cloned`, `Copied`, `Transpose` and `Flatten`. As in Rust, `UnwrapOrDefault` needs
`T : IDefault<T>`; the built-in numbers, `bool`, `char` and `string` (`""`) satisfy it.

`Result<T, E>` has the methods of Rust's `Result`, in C# spelling:

| Purpose | Methods |
|---|---|
| Reading | `Unwrap`, `UnwrapErr`, `Expect(msg)`, `ExpectErr(msg)`, `Ok()`, `Err()`, `IntoOk`, `IntoErr` |
| Checking | `IsOk`, `IsErr`, `IsOkAnd(f)`, `IsErrAnd(f)`; the last two consume the `Result`, as in Rust |
| Transforming | `Map`, `MapErr`, `MapOr(fallback, f)`, `MapOrElse(errorFn, f)`, `Inspect(f)`, `InspectErr(f)` |
| Chaining | `And(r)`, `AndThen(f)`, `Or(r)`, `OrElse(f)` |
| Fallbacks | `UnwrapOr(x)`, `UnwrapOrElse(f)`, `UnwrapOrDefault()` |
| References | `AsRef()`, `AsMut()`, `AsDeref()` (for `Rc`, `Arc`, `Box`), `AsDerefMut()` (for `Box`) |
| Copies | `Cloned()` and `Copied()` on a `Result<Ref<T>, E>` or `Result<RefMut<T>, E>` |
| Nesting | `Transpose()` on `Result<Option<T>, E>`, `Flatten()` on `Result<Result<T, E>, E>` |
| Iteration | `Iter()` for `foreach` and LINQ, `IterMut()` for `foreach (ref var v in ...)` |

### References as values: `Ref<T>` and `RefMut<T>`

`Ref<T>` is Rust's `&T`, and `RefMut<T>` is `&mut T`. Unlike `in` and `ref`, they are values and can be
type arguments, so `Result<Ref<T>, Ref<E>>` exists as in Rust:

```csharp
mut var r = int.Parse("41");
var view = r.AsRef();              // Result<Ref<int>, Ref<ParseError>>
Console.WriteLine(view.Unwrap().Value);
r.AsMut().Unwrap().Value += 1;     // changes r itself
bool big = r.AsRef().IsOkAnd(v => v.Value > 40);   // r is kept
var copy = r.AsRef().Copied();     // Result<int, ParseError>
```

The borrow checker treats them like Rust's references: as long as `view` is used, `r` is borrowed, and
assigning to `r` is then `CS9907`. Two `AsMut` at the same time are `CS9911`, and a reference that is
meant to leave a method but points into a local is `CS9912`. `Ref<T>` is Copy; `RefMut<T>` is moved.
`Ref<T>.Of(in x)` and `RefMut<T>.Of(ref x)` correspond to `&x` and `&mut x`.

**Auto-deref**, as in Rust: a member that `Ref<T>` or `RefMut<T>` does not have itself is looked up on
the value behind it, through any number of references. Operators see through them too, like Rust's
`impl Add<&i32> for i32`:

```csharp
var r = Ref<Person>.Of(in p);
Console.WriteLine(r.Name + r.Age);     // r.Value.Name, r.Value.Age
bool old = r.Age > 40 && r.IsAdult();  // readonly methods only: r.Birthday() is CS9918
mut int sum = 0;
sum += Ref<int>.Of(in x);              // the right side of a compound assignment
```

Auto-deref never changes the rules: a shared `Ref` stays shared (`r.Age = 5` is `CS9917`), and moving
out of it is `CS9902`. Two things still need `.Value`, as Rust needs `*`: converting to the value
itself (`int n = x.Value;`, `new List<int> { x.Value }`) and writing through a `RefMut`
(`m.Value += 1`, Rust's `*m += 1`). `Ref<T>`'s own members `Value`, `Of` and `ToString` win; `ToString`
shows the value.

References may also be stored in collections, like Rust's `Vec<&T>`: `List`, `Dictionary`, `HashSet`,
`Queue`, `Stack` and `SortedDictionary`. What a collection stores must outlive it
(`list.Add(Ref<int>.Of(in x))` requires `x` to live longer than `list`), and what comes out of it
(`Pop`, `list[i]`, `foreach`) is only valid as long as the collection. A collection full of references
can leave a method if its references point into the arguments:

```csharp
static List<Ref<Person>> Adults(in List<Person> people)
{
    mut var result = new List<Ref<Person>>();
    foreach (ref readonly var p in people)
        if (p.Age >= 18) result.Add(Ref<Person>.Of(in p));
    return result;
}
```

Stricter than Rust: a value copied out of a collection must not outlive the collection itself, even if
what it points to is still alive. A collection of references in a field of an object is an error
(`CS9914`), because classes have no lifetime parameters.

`Box<T>` is Rust's `Box`: a value on the heap with one owner. `Value` gives shared access, `ValueMut`
exclusive access, and `Unbox()` takes the value out. `[Copy]` on a type parameter requires a Copy type,
like `T: Copy` (`CS9922`).

The core library throws nothing. What may fail in Rust returns an `Option` or `Result` here:

| Call | Result |
|---|---|
| `int.Parse`, `long.Parse`, `decimal.Parse` | `Result<_, ParseError>` |
| `list.RemoveLast()`, `stack.Pop()`, `queue.Dequeue()` | `Option<T>`, `None` when empty |
| `First()`, `Last()`, `Single()`, `Max()`, `Min()`, `Average()` | `Option<T>`, `None` without elements |
| `dict.Add(key, value)` | `Option<V>`: replaces the old value and returns it, like `HashMap::insert` |
| `receiver.Receive()` | `Result<T, RecvError>` |

Rust's names exist as well: `List` has `Push`, `Pop`, `Len`, `IsEmpty`, `Get`/`GetMut` (an Option of a
reference), `Remove`, `SwapRemove`, `Swap`, `Truncate`, `Retain`, `Dedup`, `Extend` and `Iter`;
`Dictionary` has `Insert`, `Get`/`GetMut`, `Len`, `OrInsert` (`entry().or_insert()`), `OrInsertWith`,
`Keys` and `Values`; iterators have `Map`, `Filter`, `Fold`, `Find`, `Position`, `Nth`, `Enumerate`,
`StepBy`, `Chain`, `Rev` and `Collect`. `string.Join(sep, list)` joins.

As in Rust, on the other hand, indexers and methods that return a reference panic (`list[i]`,
`dict[key]`, `Peek()`), and so does `RefCell.BorrowMut` while a borrow exists (ask `CanBorrowMut`
first).

Networking and files return `Result<_, IoError>`. For `decimal` there are `CheckedAdd`, `CheckedSub`,
`CheckedMul`, `CheckedDiv`, `CheckedRem` and `CheckedToInt64`, which return `Option`. `Unit` is Rust's
`()`, for example in `Result<Unit, IoError>`.

**Bugs in the program are panics.** `Panic.Raise("...")`, `Panic.Unreachable()`, `Panic.Todo()` and
`Panic.Assert(condition)` correspond to `panic!`, `unreachable!`, `todo!` and `assert!`. Index errors,
division by zero, invalid casts, `checked` overflows, and `Unwrap()` on `Err` or `None` are panics too.
The message appears as in Rust, with the file, line and column in user code:

```
thread 'main' panicked at src/main.rscs:7:38:
index out of bounds
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

The panic then unwinds the thread and drops every value on the way. In the main thread, the program
ends with exit code 101. In another thread or task, a panic cannot be caught, but it can be observed:
`thread.Join()` and `await handle` then give `Err(JoinError)` with `IsPanic` and `Message`. A cancelled
task gives `Err` with `IsCancelled`.

**`Main` may return a `Result`**, also as `async Task<Result<T, E>>`. `Ok` ends the program with exit
code 0; `Err` prints `Error: ` and the error to stderr and ends with 1:

```csharp
static Result<Unit, ParseError> Main()
{
    int n = int.Parse("41")?;
    Console.WriteLine(n + 1);
    return Result<Unit, ParseError>.Ok(default);
}
```

If an iterator or task is dropped early, its destructors run. Cleanup belongs in a destructor or a
`using`; both also run while a panic unwinds.

## unsafe

In `unsafe` code, raw pointers are allowed, and borrows through them are not checked. `unsafe` is also
required for:

- accessing mutable `static` fields (CS9921), because any thread can change the field
- `Mem.Transmute` (CS9921)

The most important building blocks in `Mem`:

| Method | Meaning |
|---|---|
| `Take(ref x)` | moves the value out and leaves `T.Default()` behind (needs `T : IDefault<T>`) |
| `Replace(ref x, v)` | swaps in a new value and returns the old one |
| `Swap(ref a, ref b)` | swaps two values |
| `Drop(x)` | drops the value now |
| `Forget(x)` | takes the value without ever dropping it |
| `Read(p)`, `Write(p, v)` | bitwise reads and writes through a pointer |
| `DropInPlace(p)` | drops the value behind a pointer |

## Error codes

| Code | Meaning |
|---|---|
| CS0311 | `Mem.Take` or `UnwrapOrDefault` on a type without `IDefault<T>` |
| CS8509 | a `switch` expression does not cover every case |
| CS8618 | a field has no value after the constructor |
| CS9900 | use of a moved value |
| CS9901 | borrow of a moved value |
| CS9902 | move out of a borrow |
| CS9903 | move out of an array element |
| CS9904 | move out of a `static` field |
| CS9905 | move out of a type with a destructor |
| CS9906 | move of a borrowed value |
| CS9907 | assignment to a borrowed value |
| CS9908 | use during an exclusive borrow |
| CS9909 | exclusive borrow while a shared borrow exists |
| CS9910 | shared borrow while an exclusive borrow exists |
| CS9911 | two exclusive borrows at the same time |
| CS9912 | a value does not live long enough |
| CS9913 | a temporary is dropped while it is borrowed |
| CS9914 | returning a reference to a local variable |
| CS9915 | a lifetime is too short |
| CS9916 | a lifetime annotation is missing |
| CS9917 | assignment behind a shared reference |
| CS9918 | exclusive borrow behind a shared reference |
| CS9919 | feature not supported |
| CS9920 | the receiver does not match the declaration |
| CS9921 | `unsafe` required |
| CS9922 | the type does not implement Clone |
| CS9923 | the type is not `Send` |
| CS9924 | the type is not `Sync` |
| CS9925 | a closure may outlive what it borrows |
| CS9926 | a value must not be held across an `await` |
| CS9927 | a delegate without `[Mut]` changes its captures |
| CS9928 | a second assignment to a variable without `mut` |
| CS9929 | a change to, or exclusive borrow of, a variable without `mut` |
| CS9930 | `throw`, `try`, `catch` or `finally` |
| CS9931 | `?` on something that is neither a `Result` nor an `Option` |
| CS9932 | `?` in a method that does not return a matching `Result` or `Option` |
| CS9933 | `dynamic`: use interfaces instead of `dyn Trait`, `object` with `is` instead of `dyn Any` |
| CS9934 | a base class was given: there is no inheritance |
| CS9935 | `null`: a missing value is `Option<T>.None` |
| CS9936 | `#nullable`: references are never `null` |
| CS9937 | `x!`, `??`, `??=`, `?.` on a reference, `as` |
| CS9938 | an expression would hold `null`: `default`, `new T[n]`, `new S()` |
| CS9939 | the number of lifetime arguments does not match the declaration |
