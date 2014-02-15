import sys
import os

try:
    import pytest
except ImportError:
    fname = os.__file__
    if fname.endswith('.pyc'):
        fname = fname[:-1]

    if not os.path.islink(fname):
        raise

    real_prefix = os.path.dirname(os.path.realpath(fname))
    site_packages = os.path.join(real_prefix, 'site-packages')
    old_path = sys.path
    sys.path = old_path + [site_packages]
    try:
        import pytest
    finally:
        sys.path = old_path


class Collector(object):
    def __init__(self, send):
        self.send = send

    def extract_output(self, report):
        if report.longrepr:
            trace = str(report.longrepr)
        else:
            trace = None

        return trace, report.sections

    def pytest_runtest_logreport(self, report):
        if report.when != 'call':
            return

        if report.passed:
            self.send(('PASS', report.nodeid, self.extract_output(report)))
        elif report.failed:
            if report.when != "call":
                self.send(('ERROR', report.nodeid, self.extract_output(report)))
            else:
                self.send(('FAIL', report.nodeid, self.extract_output(report)))
        elif report.skipped:
            self.send(('SKIP', report.nodeid, self.extract_output(report)))

    def pytest_runtest_call(self, item):
        self.send(('ITEM_CALL', item.nodeid))

    def pytest_collectreport(self, report):
        if report.failed:
            self.send(('FAILED_COLLECT', report.nodeid,
                self.extract_output(report)))

    def pytest_internalerror(self, excrepr):
        self.send(('INTERNAL_ERROR', excrepr))

    def pytest_sessionstart(self, session):
        self.send(('START', str(session.fspath)))

    def pytest_sessionfinish(self, session, exitstatus):
        self.send(('END', ))

    def pytest_collection_finish(self, session):
        self.send(('COLLECTED_TESTS', [t.nodeid for t in session.items]))


#class Collector(object):
#    def __init__(self, *args, **kwargs):
#        self.f = open('/tmp/result.txt', 'w')
#
#    def __getattr__(self, name):
#        if not name.startswith('pytest_'):
#            raise AttributeError(name)
#
#        from _pytest import hookspec
#        import inspect
#
#        space = {'f':self.f}
#        exec 'def {0}{1}:\n    print >>f, "{0}{1}", locals()'.format(
#            name, inspect.formatargspec(*inspect.getargspec(getattr(hookspec, name)))) in space
#
#        return space[name]


if __name__ == '__main__':
    from multiprocessing.connection import Listener
    listener = Listener(sys.argv[1])
    conn = listener.accept()

    if sys.version_info[0] == 3:
        from pickle import dumps
        def sender(data):
            return conn.send_bytes(dumps(data, 2))
    else:
        sender = conn.send

    pytest.main(sys.argv[2:], plugins=[Collector(sender)])
