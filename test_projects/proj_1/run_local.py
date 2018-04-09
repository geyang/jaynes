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
J.set_docker(
    docker=templates.DockerRun("python:3.6",
                               pypath=":".join([m.pypath for m in J.mounts if hasattr(m, "pypath") and m.pypath]),
                               docker_startup_scripts=("pip install cloudpickle",),
                               docker_mount=" ".join([m.docker_mount for m in J.mounts]),
                               use_gpu=False).run(train, log_dir=RUN.log_dir)
)
J.run_local_setup(verbose=True)
J.launch_local_docker(verbose=True, delay=30)
