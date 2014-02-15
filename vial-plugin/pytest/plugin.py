import sys
import os.path
import time

from vial import vfunc, vim
from vial.utils import get_buf_by_name, redraw, get_winbuf


collector = None
def get_collector():
    global collector
    if not collector:
        collector = ResultCollector()

    return collector


def run_test(project_dir, executable=None, match=None, files=[], env=None):
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

    args.extend(files)
    proc = Popen(args, cwd=project_dir, env=environ, stdout=log, stderr=log, close_fds=True)
    start = time.time()
    while not os.path.exists(addr):
        if time.time() - start > 5:
            raise Exception('py.test launching timeout exceed')
        time.sleep(0.01)

    conn = Client(addr)

    return proc, conn


class ResultCollector(object):
    def init_buf(self):
        win, self.buf = get_winbuf('__vial_pytest__')
        if not self.buf:
            vim.command('badd __vial_pytest__')
            self.buf = get_buf_by_name('__vial_pytest__')

        vfunc.setbufvar(self.buf.number, '&buflisted', 0)
        vfunc.setbufvar(self.buf.number, '&buftype', 'nofile')
        vfunc.setbufvar(self.buf.number, '&swapfile', 0)

        # if not win:
        #     vim.command('sbuffer {}'.format(self.buf.number))

        if len(self.buf) > 1:
            self.buf[0:] = ['']

    def add_test_result(self, rtype, name, result):
        lines = ['{} {}'.format(rtype, name)]

        trace, out = result
        if trace:
            lines.extend(trace.splitlines())

        for k, v in out:
            lines.append('----======= {} =======----'.format(k))
            lines.extend(v.splitlines())

        lines.append('')

        buflen = len(self.buf)
        self.buf[buflen-1:] = lines
        redraw()

    def collect(self, conn):
        self.tests = []
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
    if not args:
        file = vfunc.expand('%')
    else:
        file = args[0]

    proc, conn = run_test(project, files=[file])

    # buf.options['number']    = 0
    # buf.options['colorcolumn'] = ''
    # buf.options['stl']         = 'pytest'

    get_collector().collect(conn)
