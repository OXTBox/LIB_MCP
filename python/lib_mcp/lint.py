"""lib_mcp.lint - find LiveCode script habits that compile but cause bugs. No LiveCode needed.

    lcmcp lint FILE...

Checks (each one cost real debugging time):
  empty-put     put with no into/after/before: it replaces the message box. Stray debug
                puts are easy to leave behind. (The owner's emptyPuts, made aware of
                strings and comments.)
  if-else       a one-line "if ... then x" directly followed by an "else" line: that else
                belongs to the one-line if, not the block around it.
  step-repeat   "repeat with ... step": LiveCode 9.6.3 runs one extra pass past the end
                unless the steps land on it exactly (1 to 8 step 4 gives 1, 5, 9).
  keyword-name  a t/p/s/g/b-prefixed name that spells a keyword (tExt = text, tHere = there).
Lines may end with  -- lint-ok  to silence a deliberate case.
"""
import re, sys

KEYWORDS = set('''there text time title set size put top tab end the then this char item line word into
from with field files folder target result value length number of on to in is do it as or and not div
mod ext ime ab op ull'''.split())
NAME = re.compile(r'\b([tpsgb])([A-Z][A-Za-z0-9]*)\b')


def strip_line(line):
    """remove string contents and comments; keep the code's shape"""
    out, in_str, i = [], False, 0
    while i < len(line):
        ch = line[i]
        if in_str:
            if ch == '"':
                in_str = False
                out.append('"')
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append('"')
        elif line.startswith('--', i) or line.startswith('//', i) or ch == '#':
            break
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


def lint_text(text, name='<script>'):
    problems = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    in_block_comment = False
    prev_one_line_if = None
    pending, pending_no, pending_first, pending_ok = '', 0, '', False
    for no, raw in enumerate(lines, 1):
        # a statement continued with "\" is checked as one line, numbered where it starts
        code_part = strip_line(raw).rstrip()
        if code_part.endswith('\\'):
            if not pending:
                pending_no, pending_first, pending_ok = no, raw.strip(), False
            pending_ok = pending_ok or 'lint-ok' in raw
            pending += code_part[:-1] + ' '
            continue
        first, ok_here = raw.strip(), 'lint-ok' in raw
        if pending:
            raw, no, first, ok_here = pending + raw, pending_no, pending_first, ok_here or pending_ok
            pending = ''
        if ok_here:
            prev_one_line_if = None
            continue
        line = raw
        if in_block_comment:
            if '*/' in line:
                line = line.split('*/', 1)[1]
                in_block_comment = False
            else:
                continue
        if '/*' in line and '*/' not in line.split('/*', 1)[1]:
            line = line.split('/*', 1)[0]
            in_block_comment = True
        code = strip_line(line).strip()
        if not code:
            continue
        low = code.lower()
        # if-else
        if prev_one_line_if and re.match(r'else\b', low):
            problems.append((no, 'if-else', 'this else belongs to the one-line if on line %d' % prev_one_line_if))
        prev_one_line_if = no if re.match(r'(else\s+)?if\b.*\bthen\s+\S', low) and not low.endswith('then') else None
        # empty-put: every statement in the line (one-line if/else hold more than one)
        for st in re.split(r'\b(?:then|else)\b', low):
            st = st.strip()
            if re.match(r'put\b', st) and not re.search(r'\b(into|after|before)\b', st):
                problems.append((no, 'empty-put', first + (' ...' if first != raw.strip() else '')))
        # step-repeat
        if re.match(r'repeat\s+with\b', low) and re.search(r'\bstep\b', low):
            problems.append((no, 'step-repeat', 'runs one extra pass past the end unless the steps land on it; '
                                                'consider repeat while'))
        # keyword-name
        for m in NAME.finditer(strip_line(line)):
            if (m.group(1) + m.group(2)).lower() in KEYWORDS or m.group(2).lower() in ('ext', 'here', 'ime', 'itle'):
                if (m.group(1) + m.group(2)).lower() in KEYWORDS:
                    problems.append((no, 'keyword-name', '%s reads as the keyword "%s"'
                                     % (m.group(0), (m.group(1) + m.group(2)).lower())))
    return [(name, no, kind, msg) for no, kind, msg in problems]


def main(paths):
    found = 0
    for p in paths:
        for name, no, kind, msg in lint_text(open(p, encoding='utf-8', errors='replace').read(), p):
            print('%s:%d: %s: %s' % (name, no, kind, msg))
            found += 1
    if not found:
        print('no problems found')
    return 1 if found else 0


if __name__ == '__main__':
    if any(a in ('-h', '--help') for a in sys.argv[1:]):   # A-50: every tool answers --help
        print(__doc__)
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
