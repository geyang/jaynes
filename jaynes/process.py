"""Lightweight wrapper around subprocess.Popen for jaynes remote processes.

Provides timeout-aware waiting, graceful termination, log file lifecycle
management, and context manager support.
"""

import time


class JaynesProcess:
    """Wraps a subprocess.Popen returned by jaynes's SSH launcher.

    Delegates attribute access to the underlying Popen so existing code
    (``pipe.poll()``, ``pipe.returncode``, etc.) continues to work.

    Parameters
    ----------
    proc : subprocess.Popen
        The underlying SSH subprocess.
    log_files : list[file], optional
        Open file handles (stdout/stderr logs) to close on cleanup.

    Example
    -------

    .. code:: python

        p = jaynes.run(my_fn, arg1, arg2)

        # poll like before
        if p.poll() is None:
            print("still running")

        # wait with timeout — auto-kills on expiry
        p.wait(timeout=3600)

        # or use as context manager
        with jaynes.run(my_fn, arg1) as p:
            ...  # auto-cleanup on exit
    """

    def __init__(self, proc, log_files=None):
        self._proc = proc
        self._log_files = log_files or []
        self._cleaned_up = False

    # ── Delegate to underlying Popen ──────────────────────────────────

    def __getattr__(self, name):
        return getattr(self._proc, name)

    # ── Core API ──────────────────────────────────────────────────────

    def poll(self):
        """Check if the process has terminated. Returns exit code or None."""
        return self._proc.poll()

    @property
    def returncode(self):
        return self._proc.returncode

    def wait(self, timeout=None):
        """Wait for the process to finish.

        If *timeout* is given (seconds) and the process exceeds it,
        the process is terminated gracefully via :meth:`cancel`.

        Returns the exit code.
        """
        if timeout is None:
            self._proc.wait()
            return self._proc.returncode

        start = time.time()
        while time.time() - start < timeout:
            if self._proc.poll() is not None:
                return self._proc.returncode
            time.sleep(1.0)

        # timed out — cancel
        self.cancel()
        return self._proc.returncode

    def cancel(self, grace_period=30):
        """Terminate the process gracefully, then force-kill if needed.

        Sends SIGTERM, waits up to *grace_period* seconds, then SIGKILL.
        Closes any associated log files.
        """
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=grace_period)
            except Exception:
                self._proc.kill()
                self._proc.wait()
        self.cleanup()

    def cleanup(self):
        """Close log files. Safe to call multiple times."""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        for f in self._log_files:
            try:
                if not f.closed:
                    f.close()
            except Exception:
                pass

    # ── Context manager ───────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cancel()
        return False
