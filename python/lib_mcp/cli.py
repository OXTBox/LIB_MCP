"""lcmcp - command line for a LIB_MCP dev server inside LiveCode.

    lcmcp ping                       is LiveCode there?
    lcmcp run  '<statements>'        run in the target stack ("-" reads stdin); --server: in the library
    lcmcp eval '<expression>'
    lcmcp compile FILE...            compile-check scripts: COMPILES OK or errors with file line numbers
    lcmcp errors [N]                 last N logged LiveCode errors (reads the log; no server needed)
    lcmcp lint FILE...               stray empty puts and other bug habits (no server needed)
    lcmcp snap [WINDOWS_PATH]        PNG of the target stack (default C:/LIB_MCP/snap.png)
    lcmcp reload [WINDOWS_PATH]      close and reopen the target stack from its file
    lcmcp harvest STACKFILE [OUT]    stack file -> XTJSON folder (default ~/projects/XTJSON/<file name>),
                                     using LIB_XTJSON's harvester; the stack's own handlers do not run

    --standalone   use the standalone (port 8767; started when needed) instead of the IDE (8766)
    --port N       any other port
compile and harvest use the standalone and fall back to the IDE.
"""
import argparse, sys

if __package__ in (None, ''):          # run as a file: make "lib_mcp" importable
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_mcp.client import Client, NotRunning, recent_errors, IDE_PORT


def pick(a, prefer_standalone=False):
    if a.port:
        return Client(a.port)
    if a.standalone or prefer_standalone:
        try:
            return Client.standalone(slot=None)
        except NotRunning:
            if a.standalone:
                raise
    return Client(IDE_PORT)


def load_xtjson():
    """LIB_XTJSON's python/xtjson_harvest.py: sibling folder, or $LIB_XTJSON_DIR"""
    import os
    lib = os.environ.get('LIB_XTJSON_DIR') or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '..', 'LIB_XTJSON')
    path = os.path.join(lib, 'python')
    if not os.path.isfile(os.path.join(path, 'xtjson_harvest.py')):
        raise SystemExit('lcmcp harvest needs LIB_XTJSON beside LIB_MCP (or set LIB_XTJSON_DIR); not found at ' + lib)
    sys.path.insert(0, path)
    import xtjson_harvest
    return xtjson_harvest


def main(argv=None):
    ap = argparse.ArgumentParser(prog='lcmcp', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--standalone', action='store_true')
    ap.add_argument('--port', type=int)
    ap.add_argument('command', choices=['ping', 'run', 'eval', 'compile', 'errors', 'lint', 'snap', 'reload', 'harvest'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--server', action='store_true', help='run/eval in the library itself, not the target stack')
    a = ap.parse_args(argv)

    if a.command == 'lint':
        from lib_mcp import lint
        return lint.main(a.args)
    if a.command == 'errors':
        print(recent_errors(int(a.args[0]) if a.args else 5), end='')
        return 0
    try:
        if a.command == 'harvest':
            if not a.args:
                print('usage: lcmcp harvest STACKFILE [OUTFOLDER]', file=sys.stderr)
                return 2
            xh = load_xtjson()
            ok, out = xh.harvest(a.args[0], a.args[1] if len(a.args) > 1 else None, client=pick(a, prefer_standalone=True))
            print(out)
            return 0 if ok else 1
        if a.command == 'compile':
            c, bad = pick(a, prefer_standalone=True), 0
            for f in a.args:
                ok, text = c.compile(open(f, encoding='utf-8', errors='replace').read())
                print(('%s: ' % f if len(a.args) > 1 else '') + text.strip())
                bad += 0 if (ok and text.startswith('COMPILES OK')) else 1
            return 1 if bad else 0
        c = pick(a)
        if a.command == 'ping':
            print(c.ping())
            return 0
        if a.command in ('run', 'eval'):
            text = sys.stdin.read() if a.args == ['-'] else ' '.join(a.args)
            ok, out = (c.run if a.command == 'run' else c.eval)(text, in_server=a.server)
        elif a.command == 'snap':
            ok, out = c.snap(a.args[0] if a.args else None)
        else:
            ok, out = c.reload(a.args[0] if a.args else None)
        print(out)
        return 0 if ok else 1
    except NotRunning as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
