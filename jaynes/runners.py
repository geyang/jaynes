import os
from uuid import uuid4

from .constants import JAYNES_PARAMS_KEY
from .param_codec import serialize


class RunnerType:
    @classmethod
    def from_yaml(cls, _, node):
        return cls, _.construct_mapping(node)


class Slurm(RunnerType):
    """
    SLURM SRUN runner. This runner launches using `srun`.

    The :code:`**options` catch-all allows you to specify those options not already included. For example:

    .. code:: yaml

            begin: "16:00""         # -> --begin=`16:00`
            time_limit: "71:00:00"  # -> --time-limit=`71:00:00`
            nodes: 10               # -> --nodes=`10`

    For the full set of options available on :code:`srun`, you can refer to SLURM documentation.

    Example
    -------

    to configure the Slurm runner in :code:`jaynes.yml`, you can do

    .. code:: yaml

        # ⬇️ this is a yaml syntax to select the class
        runner: !runners.Slurm
            envs: >-
              LD_LIBRARY_PATH=/public/apps/anaconda3/5.0.1/lib:/private/home/geyang/.mujoco/mjpro150/bin::/public/slurm/17.11.4/lib
            startup: >-
              source /etc/profile;
              source ~/.profile;
              module load anaconda3/5.0.1;
              source activate playground;
              export LC_CTYPE=en_US.UTF-8
            # cd {mounts[0].host_path} && pip install -e . -q
            pypath: "{mounts[0].host_path}/rl:{mounts[0].host_path}/imitation:{mounts[0].host_path}/rl_maml_tf"
            launch_directory: "{mounts[0].host_path}"
            partition: "dev,priority,uninterrupted"
            time_limit: "0:0:20"
            n_cpu: 40
            n_gpu: 0

    :param mounts: list, reserved by jaynes to pass in the mount objects.
    :param pypath: bool, whether this mounting point is included as a part of the python path
    :param setup: setup script, run in the host to setup the environments
    :param startup: startup script, run inside the :code:`srun` session, before your code is boostrapped.
    :param launch_directory: path to the current work directory for :code:`srun`.
    :param envs: string containing the environment variables. Need to be :code:`;` separated, single line.
    :param n_gpu:
    :param partition:
    :param time_limit:
    :param n_cpu:
    :param name:
    :param comment:
    :param label:
    :param options: you can specify extra options beyond what is offered above.
    """
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, mounts=None, pypath="", setup="", startup=None, launch_directory=None, envs=None,
                 n_gpu=None,
                 partition="dev", time_limit="5", n_cpu=4, name="", comment="", label=False, args=None, **options):
        launch_directory = launch_directory or os.getcwd()
        # --get-user-env
        setup_cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running on login-node"\n"""
        setup_cmd += (setup.strip() + '\n') if setup else ''
        setup_cmd += f"PYTHONPATH=$PYTHONPATH:{pypath} "

        # some cluster only allows --gres=gpu:[1-]
        gres = f"--gres=gpu:{n_gpu}" if n_gpu else ""
        extra_options = " ".join([f"--{k.replace('_', '-')}='{v}'" for k, v in options.items()])
        if args:
            extra_options = "".join([f"--{a} " for a in args]) + extra_options
        if startup:
            """
            use bash mode if there is a startup script. This is not supported on some clusters.
            For example in vector institute's cluster this does not direct outputs to the 
            stdout.
            """
            entry_script = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}} python -u -m jaynes.entry"

            cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running inside worker";"""
            cmd += (startup.strip() + ";") if startup else ""
            cmd += f"""{"cd '{}';".format(launch_directory) if launch_directory else ""}"""

            slurm_cmd = f"srun {gres} --partition={partition} --time={time_limit} " \
                        f"--cpus-per-task {n_cpu} --job-name='{name}' {'--label' if label else ''} " \
                        f"--comment='{comment}' {extra_options} /bin/bash -l -c '{cmd}; {entry_script}'"
        else:
            """
            call the python entry script directly, does not work on the FAIR cluster.
            """
            entry_env = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}}"
            entry_script = f"python -u -m jaynes.entry"
            slurm_cmd = f"{entry_env} srun {gres} --partition={partition} --time={time_limit} " \
                        f"--cpus-per-task {n_cpu} --job-name='{name}' {'--label' if label else ''} " \
                        f"--comment='{comment}' {extra_options} {entry_script}"

        self.run_script_thunk = f""" 
        {setup_cmd} {envs if envs else ""} {slurm_cmd} """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class Simple(RunnerType):
    """
    Simple runner, good for running things locally.

    :param mounts: list, reserved by jaynes to pass in the mount objects.
    :param pypath:
    :param startup:
    :param mount:
    :param launch_directory:
    :param envs: Set of environment key and variables, a string
    :param use_gpu:
    """
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, mounts=None, pypath="", launch_directory=None, setup=None, startup=None, envs=None,
                 use_gpu=False, verbose=None, **_):
        launch_directory = launch_directory or os.getcwd()
        entry_script = "python -u -m jaynes.entry"
        cmd = ""
        if verbose:
            cmd += f"""printf "\\e[1;34m%-6s\\e[m" "Running on remote host {' (gpu)' if use_gpu else ''}";"""
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
                {setup or ""}
                {test_gpu if use_gpu else ""}
                {envs if envs else ""} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class Docker(RunnerType):
    """
    Docker Runner

    Example
    -------

    to configure the Docker runner in :code:`jaynes.yml`, you can do

    .. code:: yaml

        # ⬇️ this is a yaml syntax to select the class
        runner: !runners.Docker
            name: "some-job"  # only for docker
            image: "episodeyang/super-expert"
            startup: yes | pip install jaynes ml-logger -q
            envs: "LANG=utf-8"
            pypath: "{mounts[0].container_path}"
            launch_directory: "{mounts[0].container_path}"
            ipc: host
            use_gpu: false

    :param image: string for the docker image to use.
    :param mounts: list, reserved by jaynes to pass in the mount objects.
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
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, image, mounts=None, work_directory=None, launch_directory=None, startup=None,
                 pypath=None, envs=None, name=None, use_gpu=False, ipc=None, tty=False, **_):
        mount_string = " ".join([m.docker_mount for m in mounts])
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
                {envs if envs else ""} {docker_cmd} run -i{"t" if tty else ""} {wd_config} {ipc_config} {mount_string} --name '{docker_container_name}' \\
                {image} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self
