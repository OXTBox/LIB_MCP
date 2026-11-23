"""lib_mcp.client - talk to a LIB_MCP dev server running inside LiveCode.

The server listens on Windows' 127.0.0.1. From WSL2 that address is not reachable
directly, so requests go through Windows' own curl.exe (also fine on native Windows).
Standard library only.

    from lib_mcp.client import Client
    ide = Client(8766)                       # the IDE
    sa = Client.standalone()                 # the standalone, started if needed
    print(sa.compile(open('x.livecodescript').read()))
"""
import glob, os, shutil, subprocess, time

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.dirname(os.path.dirname(PACKAGE_DIR))          # .../LIB_MCP
IDE_PORT, STANDALONE_PORT = 8766, 8767
# ABSOLUTE RULES for standalone copies (owner, 21 Nov): at most MAX_COPIES at a time; slot N listens on
# STANDALONE_PORT + N and nowhere else; its exe is xt3d_MCP.exe (slot 0) or xt3d_MCP_<N>.exe. The launcher
# enforces the same table itself, so a wrong name or port never gets to listen.
MAX_COPIES = 2


def _runtime_dir():
    """C:/LIB_MCP as seen from here (WSL: /mnt/c/LIB_MCP)"""
    return '/mnt/c/LIB_MCP' if os.path.isdir('/mnt/c') else 'C:/LIB_MCP'


RUNTIME = _runtime_dir()
ERROR_LOG = os.path.join(RUNTIME, 'livecode_errors.txt')


def win_to_local(path):
    """C:/x or C:\\x -> /mnt/c/x when running in WSL"""
    p = path.replace('\\', '/')
    if os.path.isdir('/mnt/c') and len(p) > 1 and p[1] == ':':
        return '/mnt/' + p[0].lower() + p[2:]
    return p


def local_to_win(path):
    if path.startswith('/mnt/') and len(path) > 6 and path[6] == '/':
        return path[5].upper() + ':' + path[6:]
    if path.startswith('/'):
        try:
            return subprocess.run(['wslpath', '-w', path], capture_output=True, text=True).stdout.strip()
        except OSError:
            pass
    return path


class NotRunning(Exception):
    pass


class Client:
    def __init__(self, port=IDE_PORT):
        self.port = port
        self.token_file = os.path.join(RUNTIME, 'devtoken_%d.txt' % port)

    # ---------------------------------------------------------------- connection
    def running(self):
        return os.path.isfile(self.token_file)

    def _token(self):
        try:
            lines = open(self.token_file).read().splitlines()
            return lines[0].strip(), int(lines[1].strip())
        except (OSError, IndexError, ValueError):
            raise NotRunning(self._not_running_text())

    def _not_running_text(self):
        if self.port == STANDALONE_PORT:
            return 'The LIB_MCP standalone is not running and could not be started.'
        return ('No LIB_MCP server on port %d. In LiveCode, start it from a stack '
                '(start using stack ".../LIB_MCP/livecode/lib_mcp.livecodescript" then DevServer.Start) '
                'or open the xt3d test bench, which does that.' % self.port)

    def request(self, method, route, body=None, timeout=60):
        """returns (ok, text); raises NotRunning"""
        token, port = self._token()
        cmd = ['curl.exe', '-sS', '-m', str(timeout), '-w', '\n%{http_code}', '-H', 'X-Token: ' + token]
        if method == 'POST':
            cmd += ['-X', 'POST', '-H', 'Expect:', '-H', 'Content-Type: text/plain; charset=utf-8', '--data-binary', '@-']
        cmd.append('http://127.0.0.1:%d%s' % (port, route))
        try:
            r = subprocess.run(cmd, input=(body or '').encode('utf-8'), capture_output=True, timeout=timeout + 5)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise NotRunning(self._not_running_text()) from e
        out = r.stdout.decode('utf-8', 'replace').replace('\r', '')
        if r.returncode != 0 or '\n' not in out:
            raise NotRunning(self._not_running_text())
        text, code = out.rsplit('\n', 1)
        return code.strip() == '200', text

    # ---------------------------------------------------------------- standalone
    @staticmethod
    def standalone_exe():
        hits = [h for h in [os.path.join(LIB_DIR, 'standalone', 'xt3d_MCP.exe')] if os.path.isfile(h)] or \
            sorted(glob.glob(os.path.join(LIB_DIR, 'standalone', '*', 'Windows x86-64', 'xt3d_MCP.exe')))
        return hits[0] if hits else None

    @staticmethod
    def slot_exe(slot):
        """the exe of copy `slot` (0 = the original, 1 = xt3d_MCP_1.exe, a byte copy made here)"""
        exe = Client.standalone_exe()
        if not exe or slot == 0:
            return exe
        copy = os.path.join(os.path.dirname(exe), 'xt3d_MCP_%d.exe' % slot)
        if not os.path.isfile(copy) or os.path.getmtime(copy) < os.path.getmtime(exe):
            shutil.copy2(exe, copy)
        return copy

    @staticmethod
    def running_copies():
        """image names of the standalone copies running now (Windows' tasklist)"""
        try:
            r = subprocess.run(['tasklist.exe'], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return [l.split()[0] for l in r.stdout.splitlines() if l.lower().startswith('xt3d_mcp')]

    @classmethod
    def standalone(cls, start=True, wait=30, slot=0):
        if slot is None:
            slot = int(os.environ.get('LIBMCP_SLOT', '0'))
        wait = int(os.environ.get('LIBMCP_WAIT', wait))   # a slow machine needs longer than 30 s to start a copy
        if not 0 <= slot < MAX_COPIES:
            raise NotRunning('Standalone slot %d refused: only slots 0..%d exist (at most %d copies).'
                             % (slot, MAX_COPIES - 1, MAX_COPIES))
        c = cls(STANDALONE_PORT + slot)
        if not start:
            return c
        if c.running():
            try:
                c.request('GET', '/ping', timeout=15)
                return c
            except NotRunning:
                # a token left behind by a standalone that was closed: start a fresh one
                try:
                    os.remove(c.token_file)
                except OSError:
                    pass
        exe = cls.slot_exe(slot)
        if not exe:
            raise NotRunning('No standalone build in %s/standalone' % LIB_DIR)
        name = os.path.basename(exe)
        # the rule: never more than MAX_COPIES running. Only this slot's own stale copy may be replaced.
        others = [n for n in (cls.running_copies() or []) if n.lower() != name.lower()]
        if len(others) >= MAX_COPIES:
            raise NotRunning('Refusing to start %s: %d standalone copies are already running (%s).'
                             % (name, len(others), ', '.join(others)))
        subprocess.run(['taskkill.exe', '/IM', name, '/F'], capture_output=True)
        time.sleep(1)
        # fire and forget: `start` does not return while the started copy holds the console, and captured
        # pipes would be inherited too. The token file (waited for below) says the copy is up.
        subprocess.Popen(['cmd.exe', '/c', 'start', '', local_to_win(exe)], cwd='/mnt/c' if os.path.isdir('/mnt/c') else None,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        end = time.time() + wait
        while time.time() < end:
            if c.running():
                return c
            time.sleep(0.5)
        raise NotRunning('Started %s but no token file appeared in %ds.' % (exe, wait))

    @classmethod
    def kill_slot(cls, slot):
        """end copy `slot` and drop its token (the only way a copy is ended from here)"""
        name = 'xt3d_MCP.exe' if slot == 0 else 'xt3d_MCP_%d.exe' % slot
        subprocess.run(['taskkill.exe', '/IM', name, '/F'], capture_output=True, timeout=60)
        try:
            os.remove(os.path.join(RUNTIME, 'devtoken_%d.txt' % (STANDALONE_PORT + slot)))
        except OSError:
            pass

    # ---------------------------------------------------------------- routes
    def ping(self):
        return self.request('GET', '/ping', timeout=10)[1]

    def run(self, code, in_server=False):
        return self.request('POST', '/run' + ('?in=server' if in_server else ''), code)

    def eval(self, expression, in_server=False):
        return self.request('POST', '/eval' + ('?in=server' if in_server else ''), expression)

    def compile(self, script_text):
        return self.request('POST', '/compile', script_text.replace('\r\n', '\n'))

    def reload(self, path=None):
        from urllib.parse import quote
        return self.request('POST', '/reload' + ('?path=' + quote(path, safe='') if path else ''), '')

    def snap(self, win_path=None):
        from urllib.parse import quote
        ok, text = self.request('GET', '/snap' + ('?file=' + quote(win_path, safe='') if win_path else ''))
        return ok, text


def recent_errors(count=5):
    try:
        text = open(ERROR_LOG, encoding='utf-8', errors='replace').read().replace('\r', '')
    except OSError:
        return 'No LiveCode errors logged yet.'
    entries = ['==== ' + e for e in text.split('==== ') if e.strip()]
    return ''.join(entries[-count:]) or 'No LiveCode errors logged yet.'
