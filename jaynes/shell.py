import subprocess


def popen(cmd, *args, verbose=False, **kwargs):
    if verbose:
        if args:
            print(cmd, *args)
        else:
            print(cmd)
    subprocess.Popen(cmd, *args, **kwargs)


def c(cmd, *args, verbose=False, **kwargs):
    if verbose:
        if args:
            print(cmd, *args)
        else:
            print(cmd)
    subprocess.call(cmd, *args, **kwargs)


def ck(cmd, *args, verbose=False, **kwargs):
    if verbose:
        if args:
            print(cmd, *args)
        else:
            print(cmd)
    try:
        subprocess.check_call(cmd, *args, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.output)
