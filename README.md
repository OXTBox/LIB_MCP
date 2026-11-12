# LIB_MCP

Lets Claude Code, a local model (LM Studio, through MCP) or any tool drive a running
LiveCode 9.6.3: run code, evaluate expressions, **compile-check scripts**, read script
errors (translated, from a log file), and take snapshots. Part of a family of separate
libraries; see "Family" below.

| Path | What it is |
|---|---|
| `livecode/lib_mcp.livecodescript` | The server: a LiveCode library stack (`start using`) |
| `standalone/xt3d_MCP.livecode` + `launcher.livecodescript` | A standalone build of the server (port 8767) that clients start by themselves |
| `python/lib_mcp/` | Python package, standard library only: `client`, `cli` (`lcmcp`), `mcp_server`, `ask_local`, `eval_livecode`, `livecode_primer.md` |
| `tools/lcmcp` | Runs the command line without installing anything |

## In LiveCode

```
start using stack "<path>/LIB_MCP/livecode/lib_mcp.livecodescript"
DevServer.Start 8766, "<stack that /run should talk to>"
```

Or open that file with File > Open Stack (starts on 8766). Everything it writes goes to
`C:\LIB_MCP`: token files, `livecode_errors.txt` (every script error, translated), and
LiveCode's error message lists (saved when it starts in the IDE, used by the standalone).

The target stack may define `DevServer.Exec pCode` and `DevServer.Eval pExpr` so `/run`
reaches its handlers and script locals; without them, code runs in the library.

## From a terminal (WSL or Windows)

```
tools/lcmcp ping                     # the IDE (8766)
tools/lcmcp --standalone ping        # the standalone (8767), started if needed
tools/lcmcp compile some.livecodescript
tools/lcmcp run 'put the version'
tools/lcmcp errors 3
```

Or install the package: `pip install -e python/` gives `lcmcp`, `lcmcp-server`, `lcmcp-ask`.

## MCP (LM Studio, Claude Desktop)

`python/lib_mcp/mcp_server.py`, with tool packs from other libraries via `--tools pack.py`.
See the header of `mcp_server.py` for the LM Studio `mcp.json` entry.

Built-in tools: `livecode_primer`, `livecode_status`, `livecode_run`, `livecode_eval`,
`livecode_compile`, `livecode_errors`, `livecode_snapshot`. Small local models do not know
LiveCode; `livecode_primer.md` fixes that (tested with spark-x2.6-4b).

## The standalone

Paste `standalone/launcher.livecodescript` as the stack script of
`standalone/xt3d_MCP.livecode` and build for Windows. The build lands in
`standalone/xt3d_MCP/Windows x86-64/`. It finds `livecode/lib_mcp.livecodescript` by
walking up from its own file, so server changes need no rebuild.

**This runs any code it is sent.** It answers 127.0.0.1 only and checks a fresh token,
but it is for development: never put it inside an application you give to others.

## Family (separate libraries under ~/projects, each its own git repository)

| Library | What it is |
|---|---|
| `xt3D_Raylib_Livecode_Bridge` (xt3d) | raylib 3D for LiveCode (LCB extension + DLL); its MCP tool pack is `mcp/xt3d_tools.py` |
| `LIB_MCP` | this |
| `LIB_XTJSON` | stacks <-> JSON (harvest, rebuild, diff) |
| `LIB_BIT` | 1-bit grids: PBM text, BitFontMaker2 fonts, sprite frames |
| `LIB_TRACE` | bitmap outline tracing, grid to 3D map |
| `Vibecode3D` | the vector 3D engine (contains LIB_LLM) |
| `xtalk_py` | Python runtime for xTalk (planned) |
