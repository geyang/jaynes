import os
import tempfile


def path_no_ext(path):
    return '.'.join(path.split('.')[:-1])


def get_temp_dir():
    """returns a temporal directory. Mac OSX /val is a symbolic link, which is why we return the resolved path."""
    tmp_dir = tempfile.mkdtemp()
    return os.path.realpath(tmp_dir)


def tag_instance(Name=None, region="us-west-2", verbose=False, **kwargs):
    from .shell import ck
    template = f"aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key='{{key}}',Value='{{value}}' --region {region}"
    if Name:
        kwargs.update(Name=Name)
    cmd = '''export EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id`" && ''' + \
          " && ".join([template.format(key=k, value=v) for k, v in kwargs.items()])

    return ck(cmd, shell=True, verbose=verbose)


def is_interactive():
    """pyCharm emulate terminal confuses this, show up as tty but then docker fails"""
    import os
    import sys
    return os.isatty(sys.stdout.fileno())
