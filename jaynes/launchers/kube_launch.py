from datetime import datetime

import jaynes
from jaynes.launchers.base_launcher import Launcher
from jaynes.runners import Runner


class Kube(Launcher):
    jobs = None

    def __init__(
        self,
        namespace=None,
        verbose=False,
        name=None,
        tags={},
        **_,
    ):
        super().__init__(
            namespace=namespace,
            verbose=verbose,
            name=name or f"jaynes-job-{datetime.utcnow():%H%M%S}-{jaynes.RUN.count}",
            tags=tags,
            **_,
        )

        if self.jobs is None:
            self.jobs = []

    def add_runner(self, runner: Runner):
        """Adds a job/Pod to the list of jobs to launch"""
        super().add_runner(runner)
        # cache the launch config
        runner.launch_config = self.config.copy()

    # This packs the pod.
    def plan_instance(self, verbose=False):
        while self.last_runner:
            runner = self.runners.pop(-1)
            runner.job["metadata"]["namespace"] = runner.launch_config["namespace"]
            self.jobs.append(runner.job)

            if verbose:
                print(runner.job)

    def execute(self, verbose=None):
        import yaml

        self.plan_instance(verbose=verbose)

        from tempfile import NamedTemporaryFile

        # packing all jobs into one request and launch
        with NamedTemporaryFile(
            mode="w+",
            suffix="jaynes-kube.yaml",
            delete=not verbose,
        ) as config_file:
            yaml.dump_all(self.jobs, config_file, default_flow_style=False)

            self.jobs.clear()

            if verbose:
                print("dumping the kubernetes job yaml file to " + config_file.name)

            from subprocess import Popen, PIPE

            proc = Popen("kubectl apply -f " + config_file.name, shell=True, stdout=PIPE)
            outs = []
            while True:
                out = proc.stdout.read1().decode("utf-8")
                outs.append(out[:-8])
                print(out, end="")
                if out == "":
                    break
            return outs
