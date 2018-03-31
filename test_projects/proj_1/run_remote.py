from jaynes import Jaynes
from main import LOG_DIR, train, abs_path

J = Jaynes(remote_cwd='/home/ubuntu/', bucket="ge-bair", prefix="jaynes-ssh-exec-test",  log=LOG_DIR + "/startup.log")
J.mount_s3(local="./", pypath=True)
J.mount_s3(local="../../", pypath=True, file_mask="""./__init__.py ./jaynes""")
J.mount_output(s3_dir=LOG_DIR, local=LOG_DIR, remote=LOG_DIR, docker=abs_path, s3_sync=True)
J.run_local(verbose=True)
J.setup_docker_run("thanard/matplotlib", docker_startup_scripts=("pip install cloudpickle",), use_gpu=True)
J.make_launch_script(train, a="hey", b=[0, 1, 2], log_dir=LOG_DIR, sudo=True, dry=True, verbose=True, terminate_after_finish=False)
J.run_ssh_remote(ip_address="54.200.170.99", pem="~/.ec2/ge-berkeley.pem", verbose=True)
