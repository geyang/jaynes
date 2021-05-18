import os
from textwrap import indent
from uuid import uuid4

from .constants import JAYNES_PARAMS_KEY
from .param_codec import serialize


def inline(script: str) -> str:
    script = script.strip()
    if not script:
        return ""
    return script if script.endswith(';') else f'{script};'


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
            work_dir: "{mounts[0].host_path}"
            partition: "dev,priority,uninterrupted"
            time_limit: "0:0:20"
            n_cpu: 40
            n_gpu: 0

    :param mounts: list, reserved by jaynes to pass in the mount objects.
    :param pypath: bool, whether this mounting point is included as a part of the python path
    :param setup: setup script, run in the host to setup the environments
    :param startup: startup script, run inside the :code:`srun` session, before your code is boostrapped.
    :param work_dir: path to the current work directory for :code:`srun`.
    :param envs: string containing the environment variables. Need to be :code:`;` separated, single line.
    :param entry_script: "python -u -m jaynes.entry"
    :param n_gpu:
    :param partition:
    :param time_limit:
    :param n_cpu:
    :param name:
    :param comment:
    :param label:
    :param post_script: a script attached to after run_script
    :param options: you can specify extra options beyond what is offered above.
    """
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, mounts=None, pypath="", setup="", startup=None, work_dir=None, envs=None,
                 n_gpu=None, shell="/bin/bash", entry_script="python -u -m jaynes.entry",
                 partition=None, time_limit: str = None, n_cpu=4, name=None, comment=None, label=False, args=None,
                 post_script="", **options):
        self.post_script = post_script
        work_dir = work_dir or os.getcwd()
        # --get-user-env
        setup_cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running on login-node `hostname`"\n"""
        setup_cmd += (setup.strip() + '\n') if setup else ''
        setup_cmd += f"PYTHONPATH=$PYTHONPATH:{pypath} "

        # some cluster only allows --gres=gpu:[1-]
        option_str = ""
        if partition is not None:
            option_str += f" --partition={partition}"
        if time_limit is not None:
            option_str += f" --time={time_limit}"
        if n_cpu is not None:
            option_str += f" --cpus-per-task={n_cpu}"
        if n_gpu:
            option_str += f" --gres=gpu:{n_gpu}"
        if name:
            option_str += f' --job-name="{name}"'
        if label:
            option_str += f" --label"
        if comment:
            option_str += f' --comment="{comment}"'

        extra_options = " ".join([f'--{k.replace("_", "-")}="{v}"' for k, v in options.items()])
        if args:
            extra_options = "".join([f"--{a} " for a in args]) + extra_options

        entry_env = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}}"

        if startup:
            """
            use bash mode if there is a startup script. This is not supported on some clusters.
            For example in vector institute's cluster this does not direct outputs to the 
            stdout.
            """
            cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running inside worker `hostname`";"""
            cmd += inline(startup)
            cmd += f"""{'cd {};'.format(work_dir) if work_dir else ''}"""
            slurm_cmd = f"srun {option_str} {extra_options} {shell} -c '{cmd} {entry_env} {entry_script}'"
        else:
            """
            call the python entry script directly, does not work on the FAIR cluster.
            """
            slurm_cmd = f"{entry_env} srun {option_str} {extra_options} {entry_script}"

        self.run_script_thunk = f""" 
        {setup_cmd} {envs if envs else ""} {slurm_cmd} """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


class SlurmManager(RunnerType):
    """launches slurm jobs through Jaynes Client"""
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, mounts=None, pypath="", setup="", startup=None, work_dir=None, envs=None,
                 n_gpu=None, entry_script="python -u -m jaynes.entry",
                 partition="dev", time_limit="5", n_cpu=4, name="", comment="", label=False, args=None,
                 post_script="", **options):
        """

        :param mounts:
        :param pypath:
        :param setup:
        :param startup:
        :param work_dir:
        :param envs:
        :param n_gpu:
        :param entry_script:
        :param partition:
        :param time_limit:
        :param n_cpu:
        :param name:
        :param comment:
        :param label:
        :param args:
        :param post_script: a script attached to after run_script
        :param options:
        """
        self.post_script = post_script
        work_dir = work_dir or os.getcwd()
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
            entry_env = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}}"

            cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running inside worker `hostname`";"""
            # todo: change this.
            cmd += inline(startup) if startup else ""
            cmd += f"""{"cd '{}';".format(work_dir) if work_dir else ""}"""

            slurm_cmd = f"srun {gres} --partition={partition} --time={time_limit} " \
                        f"--cpus-per-task {n_cpu} --job-name='{name}' {'--label' if label else ''} " \
                        f"--comment='{comment}' {extra_options} /bin/bash -l -c '{cmd} {entry_env} {entry_script}'"
        else:
            """
            call the python entry script directly, does not work on the FAIR cluster.
            """
            entry_env = f"{JAYNES_PARAMS_KEY}={{encoded_thunk}}"
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
    :param work_dir:
    :param envs: Set of environment key and variables, a string
    :param entry_script: "python -u -m jaynes.entry"
    :param use_gpu:
    """
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, mounts=None, pypath="", work_dir=None, setup=None, startup=None, envs=None,
                 shell="/bin/bash", entry_script="python -u -m jaynes.entry", pipe="",
                 cleanup="", detach=False, use_gpu=False, verbose=None, post_script="", **_):
        """

        :param mounts:
        :param pypath:
        :param work_dir:
        :param setup:
        :param startup:
        :param envs:
        :param shell:
        :param entry_script:
        :param pipe:
        :param cleanup:
        :param detach: keep the process running after ssh detachment.
        :param use_gpu:
        :param verbose:
        :param post_script: a script attached to after run_script
        :param _:
        """
        work_dir = work_dir or os.getcwd()
        cmd = ""
        self.post_script = post_script
        if verbose:
            cmd += f"""printf "\\e[1;34m%-6s\\e[m" "Running on remote host {' (gpu)' if use_gpu else ''}";"""
        cmd += inline(startup) if startup else ''
        cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath};"
        cmd += f"""{"cd {};".format(work_dir) if work_dir else ""}"""
        cmd += f"{JAYNES_PARAMS_KEY}={{encoded_thunk}} {entry_script}"

        test_gpu = f"""
                echo 'Testing nvidia-smi inside docker'
                {envs if envs else ""} nvidia-smi
                """
        if detach:
            setup = """
                export pipe=`mktemp -u`
                mkfifo $pipe
                """ + setup
            cleanup = """
            cat $pipe
            rm -f $pipe
            """ + cleanup
            # -p ignores NONPIPEs, s.t. screen keeps running after parent process exits
            pipe = " |& tee -p $pipe" + pipe
            shell = "screen -md " + shell

        self.run_script_thunk = f"""
                {setup or ""}
                {test_gpu if use_gpu else ""}
                {envs if envs else ""} {shell} -c '{cmd}{pipe}'
                {cleanup}
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
            work_dir: "{mounts[0].container_path}"
            ipc: host
            use_gpu: false

    :param image: string for the docker image to use.
    :param mounts: list, reserved by jaynes to pass in the mount objects.
    :param startup: the script you want to run first INSIDE docker
    :param mount:
    :param pypath:
    :param work_directory:
    :param work_dir:
    :param envs: Set of environment key and variables, a string
    :param entry_script: "python -u -m jaynes.entry"
    :param name: Name of the docker container instance, use uuid if is None
    :param use_gpu:
    :param sudo: Flag, useful for when running on EC2
    :param ipc: specify ipc for multiprocessing. Typically 'host'
    :param tty: almost never used. This is because when this script is ran, it is almost garanteed that the
                ssh/bash session is not going to be tty.
    :param post_script: a script attached to after run_script
    :param **kwargs: passed in as parameters to docker command.
                memory="4g" gets translated into `--memory 4g`
    """
    setup_script = ""
    run_script = ""
    post_script = ""

    def __init__(self, *, image, mounts=None, work_directory=None, work_dir=None, setup="", startup=None,
                 pypath=None, envs=None, entry_script="python -u -m jaynes.entry", name=None,
                 docker_cmd="docker", ipc=None, tty=False, options=None,
                 post_script="", **_):
        mount_string = " ".join([m.docker_mount for m in mounts])
        self.setup_script = setup
        self.docker_image = image
        self.post_script = post_script

        cmd = f"""echo "Running in {docker_cmd}";"""
        cmd += inline(startup) if startup else ''
        cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath};" if pypath else ""
        cmd += f"cd '{work_dir}';" if work_dir else ""
        cmd += f"""{JAYNES_PARAMS_KEY}={{encoded_thunk}} {entry_script}"""
        docker_container_name = name or uuid4()
        test_gpu = f"""
                echo 'Testing nvidia-smi inside docker'
                {envs if envs else ""} {docker_cmd} run --rm {image} nvidia-smi
                """

        remove_by_name = f"""
            echo -ne 'kill running instances '
            {docker_cmd} kill {docker_container_name}
            echo -ne 'remove existing container '
            {envs if envs else ""} {docker_cmd} rm {docker_container_name}""" if docker_container_name else ""

        ipc_config = f"--ipc={ipc}" if ipc else ""
        wd_config = f"-w={work_directory}" if work_directory else ""
        rest_config = ""
        options = options or {}
        for k, v in options.items():
            rest_config += f"--{k.replace('_', '-')}={v}"
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
            {indent(self.setup_script, " " * 12).strip()}
            {remove_by_name if name else ""}
            {test_gpu if "nvidia" in docker_cmd else ""}
            echo 'Now run docker'
            {envs if envs else ""} {docker_cmd} run -i{"t" if tty else ""} {wd_config} {ipc_config} {rest_config} {mount_string} --name '{docker_container_name}' \\
            {image} /bin/bash -c '{cmd}'
            """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self
