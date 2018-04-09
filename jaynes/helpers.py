import os
import tempfile


def path_no_ext(path):
    return '.'.join(path.split('.')[:-1])


def get_temp_dir():
    """returns a temporal directory. Mac OSX /val is a symbolic link, which is why we return the resolved path."""
    tmp_dir = tempfile.mkdtemp()
    return os.path.realpath(tmp_dir)
