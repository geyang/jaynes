import os
from uuid import uuid4

from .constants import JAYNES_PARAMS_KEY
from .param_codec import serialize

# default startup script. At minimum install jaynes.
STARTUP = 'pip install jaynes awscli -q'


class Slurm:
    setup_script = ""
    run_script = ""
    post_script = ""

    @classmethod
    def from_yaml(cls, _, node):
        return cls, {k.value: v.value for k, v in node.value}

    def __init__(self, pypath="", startup=STARTUP, mount=None, launch_directory=None, envs=None, n_gpu=None,
                 partition="dev", time_limit="5", n_cpu=4, ):
        launch_directory = launch_directory or os.getcwd()
        entry_script = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}} python -u -m jaynes.entry"
        cmd = f"/bin/bash -l -c '{entry_script}'"
        slurm_cmd = f"srun --gres=gpu:{n_gpu or 0} --partition={partition} --time={time_limit} " \
            f"--cpus-per-task {n_cpu} {cmd}"
        cmd = f"""printf "\\e[1;34m%-6s\\e[m" "Running on slurm cluster";"""
        cmd += (startup.strip() + ';') if startup else ''
        cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath};"
        cmd += f"""{"cd '{}';".format(launch_directory) if launch_directory else ""}"""
        cmd += f"pwd; {slurm_cmd}"
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
                {envs if envs else ""} {cmd}
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class Simple:
    setup_script = ""
    run_script = ""
    post_script = ""

    @classmethod
    def from_yaml(cls, _, node):
        return cls, {k.value: v.value for k, v in node.value}

    def __init__(self, pypath="", startup=STARTUP, mount=None, launch_directory=None, envs=None, use_gpu=False):
        """
        SLURM runner

        :param pypath:
        :param startup:
        :param mount:
        :param launch_directory:
        :param envs: Set of environment key and variables, a string
        :param use_gpu:
        """
        launch_directory = launch_directory or os.getcwd()
        entry_script = "python -u -m jaynes.entry"
        cmd = f"""printf "\\e[1;34m%-6s\\e[m" "Running on cluster{' (gpu)' if use_gpu else ''}";"""
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
                {test_gpu if use_gpu else "" }
                {envs if envs else ""} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class Docker:
    setup_script = ""
    run_script = ""
    post_script = ""

    @classmethod
    def from_yaml(cls, _, node):
        return cls, {k.value: v.value for k, v in node.value}

    def __init__(self, *, image, work_directory=None, launch_directory=None, startup=STARTUP, mount=None,
                 pypath=None, envs=None, name=None, use_gpu=False, ipc=None, tty=False, ):
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
            sudo service docker start # this is optional.
            docker pull {image}
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
                {test_gpu if use_gpu else "" }
                {remove_by_name}
                {envs if envs else ""} {docker_cmd} info
                echo 'Now run docker'
                {envs if envs else ""} {docker_cmd} run -i{"t" if tty else ""} {wd_config} {ipc_config} {mount} --name '{docker_container_name}' \\
                {image} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self
