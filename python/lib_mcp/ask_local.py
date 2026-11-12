#!/usr/bin/env python3
"""ask_local.py - ask a local LM Studio model a question, letting it use the LIB_MCP tools
(plus any tool packs, e.g. xt3d's).

    python3 -m lib_mcp.ask_local "Which xt3d command draws a sphere?" --tools .../xt3d/mcp/xt3d_tools.py
    python3 -m lib_mcp.ask_local --model qwen2.5-7b-instruct-1m --no-tools "..."

Runs the tool loop itself (the same tools as lib_mcp.mcp_server), so it works through
LM Studio's plain chat API without the LM Studio app's MCP support. Prints each tool
call, then the answer. LM Studio is reached through Windows' curl.exe.
"""
import argparse, json, os, subprocess, sys
if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_mcp import mcp_server

URL = 'http://127.0.0.1:1234/v1/chat/completions'
SYSTEM = ('You help with LiveCode 9.6.3 projects. You can call tools to read a LiveCode primer, look up '
          'library handlers, compile-check code and run code in the user\'s LiveCode. '
          'Read livecode_primer before writing any LiveCode Script; LiveCode is not JavaScript or Python. '
          'Look up exact handler names with the lookup tools instead of guessing, and compile-check '
          'what you write with livecode_compile. Answer briefly.')


def chat(model, messages, tools, effort):
    body = {'model': model, 'messages': messages, 'temperature': 0.2, 'max_tokens': 2048}   # thinking included; caps runaways
    if effort:
        body['reasoning_effort'] = effort
    if tools:
        body['tools'] = tools
    r = subprocess.run(['curl.exe', '-sS', '-m', '600', URL, '-H', 'Content-Type: application/json',
                        '--data-binary', '@-'], input=json.dumps(body).encode('utf-8'), capture_output=True)
    if r.returncode != 0:
        sys.exit('LM Studio not answering at %s: %s' % (URL, r.stderr.decode(errors='replace')))
    d = json.loads(r.stdout.decode('utf-8', 'replace'))
    if 'choices' not in d:
        sys.exit('LM Studio error: %s' % d)
    return d['choices'][0]['message']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--model', default='spark-x2.6-4b')
    ap.add_argument('--effort', default='low', help='reasoning effort: low/medium/high, or "" to omit')
    ap.add_argument('--no-tools', action='store_true')
    ap.add_argument('--max-steps', type=int, default=8)
    ap.add_argument('--tools', action='append', default=[], help='tool pack .py file (repeatable)')
    a = ap.parse_args()
    registry = mcp_server.all_tools(a.tools)
    tools = None if a.no_tools else [
        {'type': 'function', 'function': {'name': n, 'description': d, 'parameters': s}}
        for n, _, d, s in registry if 'snapshot' not in n]   # text-only models
    messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': a.question}]
    for _ in range(a.max_steps):
        m = chat(a.model, messages, tools, a.effort)
        calls = m.get('tool_calls') or []
        if not calls:
            print(m.get('content') or '(no answer)')
            return
        messages.append({'role': 'assistant', 'content': m.get('content') or '', 'tool_calls': calls})
        for c in calls:
            name = c['function']['name']
            try:
                args = json.loads(c['function'].get('arguments') or '{}')
            except ValueError:
                args = {}
            content, err = mcp_server.call_tool(registry, name, args)
            text = '\n'.join(x.get('text', '') for x in content)
            print('[tool] %s %s -> %s' % (name, json.dumps(args), text[:160].replace('\n', ' | ')), file=sys.stderr)
            messages.append({'role': 'tool', 'tool_call_id': c.get('id', ''), 'content': text})
    print('(stopped after %d steps)' % a.max_steps)


if __name__ == '__main__':
    main()
