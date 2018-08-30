import os
from textwrap import dedent
from uuid import uuid4

from jaynes.helpers import get_temp_dir
from jaynes.constants import JAYNES_PARAMS_KEY
from jaynes.param_codec import serialize
from os.path import join as pathJoin


class RemoteMount():
    def __init__(self, remote_abs, docker_abs, pypath=False):
        """Mount a directory on the remote instance to docker"""
        # remote_abs = remote if os.path.isabs(remote) else pathJoin(self.remote_cwd, remote)
        assert os.path.isabs(remote_abs), "remote path has to be absolute"
        assert os.path.isabs(docker_abs), "docker linked path has to be absolute"
        self.docker_mount = f"-v '{remote_abs}':'{docker_abs}'"
        self.pypath = docker_abs if pypath else None


class S3Mount:
    def __init__(self, local, s3_prefix, remote=None, remote_tar=None, docker=None, pypath=False, excludes=None,
                 file_mask=None, name=None, compress=True, public=True, no_signin=True):
        """
        Tars a local folder, uploads the content to S3, downloads the tar ball on the remote instance and mounts it
        in docker.
        
        :param name: the name for the tar ball. Default to {uuid4()}
        :param local: path to the local directory. Doesn't have to be absolute.
        :param s3_prefix: The s3 prefix including the s3: protocol, the bucket, and the path prefix.
        :param remote: The path on the remote instance. Default /tmp/{uuid4()}
        :param docker: The path for the docker instance. Can be something like /Users/ge/project-folder/blah
        :param pypath (bool): Whether this directory should be added to the python path
        :param excludes: The files paths to exclude, default to "--exclude='*__pycache__'"
        :param file_mask: The file mask for files to include. Default to "."
        :return: self
        """
        # I fucking hate the behavior of python defaults. -- GY
        file_mask = file_mask or "."  # file_mask can Not be None or "".
        excludes = excludes or "--exclude='*__pycache__' --exclude='*.git' --exclude='*.idea' --exclude='*.egg-info'"
        name = name or uuid4()
        tar_name = f"{name}.tar"
        self.temp_dir = get_temp_dir()
        local_tar = pathJoin(self.temp_dir, tar_name)
        assert os.path.isabs(local), 'local path must be absolute to avoid ambiguity.'
        local_abs = local
        if remote:
            assert os.path.isabs(remote), "remote path has to be absolute"
        docker_abs = os.path.abspath(docker) if docker else local_abs
        self.pypath = docker_abs if pypath else None
        self.local_script = f"""
                pwd &&
                mkdir -p '{self.temp_dir}'
                # Do not use absolute path in tar.
                tar {excludes} -c{"z" if compress else ""}f '{local_tar}' -C '{local_abs}' {file_mask}
                echo "uploading to s3"
                # aws s3 cp '{local_tar}' '{pathJoin(s3_prefix, tar_name)}' --only-show-errors
                aws s3 cp '{local_tar}' '{pathJoin(s3_prefix, tar_name)}' {'--acl public-read-write' if public else ''}
                """
        remote_tar = remote_tar or f"/tmp/{tar_name}"
        remote_abs = remote or f"/tmp/{name}"
        self.remote_setup = f"""
                aws s3 cp '{pathJoin(s3_prefix, tar_name)}' '{remote_tar}' {'--no-sign-request' if no_signin else ''}
                mkdir -p '{remote_abs}'
                tar -{"z" if compress else ""}xf '{remote_tar}' -C '{remote_abs}'
                """
        self.docker_mount = f"-v '{remote_abs}':'{docker_abs}'"


class S3UploadMount:
    def __init__(self, docker_abs, s3_prefix, remote_abs=None, name=None, local=None, interval=15,
                 pypath=False, sync_s3=True):
        """
        Mounting a remote directory to docker, and upload it's content periodically to s3.

        **To Avoid downloading to local during startup**: set local to None

        s3 path syntax:
                    {s3_prefix}{s3_dir}
        local path syntax:
                    file://{local}
        remote path syntax:
                    ssh://<remote>:{remote if isabs(remote) else remote_cwd + remote}
                note that the remote path is made absolute using the remote_cwd parameter

        :param remote_cwd:
        :param name:
        :param bucket:
        :param prefix:
        :param s3_prefix: Need slash at the end.
        :param local: When None, do not download those files
        :param remote:
        :param docker:
        :param interval:
        :param pypath:
        :param sync_s3:
        :return:
        """

        if remote_abs is None:
            remote_abs = f"/tmp/jaynes_mounts/{uuid4() if name is None else name}"
        else:
            assert os.path.isabs(remote_abs), "ATTENTION: remote_abs path has to be an absolute path."

        # used for getting the container log path
        self.remote_abs = remote_abs

        assert os.path.isabs(docker_abs), \
            "ATTENTION: docker path has to be absolute, to make sure your code knows where it is writing to."
        if local:
            download_script = f"""
                aws s3 cp --recursive {s3_prefix} '{local}' || echo "s3 bucket is EMPTY" """
            self.local_script = f"""
                mkdir -p '{local}'
                while true; do
                    echo "downloading..." {download_script}
                    sleep {interval}
                done & echo 'sync {local} initiated'
            """
        else:
            print('S3UploadMount(**{}) generated no local_script.'.format(locals()))
            # pass
        self.upload_script = f"""
                aws s3 cp --recursive '{remote_abs}' {s3_prefix} """  # --only-show-errors"""
        self.remote_setup = f"""
                echo 'making main_log directory {remote_abs}'
                mkdir -p '{remote_abs}'
                echo "made main_log directory" """ + ("" if not sync_s3 else f"""
                while true; do
                    echo "uploading..." {self.upload_script}
                    sleep {interval}
                done & echo "sync {remote_abs} initiated" 
                while true; do
                    if [ -z $(curl -Is http://169.254.169.254/latest/meta-data/spot/termination-time | head -1 | grep 404 | cut -d \  -f 2) ]
                    then
                        logger "Running shutdown hook." {self.upload_script}
                        break
                    else
                        # Spot instance not yet marked for termination. This is hoping that there's at least 3 seconds
                        # between when the spot instance gets marked for termination and when it actually terminates.
                        sleep 3
                    fi
                done & echo main_log sync initiated
                """)
        self.docker_mount = f"-v '{remote_abs}':'{docker_abs}'"
        self.pypath = docker_abs if pypath else None


class DockerRun:
    def __init__(self, docker_image, pypath="", docker_startup_scripts=None, docker_mount=None, cwd=None,
                 envs=None, name=None, use_gpu=False, ipc=None, tty=False):
        """

        :param docker_image:
        :param pypath:
        :param docker_startup_scripts:
        :param docker_mount:
        :param cwd:
        :param envs: Set of environment key and variables, a string
        :param name: Name of the docker container instance, use uuid if is None
        :param use_gpu:
        :type ipc: specify ipc for multiprocessing. Typically 'host'
        :param tty: almost never used. This is because when this script is ran, it is almost garanteed that the
                    ssh/bash session is not going to be tty.
        """
        self.run_script = None
        self.docker_image = docker_image
        cwd = cwd or os.getcwd()
        docker_cmd = "nvidia-docker" if use_gpu else "docker"
        entry_script = "python -u -m jaynes.entry"
        docker_startup_scripts = docker_startup_scripts or ('yes | pip install jaynes awscli',)
        cmd = f"""echo "Running in docker{' (gpu)' if use_gpu else ''}";""" \
              f"""{';'.join(docker_startup_scripts) + ';' if len(docker_startup_scripts) else ''}""" \
              f"""export PYTHONPATH=$PYTHONPATH:{pypath};""" \
              f"""{"cd '{}';".format(cwd) if cwd else ""}""" \
              f"pwd;" \
              f"""{JAYNES_PARAMS_KEY}={{encoded_thunk}} {entry_script}"""
        docker_container_name = name or uuid4()
        test_gpu = f"""
                echo 'Testing nvidia-smi inside docker'
                {envs if envs else ""} {docker_cmd} run --rm {docker_image} nvidia-smi
                """
        remove_by_name = f"""
                echo 'kill running instances'
                {docker_cmd} kill {docker_container_name}
                echo 'remove existing docker with name'
                {docker_cmd} rm {docker_container_name}""" if docker_container_name else ""
        ipc_config = f"--ipc={ipc} " if ipc else " "
        # note: always connect the docker to stdin and stdout.
        self.run_script_thunk = f"""
                {test_gpu if use_gpu else "" }
                {remove_by_name}
                {docker_cmd} info
                echo 'Now run docker'
                {envs if envs else ""} {docker_cmd} run -i{"t" if tty else ""} {ipc_config}{docker_mount} --name '{docker_container_name}' \\
                {docker_image} /bin/bash -c '{cmd}'
                """

    def run(self, fn, *args, **kwargs):
        encoded_thunk = serialize(fn, args, kwargs)
        self.run_script = self.run_script_thunk.format(encoded_thunk=encoded_thunk)
        return self


def ssh_remote_exec(user, ip_address, script_path, pem=None, sudo=True, remote_script_dir=None):
    """
    run script remotely via ssh agent

    :param user:
    :param ip_address:
    :param pem:
    :param script_path:
    :param sudo:
    :param remote_script_dir: path for the remote script to be scp'ed.
    :return:
    """
    # cmd = f"""plink root@MachineB -m local_script.sh"""  # windows
    # options = "-o 'StrictHostKeyChecking=no' -o 'PasswordAuthentication=no' -o 'ChallengeResponseAuthentication=no'"
    options = "-o 'StrictHostKeyChecking=no'"
    if sudo:
        # cmd = f"""ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem} ' if pem else ''}'echo \"rootpass\" | sudo -Sv && bash -s' < {script_path}"""
        # solution found: https://stackoverflow.com/questions/44916319/how-to-sudo-run-a-local-script-over-ssh
        # remote_script_dir = remote_script_dir or script_path
        # remote_directory = os.path.dirname(remote_script_dir)
        assert os.path.isabs(remote_script_dir), "remote_script_dir need to be absolute"
        remote_path = pathJoin(remote_script_dir, os.path.basename(script_path))
        send_file = \
            f"""ssh {options} {user}@{ip_address} {f'-i {pem}' if pem else ''} 'mkdir -p {remote_script_dir}'\n""" \
            f"""scp {f'-i {pem}' if pem else ''} {script_path} {user}@{ip_address}:{remote_script_dir}""",
        launch = f"""ssh {options} {user}@{ip_address} {f'-i {pem}' if pem else ''} 'sudo -n -s bash {remote_path}'"""
        return send_file, launch
    else:
        launch = f"""ssh {options} {user}@{ip_address} {f'-i {pem}' if pem else ''} 'bash -s' < {script_path}"""
        return None, launch
