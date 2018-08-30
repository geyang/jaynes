import base64
import os
import tempfile

import uuid
from textwrap import dedent

from .helpers import get_temp_dir
from .templates import ssh_remote_exec, DockerRun
from .shell import ck, popen


class Jaynes:
    def __init__(self, launch_log=None, error_log=None, mounts=None, docker=None):
        self.launch_log = launch_log or "jaynes_launch.log"
        self.error_log = error_log or "jaynes_launch.err.log"
        self.mounts = mounts or []
        self.set_docker(docker)

    def set_docker(self, docker):
        self.docker: DockerRun = docker

    def mount(self, *mounts):
        self.mounts.extend(mounts)

    def run_local_setup(self, verbose=False, dry=False):
        cmd = '\n'.join([m.local_script for m in self.mounts if hasattr(m, "local_script") and m.local_script])
        if dry:
            return cmd
        else:
            ck(cmd, verbose=verbose, shell=True)
            return self

    def launch_local_docker(self, log_dir=None, delay=None, verbose=False, dry=False):
        # the log_dir is primarily used for the run script. Therefore it should use ued here instead.
        if log_dir is None:
            log_dir = get_temp_dir()  # this is always absolute
        log_path = os.path.join(log_dir, self.launch_log)
        error_path = os.path.join(log_dir, self.error_log)

        upload_script = '\n'.join(
            [m.upload_script for m in self.mounts if hasattr(m, "upload_script") and m.upload_script]
        )
        remote_setup = "\n".join(
            [m.remote_setup for m in self.mounts if hasattr(m, "remote_setup") and m.remote_setup]
        )

        remote_script = f"""
        #!/bin/bash
        # to allow process substitution
        set +o posix
        mkdir -p {log_dir}
        {{
            # clear main_log
            truncate -s 0 {log_path}
            truncate -s 0 {error_path}
            
            # remote_setup
            {remote_setup}
            # upload_script
            {upload_script}
            # sudo service docker start
            # pull docker
            docker pull {self.docker.docker_image}
            # run docker
            {self.docker.run_script}
            
            # Now sleep before ending this script
            sleep {delay}
        }} > >(tee -a {log_path}) 2> >(tee -a {error_path} >&2)
        """
        if verbose:
            print(remote_script)
        if not dry:
            ck(remote_script, shell=True)
        return self

    def make_launch_script(self, log_dir, sudo=False, terminate_after_finish=False, delay=None,
                           instance_tag=None, region=None):
        log_path = os.path.join(log_dir, self.launch_log)
        error_path = os.path.join(log_dir, self.error_log)

        upload_script = '\n'.join(
            [m.upload_script for m in self.mounts if hasattr(m, "upload_script") and m.upload_script]
        )
        remote_setup = "\n".join(
            [m.remote_setup for m in self.mounts if hasattr(m, "remote_setup") and m.remote_setup]
        )

        assert len(instance_tag) <= 128, "Error: aws limits instance tag to 128 unicode characters."

        tag_current_instance = f"""
            EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id`"
            aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags 'Key=Name,Value={instance_tag}' --region {region}
            aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags 'Key=exp_prefix,Value={instance_tag}' --region {region}
        """
        install_aws_cli = f"""
            pip install awscli --upgrade --user
        """
        termination_script = f"""
            echo "Now terminate this instance"
            EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die "wget instance-id has failed: $?"`"
            aws ec2 terminate-instances --instance-ids $EC2_INSTANCE_ID --region {region}
        """
        delay_script = f"""
            # Now sleep before ending this script
            sleep {delay}
        """ if delay else ""
        # TODO: path.join is running on local computer, so it might not be quite right if remote is say windows.
        launch_script = f"""
        #!/bin/bash
        # to allow process substitution
        set +o posix
        mkdir -p {log_dir}
        {{
            # clear main_log
            truncate -s 0 {log_path}
            truncate -s 0 {error_path}
            
            die() {{ status=$1; shift; echo "FATAL: $*"; exit $status; }}
            {install_aws_cli}
            
            export AWS_DEFAULT_REGION={region}
            {tag_current_instance if instance_tag else ""}
            
            # remote_setup
            {remote_setup}
            # upload_script
            {upload_script}
            # {"sudo " if sudo else ""}service docker start
            # pull docker
            docker pull {self.docker.docker_image}
            # run docker
            {self.docker.run_script}
            {delay_script}
            {termination_script if terminate_after_finish else ""}
        }} > >(tee -a {log_path}) 2> >(tee -a {error_path} >&2)
        """

        self.launch_script = dedent(launch_script).strip()

        return self

    def launch_ssh(self, ip_address, username="ubuntu", pem=None, script_dir=None, sudo=False, verbose=False, dry=False,
                   detached=False):
        """
        run launch_script remotely by ip_address. First saves the run script locally as a file, then use
        scp to transfer the script to remote instance then run.

        :param detached: use call instead of checkcall
        :param ip_address:
        :param pem:
        :param verbose:
        :param dry:
        :return:
        """
        script_dir = script_dir or f"/tmp/{uuid.uuid4()}"
        tf = tempfile.NamedTemporaryFile(prefix="jaynes_launcher-", suffix=".sh", delete=False)
        with open(tf.name, 'w') as f:
            script_name = os.path.basename(tf.name)
            # note: kill requires sudo
            f.write(self.launch_script + "\n"
                                         f"sudo kill $(ps aux | grep '{script_name}' | awk '{{print $2}}')\n"
                                         f"echo 'clean up all startup script processes'\n")
        tf.file.close()

        upload_script, launch = ssh_remote_exec(username, ip_address, tf.name, pem=pem, sudo=sudo,
                                                remote_script_dir=script_dir)

        if not dry:
            if upload_script:
                # done: separate out the two commands
                ck(upload_script, verbose=verbose, shell=True)
            if detached:
                import sys
                popen(launch, verbose=verbose, shell=True, stdout=sys.stdout, stderr=sys.stderr)
            else:
                ck(launch, verbose=verbose, shell=True)

        elif verbose:
            if upload_script:
                print(upload_script)
            print(launch)

        import time
        time.sleep(0.1)
        os.remove(tf.name)


    def launch_ec2(self, region, image_id, instance_type, key_name, security_group, spot_price=None,
                   iam_instance_profile_arn=None, verbose=False, dry=False):
        import boto3
        ec2 = boto3.client("ec2", region_name=region, aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'),
                           aws_secret_access_key=os.environ.get('AWS_ACCESS_SECRET'))

        instance_config = dict(ImageId=image_id, KeyName=key_name, InstanceType=instance_type,
                               SecurityGroups=(security_group,),
                               IamInstanceProfile=dict(Arn=iam_instance_profile_arn))
        if spot_price:
            # for detailed settings see:
            #     http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.request_spot_instances
            # issue here: https://github.com/boto/boto3/issues/368
            instance_config.update(UserData=base64.b64encode(self.launch_script.encode()).decode("utf-8"))
            response = ec2.request_spot_instances(InstanceCount=1, LaunchSpecification=instance_config,
                                                  SpotPrice=str(spot_price), DryRun=dry)
            spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            if verbose:
                print(response)
            return spot_request_id
        else:
            instance_config.update(UserData=self.launch_script)
            response = ec2.run_instances(MaxCount=1, MinCount=1, **instance_config, DryRun=dry)
            if verbose:
                print(response)
            return response
