from datetime import datetime

import jaynes
from jaynes.launchers.base_launcher import Launcher, make_launch_script
from jaynes.runners import Runner


class Kube(Launcher):
    def __init__(self, namespace=None, verbose=False, name=None, tags={}, **_):
        super().__init__(namespace=namespace,
                         verbose=verbose,
                         name=name or f"jaynes-job-{datetime.utcnow():%H%M%S}-{jaynes.RUN.count}",
                         tags=tags, **_)
        self.jobs = []

    def add_runner(self, runner: Runner):
        """Adds a job/Pod to the list of jobs to launch"""
        super().add_runner(runner)
        # cache the launch config
        runner.launch_config = self.config.copy()

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
        with NamedTemporaryFile(mode="w+", suffix="jaynes-kube.yaml", delete=False) as config_file:
            yaml.dump_all(self.jobs, config_file, default_flow_style=False)
            if verbose:
                print('dumping the kubernetes job yaml file to ' + config_file.name)
            import os
            os.system(f"kubectl apply -f " + config_file.name)

        self.jobs.clear()
