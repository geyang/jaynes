def path_no_ext(path):
    return '.'.join(path.split('.')[:-1])


def get_temp_dir():
    """returns a temporal directory. Mac OSX /val is a symbolic link, which is why we return the resolved path."""
    import os, tempfile
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
    """pyCharm emulate terminal confuses this, show up as tty but then runner fails"""
    import os
    import sys
    return os.isatty(sys.stdout.fileno())


def get_home_dir():
    """get the home directory on both PC and unix."""
    from os.path import expanduser
    home = expanduser("~")
    return home


def cwd_ancestors():
    """generator returning the the current directory and ancestors one after another"""
    import os
    _ = os.path.abspath(os.getcwd())
    while True:
        yield _
        parent = os.path.dirname(_)
        if parent == _:
            break
        else:
            _ = parent


def pick(m, *keys):
    """because they prefer verbosity."""
    return {k: v for k, v in m.items() if k in keys}


def omit(m, *keys):
    """because guido sucks."""
    return {k: v for k, v in m.items() if k not in keys}


def n_to_m(yaml_node):
    return {k.value: v.value for k, v in yaml_node.value}


# note: now we properly handle the node types.
def hydrate(Constructor, ctx):
    def _fn(_, node):
        kwargs = {}
        for k, v in _.construct_mapping(node).items():
            if isinstance(v, str):
                try:
                    kwargs[k] = v.format(**ctx)
                except AttributeError as e:
                    raise Exception(f"during comprehension of <{k}: {v}>: {str(e)}")
            else:
                kwargs[k] = v
        return Constructor(**kwargs)

    return _fn


def snake2camel(word):
    return ''.join(x.capitalize() or '_' for x in word.split('_'))
