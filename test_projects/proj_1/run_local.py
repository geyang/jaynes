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
# print(J.run_local(dry=False))
# print(J.make_launch_script(docker_image="python:3.6", dry=True))

# J.apply()
