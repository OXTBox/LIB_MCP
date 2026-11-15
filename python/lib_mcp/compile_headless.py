#!/usr/bin/env python3
"""compile_headless.py - compile-check LiveCode scripts with the LiveCode 9.6.3 SERVER in WSL:
no window, no IDE, nothing on the owner's screen (found 2026-11-15; until then a compile check
needed the IDE or the LIB_MCP standalone on Windows).

    python3 -I python/lib_mcp/compile_headless.py FILE...
    python3 -I python/lib_mcp/compile_headless.py --help

Each file is set as the script of an in-memory stack; the engine's answer is the compile result.
Prints COMPILES or ERRORS per file, and for errors the line number, the word and the line itself.
Exit code 1 if any file has errors. A first line "script ..." (a .livecodescript header) is
skipped, as the IDE does. The server is $LIB_BIN/livecode-server/9.6.3-linux-x64/
livecode-community-server (LIB_BIN defaults to ~/projects/LIB_BIN).
What it does NOT check: anything at run time (a handler that does not exist, a wrong object
name); for that the script has to run, in the IDE or headless with stubs.
"""
import os, subprocess, sys, tempfile

LIB_BIN = os.environ.get('LIB_BIN', os.path.expanduser('~/projects/LIB_BIN'))
SERVER = os.path.join(LIB_BIN, 'livecode-server', '9.6.3-linux-x64', 'livecode-community-server')

RUNNER = '''<?lc
lock messages
create stack "probe"
put url ("file:%s") into tList
repeat for each line tF in tList
  if tF is empty then next repeat
  put url ("binfile:" & tF) into tS
  replace numToChar(13) & numToChar(10) with numToChar(10) in tS
  replace numToChar(13) with numToChar(10) in tS
  if word 1 of line 1 of tS is "script" then
    put "--" & line 1 of tS into line 1 of tS
  end if
  set the script of stack "probe" to tS
  put the result into tR
  put "@@" & tF & "@@" & line 1 of tR & cr
end repeat
?>
'''


def check(paths):
    """[(path, None | (line, word))]"""
    if not os.path.exists(SERVER):
        raise FileNotFoundError('no LiveCode server at %s' % SERVER)
    with tempfile.TemporaryDirectory() as d:
        lst = os.path.join(d, 'list.txt')
        open(lst, 'w').write('\n'.join(os.path.abspath(p) for p in paths) + '\n')
        run = os.path.join(d, 'run.lc')
        open(run, 'w').write(RUNNER % lst)
        out = subprocess.run([SERVER, run], capture_output=True, text=True, timeout=300, cwd=d).stdout
    res = {}
    for line in out.split('\n'):
        if line.startswith('@@'):
            _, path, err = line.split('@@', 2)
            if err.strip():
                f = err.split(',')
                res[path] = (int(f[1]) if len(f) > 1 and f[1].isdigit() else 0, f[3] if len(f) > 3 else '')
            else:
                res[path] = None
    return [(p, res.get(os.path.abspath(p), (0, 'no answer from the server'))) for p in paths]


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    bad = 0
    for path, err in check(argv):
        if err is None:
            print('COMPILES  %s' % path)
            continue
        bad += 1
        no, wordx = err
        try:
            text = open(path, 'rb').read().decode('latin-1').replace('\r\n', '\n').replace('\r', '\n').split('\n')
            src = text[no - 1].strip() if 0 < no <= len(text) else ''
        except OSError:
            src = ''
        print('ERRORS    %s\n          line %d near "%s": %s' % (path, no, wordx, src[:100]))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
