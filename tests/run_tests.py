#!/usr/bin/env python3
"""LIB_MCP's checks that run without LiveCode (A-50: one test that runs): the script linter and
the WSL -> Windows path helper. The server routes need a running LiveCode and are not tested here.

    python3 -I tests/run_tests.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'python'))
from lib_mcp import lint                      # noqa: E402
from lib_mcp.client import local_to_win       # noqa: E402

CHECKS, FAILS = [0], []


def check(name, ok, got=None):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(name)
        print("FAIL  %s%s" % (name, "" if got is None else "  (got %r)" % (got,)))
    else:
        print("ok    %s" % name)


def done():
    print("\n%d of %d passed" % (CHECKS[0] - len(FAILS), CHECKS[0]))
    return 1 if FAILS else 0


def kinds(text):
    return [k for _, _, k, _ in lint.lint_text(text)]


def main():
    check('a clean handler has no problems', kinds('on mouseUp\n  put 1 into x\nend mouseUp\n') == [])
    check('empty-put: a put with no into', 'empty-put' in kinds('on mouseUp\n  put x\nend mouseUp\n'))
    check('a put into a variable is not empty-put', 'empty-put' not in kinds('on m\n  put "into" into x\nend m\n'))
    check('if-else: else after a one-line if', 'if-else' in kinds('on m\n  if x then put 1 into y\n  else\n    put 2 into y\n  end if\nend m\n'))
    check('step-repeat', 'step-repeat' in kinds('on m\n  repeat with i = 1 to 8 step 4\n  end repeat\nend m\n'))
    check('keyword-name: tText reads as text', 'keyword-name' in kinds('on m\n  put 1 into tExt\nend m\n'))
    check('-- lint-ok silences a line', kinds('on m\n  put x -- lint-ok\nend m\n') == [])
    check('/mnt/c path to C:', local_to_win('/mnt/c/LIB_MCP/x.txt') == 'C:/LIB_MCP/x.txt', local_to_win('/mnt/c/LIB_MCP/x.txt'))
    # headless compile (the LiveCode server in WSL, no window), when the server is installed
    from lib_mcp import compile_headless as ch
    import tempfile
    if os.path.exists(ch.SERVER):
        with tempfile.TemporaryDirectory() as d:
            good, bad = os.path.join(d, 'good.livecodescript'), os.path.join(d, 'bad.livecodescript')
            open(good, 'w').write('script "good"\non mouseUp\n   put 1 into x\nend mouseUp\n')
            open(bad, 'w').write('on mouseUp\n   put 1 into x\n   put 2 intoo y\nend mouseUp\n')
            res = dict(ch.check([good, bad]))
            check('headless compile: a good script compiles (the "script" header line skipped)', res[good] is None, res[good])
            check('headless compile: an error is found on its line', res[bad] and res[bad][0] == 3, res[bad])
    else:
        print('skip  headless compile (no LiveCode server in LIB_BIN)')
    return done()


if __name__ == '__main__':
    sys.exit(main())
