import os
import tempfile


def path_no_ext(path):
    return '.'.join(path.split('.')[:-1])


def get_temp_dir():
    """returns a temporal directory. Mac OSX /val is a symbolic link, which is why we return the resolved path."""
    tmp_dir = tempfile.mkdtemp()
    return os.path.realpath(tmp_dir)


def tag_instance(Name=None, **kwargs):
    from .shell import ck
    cmd = f"aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=Name,Value='{Name}' --region us-west-2"
    # f"aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=exp_prefix,Value={instance_tag} --region us-west-2"
    return ck(cmd)
