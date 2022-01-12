import os
from textwrap import dedent
from typing import Union, Tuple, Sequence

from jaynes.mounts import Mount
from jaynes.runners import Runner
from jaynes.templates import ec2_terminate, gce_terminate, ec2_tag_instance


class Launcher:
    BATCH_EXE = False  # class flag for batch execution support
    runners = None

    def __init__(self, **kwargs):
        self.runners = self.runners or []
        self.config = kwargs

    def setup_host(self, verbose=None, **kw):
        pass

    def add_runner(self, runner):
        self.runners.append(runner)

    @property
    def last_runner(self):
        if self.runners:
            return self.runners[-1]
        return None

    @property
    def all_mounts(self):
        # this preserves the order
        all_mounts = sum([r.mounts for r in self.runners], [])
        return list(dict.fromkeys(all_mounts))

    def plan_instance(self, verbose=False):
        pass

    def execute(self, verbose=None):
        pass


def make_host_unpack_script(mounts: Sequence[Mount], launch_dir="/tmp/jaynes-mount", delay=None, root_config=None, **_):
    """

    :param mounts:
    :param launch_dir:
    :param delay:
    :param root_config: a setup script **before** anything is ran.
    :param _:
    :return:
    """
    # the log_dir is primarily used for the run script. Therefore it should use ued here instead.
    log_path = os.path.join(launch_dir, "jaynes-launch.log")
    error_path = os.path.join(launch_dir, "jaynes-launch.err.log")

    all_setup = "\n".join(
        [m.host_setup for m in mounts if hasattr(m, "host_setup") and m.host_setup]
    )

    host_unpack_script = dedent(f"""
        #!/bin/bash
        # to allow process substitution
        set +o posix
        {root_config or ""}
        mkdir -p {launch_dir}
        {{
            {all_setup}
            {f"sleep {delay}" if delay else ""}
        }} > >(tee -a {log_path}) 2> >(tee -a {error_path} >&2)
        """).strip()

    return host_unpack_script


# noinspection PyShadowingBuiltins
def make_launch_script(runners: Tuple[Runner],
                       mounts: Sequence[Mount],
                       unpack_on_host: Union[bool, None],
                       type: str,
                       launch_dir="~/jaynes-launch",
                       pipe_out: bool = None,
                       setup: str = None,
                       terminate_after=False,
                       delay: float = None,
                       instance_name: str = None,
                       root_config: dict = None, **_):
    """
    function to make the host script

    :param type:
    :param root_config:
    :param setup:
    :param pipe_out:
    :type pipe_out:
    :param unpack_on_host:
    :type unpack_on_host:
    :param runners:
    :param mounts:
    :param launch_dir:
    :param terminate_after:
    :param delay:
    :param instance_name: less than 128 ascii characters
    :return:
    """
    log_setup = dedent(f"""
        mkdir -p {launch_dir}
        JAYNES_LAUNCH_DIR={launch_dir}
        """)

    if not pipe_out:
        log_path = os.path.join(launch_dir, "jaynes-launch.log")
        error_path = os.path.join(launch_dir, "jaynes-launch.err.log")
        pipe_out = pipe_out or f""" > >(tee -a {log_path}) 2> >(tee -a {error_path} >&2)"""

    upload_script = '\n'.join(
        [m.upload_script for m in mounts if hasattr(m, "upload_script") and m.upload_script]
    )
    # does not unpack if the self.host_unpack_script has already been generated.
    if unpack_on_host:
        host_unpack_script = "\n".join(
            [m.host_setup for m in mounts if hasattr(m, "host_setup") and m.host_setup]
        )
    else:
        host_unpack_script = ""
    if instance_name:
        assert len(instance_name) <= 128, "Error: ws limits instance tag to 128 unicode characters."

    # NOTE: path.join is running on local computer, so it might not be quite right if remote is say windows.
    # NOTE: dedent is required by aws EC2.
    terminate_commands = ""
    if terminate_after:
        if type == "ec2":
            terminate_commands = ec2_terminate(delay)
        elif type == "gce":
            terminate_commands = gce_terminate(delay)
        else:
            raise NotImplementedError(f"terminate_after is not supported with {type}")

    setup_scripts = "\n".join([r.setup_script for r in runners])
    # note: add wait at the end to terminate process only after all launch scripts finish. Always blocking
    run_scripts = "& \n".join([r.run_script for r in runners] + ["wait"])
    post_scripts = "\n".join([r.post_script for r in runners])

    return f"""
#!/bin/bash
# to allow process substitution
set +o posix
{root_config or ''}
{log_setup or ''}
{{
# launch.setup script
{setup or ""}
{ec2_tag_instance(instance_name) if type == "ec2" and instance_name else ""}
{host_unpack_script}
# upload_script from within the host.
{upload_script}
# runner.setup script
{setup_scripts}
# run script
{run_scripts}
# post script
{post_scripts}
{terminate_commands}
}} {pipe_out or ""}
""".strip()
