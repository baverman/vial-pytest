from vial import register_command


def init():
    register_command('VialPytestRun', '.plugin.run', nargs='*')
