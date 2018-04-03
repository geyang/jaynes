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

Take a look at the folder [test_projects/](test_projects/)! These project scripts are used for test and development, so
they should work out-of-the-box (if you have the right box ahem). 

### To run Local Docker

```python
import os
from jaynes import Jaynes
from main import LOG_DIR, train, abs_path

J = Jaynes(os.getcwd(), bucket="ge-bair", log=LOG_DIR + "/startup.log")
J.mount_s3(local="./", pypath=True)
J.mount_s3(local="../../", pypath=True, file_mask="""./__init__.py ./jaynes""")
J.mount_output(s3_dir=LOG_DIR, local=LOG_DIR, remote=LOG_DIR, docker=abs_path, sync_s3=False)
J.run_local()
J.setup_docker_run("python:3.6", docker_startup_scripts=("pip install cloudpickle",), use_gpu=False)
J.run_local_docker(train, a="hey", b=[0, 1, 2], log_dir=abs_path)
```

### To run on remote server with ssh

```python
from jaynes import Jaynes
from main import LOG_DIR, train, abs_path

J = Jaynes(remote_cwd='/home/ubuntu/', bucket="ge-bair", log=LOG_DIR + "/startup.log")
J.mount_s3(local="./", pypath=True)
J.mount_s3(local="../../", pypath=True, file_mask="""./__init__.py ./jaynes""")
J.mount_output(s3_dir=LOG_DIR, local=LOG_DIR, remote=LOG_DIR, docker=abs_path)
J.run_local(verbose=True)
J.setup_docker_run("thanard/matplotlib", docker_startup_scripts=("pip install cloudpickle",), use_gpu=True)
J.make_launch_script(train, a="hey", b=[0, 1, 2], log_dir=LOG_DIR, dry=True, verbose=True)
```


### To Launch EC2 instance and Run on Startup

make sure the instance terminate after docker run!

```python
from jaynes import Jaynes
from main import LOG_DIR, train, abs_path

J = Jaynes(remote_cwd='/home/ubuntu/', bucket="ge-bair", log=LOG_DIR + "/startup.log")
J.mount_s3(local="./", pypath=True)
J.mount_s3(local="../../", pypath=True, file_mask="""./__init__.py ./jaynes""")
J.mount_output(s3_dir=LOG_DIR, local=LOG_DIR, remote=LOG_DIR, docker=abs_path)
J.run_local(verbose=True)
J.setup_docker_run("thanard/matplotlib", docker_startup_scripts=("pip install cloudpickle",), use_gpu=True)
J.make_launch_script(train, a="hey", b=[0, 1, 2], log_dir=LOG_DIR, dry=True, verbose=True, terminate_after_finish=True)
J.launch_and_run(region="us-west-2", image_id="ami-bd4fd7c5", instance_type="t2.micro", key_name="ge-berkeley",
                 security_group="torch-gym-prebuilt", is_spot_instance=True, spot_price=0.004,
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
