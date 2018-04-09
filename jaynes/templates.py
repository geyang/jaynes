import os
import tempfile
from textwrap import dedent

import uuid

from jaynes.helpers import get_temp_dir
from jaynes.constants import JAYNES_PARAMS_KEY
from jaynes.param_codec import serialize


class RemoteMount():
    def __init__(self, remote_abs, docker, docker_abs=None, pypath=False):
        """Mount a directory on the remote instance to docker"""
        # remote_abs = remote if os.path.isabs(remote) else os.path.join(self.remote_cwd, remote)
        assert os.path.isabs(remote_abs), "remote path has to be absolute"
        docker_abs = docker_abs or os.path.abspath(docker)
        self.docker_mount = f"-v '{remote_abs}':'{docker_abs}'"
        self.pypath = docker_abs if pypath else None


class S3Mount:
    def __init__(self, local, s3_prefix, remote=None, remote_tar=None, docker=None, pypath=False, file_mask="."):
        """
        Tars a local folder, uploads the content to S3, downloads the tar ball on the remote instance and mounts it
        in docker.
        :param local:
        :param s3_prefix:
        :param remote:
        :param docker:
        :param pypath:
        :param file_mask:
        :return:
        """
        temp_basename = uuid.uuid4()
        temp_filename = f"{temp_basename}.tar"
        temp_dir = get_temp_dir()
        local_tar = os.path.join(temp_dir, temp_filename)
        local_abs = os.path.abspath(local)
        if remote:
            assert os.path.isabs(remote), "remote path has to be absolute"
        docker_abs = os.path.abspath(docker) if docker else local_abs
        self.pypath = docker_abs if pypath else None
        self.local_script = f"""
                pwd &&
                mkdir -p {temp_dir}
                # Do not use absolute path in tar.
                tar czf {local_tar} -C "{local_abs}" {file_mask}
                echo "uploading to s3"
                aws s3 cp {local_tar} {s3_prefix}{temp_filename} 
                """
        remote_tar = remote_tar or f"/tmp/{temp_filename}"
        remote_abs = remote or f"/tmp/{temp_basename}"
        self.remote_setup = f"""
                aws s3 cp {s3_prefix}{temp_filename} {remote_tar}
                mkdir -p {remote_abs}
                tar -zxf {remote_tar} -C {remote_abs}
                """
        self.docker_mount = f"-v '{remote_abs}':'{docker_abs}'"


class S3UploadMount:
    def __init__(self, docker_abs, s3_prefix, remote_abs=None, local=None, interval=15, pypath=False, sync_s3=True):
        """
        Mounting a remote directory to docker, and upload it's content periodically to s3.

        s3 path syntax:
                    {s3_prefix}{s3_dir}
        local path syntax:
                    file://{local}
        remote path syntax:
                    ssh://<remote>:{remote if isabs(remote) else remote_cwd + remote}
                note that the remote path is made absolute using the remote_cwd parameter
        :param remote_cwd:
        :param bucket:
        :param prefix:
        :param s3_prefix: Need slash at the end.
        :param local:
        :param remote:
        :param docker:
        :param interval:
        :param pypath:
        :param sync_s3:
        :return:
        """

        if remote_abs is None:
            remote_abs = f"/tmp/jaynes_mounts/{uuid.uuid4()}"
        else:
            assert os.path.isabs(remote_abs), "ATTENTION: remote_abs path has to be an absolute path."

        # used for getting the container log path
        self.remote_abs = remote_abs

        assert os.path.isabs(docker_abs), \
            "ATTENTION: docker path has to be absolute, to make sure your code knows where it is writing to."
        if local:
            download_script = f"""
                aws s3 cp --recursive {s3_prefix} {local} || echo "s3 bucket is EMPTY" """
            self.local_script = f"""
                mkdir -p {local}
                while true; do
                    echo "downloading..." {download_script}
                    sleep {interval}
                done & echo "sync {local} initiated"
            """
        self.upload_script = f"""
                aws s3 cp --recursive {remote_abs} {s3_prefix} """
        self.remote_setup = f"""
                echo "making main_log directory {remote_abs}"
                mkdir -p {remote_abs}
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
                 use_gpu=False):
        self.run_script = None
        self.docker_image = docker_image
        cwd = cwd or os.getcwd()
        docker_cmd = "nvidia-docker" if use_gpu else "docker"
        entry_script = "python -u -m jaynes.entry"
        docker_startup_scripts = docker_startup_scripts or ()
        cmd = f"""echo "Running in docker{' (gpu)' if use_gpu else ''}";""" \
              f"""{';'.join(docker_startup_scripts) + ';' if len(docker_startup_scripts) else ''}""" \
              f"""export PYTHONPATH=$PYTHONPATH{pypath};""" \
              f"""{"cd '{}';".format(cwd) if cwd else ""}""" \
              f"""{JAYNES_PARAMS_KEY}={{encoded_thunk}} {entry_script}"""
        docker_container_name = uuid.uuid4()
        test_gpu = f"""
                echo 'Testing nvidia-smi inside docker'
                {docker_cmd} run --rm {docker_image} nvidia-smi
                """
        self.run_script_thunk = f"""
                {test_gpu if use_gpu else "" }
                
                echo 'Now run docker'
                {docker_cmd} run {docker_mount} --name {docker_container_name} \\
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
    if sudo:
        # cmd = f"""ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem} ' if pem else ''}'echo \"rootpass\" | sudo -Sv && bash -s' < {script_path}"""
        # solution found: https://stackoverflow.com/questions/44916319/how-to-sudo-run-a-local-script-over-ssh
        # remote_script_dir = remote_script_dir or script_path
        # remote_directory = os.path.dirname(remote_script_dir)
        assert os.path.isabs(remote_script_dir), "remote_script_dir need to be absolute"
        remote_path = os.path.join(remote_script_dir, os.path.basename(script_path))
        cmd = f"""
            ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem}' if pem else ''} 'mkdir -p {remote_script_dir}'
            scp {f'-i {pem}' if pem else ''} {script_path} {user}@{ip_address}:{remote_script_dir}
            ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem}' if pem else ''} 'sudo -n -s bash {remote_path}'"""
    else:
        cmd = f"""ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem}' if pem else ''} 'bash -s' < {script_path}"""
    return dedent(cmd)
