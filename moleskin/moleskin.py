import os
import sys
import time
import traceback
from collections import defaultdict

from boltons.funcutils import wraps
from pprint import pprint
import subprocess
from termcolor import cprint as _cprint


class Moleskin:
    def __init__(self, *, debug=True, file=None):
        self.is_debug = debug
        self.log_file = None
        self.log_directory = None
        if file:
            directory, filename = os.path.split(file)
            try:
                os.makedirs(directory)
            except FileExistsError:
                pass
            self.log_file = file
            self.log_directory = os.path.realpath(directory)

        self.tics = defaultdict(lambda: None)

    config = __init__

    ## Timing Functions
    def timeit(self, fn):
        """A timing decorator, preserves function metadata."""

        @wraps(fn)
        def _time(*args, **kwargs):
            self.start(fn.__name__)
            results = fn(*args, **kwargs)
            self.split(fn.__name__)
            return results

        return _time

    def tic(self, key='default', silent=True):
        # todo: add named timers like start('name')
        tic = time.time()
        self.tics[key] = tic
        if not silent:
            self.green(f'{key} timer started')
        return tic

    def toc(self, key='default', silent=False, time_format=":.4f", __is_split=False):
        tic = self.tics[key]
        if tic is None:
            raise Exception('Need to start the timer first.')
        toc = time.time()
        delta = toc - tic
        if not silent:
            self.print(f"{key} lap time:", end=' ')
            self.green(("{" + time_format + "}s").format(delta))
        if __is_split:
            self.tics[key] = toc
        return delta

    def start(self, key='default', silent=True):
        return self.tic(key, silent)

    def split(self, key='default', silent=False, time_format=":.4f"):
        return self.toc(key, silent, time_format, _Moleskin__is_split=True)

    def p(self, *args, **kwargs):
        self.print(*args, **kwargs)

    def print(self, *args, **kwargs):
        """use stdout.flush to allow streaming to file when used by IPython. IPython doesn't have -u option."""
        if self.log_file and 'file' not in kwargs:
            with open(self.log_file, 'a+') as logfile:
                print(*args, **kwargs, file=logfile)
        print(*args, **kwargs)
        sys.stdout.flush()

    def cp(self, *args, **kwargs):
        self.cprint(*args, **kwargs)

    def cprint(self, *args, sep=' ', color='white', **kwargs):
        """use stdout.flush to allow streaming to file when used by IPython. IPython doesn't have -u option."""
        if self.log_file and 'file' not in kwargs:
            with open(self.log_file, 'a+') as logfile:
                _cprint(sep.join([str(a) for a in args]), color, **kwargs, file=logfile)
        _cprint(sep.join([str(a) for a in args]), color, **kwargs)
        sys.stdout.flush()

    def pp(self, *args, **kwargs):
        self.pprint(*args, **kwargs)

    def pprint(self, *args, **kwargs):
        if self.log_file and 'file' not in kwargs:
            with open(self.log_file, 'a+') as logfile:
                pprint(*args, **kwargs, stream=logfile)
        pprint(*args, **kwargs)
        sys.stdout.flush()

    def log(self, *args, **kwargs):
        """use stdout.flush to allow streaming to file when used by IPython. IPython doesn't have -u option."""
        self.print(*args, **kwargs)

    # TODO: take a look at https://gist.github.com/FredLoney/5454553
    def debug(self, *args, **kwargs):
        # DONE: current call stack instead of last traceback instead of.
        if self.is_debug:
            stacks = traceback.extract_stack()
            last_caller = stacks[-2]
            path = last_caller.filename.split('/')
            if len(path) >= 2:
                self.white(path[-2], end='/')
            if len(path) >= 1:
                self.green(path[-1], end=' ')
            self.white('L', end='')
            self.red('{}'.format(last_caller.lineno), end='')
            self.print(': ', end='')
            self.print(last_caller.line)
            self.print(*args, **kwargs)

    def refresh(self, *args, **kwargs):
        """allow keyword override of end='\r', so that only last print refreshes the console."""
        # to prevent from creating new line
        # default new end to single space.
        if 'end' not in kwargs:
            kwargs['end'] = ' '
        self.print('\r', *args, **kwargs)

    def info(self, *args, **kwargs):
        self.cprint(*args, color='blue', **kwargs)

    def error(self, *args, sep='', **kwargs):
        self.cprint(*args, color='red', **kwargs)

    def warn(self, *args, **kwargs):
        self.cprint(*args, color='yellow', **kwargs)

    def highlight(self, *args, **kwargs):
        self.cprint(*args, color='green', **kwargs)

    def green(self, *args, **kwargs):
        self.cprint(*args, color='green', **kwargs)

    def grey(self, *args, **kwargs):
        self.cprint(*args, color='grey', **kwargs)

    def gray(self, *args, **kwargs):
        self.grey(*args, **kwargs)

    def red(self, *args, **kwargs):
        self.cprint(*args, color='red', **kwargs)

    def yellow(self, *args, **kwargs):
        self.cprint(*args, color='yellow', **kwargs)

    def blue(self, *args, **kwargs):
        self.cprint(*args, color='blue', **kwargs)

    def magenta(self, *args, **kwargs):
        self.cprint(*args, color='magenta', **kwargs)

    def cyan(self, *args, **kwargs):
        self.cprint(*args, color='cyan', **kwargs)

    def white(self, *args, **kwargs):
        self.cprint(*args, color='white', **kwargs)

    # def assert(self, statement, warning):
    #     if not statement:
    #         self.error(warning)
    #

    def raise_(self, exception, *args, **kwargs):
        self.error(*args, **kwargs)
        raise exception

    def diff(self, diff_directory=".", log_directory=None, diff_filename="index.diff"):
        """
        example usage: M.diff('.')
        :param diff_directory: The root directory to call `git diff`.
        :param log_directory: The overriding log directory to save this diff index file
        :param diff_filename: The filename for the diff file.
        :return: None
        """
        if log_directory is None:
            log_directory = os.path.realpath(self.log_directory)
        try:
            cmd = "cd \"{}\" && git add . && git diff > \"{}\" 2>/dev/null" \
                .format(os.path.realpath(diff_directory),
                        os.path.join(log_directory, diff_filename))
            subprocess.check_call(cmd, shell=True)  # Save git diff to experiment directory
        except subprocess.CalledProcessError as e:
            self.warn("configure_output_dir: not storing the git diff due to {}".format(e))


moleskin = Moleskin()
