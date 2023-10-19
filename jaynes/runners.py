import os
from copy import deepcopy
from datetime import datetime

import jaynes
from .constants import JAYNES_PARAMS_KEY
from .param_codec import serialize


def inline(script: str) -> str:
    script = script.strip()
    if not script:
        return ""
    return script if script.endswith(';') else f'{script};'


class Runner:
    launch_config = None

    setup_script = ""
    run_script = ""
    post_script = ""

    main_script = ""

    @classmethod
    def from_yaml(cls, _, node):
        return cls, _.construct_mapping(node)

    def __init__(self, mounts, work_dir=None, pypath=None, startup=None, entry_script="python -u -m jaynes.entry",
                 post_script="", **_):

        # mounts can be an empty list []
        if mounts is not None:
            self.mounts = mounts

        self.work_dir = work_dir
        self.pypath = pypath
        self.startup = startup
        self.entry_script = entry_script
        self.post_script = post_script

    @property
    def main_script_thunk(self):
        entry_env = f"{JAYNES_PARAMS_KEY}={{JYNS_encoded_thunk}}"

        cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running inside worker `hostname`" 1>&2;"""
        if self.startup:
            cmd += inline(self.startup)
        if self.work_dir:
            cmd += f"""cd {self.work_dir};"""
        if self.pypath:
            cmd += f"PYTHONPATH=$PYTHONPATH:{self.pypath}"
        return f"{cmd} {entry_env} {self.entry_script}"

    def build(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.main_script = self.main_script_thunk.format(JYNS_encoded_thunk=encoded_thunk)
        self.run_script = self.run_script_thunk.format(JYNS_main_script=self.main_script)
        return self

    def chain(self, fn, *args, __sep=" &\n", **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.main_script += __sep + self.main_script_thunk.format(JYNS_encoded_thunk=encoded_thunk)
        self.run_script = self.run_script_thunk.format(JYNS_main_script=self.main_script)


class Slurm(Runner):
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
    :param interactive: bool, uses :code:`srun` when True, :code:`sbatch` when False.
    :param n_seq_jobs: int, set a value > 1 if you run a sequence of jobs with :code:`sbatch`.
    :param time_limit:
    :param n_cpu:
    :param name:
    :param comment:
    :param label:
    :param post_script: a script attached to after run_script
    :param options: you can specify extra options beyond what is offered above.
    """

    def __init__(self, *, mounts=None, work_dir, pypath=None, setup="", startup=None, envs=None,
                 n_gpu=None, shell="/bin/bash", entry_script="python -u -m jaynes.entry",
                 partition=None, interactive=True, n_seq_jobs=1, time_limit: str = None, n_cpu=4, name=None,
                 comment=None, label=False, args=None,
                 post_script="", **options):
        super().__init__(mounts, work_dir, pypath, startup, entry_script, post_script)

        # --get-user-env
        setup_cmd = f"""printf "\\e[1;34m%-6s\\e[m\\n" "Running on login-node `hostname`"\n"""
        setup_cmd += (setup.strip() + '\n') if setup else ''
        # remove
        # if pypath:
        #     setup_cmd += f"export PYTHONPATH=$PYTHONPATH:{pypath}"

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

        if interactive:
            srun_cmd = f"srun {option_str} {extra_options} {shell} -c '{{JYNS_main_script}} & wait'"
            if n_seq_jobs is not None and n_seq_jobs > 1:
                assert interactive is False, "interactive mode only supports non-sequential jobs."
            self.run_script_thunk = f"""
                {setup_cmd}
                {envs if envs else ""} {srun_cmd}"""
        else:
            """
            use sbatch to submit a sequence of jobs.
            sbatch job saves stdout/stderr to a log file, thus this script waits until the file
            shows up and runs `tail -f` for it.
            NOTE: It's quite hard to run `tail -f` on all the logfiles in the proper order,
            thus it is only applied to the first job.
            """
            # logfile = f"{work_dir}/slurm-%j.out"
            # sbatch_options = (f"--output {logfile}", f"--error {logfile}")
            # sbatch_options = "\n".join(["#SBATCH " + opt for opt in sbatch_options])
            sbatch_cmds = [setup_cmd]
            for i in range(n_seq_jobs or 1):
                sbatch_cmds += [f"{envs if envs else ''} sbatch {option_str} {extra_options} -d singleton"
                                f"<<<'#!/bin/bash\n{{JYNS_main_script}} & wait'"]

            # Note: The tailing leave Ghost processes running on the login node, which eventually
            #   max-outs the number of processes in the system. We remove this support because
            #   real-time pipe-back is not necessary for non-interactive mode.
            #
            #     if i == 0:
            #         # NOTE: store the "Submitted batch job xxx" message to $SUBMISSION,
            #         # and some shell magic to extract the last word that is jobid.
            #         # ref: https://stackoverflow.com/a/20021078/7057866
            #         sbatch_cmd = ' && '.join([f"SUBMISSION=$({sbatch_cmd})",
            #                                   f"echo $SUBMISSION",
            #                                   "JOBID=${SUBMISSION##* }",
            #                                   f"LOGFILE={work_dir}/slurm-$JOBID.out",
            #                                   "echo Logs are stored at $LOGFILE\n"])
            # # wait until the logfile is generated
            # wait_logic = f"while [ ! -f $LOGFILE ]; do sleep 1; done"
            # sbatch_cmd = f"{sbatch_cmd} {wait_logic} && tail -f $LOGFILE"

            self.run_script_thunk = '\n'.join(sbatch_cmds)


class Simple(Runner):
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

    def __init__(self, *, mounts=None, pypath="", work_dir=None, setup=None, startup=None, envs=None,
                 shell="/bin/bash", entry_script="python -u -m jaynes.entry", pipe="",
                 cleanup="", detach=False, post_script="", **_):
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
        :param post_script: a script attached to after run_script
        :param _:
        """
        work_dir = work_dir or os.getcwd()

        super().__init__(mounts, work_dir, pypath, startup, entry_script, post_script)

        self.post_script = post_script

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
            {envs if envs else ""} {shell} -c '{{JYNS_main_script}}{pipe}'
            {cleanup}
            """


class Docker(Runner):
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
    :param workdir: this is the option passed on to docker.
    :param work_dir: this is the current work directory for the bash script.
    :param envs: Set of environment key and variables, a string
    :param entry_script: "python -u -m jaynes.entry"
    :param name: Name of the docker container instance, use uuid if is None
    :param use_gpu:
    :param sudo: Flag, useful for when running on EC2
    :param ipc: specify ipc for multiprocessing. Typically 'host'
    :param net: for ec2, `--net host` allows docker to use the host's IAM for ec2 services
    :param tty: almost never used. This is because when this script is ran, it is almost garanteed that the
                ssh/bash session is not going to be tty.
    :param post_script: a script attached to after run_script
    :param **kwargs: passed in as parameters to docker command.
                memory="4g" gets translated into `--memory 4g`
    """

    def __init__(self, *, image, mounts=None, work_dir=None, workdir=None, setup="", startup=None,
                 pypath=None, envs=None, entry_script="python -u -m jaynes.entry", name=None,
                 docker_cmd="docker", ipc=None, tty=False, post_script="", net=None, **options):
        super().__init__(mounts, work_dir, pypath, startup, entry_script, post_script)

        mount_string = " ".join([m.docker_mount for m in mounts])
        self.setup_script = setup

        is_gpu = options.get('gpus', None) or "nvidia" in docker_cmd

        # dynamically generate the job name to avoid conflict
        docker_container_name = name or f"jaynes-job-{datetime.utcnow():%H%M%S}-{jaynes.RUN.count}"

        remove_by_name = f"""
echo -ne 'kill running instances '
{docker_cmd} kill {docker_container_name}
echo -ne 'remove existing container '
{docker_cmd} rm {docker_container_name}""" if docker_container_name else ""

        config = ""
        for env_string in envs.split(' '):
            config += f"--env {env_string} "

        if workdir:
            options['workdir'] = workdir
        if net:
            options['net'] = net
        if ipc:
            options['ipc'] = ipc

        rest_config = " ".join(f"--{k.replace('_', '-')}={v}" for k, v in options.items())

        test_gpu = f"""
            echo 'Testing nvidia-smi inside docker'
            {docker_cmd} run --rm {rest_config} {image} nvidia-smi
            """
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
{remove_by_name if name else ""}
echo 'running {image} on' `hostname`
{docker_cmd} run -i{"t" if tty else ""} {config} {rest_config} {mount_string} --name '{docker_container_name}' \\
{image} /bin/sh -c '{{JYNS_main_script}} & wait' """

    chain = None
    # def chain(self, fn, *args, __sep=" &\n", **kwargs):
    #     encoded_thunk = serialize(fn, args, kwargs)
    #     self.main_script = self.main_script_thunk.format(JYNS_encoded_thunk=encoded_thunk)
    #     self.run_script += __sep + self.run_script_thunk.format(JYNS_main_script=self.main_script).strip()


class Container(Runner):
    """
    Container Runner for Kubernetes

    Example
    -------

    to configure the Container runner in :code:`jaynes.yml`, you can do

    .. code:: yaml

        # ⬇️ this is a yaml syntax to select the class
        runner: !runners.Container
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
    :param workdir: this is the option passed on to docker.
    :param work_dir: this is the current work directory for the bash script.
    :param envs: Set of environment key and variables, a string
    :param entry_script: "python -u -m jaynes.entry"
    :param name: Name of the docker container instance, use uuid if is None
    :param use_gpu:
    :param sudo: Flag, useful for when running on EC2
    :param ipc: specify ipc for multiprocessing. Typically 'host'
    :param net: for ec2, `--net host` allows docker to use the host's IAM for ec2 services
    :param tty: almost never used. This is because when this script is ran, it is almost guaranteed that the
                ssh/bash session is not going to be tty.
    :param post_script: a script attached to after run_script
    :param **kwargs: Not used
    """
    job = None

    def __init__(self, *, image,
                 image_pull_policy="IfNotPresent",
                 image_pull_secret=None,
                 mounts=None,
                 work_dir=None,
                 workdir=None,
                 setup="",
                 startup=None,
                 namespace=None,
                 pypath=None,
                 envs=None,
                 entry_script="python -u -m jaynes.entry", name=None,
                 docker_cmd="docker",
                 ipc=None,
                 tty=False,
                 gpu=0,
                 gpu_types=None,
                 gpu_limit=0,
                 post_script="",
                 net=None,
                 volumes=None,
                 cpu="50m", mem="50Mi",
                 cpu_limit=None, mem_limit=None,
                 restart_policy="Never",
                 backoff_limit=1,
                 ttl_seconds_after_finished=3600,
                 **options):
        super().__init__(mounts, work_dir, pypath, startup, entry_script, post_script)

        # self.mounts reuses the mounts from the Runner class
        init_containers = [m.init_container for m in self.mounts]
        volume_mounts = [m.volume_mount for m in self.mounts]

        self.is_gpu = options.get('gpus', None) or "nvidia" in docker_cmd

        if not gpu_limit:
            gpu_limit = gpu
        if not cpu_limit:
            cpu_limit = cpu
        if not mem_limit:
            mem_limit = mem

        # dynamically generate the job name to avoid conflict
        docker_container_name = name or f"jaynes-job-{datetime.utcnow():%H%M%S}-{jaynes.RUN.count}"

        self.container_template = {
            "name": docker_container_name,
            "image": image,
            "imagePullPolicy": image_pull_policy,
            "resources": {
                "requests": {"memory": mem, "cpu": cpu, "nvidia.com/gpu": gpu},
                "limits": {"memory": mem_limit, "cpu": cpu_limit, "nvidia.com/gpu": gpu_limit},
            },
            "volumeMounts": volume_mounts,
            "command": ["/bin/bash", "-c"],
        }
        if namespace:
            self.container_template["namespace"] = namespace
        if workdir:
            self.container_template["workingDir"] = workdir

        self.job_template = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            # reuse the container name for the job
            "metadata": {"name": docker_container_name},
            "spec": {
                "template": {
                    "spec": {
                        "volumes": volumes,
                        "initContainers": init_containers,
                        "containers": [],
                        "restartPolicy": restart_policy,
                    },

                },
                "backoffLimit": backoff_limit,
                "ttlSecondsAfterFinished": ttl_seconds_after_finished
            },
        }
        if image_pull_secret:
            self.job_template['spec']['template']['spec']["imagePullSecrets"] = [{"name": image_pull_secret}]

        if gpu_types is not None:
            affinity = {"nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [{
                        "matchExpressions": [{
                            "key": "nvidia.com/gpu.product",
                            "operator": "In",
                            "values": gpu_types.split(',')
                        }]
                    }]
                }
            }}
            self.job_template["spec"]["template"]["spec"]["affinity"] = affinity

    def build(self, fn, *args, __sep="\n", **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.main_script = self.main_script_thunk.format(JYNS_encoded_thunk=encoded_thunk)

        if self.job is None:
            self.job = deepcopy(self.job_template)

        container = deepcopy(self.container_template)
        container['command'].append(self.main_script)
        self.job['spec']['template']['spec']['containers'].append(container)

    def chain(self, fn, *args, __sep=" &\n", **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.main_script = self.main_script_thunk.format(JYNS_encoded_thunk=encoded_thunk)

        assert self.job is not None

        command_list = self.job['spec']['template']['spec']['containers'][-1]['command']

        if command_list[-1].endswith("& wait"):
            command_list[-1] = command_list[-1][:-6]

        command_list[-1] += "&\n" + self.main_script + "& wait"
