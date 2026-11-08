# RustSharp Sprachreferenz

RustSharp ist C#-Syntax mit Rusts Regeln. Dieses Dokument beschreibt nur, was sich gegenüber C# ändert. Es
richtet sich an Leser, die C# kennen. Rust-Kenntnisse helfen, sind aber nicht nötig.

## Unveränderlich als Standard

Wie in Rust ändert sich eine Variable nur, wenn sie `mut` trägt:

```csharp
int a = 1;
a++;                          // CS9928
mut int b = 1;
b++;                          // ok

var list = new List<int>();
list.Add(1);                  // CS9929: Add braucht exklusiven Zugriff
mut var grow = new List<int>();
grow.Add(1);                  // ok
```

`mut` steht vor dem Typ und geht überall, wo eine Variable entsteht: lokal, in `for`, in
`foreach (mut var x in list)`, bei Parametern (`int F(mut int x)`), in Lambdas (`(mut int v) => ...`) und in
Patterns. Es gehört zur Variable, nicht zum Wert: Ein Move in eine `mut`-Variable macht einen Wert
veränderlich.

- `CS9928`: eine zweite Zuweisung. Spätes Initialisieren bleibt erlaubt: `int x; if (c) x = 1; else x = 2;`
- `CS9929`: Feldzuweisung, exklusiver Borrow oder ein Methodenaufruf ohne `readonly`. Das gilt auch für
  Klassen: Sie gehören ihrer Variable.
- Eine Closure, die eine Variable ändert, braucht diese als `mut`. Ein `[Mut]`-Delegate wie `Func<A, R>`
  braucht zum Aufrufen selbst `mut`, genau wie `let mut f` für `FnMut`.
- Ein Parameter `ref int x` ist unveränderlich, was er referenziert, nicht. `out`-Argumente zählen als
  erste Zuweisung.

Der Compiler nennt in der Meldung Zeile und Spalte für das `mut`. `tools/migrate_mut.py` trägt es in
bestehendem Code automatisch ein.

Shadowing wie Rusts `let`: `var x = 5; var x = x + 1;` deklariert ein neues `x`, der Initialisierer sieht
noch das alte. Das geht im selben Block, in inneren Blöcken und über Parametern.

## Ownership

Jeder Wert hat genau einen Besitzer. Verlässt der Besitzer seinen Scope, wird der Wert freigegeben.
Lokale Variablen werden in umgekehrter Deklarationsreihenfolge freigegeben, temporäre Werte am Ende
der Anweisung.

Zuweisen und Übergeben **verschiebt** einen Wert. Die Quelle ist danach nicht mehr benutzbar:

```csharp
var a = new Foo();
var b = a;          // a ist verschoben
a.Bar();            // CS9901: borrow of moved value
```

Eine verschobene `mut`-Variable lässt sich durch Neuzuweisung wieder verwenden. Eine Zuweisung gibt den
alten Wert zuerst frei.

### Welche Typen kopiert werden

Copy-Typen werden beim Lesen dupliziert, statt verschoben zu werden:

- Zahlen, `bool`, `char`, Zeiger und Tupel aus Copy-Typen
- eigene Structs und Enums mit `[Copy]`, wie `#[derive(Copy)]`; alle Felder müssen Copy sein (`CS9922`)
- Typparameter mit `where T : unmanaged`

Ohne `[Copy]` wird auch ein Struct aus lauter Zahlen verschoben, ebenso ein Enum wie `Color`.

Alles andere wird verschoben: Klassen, Arrays, Delegates, Interfaces, Structs mit solchen Feldern
und unbeschränkte Typparameter.

`string` ist Rusts `String`: UTF-8, `Length` zählt Bytes, `s[i]` gibt es nicht, `Chars()` liefert
`Rune` (Rusts `char`), `Bytes()` die Bytes. Ein Ausschnitt mitten in einem Zeichen panikt. Mit `mut`
ändern `Push`, `PushStr`, `Pop`, `Insert`, `Truncate` und `Clear` den String. Ein `Clone()` und der
Original-String beeinflussen sich nie (Copy-on-Write), auch ein Literal ist bei jeder Verwendung ein
eigener String. Weitere Methoden: `Find`, `Contains`, `StartsWith`, `EndsWith`, `Trim`, `Split`,
`Replace`, `Repeat`, `ToUpper`, `ToLower`, `AsPtr`. `fixed` auf einem String geht nicht mehr.
Zuweisen, Übergeben und `return` verschieben einen String, `Clone()` kopiert.

`str` ist Rusts `&str`: ein geborgter Ausschnitt ohne Kopie, Copy, vom Borrow-Checker verfolgt. Ein
`string` wird implizit zu `str`, ein Literal wird ein `'static str` und darf eine Methode verlassen, auch `"a b".Split(' ')`.
`s[a..b]`, `s[..5]`, `s[^3..]`, `Trim`, `Slice`, `Split` und `Lines` liefern `str` ohne Kopie, `ToOwned()`
macht daraus einen `string`. Teile von `Split` leben so lange wie Text und Trenner.

```csharp
static str FirstWord(str s) => s.IndexOf(" ") is var i && i >= 0 ? s.Slice(0, i) : s;
```
Eine Methode, die nur liest, nimmt `in string` (Rusts `&str`). Corelib-Methoden mit einem
`string`-Parameter, `a + b`, `==`, `$"…"` und `switch` lesen nur und verbrauchen nichts.

### Woraus nicht verschoben werden darf

| Quelle | Fehler | Stattdessen |
|---|---|---|
| hinter `ref`, `in` oder `this` | CS9902 | `Mem.Replace`, `Option.Take()`, oder borgen |
| Array-Element | CS9903 | `Mem.Replace(ref a[i], neu)`, bei einer Liste `RemoveAt(i)` |
| `static`-Feld | CS9904 | `Mem.Replace` oder `Option.Take()` in einem `unsafe`-Block |
| Feld eines Typs mit Destruktor | CS9905 | `Mem.Replace`, oder das Feld als `T?` und `Take()` |

`Mem.Take` verlangt wie Rusts `mem::take` ein `Default`: `where T : IDefault<T>` (sonst `CS0311`). Es lässt
`T.Default()` zurück, nie eine Null.

Aus einem eigenen Objekt dürfen einzelne Felder verschoben werden (Partial Move). Die übrigen Felder
werden dann normal freigegeben, das Objekt als Ganzes ist aber nicht mehr benutzbar.

## Borrows

C#-Referenzen sind Borrows:

```csharp
void Read(in Foo x)   { }     // shared: lesen, beliebig viele gleichzeitig
void Edit(ref Foo x)  { }     // exklusiv: schreiben, nur einer zur selben Zeit
```

Es gilt die Rust-Regel: **entweder beliebig viele Shared-Borrows oder genau ein exklusiver.** Das
verhindert zum Beispiel, dass eine Liste wächst, während eine Referenz in ihren Puffer zeigt:

```csharp
ref int first = ref list[0];
list.Add(2);                  // CS9911
first = 3;
```

Ein Borrow endet mit seiner letzten Verwendung, nicht am Ende des Scopes (Non-Lexical Lifetimes).
Dieser Code ist also gültig:

```csharp
ref int r = ref a;
r = 10;
a = 11;                       // ok: r wird nicht mehr benutzt
```

Verschiedene Felder dürfen gleichzeitig geborgt werden. Verschiedene Array-Elemente zählen dagegen
als derselbe Speicher.

Hinter einer Shared-Referenz ist alles unveränderlich, auch tief verschachtelt: Über `in Foo x` ist
`x.Bar.Baz = 1` ein Fehler (CS9917).

### Der Empfänger `this`

| Deklaration | `this` ist | Rust |
|---|---|---|
| `void M()` | exklusiver Borrow | `&mut self` |
| `readonly void M()` | Shared-Borrow | `&self` |
| `move void M()` | Wert, wird verbraucht | `self` |

`get`-Accessoren sind automatisch `readonly`, außer sie liefern `ref T`. Konstruktoren und
Destruktoren borgen `this` exklusiv.

Overrides und Interface-Implementierungen müssen zur Deklaration passen (CS9920). `readonly` darf
eine normale Methode ersetzen, weil es mehr verspricht. Umgekehrt geht das nicht, und `move` muss
auf beiden Seiten gleich sein.

Argumente werden vor dem Borgen des Empfängers ausgewertet, also ist `list.Add(list.Count)` gültig.

## Lifetimes

Meist sind keine Angaben nötig, die Regeln entsprechen Rusts Elision:

1. Eine Methode, die `this` borgt, gibt einen Borrow aus `this` zurück.
2. Sonst stammt das Ergebnis aus der einzigen Eingabe, die eine Referenz trägt.
3. Mehrere Kandidaten ohne Angabe sind ein Fehler (CS9916).

Eingaben, aus denen das Ergebnis nicht stammt, lassen sich mit `scoped` ausschließen. Mehrdeutige
Fälle bekommen einen Namen. Lifetimes werden nicht deklariert, ein Name gilt pro Signatur:

```csharp
static ref 'a int Larger(ref 'a int x, ref 'a int y) { ... }
static ref int First(ref int x, scoped ref int y) => ref x;
static 'a View Make(ref 'a int x, ref int y) { ... }
```

`'a` wird nur dann als Lifetime gelesen, wenn kein schließendes Hochkomma folgt. `'a'` bleibt ein
Zeichenliteral.

### Ref Structs

Ein `ref struct` darf Borrows enthalten und hat eine implizite Lifetime. Er lebt nie länger als die
Daten, die er referenziert:

```csharp
ref struct View
{
    ref int _p;
    public View(ref int p) { _p = ref p; }
    public readonly int Read() => _p;
}

var v = new View(ref k);
k = 2;                 // CS9907, solange v noch benutzt wird
```

Ein `ref struct` ist nicht Copy, ein `readonly ref struct` schon.

## Destruktoren

`~T()` läuft deterministisch, wenn der Besitzer den Wert freigibt, und zwar genau einmal. Bei
Klassen laufen zuerst alle Destruktoren von der abgeleiteten Klasse zur Basisklasse. Danach werden
die Felder in Deklarationsreihenfolge freigegeben, die Felder der Basisklasse zuerst.

Auch Structs dürfen Destruktoren haben. Er läuft nur für Werte, die mit `new` erzeugt wurden. Ein
`default(T)` gilt als leer und löst ihn nicht aus.

`using` und `IDisposable` funktionieren wie gewohnt und sind von Destruktoren unabhängig.

## Kein `null`: `Option<T>`

Wie in Rust gibt es kein `null`. Ein `string`, eine Klasse oder ein Array hat immer einen Wert. Ein Wert,
der fehlen kann, ist ein `Option<T>`, und `T?` ist nur eine Kurzschreibweise dafür, für Klassen wie
für Structs: `string?` ist `Option<string>`, `int?` ist `Option<int>`.

```csharp
static int? Digit(char c) => c >= '0' && c <= '9' ? Some(c - '0') : None;

static string Show(int? d) => d switch
{
    Some(var v) => "Ziffer " + v.ToString(),
    None => "keine",
};

static int? Sum(string s)
{
    mut int sum = 0;
    foreach (var c in s.Chars()) sum += Digit(c)?;   // None wird weitergereicht
    return Some(sum);
}
```

- `Some(x)` und `None` kommen aus dem Prelude (`System.Option`), wie in Rust. `None` passt zu jedem
  `Option<T>`; ausgeschrieben ist es `Option<T>.None`.
- An den Wert kommt man nur nach einer Prüfung: `if (o is Some(var v))`, ein `switch` mit `Some(var v)` und
  `None` (er muss beide abdecken, `CS8509`), oder `Unwrap()`, `Expect(msg)`, die bei `None` ausdrücklich
  paniken. `IsSome`, `IsNone`, `UnwrapOr`, `Map`, `AndThen` und die übrigen Methoden stehen unten.
- `x?` reicht `None` aus einer Methode weiter, die selbst ein `Option` zurückgibt. `x?.M()` ruft danach ein
  Member auf.
- `T` wird nie von selbst zu `Option<T>`: `int? i = 5;` ist ein Fehler, richtig ist `Some(5)`.
- Patterns auf einem geborgten Option gehen über `AsRef()`: `o.AsRef() is Some(var r)` gibt ein `Ref<T>`,
  `o.AsMut()` ein `RefMut<T>`, durch das man ohne `mut` schreiben kann. `Some(var v)` direkt auf `o`
  verschiebt den Wert heraus, wie Rusts `match o { Some(v) => ... }`.

Im Benutzercode ist alles verboten, was ein `null` erzeugt oder voraussetzt:

| Geschrieben | Fehler | Stattdessen |
|---|---|---|
| `null` | CS9935 | `None`, `Some(x)` |
| `x!`, `a ?? b`, `a ??= b`, `x?.M()` auf einer Referenz, `x as T` | CS9937 | `Unwrap()`, `UnwrapOr(b)`, `GetOrInsert(b)`, `.`, `x is T v` |
| `default` für einen Typ, der Referenzen enthält | CS9938 | `None`, oder `T.Default()` mit `where T : IDefault<T>` |
| `new string[n]`, `new S()` ohne eigenen Konstruktor | CS9938 | Elemente aufzählen, `List<T>`, Konstruktor oder Initialisierer |
| `Mem.Take(ref slot)` ohne `IDefault<T>` | CS0311 | `RemoveAt(i)`, `Pop()`, `Mem.Replace`, `Option.Take()` |
| `#nullable` | CS9936 | Zeile entfernen |

Felder brauchen einen Wert (`CS8618`): im Konstruktor, als Initialisierer, oder als `T? x = None`.
`unsafe`-Code darf Nullzeiger benutzen (`p == null` auf `int*`), wie Rusts `ptr::null`, aber keine
Nullreferenzen.

Dieselben Regeln gelten für die Corelib: Sie hat kein `#nullable`, kein `null` außer für rohe Zeiger und
keine genullten Werte. Wo ein Wert fehlen kann, steht ein `Option`: das Ergebnis eines Tasks, ein
wartender `Waker`, das Feld eines Generators. `Result` besteht aus zwei `Option`-Feldern, von denen genau
eines `Some` ist. Der leere Teil eines `None` ist uninitialisierter Speicher, den niemand liest, wie in
Rust. `StringBuilder.Append` gibt wie Rusts `push_str` nichts zurück.

APIs, bei denen ein Wert fehlen kann, liefern `Option` oder `Result`: `Console.ReadLine()` (`None` am
Ende der Eingabe), `list.Get(i)`, `list.Pop()`, `dict.Get(k)`, `First()`, `rx.ReceiveAsync()` (`None`,
wenn alle Sender weg sind), `stream.ReadLineAsync()` (`Result<Option<string>, IoError>`) und
`int.Parse(s)` (`Result<int, ParseError>`). Indexer wie `list[i]` paniken wie in Rust.

Ein `switch`-Ausdruck muss alle Fälle abdecken wie Rusts `match` (`CS8509`). Ein `enum` kann in C#
auch unbenannte Werte tragen: Sind alle benannten Werte abgedeckt, kompiliert der Ausdruck, und ein
unbenannter Wert wirft zur Laufzeit
`SwitchExpressionException`.

## Pattern Matching

Pattern-Variablen borgen vom geprüften Wert:

```csharp
if (shape is Circle c) c.Radius = 2;   // shape bleibt der Besitzer
```

Solange `c` benutzt wird, ist `shape` geborgt. Aus `c` zu verschieben ist ein Fehler. Um das Objekt
tatsächlich zu übernehmen, dient ein Cast: `var c = (Circle)shape;`. Der Cast verbraucht `shape`.
`as` gibt es nicht (`CS9937`), weil es bei einem Fehlschlag `null` liefern würde.

## Anonyme Typen

Felder anonymer Typen werden direkt gelesen und folgen den normalen Regeln: Copy-Werte und Strings
lassen sich beliebig oft lesen, ein Objekt wird beim Lesen herausverschoben (`var x = a.Obj;`).

## foreach

`foreach` über Arrays und `List<T>` borgt die Sammlung. Für Copy-Elemente funktioniert es wie
gewohnt. Andere Elemente müssen als Referenz durchlaufen werden, weil sie sonst aus der Sammlung
verschoben würden:

```csharp
foreach (ref readonly var node in nodes) Console.WriteLine(node.Value);
```

## Clone

Nichts wird implizit tief kopiert. Wer eine Kopie braucht, ruft `x.Clone()` auf. Das geht für Copy-Typen,
Strings, Arrays von klonbaren Elementen und Typen, die es erlauben:

```csharp
[Clone] class Node { public int V; public Node Next; }   // Feld für Feld, wie #[derive(Clone)]
class Shape : IClone<Shape> { public readonly Shape Clone() => ...; }   // eigene Implementierung
```

Ein Typ ohne Clone ergibt `CS9922`. Geklont wird immer der dynamische Typ, auch hinter einer
Basisklasse.

## Records

Records sind automatisch klonbar und vergleichbar. `with` klont, `==` vergleicht strukturell und borgt
beide Seiten, `ToString` liefert `Point { X = 1, Name = a }`.

Eigenschaften mit einem Typ ohne Copy werden wie Felder gelesen: `var y = r.Y;` verschiebt den Wert aus
dem Record. Eine Destrukturierung `var (a, b) = r;` verbraucht `r`, wenn eines der Felder verschoben
werden muss.

## Traits

Es gibt keine Vererbung (`CS9934`): Eine Klasse implementiert nur Interfaces. Gemeinsames Verhalten
gehört in einen Trait mit Default-Methoden, eine feste Menge von Fällen in ein Enum mit Daten.
`ToString`, `Equals` und `GetHashCode` dürfen überschrieben werden, wie `Display` und `PartialEq`.

Varianten entstehen wie in Rust ohne `new`: `Abx.A`, `Shape.Circle(2)` (`new` geht auch).

Ein Enum implementiert einen Trait wie Rusts `impl Trait for Enum`: `enum Abx : ICool<int> { A, B, C; public
readonly int a() => …; }`. Ein Enum mit Trait, mit Methoden nach `;` oder mit Daten ist ein Rust-Enum (wird
verschoben), sonst ein C#-Enum mit Zahlenwerten.

Interfaces sind Traits. Eine Methode sagt wie in Rust, wie sie `self` nimmt: `readonly` ist `&self`,
ohne Modifikator `&mut self`, `move` ist `self`. Implementierungen müssen das einhalten (`CS9920`).

```csharp
interface IGreet
{
    readonly string Name();
    readonly string Hello() => "Hello " + Name();   // Default-Methode
}
static string Say<T>(in T x) where T : IGreet => x.Hello();   // Bound wie `T: Greet`
static T Make<T>() where T : IDefault<T> => T.Default();      // `T::default()`
```

## Lambdas

Eine Lambda borgt, was sie benutzt, und zwar pro Variable: lesend, wenn sie nur liest, exklusiv, wenn
sie schreibt.

```csharp
mut int a = 1, b = 2;
G incA = () => { a++; };
G incB = () => { b++; };       // ok: eine andere Variable
int read = a;                  // CS9908, solange incA noch benutzt wird
```

Eine Closure darf ihre Variablen nicht überleben. Ein `move`-Lambda übernimmt sie deshalb:

```csharp
static F MakeAdder(int n) => move x => x + n;     // ohne move: CS9925
```

Delegates tragen die Lifetime dessen, was sie borgen. Wo ein Delegate gespeichert wird, etwa in einem
Feld oder einer Liste, muss er ohne Borrows auskommen. Das sagt die Signatur mit `'static`:

```csharp
class Button { F _click; public Button('static F click) { _click = click; } }
```

Ein `move`-Lambda darf ihre Captures nur verbrauchen, wenn der Delegate-Typ `[Once]` trägt. Der Aufruf
verbraucht dann den Delegate selbst, ein zweiter Aufruf ist `CS9900`. Das entspricht `FnOnce`.

Ein Delegate-Typ mit `[Mut]` entspricht `FnMut`: Nur solche Delegates dürfen ihre Captures ändern, und
ihr Aufruf braucht exklusiven Zugriff (`CS9927`).

## LINQ

LINQ funktioniert direkt auf Listen und Arrays, auch in Query-Syntax. Es ist lazy, wird monomorphisiert
und borgt die Sammlung. Lambdas bekommen die Elemente per `in` geliehen:

```csharp
var names = people.Where(p => p.Age >= 18).Select(p => p.Name).ToList();
var squares = from x in nums where x < 4 select x * x;
```

Eine Query darf nur einmal durchlaufen werden. `ToList`, `First` und ähnliche Methoden klonen ihre
Ergebnisse, die Elemente brauchen also Clone. Solange eine Query lebt, ist die Sammlung geborgt.
Sammlungen ohne direkten `Where`-Einstieg erreichen die übrigen Methoden über `AsQuery()`.

## Iteratoren

`yield return` funktioniert wie gewohnt und erzeugt eine Coroutine. `foreach` verbraucht die Sequenz:
Ein zweiter Durchlauf derselben Variable ist `CS9900`. Eine Iterator-Methode auf einer Instanz borgt
`this`, solange die Sequenz lebt.

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
t.Join().Unwrap();   // Err, wenn der Thread mit einem Panic endete
```

Jeder Typ ist automatisch `Send` (darf in einen anderen Thread wandern) und `Sync` (darf von mehreren
Threads geteilt werden), wenn seine Felder es sind. Rohzeiger, `Rc<T>`, `object` und Interfaces sind
es nicht. Verstöße ergeben `CS9923` und `CS9924`. Eigene Typen mit `unsafe` im Inneren geben ihre Regel
mit `[SendWhen]` und `[SyncWhen]` an.

Eine Closure für `Thread.Run` oder `Task.Run` muss ein `move`-Lambda sein. Ein `Mutex<T>` besitzt seine
Daten, sie sind nur über den Guard erreichbar, und der Guard gibt die Sperre am Scope-Ende frei.

Zur Verfügung stehen `Arc<T>`, `WeakArc<T>`, `Mutex<T>`, `RwLock<T>`, `RefCell<T>`, `Condvar`, `Barrier`,
`Lazy<T>`, `AtomicInt`, `AtomicLong`, `AtomicBool`, `Channel` und `ThreadScope` für Threads, die lokale
Daten borgen. `lock (x)` geht nur auf `System.Threading.Lock`, das keine Daten schützt; `Mutex<T>` ist
vorzuziehen.

Veränderliche `static`-Felder verlangen wegen möglicher Data Races `unsafe` (`CS9921`). `readonly static`
ist frei lesbar, muss aber `Sync` sein und ist auch im Inneren unveränderlich.

## async und await

```csharp
static async Task<int> Add(int a, int b)
{
    await Task.Delay(10);
    return a + b;
}

var handle = Task.Run(move () => Add(1, 2));
Console.WriteLine(await handle);
```

Die Schreibweise ist C#, das Verhalten ist Rust:

- **Tasks sind lazy.** Eine `async`-Methode läuft erst, wenn jemand sie mit `await` oder `Task.Run` antreibt.
- **`await` verbraucht den Task.**
- **Tasks lassen sich abbrechen, indem man sie freigibt.** Lokale Werte werden dabei freigegeben.
- **`await handle` liefert `Result<T, JoinError>`**, wie in Tokio: `Err`, wenn der Task mit einem
  Panic endete oder abgebrochen wurde.
- **Ein Task borgt, was seine Methode borgt.** Eine `async`-Instanzmethode borgt `this`, solange der Task lebt.
- **`Task.Run` verteilt auf Worker-Threads.** Freie Worker stehlen wartende Tasks. Nur die Closure und
  ihr Ergebnis müssen `Send` sein: Hält der Zustand eines Tasks etwas, das nicht `Send` ist, etwa ein
  `Rc<T>`, bleibt der Task ab dem ersten Poll auf seinem Thread.
- **Kooperatives Budget.** Nach 128 sofort bereiten I/O-Operationen gibt ein Task den Worker frei.
- **Programmende.** Endet `async Main`, werden noch lebende Tasks abgebrochen und freigegeben.
- **Sperren dürfen nicht über ein `await` gehalten werden** (`CS9926`).

Außerdem gibt es `Task.Yield`, `Task.FromResult`, `Task.WhenAll` und `async Task Main`. Für eigene
Leaf-Futures steht `Runtime.CurrentWaker()` bereit.

### Tokio-Bausteine

| Baustein | Bedeutung |
|---|---|
| `Task.Run` | Liefert einen `JoinHandle<T>`. Freigeben entkoppelt den Task, `Abort()` bricht ihn ab. |
| `Task.RunBlocking` | Blockierender Code auf einem eigenen Thread |
| `Task.WhenAny`, `Task.Race` | Der Erste gewinnt, die anderen werden abgebrochen |
| `Task.Timeout(task, ms)` | Bricht ab und liefert `Err(Elapsed)` |
| `Interval` | Gleichmäßiger Takt: `await tick.TickAsync()` |
| `AsyncMutex<T>` | Der Guard darf über `await` gehalten werden, Klone teilen die Daten |
| `Semaphore` | `await s.AcquireAsync()`, das Freigeben des Permit gibt ihn zurück |
| `Channel.CreateBounded<T>(n)` | `await tx.SendAsync(v)` wartet bei vollem Kanal |
| `rx.ReceiveAsync()` | Liefert `Option<T>`, `None`, wenn alle Sender weg sind: `while (await rx.ReceiveAsync() is Some(var v))` |
| `TaskCompletionSource<T>` | Ein von Hand abgeschlossener Task |
| `Notify` | `await n.NotifiedAsync()`, `n.NotifyOne()` weckt einen Wartenden |
| `Watch<T>` | Der neueste Wert: `Set`, `Get`, `await w.ChangedAsync()` |
| `Broadcast<T>` | Jeder `Subscribe()`-Empfänger bekommt jeden Wert, `T` muss Clone sein |
| `CancellationTokenSource` | `Cancel()`, `IsCancellationRequested`, `await CancelledAsync()` |
| `Signal.WaitAsync(n)` | Wartet auf ein Betriebssystem-Signal |

`async IAsyncEnumerable<T>` mit `yield return`, `await foreach` und `await using` funktionieren wie in C#.
`async ValueTask` und `async ValueTask<T>` ebenso. Wird ein `await foreach` verlassen, gibt das den
Iterator frei.

### Netzwerk

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

`ReadAsync` und `WriteAsync` borgen den Puffer, bis der Task fertig ist. Daneben gibt es
`TcpStream.ConnectAsync`, `ReadLineAsync`, `WriteAsync(string)` und `ShutdownWrite`. Jede Operation
liefert `Result<_, IoError>`, eine abgelehnte Verbindung ist also ein `Err`-Wert. `TcpListener` und `TcpStream` können IPv6 (`"::1"`), Hostnamen löst
`ConnectAsync` über `Dns.ResolveAsync` auf. Für Unix-Sockets gibt es `UnixListener` und `UnixStream`, für
Datagramme `UdpSocket` mit `SendToAsync` und `ReceiveFromAsync`. `File.ReadAllTextAsync` und `WriteAllTextAsync` laufen auf eigenen Threads.

## typeof und GetType

`typeof(T)` und `x.GetType()` liefern einen `Type` mit `Name` und `FullName`, mehr nicht. Generische
Parameter sind aufgelöst, `typeof(T)` in `NameOf<string>()` ist also `String`. `==` verbraucht beide
Operanden, `a.Same(in b)` nicht. Auf einem Typparameter liefert `GetType` den statischen Typ.

## Fehler: Result, `?` und Panics

Es gibt keine Exceptions. `throw`, `try`, `catch` und `finally` sind im Benutzercode Fehler (`CS9930`).
Wie in Rust gibt es zwei Arten von Fehlern:

**Erwartbare Fehler sind Werte.** Eine Methode, die scheitern kann, gibt `Result<T, E>` oder
`Option<T>` zurück. `x?` reicht den Fehler weiter: Bei `Err` (oder `None`) kehrt die Methode sofort
zurück und gibt ihre lokalen Werte frei, sonst ist `x?` der Wert darin.

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

- `f()?;` steht auch allein als Anweisung, `x?.Name` ruft nach dem Weiterreichen ein Member auf.
- Hat die Methode einen anderen Fehlertyp, wandelt `?` den Fehler über einen `implicit operator` um.
  Das ist Rusts `From`.
- `?` braucht eine Methode, die `Result` oder `Option` zurückgibt (`CS9932`), und einen Operanden dieses
  Typs (`CS9931`).
- Ein `?` gefolgt von `:` bleibt der Bedingungsoperator. `?.` auf anderen Typen ist ein Fehler (`CS9937`),
  denn eine Referenz ist nie `null`.

`Option<T>` hat die Methoden von Rusts `Option`: `IsSome`, `IsNone`, `IsSomeAnd`, `IsNoneOr`, `AsRef`,
`AsMut`, `AsDeref`, `AsDerefMut`, `Unwrap`, `Expect`, `UnwrapOr`, `UnwrapOrElse`, `UnwrapOrDefault`, `Map`,
`MapOr`, `MapOrElse`, `Inspect`, `OkOr`, `OkOrElse`, `Filter`, `And`, `AndThen`, `Or`, `OrElse`, `Xor`, `Zip`,
`Unzip`, `Take`, `TakeIf`, `Replace`, `Insert`, `GetOrInsert`, `GetOrInsertWith`, `Iter`, `IterMut`,
`Cloned`, `Copied`, `Transpose` und `Flatten`. `UnwrapOrDefault` verlangt wie in Rust `T : IDefault<T>`;
die eingebauten Zahlen, `bool`, `char` und `string` (`""`) erfüllen das.

`Result<T, E>` hat die Methoden von Rusts `Result`, in C#-Schreibweise:

| Zweck | Methoden |
|---|---|
| Auslesen | `Unwrap`, `UnwrapErr`, `Expect(msg)`, `ExpectErr(msg)`, `Ok()`, `Err()`, `IntoOk`, `IntoErr` |
| Prüfen | `IsOk`, `IsErr`, `IsOkAnd(f)`, `IsErrAnd(f)`; die beiden letzten verbrauchen das `Result` wie in Rust |
| Umwandeln | `Map`, `MapErr`, `MapOr(standard, f)`, `MapOrElse(fehlerFn, f)`, `Inspect(f)`, `InspectErr(f)` |
| Verketten | `And(r)`, `AndThen(f)`, `Or(r)`, `OrElse(f)` |
| Standardwerte | `UnwrapOr(x)`, `UnwrapOrElse(f)`, `UnwrapOrDefault()` |
| Referenzen | `AsRef()`, `AsMut()`, `AsDeref()` (für `Rc`, `Arc`, `Box`), `AsDerefMut()` (für `Box`) |
| Kopien | `Cloned()` und `Copied()` auf einem `Result<Ref<T>, E>` oder `Result<RefMut<T>, E>` |
| Verschachtelt | `Transpose()` auf `Result<Option<T>, E>`, `Flatten()` auf `Result<Result<T, E>, E>` |
| Iteration | `Iter()` für `foreach` und LINQ, `IterMut()` für `foreach (ref var v in ...)` |

### Referenzen als Werte: `Ref<T>` und `RefMut<T>`

`Ref<T>` ist Rusts `&T`, `RefMut<T>` ist `&mut T`. Anders als `in` und `ref` sind sie Werte und können
Typargumente sein, deshalb gibt es `Result<Ref<T>, Ref<E>>` wie in Rust:

```csharp
mut var r = int.Parse("41");
var view = r.AsRef();              // Result<Ref<int>, Ref<ParseError>>
Console.WriteLine(view.Unwrap().Value);
r.AsMut().Unwrap().Value += 1;     // ändert r selbst
bool big = r.AsRef().IsOkAnd(v => v.Value > 40);   // r bleibt erhalten
var copy = r.AsRef().Copied();     // Result<int, ParseError>
```

Der Borrow-Checker behandelt sie wie Rusts Referenzen: Solange `view` benutzt wird, ist `r` geborgt,
eine Zuweisung an `r` ist dann `CS9907`. Zwei `AsMut` gleichzeitig sind `CS9911`, und eine Referenz,
die eine Methode verlassen soll, aber in einen lokalen Wert zeigt, ist `CS9912`. `Ref<T>` ist Copy,
`RefMut<T>` wird verschoben. `Ref<T>.Of(in x)` und `RefMut<T>.Of(ref x)` entsprechen `&x` und `&mut x`.

Referenzen dürfen auch in Sammlungen stehen, wie Rusts `Vec<&T>`: `List`, `Dictionary`, `HashSet`,
`Queue`, `Stack` und `SortedDictionary`. Was eine Sammlung speichert, muss sie überleben
(`list.Add(Ref<int>.Of(in x))` verlangt, dass `x` länger lebt als `list`), und was herauskommt (`Pop`,
`list[i]`, `foreach`), ist nur so lange gültig wie die Sammlung. Eine Sammlung voller Referenzen kann
eine Methode verlassen, wenn ihre Referenzen in die Argumente zeigen:

```csharp
static List<Ref<Person>> Adults(in List<Person> people)
{
    mut var result = new List<Ref<Person>>();
    foreach (ref readonly var p in people)
        if (p.Age >= 18) result.Add(Ref<Person>.Of(in p));
    return result;
}
```

Strenger als Rust: Ein Wert, der aus einer Sammlung herauskopiert wird, darf die Sammlung selbst nicht
überleben, auch wenn das, worauf er zeigt, noch lebt. Eine Sammlung von Referenzen in einem Feld eines
Objekts ist ein Fehler (`CS9914`), weil Klassen keine Lifetime-Parameter haben.

`Box<T>` ist Rusts `Box`: ein Wert auf dem Heap mit einem Besitzer. `Value` gibt geteilten Zugriff,
`ValueMut` exklusiven, `Unbox()` holt den Wert heraus. `[Copy]` an einem Typparameter verlangt wie
`T: Copy` einen Copy-Typ (`CS9922`).

Die Corelib wirft nichts. Was in Rust fehlschlagen darf, liefert dort ein `Option` oder `Result`:

| Aufruf | Ergebnis |
|---|---|
| `int.Parse`, `long.Parse`, `decimal.Parse` | `Result<_, ParseError>` |
| `list.RemoveLast()`, `stack.Pop()`, `queue.Dequeue()` | `Option<T>`, `None` wenn leer |
| `First()`, `Last()`, `Single()`, `Max()`, `Min()`, `Average()` | `Option<T>`, `None` ohne Elemente |
| `dict.Add(key, value)` | `Option<V>`: ersetzt den alten Wert und gibt ihn zurück, wie `HashMap::insert` |
| `receiver.Receive()` | `Result<T, RecvError>` |

Rusts Namen gibt es zusätzlich: `List` hat `Push`, `Pop`, `Len`, `IsEmpty`, `Get`/`GetMut` (Option einer
Referenz), `Remove`, `SwapRemove`, `Swap`, `Truncate`, `Retain`, `Dedup`, `Extend`, `Iter`; `Dictionary` hat
`Insert`, `Get`/`GetMut`, `Len`, `OrInsert` (`entry().or_insert()`), `OrInsertWith`, `Keys`, `Values`;
Iteratoren haben `Map`, `Filter`, `Fold`, `Find`, `Position`, `Nth`, `Enumerate`, `StepBy`, `Chain`, `Rev`,
`Collect`. `string.Join(sep, list)` verbindet.

Wie in Rust paniken dagegen Indexer und Methoden, die eine Referenz liefern (`list[i]`, `dict[key]`,
`Peek()`), außerdem `RefCell.BorrowMut` bei bestehendem Borrow (vorher fragt man `CanBorrowMut`).

 Netzwerk und
Dateien geben `Result<_, IoError>` zurück. Für `decimal` gibt es `CheckedAdd`, `CheckedSub`,
`CheckedMul`, `CheckedDiv`, `CheckedRem` und `CheckedToInt64`, die `Option` liefern. `Unit` ist Rusts
`()`, zum Beispiel in `Result<Unit, IoError>`.

**Fehler im Programm sind Panics.** `Panic.Raise("...")`, `Panic.Unreachable()`, `Panic.Todo()` und
`Panic.Assert(bedingung)` entsprechen `panic!`, `unreachable!`, `todo!` und `assert!`. Auch
Null-Zugriffe, Indexfehler, Division durch null, ungültige Casts, `checked`-Überläufe und
`Unwrap()` auf `Err` oder `None` sind Panics. Die Meldung erscheint wie in Rust, mit Datei, Zeile und
Spalte im Benutzercode:

```
thread 'main' panicked at src/main.rscs:7:38:
index out of bounds
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

Danach wickelt der Panic den Thread ab und gibt dabei alle Werte frei. Im Hauptthread endet das
Programm mit Exit-Code 101. In einem anderen Thread oder Task lässt sich ein Panic nicht abfangen,
aber beobachten: `thread.Join()` und `await handle` liefern dann `Err(JoinError)` mit `IsPanic` und
`Message`. Ein abgebrochener Task liefert `Err` mit `IsCancelled`.

**`Main` darf ein `Result` zurückgeben**, auch als `async Task<Result<T, E>>`. `Ok` beendet das
Programm mit Exit-Code 0, `Err` gibt `Error: ` und den Fehler auf stderr aus und endet mit 1:

```csharp
static Result<Unit, ParseError> Main()
{
    int n = int.Parse("41")?;
    Console.WriteLine(n + 1);
    return Result<Unit, ParseError>.Ok(default);
}
```

Wird ein Iterator oder Task vorzeitig freigegeben, laufen seine Destruktoren. Aufräumarbeit gehört
in einen Destruktor oder ein `using`, beide laufen auch beim Abwickeln eines Panics.

## unsafe

In `unsafe`-Code sind Rohzeiger erlaubt, und Borrows durch sie werden nicht geprüft. `unsafe` ist
außerdem nötig für:

- Zugriffe auf veränderliche `static`-Felder (CS9921), weil jeder Thread das Feld ändern kann
- `Mem.Transmute` (CS9921)

Die wichtigsten Bausteine aus `Mem`:

| Methode | Bedeutung |
|---|---|
| `Take(ref x)` | verschiebt den Wert heraus, lässt `default` zurück |
| `Replace(ref x, v)` | tauscht den Wert und gibt den alten zurück |
| `Swap(ref a, ref b)` | vertauscht zwei Werte |
| `Drop(x)` | gibt sofort frei |
| `Forget(x)` | übernimmt den Wert, ohne ihn freizugeben |
| `Read(p)`, `Write(p, v)` | bitweises Lesen und Schreiben über Zeiger |
| `DropInPlace(p)` | gibt den Wert hinter einem Zeiger frei |

## Fehlercodes

| Code | Bedeutung |
|---|---|
| CS9900 | Verwendung eines verschobenen Werts |
| CS9901 | Borrow eines verschobenen Werts |
| CS9902 | Move aus einem Borrow |
| CS9903 | Move aus einem Array-Element |
| CS9904 | Move aus einem `static`-Feld |
| CS9905 | Move aus einem Typ mit Destruktor |
| CS9906 | Move eines geborgten Werts |
| CS9907 | Zuweisung an einen geborgten Wert |
| CS9908 | Verwendung während eines exklusiven Borrows |
| CS9909 | exklusiver Borrow trotz bestehendem Shared-Borrow |
| CS9910 | Shared-Borrow trotz bestehendem exklusivem Borrow |
| CS9911 | zwei exklusive Borrows zugleich |
| CS9912 | Wert lebt nicht lange genug |
| CS9913 | temporärer Wert wird freigegeben, während er geborgt ist |
| CS9914 | Referenz auf eine lokale Variable wird zurückgegeben |
| CS9915 | Lifetime reicht nicht aus |
| CS9916 | Lifetime-Angabe fehlt |
| CS9917 | Zuweisung hinter einer Shared-Referenz |
| CS9918 | exklusiver Borrow hinter einer Shared-Referenz |
| CS9919 | Feature wird nicht unterstützt |
| CS9920 | Empfänger passt nicht zur Deklaration |
| CS9921 | `unsafe` erforderlich |
| CS9922 | Typ implementiert kein Clone |
| CS9923 | Typ ist nicht `Send` |
| CS9924 | Typ ist nicht `Sync` |
| CS9925 | Closure könnte länger leben als das, was sie borgt |
| CS9926 | Wert darf nicht über ein `await` gehalten werden |
| CS9927 | Delegate ohne `[Mut]` ändert seine Captures |
| CS9933 | `dynamic`: Interfaces statt `dyn Trait`, `object` mit `is` statt `dyn Any` |
| CS9934 | Basisklasse angegeben: es gibt keine Vererbung |
| CS9930 | `throw`, `try`, `catch` oder `finally` |
| CS9931 | `?` auf etwas, das weder `Result` noch `Option` ist |
| CS9932 | `?` in einer Methode, die kein passendes `Result` oder `Option` zurückgibt |
| CS9928 | zweite Zuweisung an eine Variable ohne `mut` |
| CS9929 | Änderung oder exklusiver Borrow einer Variable ohne `mut` |
| CS8509 | `switch`-Ausdruck deckt nicht alle Fälle ab |
| CS9935 | `null`: ein fehlender Wert ist `Option<T>.None` |
| CS9936 | `#nullable`: Referenzen sind nie `null` |
| CS9937 | `x!`, `??`, `??=`, `?.` auf einer Referenz, `as` |
| CS9938 | Ein Ausdruck würde `null` enthalten: `default`, `new T[n]`, `new S()` |
| CS8618 | Feld ohne Wert nach dem Konstruktor |
