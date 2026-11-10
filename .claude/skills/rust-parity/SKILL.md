---
name: rust-parity
description: >-
  RustSharp's design rule: every language, checker, corelib and runtime decision follows Rust's
  semantics, expressed in C# syntax. Use whenever designing or changing a feature, a borrow-checker
  rule, lifetimes, variance, generics, traits, iterators, closures, threads, async, error handling,
  the core library or diagnostics; whenever choosing between several solutions; and whenever a result
  differs from what rustc would do (accepts what Rust rejects, or rejects what Rust accepts).
---

# Rust parity

RustSharp is C# syntax with Rust semantics. Rust parity is a goal in its own right. It is not only a
way to get safety. The user chose "wie Rust" for iterators, lifetimes, generics, variance and the
region model. A missing Rust feature belongs on the plan even when no program fails without it.

## Deciding

1. **Ask: what does Rust do?** Before designing anything, write down the Rust equivalent: the type
   or signature, rustc's verdict, and its error code (E0499, E0505, E0597, …). If you are not sure,
   say so and check the Rust reference or the rustc behaviour. Do not guess.
2. **Take Rust's rule and C#'s surface.** Rules and semantics come from Rust: ownership, moves,
   borrows, NLL, lifetimes, variance, Send/Sync, `Result` with `?`, panics, `Option` instead of
   `null`, `&self`/`&mut self`. Syntax comes from familiar C# forms: `foreach`, LINQ names,
   `async Task<T>`, `x.Clone()`, `where T : 'a`, `<'a>`. Add a new keyword only where C# has no form,
   as with `move` lambdas and `mut`.
3. **Model, not special case.** Build Rust's actual mechanism, for example type substitution,
   regions per lifetime position, or variance derived from fields. Do not patch one symptom. If a
   heuristic summary (one region for many) causes a gap, replace it with Rust's structure.
4. **Several Rust-faithful designs, or Rust doesn't map cleanly?** Stop and ask the user. Show a
   small side-by-side of the Rust code and the RustSharp code. Name the option that is closest to
   Rust.

## Allowed deviations

| Situation | Allowed? |
|---|---|
| Accept a program Rust rejects | **Never.** That is a checker gap: fix it first. |
| Reject a program Rust accepts (`strict`) | Only as a documented interim step. List it in STATUS.md "Offen" and in docs/LANGUAGE.md as "stricter than Rust, never unsound", with the plan to remove it. |
| Behaviour differs at run time | Only where .NET forces it. Document it and match Rust's observable output (panic message format, exit code 101). |

## Verifying

- **Probes** (`tests/probes/*.py`): every rule gets cases with Rust's verdict as the expectation.
  - `'ok'`: Rust accepts.
  - `'reject'`: Rust rejects.
  - `'strict'`: Rust accepts, RustSharp rejects soundly; this is the documented deviation.

  Write them on both sides, the case Rust rejects and the neighbouring case Rust accepts.
- **Suite**: tests/run-pass and tests/compile-fail, with `// error: CSxxxx` on the line rustc would
  blame.
- **Mutation check**: disable the new rule and confirm that its probes or tests turn red. Report
  any rule that no test catches.
- **Commands**: run `python3 tests/run.py`, `python3 tests/run.py --asan` and
  `python3 tests/probes/run.py` after every checker change.
- **Diagnostics**: phrase them like rustc, for example "cannot borrow `x` as mutable more than once
  at a time", with notes and help lines in Rust's style.

## Reporting

Say how each change relates to Rust: "as Rust", "stricter than Rust (sound)", or "Rust has no
equivalent". For soundness topics, also follow the soundness-language skill and use neutral wording.
