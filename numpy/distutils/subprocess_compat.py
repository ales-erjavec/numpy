"""
Thread safer backcompatibility layer for `subprocess`

"""
from __future__ import absolute_import, print_function

import os
import sys
import threading
import atexit
import subprocess

if sys.version_info < (3, ):
    try:
        # Use backported subprocess32 module if available; it's safer
        import subprocess32 as subprocess
    except ImportError:
        pass


class Popen(subprocess.Popen):
    """
    Thread safe**r** (friendlier) :class`subprocess.Popen`

    Note that this is only safer and not completely thread safe.
    Child processes created on other threads that do not use
    this class (instead use os.spawn*, os.popen, os.fork), ... can
    still cause open fd's to leak (https://bugs.python.org/issue12739
    http://bugs.python.org/issue10394, ...)

    See Also
    --------
    subprocess.Popen

    """
    _Popen_lock = threading.Lock()

    def __init__(self, args, *extargs, **kwargs):
        def _get_devnull():
            # Return an (process global) open os.devnull file object (rw).
            # The object will remain open until a registered atexit function
            # closes it.
            try:
                return Popen._Popen_devnull
            except AttributeError:
                with Popen._Popen_lock:
                    # handle a race condition
                    if hasattr(Popen, "_Popen_devnull"):
                        return Popen._Popen_devnull
                    Popen._Popen_devnull = open(os.devnull, "r+")
                    atexit.register(lambda: Popen._Popen_devnull.close())
                return Popen._Popen_devnull

        if sys.version_info < (3, 3):
            if kwargs.get("stdin", None) == DEVNULL:
                kwargs["stdin"] = _get_devnull()
            if kwargs.get("stdout", None) == DEVNULL:
                kwargs["stdout"] = _get_devnull()
            if kwargs.get("stderr", None) == DEVNULL:
                kwargs["stderr"] = _get_devnull()

        with Popen._Popen_lock:
            super(Popen, self).__init__(args, *extargs, **kwargs)

        if not hasattr(self, "args"):
            # Popen.args attribute was added in Python 3.3
            self.args = args


# Pull constants/functions, ... from subprocess
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
if sys.version_info >= (3, 3):
    DEVNULL = subprocess.DEVNULL  # new in Python 3.3;
else:
    DEVNULL = -3

CalledProcessError = subprocess.CalledProcessError

if sys.version_info < (3, 5):
    # Gained a stderr argument in 3.5
    class CalledProcessError(CalledProcessError):
        def __init__(self, returncode, cmd, output=None, stderr=None):
            super(CalledProcessError, self).__init__(returncode, cmd, output)
            self.stderr = stderr

        @property
        def stdout(self):
            return self.output

        @stdout.setter
        def stdout(self, value):
            self.output = value


if hasattr(subprocess, "CompletedProcess"):
    # Added to stdlib in Python 3.5
    CompletedProcess = subprocess.CompletedProcess
else:
    class CompletedProcess(object):
        def __init__(self, args, returncode, stdout=None, stderr=None):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

        def __repr__(self):
            fmt = "{}={!r}".format
            parts = [fmt("args", self.args),
                     fmt("returncode", self.returncode)]
            if self.stdout is not None:
                parts.append(fmt("stdout", self.stdout))
            if self.stderr is not None:
                parts.append(fmt("stderr", self.stderr))
            return "{}({})".format(type(self).__name__, ", ".join(parts))

        def check_returncode(self):
            if self.returncode:
                raise CalledProcessError(
                    self.returncode, self.args, self.stdout, self.stderr)

list2cmdline = subprocess.list2cmdline


# Reimplement/expose usefull utilities from stdlib subprocess but with a
# lock acquiring Popen constructor.
def run(*popenargs, **kwargs):
    """
    Run command with arguments and return a CompletedProcess instance.

    The arguments are passed to :class:`subprocess.Popen` constructor.

    Compatibility shim over stdlib subprocess, to expose a similar api as
    Python 3.5.

    Returns
    -------
    info : CompletedProcess
        An CompletedProcess with `args`, `returncode`, `stdout` and `stderr`
        fields (stdout an stderr are only present when requested with
        `stout=PIPE`, or `stderr=PIPE`).

    See Also
    --------
    subprocess.Popen, subprocess.run

    Note
    ----
    This function uses a lock around the stdlib's `subprocess.Popen`
    constructor for increased thread friendliness.
    """
    input = kwargs.pop("input", None)
    check = kwargs.pop("check", False)

    if "timeout" in kwargs:
        # Timeout was added in Python 3.3, and is not supported here
        raise TypeError("'timeout' is not supported")

    process = Popen(*popenargs, **kwargs)
    try:
        stdout, stderr = process.communicate(input=input)
    except:
        process.kill()
        raise
    finally:
        process.wait()

    retcode = process.poll()
    cproc = CompletedProcess(process.args, retcode, stdout, stderr)
    if check:
        cproc.check_returncode()
    return cproc


def check_output(*popenargs, **kwargs):
    """
    Run command with arguments and return its output.

    The arguments are passed to :class:`subprocess.Popen` constructor.

    Returns
    -------
    output: str
        Command's output text

    See Also
    --------
    subprocess.Popen, subprocess.check_output

    Note
    ----
    This function uses a lock around the stdlib's `subprocess.Popen`
    constructor for increased thread friendliness.
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    cproc = run(*popenargs, stdout=subprocess.PIPE, check=True, **kwargs)
    return cproc.stdout


def check_call(*popenargs, **kwargs):
    """
    Run command with arguments and wait for completion.

    The arguments are passed to :class:`subprocess.Popen` constructor.

    If the exit status is not 0 then raise a CalledProcessError with the
    appropriate exit status.

    Returns
    -------
    status: int
        Command's exit status

    See Also
    --------
    subprocess.Popen, subprocess.check_call

    Note
    ----
    This function uses a lock around the stdlib's `subprocess.Popen`
    constructor for increased thread friendliness.
    """
    state = run(*popenargs, stderr=None, stdout=None, **kwargs)
    state.check_returncode()
    return state.returncode
