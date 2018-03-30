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
