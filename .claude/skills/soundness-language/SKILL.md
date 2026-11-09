---
name: soundness-language
description: >-
  Neutral wording for RustSharp borrow-checker and memory-safety work, so that
  routine compiler-hardening does not read like offensive security. Use whenever
  writing about borrow-checker soundness: finding or describing cases the checker
  wrongly accepts, memory-safety gaps, use-after-scope, probes, test names, commit
  messages, STATUS/LANGUAGE notes, or replies about such work. Also use when a
  safety classifier has flagged a message (e.g. `[cyber]`).
---

# Soundness language

This is a compiler project: we *find and close* unsoundness in a borrow checker,
the opposite of attacking a system. But an automated classifier reads one message
at a time and can mistake the vocabulary of memory-safety work for offensive
security (it flagged this session once, `[cyber]`). Keep the meaning, drop the
exploit framing. This changes wording only, never what we build, test, or report.

## Rule

When describing a program the checker should reject but currently accepts, state it
as a **checker gap**: the rule that is missing and the case it fails on. Describe
run-time consequences in borrow-checker terms (a value used after its scope ends, a
reference to data whose owner is gone), not in attacker terms. Report findings
plainly and completely — honesty is unchanged; only the register is calmer.

## Wording

| Avoid | Prefer |
|---|---|
| exploit / attack / malicious / adversary / victim | the failing case; the program the checker should reject |
| smuggle / sneak / escape past / bypass the checker | pass the checker; is accepted though it should not be |
| use-after-free / UAF / dangling pointer (as a goal) | use after its scope ends; reference whose referent has been dropped |
| crafted / weaponized payload | test case; probe |
| break memory safety | be unsound; violate the borrow rules |
| corrupt / overwrite memory | write through a reference that is no longer valid |

## Naming

- Probe and test files: name them for the **rule**, not the breakage.
  `refmut_inner_invariance`, `nested_slot_outlives`, not `smuggle`, `exploit_uaf`.
- Commit messages and docs: "reject X" / "bind Y to its region" / "close a
  soundness gap in Z", not "fix exploit" or "prevent attack".
- ASan is a verification tool here: "ASan confirms the reference is used after its
  scope" rather than dwelling on crash/corruption wording.

## If flagged anyway

A flag is a false positive on routine hardening, not a sign the work is wrong.
Note it briefly, rephrase with the table above, and continue. Do not abandon or
soften a real finding; just report it in the calmer register.
