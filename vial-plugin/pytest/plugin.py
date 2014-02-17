import sys
import time
import os.path

from collections import Counter

from vial import vfunc, vim
from vial.utils import get_buf_by_name, redraw, get_winbuf, focus_window


collector = None
def get_collector():
    global collector
    if not collector:
        collector = ResultCollector()

    return collector


def run_test(project_dir, executable=None, match=None, files=None, env=None):
    from subprocess import Popen
    from multiprocessing.connection import Client, arbitrary_address

    addr = arbitrary_address('AF_UNIX')
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pt.py')

    executable = executable or sys.executable
    args = [executable, filename, addr, '-q']
    if match:
        args.append('-k %s' % match)

    environ = None
    if env:
        environ = os.environ.copy()
        environ.update(env)

    log = open('/tmp/vial-pytest.log', 'w')

    if files:
        args.extend(files)

    proc = Popen(args, cwd=project_dir, env=environ, stdout=log, stderr=log, close_fds=True)
    start = time.time()
    while not os.path.exists(addr):
        if time.time() - start > 5:
            raise Exception('py.test launching timeout exceed')
        time.sleep(0.01)

    conn = Client(addr)

    return proc, conn


def indent(width, lines):
    return ['    ' * width + r for r in lines]


class ResultCollector(object):
    def init_buf(self):
        win, self.buf = get_winbuf('__vial_pytest__')
        if not self.buf:
            vim.command('silent badd __vial_pytest__')
            self.buf = get_buf_by_name('__vial_pytest__')

        vfunc.setbufvar(self.buf.number, '&buflisted', 0)
        vfunc.setbufvar(self.buf.number, '&buftype', 'nofile')
        vfunc.setbufvar(self.buf.number, '&swapfile', 0)

        if not win:
            vim.command('silent botright sbuffer {}'.format(self.buf.number))
            vim.command('setlocal stl=pytest nonumber colorcolumn= foldmethod=manual')
        else:
            focus_window(win)

        if len(self.buf) > 1:
            self.buf[0:] = ['']

    def add_test_result(self, rtype, name, result):
        self.counts[rtype] += 1
        lines = ['{} {}'.format(rtype, name)]

        trace, out = result
        if trace:
            lines.extend(indent(1, trace.splitlines()))
            lines.append('')

        for k, v in out:
            lines.append('    ----======= {} =======----'.format(k))
            lines.extend(indent(1, v.splitlines()))

        lines.append('')
        lines.append('')

        buflen = len(self.buf)
        self.buf[buflen-1:] = lines
        vim.command('norm! {}Gzf{}j'.format(buflen, len(lines) - 2))
        redraw()

    def collect(self, conn):
        self.tests = []
        self.counts = Counter()

        self.init_buf()

        while True:
            msg = conn.recv()
            cmd = msg[0]
            if cmd == 'END':
                return
            elif cmd == 'COLLECTED_TESTS':
                self.tests[:] = cmd[1]
            elif cmd in ('PASS', 'ERROR', 'FAIL', 'SKIP'):
                self.add_test_result(*msg)


def run(*args):
    project = os.getcwd()
    files = None
    if args:
        files = [vfunc.expand(r) for r in args]

    proc, conn = run_test(project, files=files)
    get_collector().collect(conn)
