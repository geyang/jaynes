# Jaynes, A Utility for training ML models on AWS with docker
<a href="figures/ETJaynes_defiant.jpg" target="_blank"><img src="figures/ETJaynes_defiant.jpg" alt="Defiant Jaynes" align="right" width="350px"></a>

## Todo

- [x] get the initial template to work

### Done

## Installation

```bash
pip install jaynes
```

## Usage (**Show me the Mo-NAY!! :moneybag::money_with_wings:**)

Check out the example folder for projects that you can run.


## Low-level Usage (Deprecated)

Take a look at the folder [test_projects/](test_projects/)! These project scripts are used for test and development, so
they should work out-of-the-box (if you have the right box ahem). 

### To run Local Docker

```python
from jaynes import Jaynes, templates
from main import train, RUN

S3_PREFIX = "s3://ge-bair/code/new-experiment/"
J = Jaynes(
    launch_log="jaynes_launch.log",
    mounts=[
        templates.S3Mount(local="./", s3_prefix=S3_PREFIX, pypath=True),
        templates.S3Mount(local="../../", s3_prefix=S3_PREFIX, pypath=True, file_mask="./__init__.py ./jaynes"),
        templates.S3UploadMount(docker_abs=RUN.log_dir, s3_prefix=S3_PREFIX, local=RUN.log_dir, sync_s3=True)
    ],
)
J.set_runner(
    docker=templates.DockerRun("python:3.6",
                               pypath=":".join([m.pypath for m in J.mounts if hasattr(m, "pypath") and m.pypath]),
                               docker_startup_scripts=("pip install cloudpickle",),
                               docker_mount=" ".join([m.docker_mount for m in J.mounts]),
                               use_gpu=False).run(train, log_dir=RUN.log_dir)
)
J.run_local_setup(verbose=True)
J.launch_local_docker(verbose=True, delay=30)
```

### To run on remote server with ssh

```python
from jaynes import Jaynes, templates
from main import train, RUN

S3_PREFIX = "s3://ge-bair/code/run_remote/"

output_mount = templates.S3UploadMount(docker_abs=RUN.log_dir, s3_prefix=S3_PREFIX, local=RUN.log_dir, sync_s3=True)

J = Jaynes(
    launch_log="jaynes_launch.log",
    mounts=[
        templates.S3Mount(local="./", s3_prefix=S3_PREFIX, pypath=True),
        templates.S3Mount(local="../../", s3_prefix=S3_PREFIX, pypath=True, file_mask="./__init__.py ./jaynes"),
        output_mount
    ],
)
J.set_runner(
    docker=templates.DockerRun("python:3.6",
                               pypath=":".join([m.pypath for m in J.mounts if hasattr(m, "pypath") and m.pypath]),
                               docker_startup_scripts=("pip install cloudpickle",),
                               docker_mount=" ".join([m.docker_mount for m in J.mounts]),
                               use_gpu=False).run(train, log_dir=RUN.log_dir)
)
J.run_local_setup(verbose=True)
J.make_launch_script(log_dir=output_mount.remote_abs, instance_tag=RUN.instance_prefix, sudo=True,
                     terminate_after_finish=True)
J.launch_ssh(ip_address="52.11.206.135", pem="~/.ec2/ge-berkeley.pem", script_dir=output_mount.remote_abs, verbose=True)
```


### To Launch EC2 instance and Run on Startup

make sure the instance terminate after docker run!

```python
from jaynes import Jaynes, templates
from main import train, RUN

S3_PREFIX = "s3://ge-bair/code/run_ssh/"

output_mount = templates.S3UploadMount(docker_abs=RUN.log_dir, s3_prefix=S3_PREFIX, local=RUN.log_dir, sync_s3=True)

J = Jaynes(
    launch_log="jaynes_launch.log",
    mounts=[
        templates.S3Mount(local="./", s3_prefix=S3_PREFIX, pypath=True),
        templates.S3Mount(local="../../", s3_prefix=S3_PREFIX, pypath=True, file_mask="./__init__.py ./jaynes"),
        output_mount
    ],
)
J.set_runner(
    docker=templates.DockerRun("python:3.6",
                               pypath=":".join([m.pypath for m in J.mounts if hasattr(m, "pypath") and m.pypath]),
                               docker_startup_scripts=("pip install cloudpickle",),
                               docker_mount=" ".join([m.docker_mount for m in J.mounts]),
                               use_gpu=False).run(train, log_dir=RUN.log_dir)
)
J.run_local_setup(verbose=True)
J.make_launch_script(log_dir=output_mount.remote_abs, instance_tag=RUN.instance_prefix, sudo=False,
                     terminate_after_finish=True)
J.launch_ec2(region="us-west-2", image_id="ami-bd4fd7c5", instance_type="p2.xlarge", key_name="ge-berkeley",
             security_group="torch-gym-prebuilt", spot_price=None,
             iam_instance_profile_arn="arn:aws:iam::055406702465:instance-profile/main", dry=False)
```

Jaynes does the following:

1. 

## To Develop

```bash
git clone https://github.com/episodeyang/jaynes.git
cd jaynes
make dev
```

To test, run

```bash
make test
```

This `make dev` command should build the wheel and install it in your current python environment. Take a look at the [./Makefile](./Makefile) for details.

**To publish**, first update the version number, then do:

```bash
make publish
```

## Acknowledgements

This code is inspired by @justinfu's [doodad](https://github.com/justinjfu/doodad), which is in turn built on top of Peter Chen's script.

This code is written from scratch to allow a more permissible open-source license (BSD). Go bears :bear: !!
