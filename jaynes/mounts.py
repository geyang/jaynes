import os
from uuid import uuid4

from jaynes.helpers import get_temp_dir
from os.path import join as pathJoin


class Simple:
    def __init__(self, host_path, container_path, pypath=False):
        """Mount a directory from the remote host to docker"""
        # host_path = remote if os.path.isabs(remote) else pathJoin(self.remote_cwd, remote)
        assert os.path.isabs(host_path), "remote path has to be absolute"
        assert os.path.isabs(container_path), "docker linked path has to be absolute"
        self.docker_mount = f"-v '{host_path}':'{container_path}'"
        self.host_path = host_path
        self.container_path = container_path
        self.pypath = pypath


class S3Code:
    def __init__(self, *, s3_prefix, local_path, host_path=None, remote_tar=None, container_path=None, pypath=False,
                 excludes=None, file_mask=None, name=None, compress=True, public=True, no_signin=True):
        """
        Tars a local folder, uploads the content to S3, downloads the tar ball on the remote instance and mounts it
        in docker.
        
        :param local_path: path to the local directory. Doesn't have to be absolute.
        :param s3_prefix: The s3 prefix including the s3: protocol, the bucket, and the path prefix.
        :param host_path: The path on the remote instance. Default /tmp/{uuid4()}
        :param name: the name for the tar ball. Default to {uuid4()}
        :param container_path: The path for the docker instance. Can be something like /Users/ge/project-folder/blah
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
        # assert os.path.isabs(local_path), 'local_path path must be absolute, resolved outside.'
        local_abs = os.path.abspath(local_path)
        if host_path:
            assert os.path.isabs(host_path), "host_path path has to be absolute"
        else:
            host_path = f"/tmp/{name}"
        docker_abs = os.path.abspath(container_path) if container_path else local_abs
        self.local_script = f"""
                pwd &&
                mkdir -p '{self.temp_dir}'
                # Do not use absolute path in tar.
                tar {excludes} -c{"z" if compress else ""}f '{local_tar}' -C '{local_abs}' {file_mask}
                # aws s3 cp '{local_tar}' '{s3_prefix}/{tar_name}' --only-show-errors
                aws s3 cp '{local_tar}' '{s3_prefix}/{tar_name}' {'--acl public-read-write' if public else ''}
                """
        remote_tar = remote_tar or f"/tmp/{tar_name}"
        self.host_path = host_path
        self.host_setup = f"""
                aws s3 cp '{pathJoin(s3_prefix, tar_name)}' '{remote_tar}' {'--no-sign-request' if no_signin else ''}
                mkdir -p '{host_path}'
                tar -{"z" if compress else ""}xf '{remote_tar}' -C '{host_path}'
                """
        self.pypath = pypath
        self.container_path = docker_abs
        self.docker_mount = f"-v '{host_path}':'{docker_abs}'"


class S3Output:
    def __init__(self, *, container_path, s3_prefix, host_path=None, name=None, local_path=None, interval=15,
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

        :param name:
        :param s3_prefix: Need slash at the end.
        :param local_path: When None, do not download those files
        :param interval:
        :param pypath:
        :param sync_s3:
        :return:
        """

        if host_path is None:
            host_path = f"/tmp/jaynes_mounts/{uuid4() if name is None else name}"
        else:
            assert os.path.isabs(host_path), "ATTENTION: host_path path has to be an absolute path."

        # used for getting the container log path
        self.host_path = host_path

        assert os.path.isabs(container_path), \
            "ATTENTION: docker path has to be absolute, to make sure your code knows where it is writing to."
        if local_path:
            download_script = f"""
                aws s3 cp --recursive {s3_prefix} '{local_path}' || echo "s3 bucket is EMPTY" """
            self.local_script = f"""
                mkdir -p '{local_path}'
                while true; do
                    echo "downloading..." {download_script}
                    sleep {interval}
                done & echo 'sync {local_path} initiated'
            """
        else:
            print('S3UploadMount(**{}) generated no local_script.'.format(locals()))
            # pass
        self.upload_script = f"""
                aws s3 cp --recursive '{host_path}' {s3_prefix} """  # --only-show-errors"""
        self.host_setup = f"""
                echo 'making main_log directory {host_path}'
                mkdir -p '{host_path}'
                echo "made main_log directory" """ + ("" if not sync_s3 else f"""
                while true; do
                    echo "uploading..." {self.upload_script}
                    sleep {interval}
                done & echo "sync {host_path} initiated" 
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
        self.docker_mount = f"-v '{host_path}':'{container_path}'"
        self.container_path = container_path
        self.pypath = pypath
