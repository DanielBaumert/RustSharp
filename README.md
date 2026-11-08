# RustSharp

RustSharp is an experimental C# compiler that combines C# syntax with Rust-inspired
ownership, borrowing, lifetimes, and deterministic destruction. It is built as
a fork of [Roslyn](https://github.com/dotnet/roslyn), with a native LLVM
backend instead of the CLR/IL runtime.

The goal is to make memory safety and data-race prevention compile-time
properties while keeping the familiar C# programming model:

```csharp
var log = new File("log.txt");
Archive(log);          // ownership moves into Archive
log.Close();           // compile-time error: log was moved
```

Programs are compiled to native ELF binaries that depend only on `libc` and
`libm`. There is no garbage collector: values have a single owner and are
released deterministically when their owner leaves scope.

> **Status:** RustSharp is an experimental project. The ownership checker is heavily
> tested, but it is not formally verified and the supported platform is
> currently x86-64 Linux.

## Features

- Rust-style ownership and move checking
- Shared (`in`) and exclusive (`ref`) borrows
- Non-lexical lifetimes and lifetime annotations
- `mut` variables with immutable-by-default bindings
- `Option<T>` instead of `null`, in user code and in the core library
- `Result<T, E>` and `?` error propagation
- `Drop`, `Clone`, and opt-in `[Copy]` types
- Traits through C# interfaces with default methods
- UTF-8 `string`/`str` types
- Generics, LINQ, iterators, records, closures, and pattern matching
- Native `async`/`await`, tasks, channels, timers, and networking
- LLVM IR and MIR output for compiler development
- A VS Code extension with diagnostics, hover information, completion,
  navigation, syntax highlighting, and build/run commands

## Quick start

Requirements: .NET SDK 10.0.1xx, the .NET 9 runtime, and `clang` on `PATH`. The compiler is a fork of
Roslyn, kept as the submodule `roslyn` (branch `rustsharp` of
[DanielBaumert/roslyn](https://github.com/DanielBaumert/roslyn)).

```bash
git clone --recurse-submodules https://github.com/DanielBaumert/RustSharp.git
cd RustSharp
tools/build.sh Release
./rustsharp examples/demo.rscs -o demo
./demo

# Check ownership and borrowing without producing a binary
./rustsharp examples/errors.rscs --check

# Run the test suite
python3 tests/run.py
python3 tests/run.py --asan
```

### Docker

The image builds the compiler and brings `clang`, so nothing else is needed on the host:

```bash
git clone --recurse-submodules https://github.com/DanielBaumert/RustSharp.git
cd RustSharp
docker build -t rustsharp .
docker run --rm -v "$PWD":/work -w /work rustsharp examples/demo.rscs -o demo
./demo
```

The compiler supports `-O0` through `-O3`, `--check`, `--asan`, `--tsan`,
`--emit-llvm <file>`, `--emit-mir <file>`, `--no-borrowck`, and
`--corelib <directory>`.

## RustSharp and Rust concepts

| RustSharp | Rust equivalent |
|---|---|
| `mut int x = 1` | `let mut x = 1` |
| `void F(Foo x)` | `fn f(x: Foo)`; ownership moves into the function |
| `in Foo x` | `x: &Foo` |
| `ref Foo x` | `x: &mut Foo` |
| `readonly` instance method | `&self` |
| normal instance method | `&mut self` |
| `move` instance method | `self` |
| `Result<T, E>`, `x?` | `Result<T, E>`, `?` |
| `Option<T>` | `Option<T>` |
| `[Copy]` | `#[derive(Copy)]` |
| `Rc<T>`, `Mutex<T>` | `Rc<T>`, `Mutex<T>` |
| `async Task<T>`, `await` | `async fn`, `.await` |
| `string`, `str` | `String`, `&str` |

The complete language reference is in
[docs/LANGUAGE.md](docs/LANGUAGE.md).

## VS Code

The `editors/vscode` extension starts `rustsharp --lsp` and reports Roslyn and
ownership-checker diagnostics while editing. It also provides type and
ownership information on hover, completion, go-to-definition, syntax
highlighting, snippets, and commands for running, building, checking, and
inspecting MIR or LLVM IR.

```bash
python3 tools/package_vscode.py
code --install-extension editors/rustsharp-0.6.0.vsix
```

RustSharp source files end in `.rscs`, the core library's included; the extension recognizes them
everywhere. Ordinary `.cs` files stay with the C# extension.

## Compiler architecture

```text
Source
  -> Roslyn lexer/parser/binder/flow analysis
  -> MIR builder
  -> borrow checker (moves, NLL regions, loan conflicts)
  -> monomorphization
  -> LLVM IR
  -> clang
  -> native ELF binary
```

The main RustSharp implementation is under
`roslyn/src/Compilers/CSharp/Portable/Ownership/`:

| Component | Purpose |
|---|---|
| `Mir.cs` | Mid-level representation based on rustc's MIR |
| `OwnershipFacts.cs` | Copy/Drop rules and lifetime elision |
| `MirBuilder.cs` | Bound tree lowering, drop scopes, and unwind edges |
| `BorrowChecker.cs` | Move, borrow, and lifetime checking |
| `LlvmBackend.cs` and `LlvmFunction.cs` | Native code generation and coroutines |
| `NativeCompiler.cs` | Public compiler pipeline |

The RustSharp driver is in `roslyn/src/Compilers/CSharp/rustsharp/`, the standard
library is in `corelib/`, and compiler/runtime tests are in `tests/`.

Without the `ownership` feature flag, the Roslyn fork remains a regular C#
compiler that emits IL.

## Verification

The project includes compile-pass and compile-fail tests, runtime tests,
AddressSanitizer/LeakSanitizer and ThreadSanitizer runs, decimal differential
tests against .NET, and selected Roslyn test suites. The current project status
and test counts are tracked in [STATUS.md](STATUS.md).

Benchmarks in this repository compare native RustSharp programs with equivalent C
and Tokio programs. They are illustrative single-machine measurements, not
general performance claims.

## Known limitations

- Only x86-64 Linux is currently tested; `clang` is required at compile time.
- `dynamic`, general reflection, and arbitrary-object `lock` are unsupported.
- There is no `null`, neither in user code nor in the core library; use `Option<T>` for optional values.
  Only raw pointers in `unsafe` code may be null, as with Rust's `ptr::null`.
- Core-library iterators (`IIter<T>.Next()`) still return a raw `T*` and signal the end with a null
  pointer, instead of an `Option<Ref<T>>` like Rust's `Iterator::next`.
- Tasks are lazy, like Rust futures, rather than automatically starting like
  ordinary C# tasks.
- The runtime uses a single reactor thread; file I/O runs on dedicated threads.
- Lifetimes and `ref struct` rules are intentionally simpler than Rust's.
- The core library is deliberately small.
- The ownership checker has not been formally verified.

See the final section of [docs/LANGUAGE.md](docs/LANGUAGE.md) for the detailed
language and runtime limitations.

## License

RustSharp is licensed under the [MIT License](LICENSE). The included Roslyn
fork and other third-party components remain subject to their respective
licenses.

## AI Disclosure

Parts of RustSharp were developed with assistance from AI tools.
