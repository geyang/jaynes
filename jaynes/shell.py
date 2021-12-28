import subprocess


def popen(cmd, *args, verbose=False, **kwargs):
    if verbose:
        print(cmd, *args)
    return subprocess.Popen(cmd, *args, **kwargs)


def call(cmd, *args, verbose=False, **kwargs):
    if verbose:
        print(cmd, *args)
    return subprocess.call(cmd, *args, **kwargs)


def check_call(cmd, *args, verbose=False, **kwargs) -> object:
    if verbose:
        print(cmd, *args)
    try:
        return subprocess.check_call(cmd, *args, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e)


def run(cmd, *args, verbose=False, **kwargs) -> [str, str]:
    if verbose:
        print(cmd, *args)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    return process.communicate()
