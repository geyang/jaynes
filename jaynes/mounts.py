import os
from os.path import join as pathJoin
from textwrap import dedent
from uuid import uuid4

from jaynes.shell import ck

from .helpers import get_temp_dir


class Mount:
    local_script = None

    def upload(self, verbose=None, **_):
        if self.local_script is None:
            return
        assert not ck(dedent(self.local_script or ""), verbose=verbose, shell=True)


class Simple(Mount):
    """Mount a directory from the remote host to docker

    :param host_path: path on the host
    :param container_path: path inside the container
    :param pypath: boolean flag for whether this mount point should be included in the PYPATH environment variable
    """

    def __init__(self, host_path, container_path, pypath=False):
        # host_path = remote if os.path.isabs(remote) else pathJoin(self.remote_cwd, remote)
        assert os.path.isabs(host_path), "remote path has to be absolute"
        assert os.path.isabs(container_path), "docker linked path has to be absolute"
        self.docker_mount = f"-v '{host_path}':'{container_path}'"
        self.host_path = host_path
        self.container_path = container_path
        self.pypath = pypath


class S3Code(Mount):
    """
    Tars a local folder, uploads the content to S3, downloads the tar ball on the remote instance and mounts it
    in docker.

    To configure in the yaml file, you can do:

    .. code:: yaml

        mounts: # mount configurations Available keys: NOW, UUID,
        - !mounts.S3Code &code_mount
          s3_prefix: s3://ge-bair/jaynes-debug
          local_path: .
          host_path: /home/ubuntu/jaynes-mounts/{now:%Y-%m-%d}/{now:%H%M%S.%f}
          # container_path: /Users/geyang/learning-to-learn
          pypath: true
          excludes: "--exclude='*__pycache__' --exclude='*.git' --exclude='*.idea' --exclude='*.egg-info' --exclude='*.pkl'"
          compress: true
        - !mounts.S3Code &fair_code_mount
          s3_prefix: s3://ge-bair/jaynes-debug
          local_path: .
          host_path: /private/home/geyang/jaynes-mounts/{now:%Y-%m-%d}/{now:%H%M%S.%f}
          pypath: true
          excludes: "--exclude='*__pycache__' --exclude='*.git' --exclude='*.idea' --exclude='*.egg-info' --exclude='*.pkl'"
          compress: true


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

    def __init__(self, *, s3_prefix, local_path, host_path=None, remote_tar=None,
                 container_path=None, pypath=False, excludes=None, file_mask=None,
                 name=None, compress=True, no_signin=False, acl=None, region=None):
        # I fucking hate the behavior of python defaults. -- GY
        file_mask = file_mask or "."  # file_mask can Not be None or "".
        excludes = excludes or "--exclude='*__pycache__' --exclude='*.git' --exclude='*.idea' --exclude='*.egg-info'"
        name = name or uuid4()
        tar_name = f"{name}.tar"
        self.temp_dir = get_temp_dir()
        local_tar = pathJoin(self.temp_dir, tar_name)
        from .jaynes import RUN
        local_abs = os.path.join(RUN.project_root, local_path)
        if not host_path:
            host_path = f"/tmp/{name}"

        from .jaynes import RUN
        docker_abs = os.path.join(RUN.project_root, container_path) if container_path else local_abs
        self.local_script = f"""
                type gtar >/dev/null 2>&1 && alias tar=`which gtar`
                mkdir -p {self.temp_dir}
                # Do not use absolute path in tar.
                tar {excludes} -c{"z" if compress else ""}f {local_tar} -C {local_abs} {file_mask}
                aws s3 cp {local_tar} {s3_prefix}/{tar_name} {'--acl {}'.format(acl) if acl else ''} {'--region {}'.format(region) if region else ''}
                """
        remote_tar = remote_tar or f"/tmp/{tar_name}"
        self.host_path = host_path
        self.host_setup = f"""
                aws s3 cp {pathJoin(s3_prefix, tar_name)} {remote_tar} {'--no-sign-request' if no_signin else ''}
                mkdir -p {host_path}
                tar -{"z" if compress else ""}xf {remote_tar}{tar_name if remote_tar.endswith('/') else ""} -C {host_path}
                """
        self.pypath = pypath
        self.container_path = docker_abs
        self.docker_mount = f"-v {host_path}:{docker_abs}"


class S3Output(Mount):
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

    def __init__(self, *, container_path, s3_prefix, host_path=None, name=None, local_path=None, interval=15,
                 pypath=False, sync_s3=True):

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
                aws s3 cp --recursive {s3_prefix} {local_path} || echo "s3 bucket is EMPTY" """
            self.local_script = f"""
                mkdir -p {local_path}
                while true; do
                    echo "downloading..." {download_script}
                    {f"sleep {interval}" if interval else ""}
                done & echo 'sync {local_path} initiated'
            """
        else:
            print('S3UploadMount(**{}) generated no local_script.'.format(locals()))
            # pass
        self.upload_script = f"""
                aws s3 cp --recursive {host_path} {s3_prefix} """  # --only-show-errors"""
        self.host_setup = f"""
                echo 'making main_log directory {host_path}'
                mkdir -p {host_path}
                echo "made main_log directory" """ + ("" if not sync_s3 else f"""
                while true; do
                    echo "uploading..." {self.upload_script}
                    {f"sleep {interval}" if interval else ""}
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
        self.docker_mount = f"-v {host_path}:{container_path}"
        self.container_path = container_path
        self.pypath = pypath


# New
class SSHCode(Mount):
    """
    Tars a local folder, uploads the content to S3, downloads the tar ball on the remote instance and mounts it
    in docker.


    :param profile: The profile to use for untaring the code ball. Not used.
    :param password: The password to use for untaring the code ball. Not used.
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

    def __init__(self, *, local_path=None, local_tar=None, host_path=None, remote_tar=None,
                 container_path=None, pypath=False, excludes=None, file_mask=None, name=None,
                 compress=True):

        # I fucking hate the behavior of python defaults. -- GY
        self.local_path = local_path
        self.host_path = host_path
        self.container_path = container_path or host_path
        self.pypath = pypath
        self.name = name
        self.compress = compress

        self.excludes = excludes or "--exclude='*__pycache__' --exclude='*.git' --exclude='*.idea' --exclude='*.egg-info'"
        self.file_mask = file_mask or "."  # file_mask can Not be None or "".

        if local_tar is None:
            name = name or uuid4()
            tar_name = f"{name}.tar"
            self.temp_dir = get_temp_dir()
            self.local_tar = pathJoin(self.temp_dir, tar_name)
        else:
            tar_name = os.path.basename(local_tar)
            self.temp_dir = os.path.dirname(local_tar)
            self.local_tar = local_tar

        from .jaynes import RUN
        local_abs = os.path.join(RUN.project_root, local_path)
        self.container_path = os.path.join(RUN.project_root, container_path) if container_path else local_abs

        self.remote_tar = remote_tar or f"/tmp/{tar_name}"

        self.tar_script = f"""
                type gtar >/dev/null 2>&1 && alias tar=`which gtar`
                mkdir -p {self.temp_dir}
                # Do not use absolute path in tar.
                tar {self.excludes} -c{"z" if self.compress else ""}f {self.local_tar} -C {local_abs} {self.file_mask}
                """

        self.host_setup = f"""
                mkdir -p {self.host_path}
                tar -{"z" if self.compress else ""}xf {self.remote_tar}{tar_name if self.remote_tar.endswith('/') else ''} -C {self.host_path}
                """
        # used by the docker runner
        self.docker_mount = f"-v {self.host_path}:{self.container_path}"

    def upload(self, verbose=None, *, username, ip, pem=None, port=None, password=None, profile=None, **_):
        _port = "" if port is None else f"-p {port}"
        _pem = "" if pem is None else f"-i {pem}"

        ssh_string = f"ssh {_port} {_pem}" if _port or _pem else 'ssh'
        mkdir_script = f"{ssh_string} {username}@{ip} mkdir -p {os.path.dirname(self.remote_tar)}"
        rsync_script = f"rsync -az -e '{ssh_string}' {self.local_tar} {username}@{ip}:{self.remote_tar}"
        if password is not None:  # note: now supports password log in!
            # rsync_script = f'expect <<EOF\nspawn {rsync_script};expect \"password:\";send \"{password}\\r\"\nEOF'
            # need to install sshpass from:
            # https://gist.github.com/arunoda/7790979
            mkdir_script = f"sshpass -p '{password}' {mkdir_script}"
            rsync_script = f"sshpass -p '{password}' {rsync_script}"

        # # scp does not allow file rename.
        # remote_tar_dir = os.path.dirname(remote_tar)
        # scp_script = f"scp {port_.upper()} {pem} {self.local_tar} {username}@{ip}:{remote_tar_dir}"

        self.local_script = dedent(self.tar_script) + mkdir_script + "\n" + rsync_script + "\n"

        return super().upload(verbose=verbose)


class TarMount(Mount):
    tar_path = None
    host_path = None

    def __init__(self, *_, local_path, local_tar=None, remote_tar=None, host_path=None, container_path=None,
                 pypath=False, name=None, excludes=None, file_mask=None, compress=True):
        self.local_path = local_path
        self.host_path = host_path
        self.container_path = container_path or host_path
        self.pypath = pypath
        self.name = name
        self.compress = compress

        self.file_mask = file_mask or "."  # file_mask can Not be None or "".
        self.excludes = excludes or "--exclude='*__pycache__' --exclude='*.git' --exclude='*.idea' --exclude='*.egg-info'"

        if local_tar is None:
            name = name or uuid4()
            tar_name = f"{name}.tar"
            self.temp_dir = get_temp_dir()
            self.local_tar = pathJoin(self.temp_dir, tar_name)
        else:
            tar_name = os.path.basename(local_tar)
            self.temp_dir = os.path.dirname(local_tar)
            self.local_tar = local_tar

        from .jaynes import RUN
        local_abs = os.path.join(RUN.project_root, local_path)

        self.remote_tar = remote_tar or f"$TMPDIR/{tar_name}"

        self.local_script = f"""
                type gtar >/dev/null 2>&1 && alias tar=`which gtar`
                mkdir -p {self.temp_dir}
                # Do not use absolute path in tar.
                tar {self.excludes} -c{"z" if compress else ""}f {self.local_tar} -C {local_abs} {self.file_mask}
                """
        self.host_setup = f"""
                mkdir -p {host_path}
                tar -{"z" if compress else ""}xf {self.remote_tar} -C {host_path}
                """

    def upload(self, verbose=None, *, host, user=None, token=None, **_):
        from jaynes.client import JaynesClient

        if os.path.exists(self.local_tar):
            print('local tar already exists', self.local_tar)
        else:
            script = dedent(self.local_script)
            ck(script, verbose=verbose, shell=True)

        parent_dir = os.path.dirname(self.remote_tar)
        tar_name = os.path.basename(self.remote_tar)

        client = JaynesClient(host, token=token)

        # grep to speed up transmission
        stdout, *_ = client.execute(f"ls {parent_dir} | grep {tar_name}")
        print(stdout, *_)
        r = client.execute(f"ls {parent_dir} | grep {tar_name}")
        print(r)
        if tar_name in r[1]:
            print('remote tar already exists', self.remote_tar)
        else:
            client.execute(f"mkdir -p {parent_dir}")
            client.upload_file(self.local_tar, self.remote_tar)

            stdout, *_ = client.execute(f"echo {parent_dir}")
            if verbose:
                print(stdout, parent_dir, self.remote_tar, )
            stdout, *_ = client.execute(f"ls {parent_dir} | grep {tar_name}")
            assert tar_name in stdout, "file upload failed" + stdout
