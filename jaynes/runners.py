import os
from uuid import uuid4

from .constants import JAYNES_PARAMS_KEY
from .param_codec import serialize

# default startup script. At minimum install jaynes.
STARTUP = 'pip install jaynes awscli -q'


class RunnerType:
    @classmethod
    def from_yaml(cls, _, node):
        return cls, _.construct_mapping(node)


class Slurm(RunnerType):
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, pypath="", setup="", startup=STARTUP, launch_directory=None, envs=None, n_gpu=None,
                 partition="dev", time_limit="5", n_cpu=4, name="", comment="", label=False, **options):
        """
        SLURM SRUN runner. This runner launches using `srun`.

        The ..code::`**options` catch-all allows you to specify those options not already included. For example:

        .. code:: yml

                begin: "16:00""         # -> --begin=`16:00`
                time_limit: "71:00:00"  # -> --time-limit=`71:00:00`
                nodes: 10               # -> --nodes=`10`

        :param pypath:
        :param setup:
        :param startup:
        :param launch_directory:
        :param envs:
        :param n_gpu:
        :param partition:
        :param time_limit:
        :param n_cpu:
        :param name:
        :param comment:
        :param label:
        :param options: you can specify extra options beyond what is offered above.
        """
        launch_directory = launch_directory or os.getcwd()
        entry_script = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}} python -u -m jaynes.entry"
        # --get-user-env
        setup_cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running on login-node"\n"""
        setup_cmd += (setup.strip() + '\n') if setup else ''
        setup_cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath}\n"

        cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running inside worker";"""
        cmd += (startup.strip() + ";") if startup else ""
        cmd += f"""{"cd '{}';".format(launch_directory) if launch_directory else ""}"""

        # some cluster only allows --gres=gpu:[1-]
        gres = f"--gres=gpu:{n_gpu}" if n_gpu else ""
        extra_options = " ".join([f"--{k.replace('_', '-')}='{v}'" for k, v in options])
        slurm_cmd = f"srun {gres} --partition={partition} --time={time_limit} " \
            f"--cpus-per-task {n_cpu} --job-name='{name}' {'--label' if label else ''} " \
            f"--comment='{comment}' {extra_options} /bin/bash -l -c '{cmd} {entry_script}'"
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
                {envs if envs else ""} 
                {setup_cmd}
                {slurm_cmd}
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class Simple(RunnerType):
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, pypath="", launch_directory=None, startup=STARTUP, envs=None, use_gpu=False, **_):
        """
        Simple runner, good for running things locally.

        :param pypath:
        :param startup:
        :param mount:
        :param launch_directory:
        :param envs: Set of environment key and variables, a string
        :param use_gpu:
        """
        launch_directory = launch_directory or os.getcwd()
        entry_script = "python -u -m jaynes.entry"
        cmd = f"""printf "\\e[1;34m%-6s\\e[m" "Running on remote host {' (gpu)' if use_gpu else ''}";"""
        cmd += (startup.strip() + ';') if startup else ''
        cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath};"
        cmd += f"""{"cd '{}';".format(launch_directory) if launch_directory else ""}"""
        cmd += f"{JAYNES_PARAMS_KEY}={{encoded_thunk}} {entry_script}"
        test_gpu = f"""
                echo 'Testing nvidia-smi inside docker'
                {envs if envs else ""} nvidia-smi
                """
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
                {test_gpu if use_gpu else ""}
                {envs if envs else ""} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class Docker(RunnerType):
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, image, work_directory=None, launch_directory=None, startup=STARTUP, mount=None,
                 pypath=None, envs=None, name=None, use_gpu=False, ipc=None, tty=False, **_):
        """

        :param image:
        :param startup: the script you want to run first INSIDE docker
        :param mount:
        :param pypath:
        :param work_directory:
        :param launch_directory:
        :param envs: Set of environment key and variables, a string
        :param name: Name of the docker container instance, use uuid if is None
        :param use_gpu:
        :type ipc: specify ipc for multiprocessing. Typically 'host'
        :param tty: almost never used. This is because when this script is ran, it is almost garanteed that the
                    ssh/bash session is not going to be tty.
        """
        self.setup_script = f"""
            # sudo service docker start # this is optional.
            # docker pull {image}
        """
        self.docker_image = image
        docker_cmd = "nvidia-docker" if use_gpu else "docker"
        entry_script = "python -u -m jaynes.entry"
        cmd = f"""echo "Running in docker{' (gpu)' if use_gpu else ''}";"""
        cmd += f"{startup.strip()};" if startup else ''
        cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath};" if pypath else ""
        cmd += f"cd '{launch_directory}';" if launch_directory else ""
        # cmd += f"pwd;"
        cmd += f"""{JAYNES_PARAMS_KEY}={{encoded_thunk}} {entry_script}"""
        docker_container_name = name or uuid4()
        test_gpu = f"""
                echo 'Testing nvidia-smi inside docker'
                {envs if envs else ""} {docker_cmd} run --rm {image} nvidia-smi
                """
        remove_by_name = f"""
                echo 'kill running instances'
                {docker_cmd} kill {docker_container_name}
                echo 'remove existing container with name'
                {envs if envs else ""} {docker_cmd} rm {docker_container_name}""" if docker_container_name else ""
        ipc_config = f"--ipc={ipc}" if ipc else ""
        wd_config = f"-w={work_directory}" if work_directory else ""
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
                {test_gpu if use_gpu else ""}
                {remove_by_name}
                echo 'Now run docker'
                {envs if envs else ""} {docker_cmd} run -i{"t" if tty else ""} {wd_config} {ipc_config} {mount} --name '{docker_container_name}' \\
                {image} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self
