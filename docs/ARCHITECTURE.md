# RustSharp Compiler Architecture: Target and Migration

This document describes the target architecture: RustSharp's own frontend, with no dependency on
Roslyn. It also lays out the steps to get there. The current pipeline is described in the README,
under "Compiler architecture".

## Why move away from Roslyn

RustSharp has C#'s syntax and Rust's semantics. The Roslyn fork got the project running quickly, but
several Rust rules have to work around it.

- **Lifetimes are not part of the types.** The parser keeps `'a` as skipped trivia, and
  `Ownership/Lifetimes.cs` reads it back from the syntax.
- **Trait bounds are checked after monomorphization, not generically.** Rust checks
  `T: Send`, `K: Eq + Hash` and `T: Ord` before it instantiates anything. RustSharp checks Send/Sync
  only on generated code. It accepts `Dictionary<K, …>` without equality, and `Sort()` without
  ordering.
- **MIR is lowered straight from Roslyn's bound tree.** Nodes that the lowering synthesizes have no
  location of their own, so a diagnostic can point at the method body instead of the line rustc
  would blame.
- **The fork has to be maintained.** RustSharp changes are spread over Roslyn's parser and binder.
  Builds and test runs are slow.

## Target pipeline

```text
C#-like source (.rscs)
        │
        ▼
Lexer
- written anew, with Roslyn's behaviour as the reference
  (literals, escapes, interpolated and raw strings)
- real tokens for 'a, mut, move
        │
        ▼
Parser
- its own syntax tree, with locations
- C#-like grammar
- error-tolerant, for the language server
- no Roslyn syntax nodes in the compiler core
        │
        ▼
Binder
- names and overloads
- C#-like types and generics, type inference
- lambdas and delegates
- lifetimes as part of the types
- trait resolution and bound checking done generically
  (T : IEq<T>, Send/Sync), before monomorphization as in Rust
        │
        ▼
HIR
- its own symbols, independent of Roslyn
- explicit ownership, moves and borrows
- normalised forms, each with a location: tuples, foreach, await,
  initializers, patterns
        │
        ▼
MIR
- locals, assignments, move/copy
- borrows, call/return
- drop elaboration: explicit drops, each with a location
        │
        ├──────────────► Borrow checker
        │                 - one region per lifetime position
        │                 - variance, outlives, NLL
        │                 - move state, conflicts
        │
        ▼
Monomorphization
- substitution only, no checks
        │
        ▼
LLVM backend
        │
        ▼
clang / native ELF

Beside the compiler core:
Language server (rustsharp --lsp) ◄── parser + binder
```

## Decisions

| Question | Decision | Reason |
|---|---|---|
| Implementation language | C# on .NET | Starts at once, and the new frontend can be compared with the existing one. Self-hosting in RustSharp stays possible later. |
| Lexer | Written anew, not extracted from Roslyn | Roslyn's lexer depends on its whole syntax-tree infrastructure: green nodes, trivia, the text window, the preprocessor. Its behaviour and its lexer tests serve as the reference (MIT licence). |
| Where trait bounds are checked | In the binder, generically | This is how Rust works: monomorphization only substitutes. |
| Where drops are elaborated | In MIR | As in rustc. Every drop has a location. |
| Scope | What the core library and the test suite use | Not all of C#. Inheritance, `null`, exceptions and `dynamic` are excluded anyway. |

## Migration

Each step is useful on its own. The suite, the ASan suite and the probes stay green after each step.

1. **HIR and own symbols.** MIR, the borrow checker and the backend work only on HIR and RustSharp
   symbols. Roslyn becomes an adapter that produces HIR. Today the core has 67 kinds of bound node
   and more than 400 uses of Roslyn symbols in `Ownership/`; this step is the prerequisite for the
   others. It is useful even if Roslyn stays.
2. **Own lexer and parser.** They produce their own syntax tree. Differential testing: for every
   file in `corelib/` and `tests/`, both frontends must produce the same structure.
3. **Own binder, with trait checking.** It starts with the subset the core library uses: `unsafe`
   and pointers, `extern`, `ref struct`, extension methods, static abstract members (`T.Default()`),
   `partial`, attributes and interpolated strings. Then the rest follows: LINQ, patterns, `async`,
   iterators.
4. **Switch over.** The language server moves to the new frontend, and the Roslyn fork is dropped.

## Done when

- The new frontend compiles the whole `corelib/`.
- `python3 tests/run.py` (also with `--asan`) and `python3 tests/probes/run.py` are green on the new
  frontend, with the same diagnostics on the same lines.
- The VS Code extension works on `rustsharp --lsp` without Roslyn.
