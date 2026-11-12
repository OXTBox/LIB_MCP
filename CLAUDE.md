# LIB_MCP: notes for Claude Code

Read `README.md`. The owner (wrote iGame3D, fluent in LiveCode, rusty in C/Python) runs
LiveCode 9.6.3 on Windows; this repo lives in WSL and is reached from Windows as
`\\wsl$\Ubuntu\home\igame3d\projects\LIB_MCP`.

- Use `tools/lcmcp compile <file>` on every LiveCode script before giving it to the owner,
  in any of the family's projects. It starts the standalone by itself.
- LiveCode errors: `tools/lcmcp errors`. Never ask the owner to retype an error.
- Code sent with `run` goes through `do` inside a server handler: do not declare locals
  that handler uses (`tErr`, `tResult`); prefer unusual names.
- Only one listener per engine: the IDE uses 8766 (a stack starts it), the standalone 8767.
- The server is a script-only stack. If the owner saves it from the IDE, LiveCode writes
  its in-memory copy over the file (and adds a BOM). Check against git if the file changes.
- When a local model makes a new kind of LiveCode mistake, add it to
  `python/lib_mcp/livecode_primer.md`.
- Pitfalls met so far: one-line `if` before `else`; variable names that spell keywords
  (`tExt`, `tHere`); chunk order (`word of char` is a compile error); `create` without an
  explicit stack puts the control into whatever stack is the defaultStack.
