import subprocess


def popen(cmd, *args, verbose=False, **kwargs):
    if verbose:
        print(cmd, *args)
    return subprocess.Popen(cmd, *args, **kwargs)


def call(cmd, *args, verbose=False, **kwargs):
    """Run a command and return the exit code.
    
    Pipe the output to stdout and stderr.
    Args:
        cmd: The command to run.
        *args: Additional arguments to pass to subprocess.Popen.
        verbose: If True, print the command before running it.
        **kwargs: Additional keyword arguments to pass to subprocess.Popen.

    :return: The exit code of the command.
    """
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
    """Run a command and return the output and error as strings.

    Example:
        >>> run(["echo", "hey"])
        ('hey', '')

    Args:
        cmd: The command to run.
        *args: Additional arguments to pass to subprocess.Popen.
        verbose: If True, print the command before running it.
        **kwargs: Additional keyword arguments to pass to subprocess.Popen.

    :return: A tuple containing the output and error as strings.
    """
    if verbose:
        print(cmd, *args)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    return process.communicate()
