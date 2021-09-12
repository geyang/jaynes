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
    runner=templates.DockerRun("python:3.6",
                               pypath=":".join([m.pypath for m in J.mounts if hasattr(m, "pypath") and m.pypath]),
                               docker_startup_scripts=("pip install cloudpickle",),
                               docker_mount=" ".join([m.docker_mount for m in J.mounts]),
                               use_gpu=False).run(train, log_dir=RUN.log_dir)
)
J.run_local_setup(verbose=True)
J.make_host_script(log_dir=output_mount.remote_path, instance_name=RUN.instance_prefix, sudo=True,
                   terminate_after_finish=True)
J.launch_ssh(ip="34.217.66.113", pem="~/.ec2/ge-berkeley.pem", script_dir=output_mount.remote_path, verbose=True)
