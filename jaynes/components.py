import os
import tempfile
from textwrap import dedent

import uuid

from jaynes.helpers import path_no_ext
from jaynes.constants import JAYNES_PARAMS_KEY


def s3_mount(bucket, prefix, local, remote=None, docker=None, pypath=False, file_mask="."):
    with tempfile.NamedTemporaryFile('wb+', suffix='.tar') as tf:
        temp_path = tf.name
    temp_dir = os.path.dirname(temp_path)
    temp_filename = os.path.basename(temp_path)
    remote = remote if remote else path_no_ext(f"/tmp/{temp_filename}")
    docker = docker if docker else remote
    abs_local = os.path.abspath(local)
    abs_remote = os.path.abspath(remote)
    abs_docker = os.path.abspath(docker)
    local_script = f"""
            pwd &&
            mkdir -p {temp_dir}
            # Do not use absolute path in tar.
            tar czf {temp_path} -C "{abs_local}" {file_mask}
            echo "uploading to s3"
            aws s3 cp {temp_path} s3://{bucket}/{prefix}/{temp_filename} 
            """
    remote_tar = f"/tmp/{temp_filename}"
    remote_script = f"""
            aws s3 cp s3://{bucket}/{prefix}/{temp_filename} {remote_tar}
            mkdir -p {remote}
            tar -zxf {remote_tar} -C {remote}
            """
    docker_mount = f"-v '{abs_remote}':'{abs_docker}'"
    return local_script, remote_script, docker_mount, abs_docker if pypath else None


def output_mount(remote_cwd, bucket, prefix, s3_dir, local=None, remote=None, docker=None, interval=15, pypath=False,
                 sync_s3=True):
    """
    s3 path syntax:
                s3://{bucket}/{prefix}/{s3_dir}
    local path syntax:
                file://{local}
    remote path syntax:
                ssh://<remote>:{remote if isabs(remote) else remote_cwd + remote}
            note that the remote path is made absolute using the remote_cwd parameter
    :param remote_cwd:
    :param bucket:
    :param prefix:
    :param s3_dir:
    :param local:
    :param remote:
    :param docker:
    :param interval:
    :param pypath:
    :param sync_s3:
    :return:
    """
    remote = remote or local
    abs_remote = remote if os.path.isabs(remote) else os.path.join(remote_cwd, remote)
    assert os.path.isabs(abs_remote), "ATTENTION: remote_cwd + remote has to be an absolute path."
    assert os.path.isabs(docker), \
        "ATTENTION: docker path has to be absolute, to make sure your code knows where it is writing to."
    download_script = "" if local is None else f"""
                aws s3 cp --recursive s3://{bucket}/{prefix}/{s3_dir} {local} || echo "s3 bucket is EMPTY" """
    local_script = "" if local is None else f"""
            mkdir -p {local}
            while true; do
                echo "downloading..." {download_script}
                sleep {interval}
            done & echo "sync {local} initiated"
    """
    upload_script = f"""
                aws s3 cp --recursive {abs_remote} s3://{bucket}/{prefix}/{s3_dir} """
    remote_script = f"""
            echo "making main_log directory {abs_remote}"
            mkdir -p {abs_remote}
            echo "made main_log directory" """ + ("" if not sync_s3 else f"""
            while true; do
                echo "uploading..." {upload_script}
                sleep {interval}
            done & echo "sync {abs_remote} initiated" 
            while true; do
                if [ -z $(curl -Is http://169.254.169.254/latest/meta-data/spot/termination-time | head -1 | grep 404 | cut -d \  -f 2) ]
                then
                    logger "Running shutdown hook." {upload_script}
                    break
                else
                    # Spot instance not yet marked for termination. This is hoping that there's at least 3 seconds
                    # between when the spot instance gets marked for termination and when it actually terminates.
                    sleep 3
                fi
            done & echo main_log sync initiated
            """)
    docker_mount = f"-v '{abs_remote}':'{docker}'"
    return local_script, remote_script, docker_mount, upload_script, docker if pypath else None


def docker_run(docker_image, pypath="", docker_startup_scripts=None, cwd=None, use_gpu=False):
    docker_cmd = "nvidia-docker" if use_gpu else "docker"
    entry_script = "python -u -m jaynes.entry"
    docker_startup_scripts = docker_startup_scripts if docker_startup_scripts else ()
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
    run_script = f"""
            {test_gpu if use_gpu else "" }
            
            echo 'Now run docker'
            {docker_cmd} run {{docker_mount}} --name {docker_container_name} \\
            {docker_image} /bin/bash -c '{cmd}'
            """
    return run_script


def ssh_remote_exec(user, ip_address, script, log_dir, pem=None, sudo=True):
    """
    run script remotely via ssh agent
    :param user:
    :param ip_address:
    :param pem:
    :param script:
    :param sudo:
    :return:
    """
    # cmd = f"""plink root@MachineB -m local_script.sh"""  # windows
    if sudo:
        # cmd = f"""ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem} ' if pem else ''}'echo \"rootpass\" | sudo -Sv && bash -s' < {script}"""
        # solution found: https://stackoverflow.com/questions/44916319/how-to-sudo-run-a-local-script-over-ssh
        # log_dir = log_dir or script
        # remote_directory = os.path.dirname(log_dir)
        assert os.path.isabs(log_dir), "log_dir need to be absolute"
        remote_path = os.path.join(log_dir, os.path.basename(script))
        cmd = f"""
            ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem}' if pem else ''} 'mkdir -p {log_dir}'
            scp {f'-i {pem}' if pem else ''} {script} {user}@{ip_address}:{log_dir}
            ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem}' if pem else ''} 'sudo -n -s bash {remote_path}'"""
    else:
        cmd = f"""ssh -o StrictHostKeyChecking=no {user}@{ip_address} {f'-i {pem}' if pem else ''} 'bash -s' < {script}"""
    return dedent(cmd)
