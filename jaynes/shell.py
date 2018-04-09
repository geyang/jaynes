import subprocess


def c(cmd, *args, verbose=False, **kwargs):
    if verbose:
        print(cmd, *args)
    subprocess.call(cmd, *args, **kwargs)


def ck(cmd, *args, verbose=False, **kwargs):
    if verbose:
        print(cmd, *args)
    try:
        subprocess.check_call(cmd, *args, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.output)
