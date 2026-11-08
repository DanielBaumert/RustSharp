# RustSharp for VS Code

Editor support for RustSharp, C# syntax with Rust semantics, compiled natively by `rustsharp`.

- **Errors as you type:** Roslyn's errors and the ownership checker's (moves, borrows, lifetimes, `mut`,
  Send/Sync), with the related spans that `rustsharp` shows in the terminal.
- **Hover:** the type, `mut`, whether a value is copied or moved, and the doc comment.
- **Go to definition**, also into the core library, **completion** after `.` and an **outline**.
- **Highlighting** for `mut`, `move`, lifetimes such as `'a`, the `?` operator, `Panic.Raise`, `str` and `Rune`.
- **Commands:** RustSharp: Run File (Ctrl+F5), Build File, Check File, Show MIR, Show LLVM IR.
- **Tasks** with the `$rustsharp` problem matcher, and snippets (`mainr`, `maina`, `fnr`, `enumd`, `enumt`, `trait`, `match`, `str`, `mut`, `spawn`, ...).

The extension starts `rustsharp --lsp`. It finds `rustsharp` at the root of a workspace folder or on the PATH;
the setting `rustsharp.compilerPath` overrides that.

RustSharp files end in `.rscs`; the extension takes them everywhere. Ordinary `.cs` files stay with the C# extension.
