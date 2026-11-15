"""lib_mcp.mcp_server - MCP tool server (stdio) for LiveCode, for LM Studio, Claude Desktop
or any MCP client. Standard library only.

    python3 .../LIB_MCP/python/lib_mcp/mcp_server.py [--tools PACK.py ...] [--selftest]

Built-in tools (any LiveCode stack): livecode_primer, livecode_status, livecode_run,
livecode_eval, livecode_compile, livecode_errors, livecode_snapshot.

Tool packs add library-specific tools. A pack is a Python file defining
    TOOLS = [(name, function(args) -> str or MCP content list, description, json_schema), ...]
It may import lib_mcp.client. Example: xt3d's mcp/xt3d_tools.py.

LM Studio (C:\\Users\\<you>\\.cache\\lm-studio\\mcp.json):
  {"mcpServers": {"livecode": {"command": "wsl.exe", "args": ["-d", "Ubuntu", "-e", "python3",
     "/home/<you>/projects/LIB_MCP/python/lib_mcp/mcp_server.py",
     "--tools", "/home/<you>/projects/xt3D_Raylib_Livecode_Bridge/mcp/xt3d_tools.py"]}}}

livecode_run runs real code in LiveCode: leave the client's "ask before each tool call" on.
"""
import base64, importlib.util, json, os, sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_mcp.client import Client, NotRunning, recent_errors, win_to_local, IDE_PORT

PRIMER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'livecode_primer.md')
SNAP = 'C:/LIB_MCP/snap.png'


def ide():
    return Client(IDE_PORT)


def schema(props=None, required=None):
    return {'type': 'object', 'properties': props or {}, 'required': required or []}


S = {'type': 'string'}


def t_primer(_):
    return open(PRIMER, encoding='utf-8').read()


def t_status(_):
    lines = []
    for name, c in (('IDE', ide()), ('standalone', Client.standalone(start=False))):
        try:
            lines.append('%s: %s' % (name, c.ping()))
        except NotRunning:
            lines.append('%s: not running' % name)
    return '\n'.join(lines)


def t_run(a):
    return ide().run(a['code'])[1] or '(done, nothing returned)'


def t_eval(a):
    return ide().eval(a['expression'])[1]


def t_compile(a):
    try:
        c = Client.standalone()
    except NotRunning:
        c = ide()
    return c.compile(a['script'])[1]


def t_errors(a):
    return recent_errors(int(a.get('count') or 5))


def t_snap(_):
    ok, text = ide().snap(SNAP)
    if not ok:
        return text
    data = open(win_to_local(SNAP), 'rb').read()
    return [{'type': 'text', 'text': 'Snapshot of the target stack (%d bytes PNG).' % len(data)},
            {'type': 'image', 'data': base64.b64encode(data).decode('ascii'), 'mimeType': 'image/png'}]


TOOLS = [
    ('livecode_primer', t_primer, 'Read this first if you will write LiveCode Script: a short guide to its syntax '
     '(it is NOT JavaScript or Python) with common mistakes.', schema()),
    ('livecode_status', t_status, 'Is LiveCode running with LIB_MCP (IDE and standalone)?', schema()),
    ('livecode_run', t_run, 'Run LiveCode Script statements in the running IDE and return what they put into the '
     'message box and the result. Use "put x" (no "into") to return a value. Errors come back translated.',
     schema({'code': dict(S, description='LiveCode Script statements, one per line')}, ['code'])),
    ('livecode_eval', t_eval, 'Evaluate one LiveCode expression in the running IDE and return its value.',
     schema({'expression': dict(S, description='a LiveCode expression')}, ['expression'])),
    ('livecode_compile', t_compile, 'Compile-check LiveCode Script without running it. Returns COMPILES OK or '
     'the compile errors with line numbers. Use it on every handler you write before giving it to the user.',
     schema({'script': dict(S, description='one or more complete handlers')}, ['script'])),
    ('livecode_errors', t_errors, 'Read the most recent LiveCode script errors (translated) from the error log.',
     schema({'count': {'type': 'integer', 'description': 'how many recent errors (default 5)'}})),
    ('livecode_snapshot', t_snap, 'PNG picture of the target stack window (for models that can see images).', schema()),
]


def load_pack(path):
    spec = importlib.util.spec_from_file_location('pack_' + os.path.splitext(os.path.basename(path))[0], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(getattr(mod, 'TOOLS', []))


def all_tools(pack_paths):
    tools = list(TOOLS)
    for p in pack_paths:
        tools += load_pack(p)
    return tools


def call_tool(tools, name, args):
    by = {t[0]: t for t in tools}
    if name not in by:
        return [{'type': 'text', 'text': 'Unknown tool ' + str(name)}], True
    try:
        out = by[name][1](args or {})
        return (out if isinstance(out, list) else [{'type': 'text', 'text': str(out)}]), False
    except NotRunning as e:
        return [{'type': 'text', 'text': str(e)}], True
    except (KeyError, ValueError, OSError) as e:
        return [{'type': 'text', 'text': 'Tool failed: %s' % e}], True


def reply(id_, result=None, error=None):
    msg = {'jsonrpc': '2.0', 'id': id_}
    msg['error' if error is not None else 'result'] = error if error is not None else result
    sys.stdout.write(json.dumps(msg) + '\n')
    sys.stdout.flush()


def serve(tools):
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, id_ = msg.get('method'), msg.get('id')
        if method == 'initialize':
            reply(id_, {'protocolVersion': (msg.get('params') or {}).get('protocolVersion') or '2024-11-05',
                        'capabilities': {'tools': {}}, 'serverInfo': {'name': 'lib_mcp', 'version': '0.1.0'},
                        'instructions': 'Tools for LiveCode 9.6.3. Call livecode_primer before writing LiveCode '
                                        'Script, and livecode_compile on what you write.'})
        elif method == 'tools/list':
            reply(id_, {'tools': [{'name': n, 'description': d, 'inputSchema': s} for n, _, d, s in tools]})
        elif method == 'tools/call':
            p = msg.get('params') or {}
            content, err = call_tool(tools, p.get('name'), p.get('arguments'))
            reply(id_, {'content': content, 'isError': err})
        elif method == 'ping':
            reply(id_, {})
        elif id_ is not None:
            reply(id_, error={'code': -32601, 'message': 'method not found: %s' % method})


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    packs = [argv[i + 1] for i, x in enumerate(argv) if x == '--tools' and i + 1 < len(argv)]
    tools = all_tools(packs)
    if '--selftest' in argv:
        print('tools:', ', '.join(t[0] for t in tools))
        for name, args in [('livecode_status', {}), ('livecode_errors', {'count': 1}),
                           ('livecode_compile', {'script': 'on t\n   put word 1 of char 1 to 3 of "abc"\nend t'})]:
            content, err = call_tool(tools, name, args)
            print('== %s%s\n%s' % (name, ' (error)' if err else '', content[0]['text'][:500]))
        return
    serve(tools)


if __name__ == '__main__':
    if any(a in ('-h', '--help') for a in sys.argv[1:]):   # A-50: every tool answers --help
        print(__doc__)
        sys.exit(0)
    main()
