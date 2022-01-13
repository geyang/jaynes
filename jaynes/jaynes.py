import glob
import math
import os
import time
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import yaml
from termcolor import cprint

import jaynes.launchers
import jaynes.launchers.base_launcher
import jaynes.mounts
import jaynes.runners
from jaynes.helpers import cwd_ancestors, hydrate


class RUN:
    count = 0
    # This is the absolute path to the `.jaynes.yml` config file. Used to produce mount paths.
    config_root = None

    # default value for the run mode
    mode = None
    now = datetime.now()
    utcnow = datetime.utcnow()

    # @classmethod
    # def NOW(cls, fmt):
    #     from datetime import datetime
    #     return datetime.now().strftime(fmt)

    @classmethod
    def reset(cls):
        cls.__now = None


class Jaynes:
    verbose = None
    mounts = []
    launcher = None
    runner_config = None

    _raw_config = None
    _secret = None

    @classmethod
    def format_context(cls, config_root=None, **ext):
        try:
            with open(config_root + "/.secret.yml", 'r') as f:
                secret = yaml.safe_load(f)
        except FileNotFoundError:
            secret = dict()

        return dict(env=SimpleNamespace(**os.environ), now=RUN.now, uuid=uuid4(), RUN=RUN,
                    secret=SimpleNamespace(**secret), **ext)

    @classmethod
    def config_root(cls, config_path=None):
        if config_path is None:
            for d in cwd_ancestors():
                try:
                    config_path, = glob.glob(d + "/.jaynes.yml")
                    break
                except Exception:
                    pass

        if config_path is None:
            cprint('No `.jaynes.yml` is found. Run `jaynes.init` to create a configuration file.', "red")
            return

        return os.path.dirname(config_path), config_path

    @classmethod
    def raw_config(cls, config_path=None, ctx={}):
        if cls._raw_config:
            return cls._raw_config

        from inspect import isclass

        # add env class for interpolation
        yaml.SafeLoader.add_constructor("!ENV", hydrate(dict, ctx), )

        for k, c in jaynes.mounts.__dict__.items():
            if isclass(c):
                yaml.SafeLoader.add_constructor("!mounts." + k, hydrate(c, ctx), )

        for k, c in jaynes.runners.__dict__.items():
            if hasattr(c, 'from_yaml'):
                yaml.SafeLoader.add_constructor("!runners." + k, c.from_yaml)

        yaml.SafeLoader.add_constructor("!host", hydrate(lambda **args: args, ctx))

        with open(config_path, 'r') as f:
            raw = yaml.safe_load(f)

        # order or precendence: mode -> run -> root
        cls._raw_config = raw
        return raw

    host_unpacked = None

    _uploaded = []

    @classmethod
    def upload_mount(J, mounts, verbose=None, **host, ):
        for mount in mounts:
            if mount in J._uploaded:
                print('this package is already uploaded')
            else:
                J._uploaded.append(mount)
                mount.upload(verbose=verbose, **host)

    @classmethod
    def config(cls, mode=None, *, config_path=None, runner=None, host=None, launch=None, verbose=None,
               **ext):
        """
        Configuration function for Jaynes

        :param mode: the run mode you want to use, specified under the `modes` key inside your jaynes.yml config file
        :param config_path: the path to the configuration file. Allows you to use a custom configuration file
        :param runner: configuration for the runner, overwrites what's in the jaynes.yml file.
        :param host: configuration for the host machine, overwrites what's in the jaynes.yml file.
        :param launch: configuration for the `launch` function, overwrites what's in the jaynes.yml file
        :param ext: variables to pass into the string interpolation. Shows up directly as root-level variables in
                    the string interpolation context
        :return: None
        """
        from termcolor import cprint

        cprint(f"Launching {mode or '<default>'} mode", color="blue")

        RUN.config_root, config_path = cls.config_root(config_path)

        ctx = cls.format_context(RUN.config_root, **ext)
        config = cls.raw_config(config_path, ctx).copy()

        # saving so that ml-logger can use this
        cls.mode = mode
        if mode == 'local':
            cprint("running local mode", "green")
            return
        elif mode:
            modes = config.get('modes', {})
            config.update(modes[mode])
        else:
            run = config.get('run')
            assert run, "`run` field in .jaynes.yml can not be empty when using default config"
            config.update(run)

        if verbose is not None:
            cls.verbose = verbose
        elif cls.verbose is None:
            cls.verbose = config.get('verbose', None)

        if cls.runner_config is None:
            cls.runner_config = config['runner']
        if runner:
            Runner, runner_config = cls.runner_config
            local_copy = runner_config.copy()
            local_copy.update(runner)
            cls.runner_config = Runner, local_copy

        launch_config = config['launch'].copy()
        if launch:
            launch_config.update(launch)

        if cls.launcher is None:
            # launch_type = launch_config.pop("type")
            launch_type = launch_config["type"]
            # J.launcher = getattr(jaynes.launchers, launch_type)(**J.launch_config)
            cls.launcher = getattr(jaynes.launchers, launch_type)(**launch_config)

            cls.mounts = config.get('mounts', [])

            cls.upload_mount(**launch_config, mounts=cls.mounts, verbose=cls.verbose)
        else:
            # if cls.launcher.last_runner and cls.launcher.last_runner.chain is None:
            #     cls.launcher.plan_instance()
            cls.launcher.__init__(**launch_config)

    @classmethod
    def process_runner_config(cls):
        # config.RUNNER
        Runner, runner_kwargs = cls.runner_config
        # interpolation context
        context = cls.format_context(
            RUN.config_root,
            mounts=cls.mounts,
            run=SimpleNamespace(
                count=RUN.count,
                cwd=os.getcwd(),
                now=datetime.now(),
                uuid=uuid4(),
                # unclear if this is needed
                pypaths=SimpleNamespace(
                    host=":".join([m.host_path for m in cls.mounts if m.pypath]),
                    container=":".join([m.container_path for m in cls.mounts if m.pypath])
                )
            )
        )
        RUN.count += 1
        # todo: mapping current work directory correction on the remote instance.

        hydrated_runner_config = {}
        for k, v in runner_kwargs.items():
            if type(v) is str:
                try:
                    hydrated_runner_config[k] = v.format(**context)
                except IndexError as e:
                    a = '\n'
                    print(f"{k} '{v}' context: {list(context.items())}")
                    raise e
            else:
                hydrated_runner_config[k] = v
        if 'work_dir' not in hydrated_runner_config:
            hydrated_runner_config['work_dir'] = os.getcwd()

        return Runner, hydrated_runner_config

    @classmethod
    def add(cls, fn, *args, **kwargs, ):
        """
        Method for adding a runner.

        this is aware of the launch type"""

        if not cls.launcher:
            cls.config(cls.mode)

        if cls.launcher.last_runner:
            cls.launcher.plan_instance(cls.verbose)

        Runner, hydrated_config = cls.process_runner_config()

        runner = Runner(**hydrated_config, mounts=cls.mounts)
        runner.build(fn, *args, **kwargs)
        cls.launcher.add_runner(runner)

        return cls

    @classmethod
    def chain(cls, fn, *args, **kwargs):
        assert cls.launcher.last_runner, "launcher must already contain a runner"
        if cls.launcher.last_runner.chain is None:
            # In Docker for example, chaining should just add another runner.
            # return cls.add(fn, *args, **kwargs)
            if not cls.launcher:
                config()

            Runner, hydrated_config = cls.process_runner_config()

            runner = Runner(**hydrated_config, mounts=cls.mounts)
            runner.build(fn, *args, **kwargs)
            cls.launcher.add_runner(runner)

        else:
            Runner, hydrated_config = cls.process_runner_config()

            cls.launcher.last_runner.__init__(**hydrated_config)
            cls.launcher.last_runner.chain(fn, *args, **kwargs)

        return cls

    @classmethod
    def launch_instance(cls, verbose=None):
        """with GCP, this returns the request ID."""
        return cls.launcher.launch_instance(verbose=verbose or cls.verbose)

    @classmethod
    def execute(J, verbose=None):
        verbose = verbose or J.verbose
        J.launcher.setup_host(verbose=verbose)
        return J.launcher.execute(verbose=verbose)

    @classmethod
    def run(J, fn, *args, **kwargs, ):
        if J.mode == "local":
            return fn(*args, **kwargs)

        J.add(fn, *args, **kwargs)
        return J.execute()


def listen(timeout=None):
    """Just a for-loop, to keep ths process connected to the ssh session"""

    cprint('Jaynes pipe-back is now listening...', "blue")

    if timeout:
        time.sleep(timeout)
        cprint(f'jaynes.listen(timeout={timeout}) is now timed out. remote routine is still running.', 'green')
    else:
        while True:
            time.sleep(math.pi * 20)
            cprint('Listening to pipe back...', 'blue')


config = Jaynes.config
run = Jaynes.run
add = Jaynes.add
chain = Jaynes.chain
launch_instance = Jaynes.launch_instance
# plan = Jaynes.plan
execute = Jaynes.execute
