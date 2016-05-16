from __future__ import division, absolute_import, print_function

import sys
import threading

from numpy.distutils import subprocess_compat as subprocess

# Test subprocess under threaded use

NTHREADS = 10


def test_threaded():
    if sys.platform == "win32":
        cmd = "echo hello & echo does not compute 1>&2"
    else:
        cmd = "echo hello && { echo does not compute >&2; }"

    def run_repeat(count=50):
        for i in range(count):
            cpr = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            assert cpr.stdout.rstrip(" \n") == "hello", cpr.stdout
            assert cpr.stderr.rstrip(" \n") == "does not compute", cpr.stderr

    threads = [threading.Thread(target=run_repeat)
               for i in range(NTHREADS)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    def run_repeat(count=50):
        for i in range(count):
            cpr = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            assert cpr.stdout.rstrip(" \n") == "hello", cpr.stdout
            assert cpr.stderr is None, cpr.stderr

    threads = [threading.Thread(target=run_repeat)
               for i in range(NTHREADS)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    def run_repeat(count=50):
        for i in range(count):
            cpr = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            assert cpr.stderr is None, cpr.stderr
            lines = [line.rstrip(" \n") for line in cpr.stdout.splitlines()]
            assert lines == ["hello", "does not compute"]


    threads = [threading.Thread(target=run_repeat)
               for i in range(NTHREADS)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    test_threaded()
