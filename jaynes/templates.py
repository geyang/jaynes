import os
from os.path import join as pathJoin

ec2_terminate = lambda region, delay=30: f"""
            {f"sleep {delay}" if delay else ""}
            die() {{ status=$1; shift; echo "FATAL: $*"; exit $status; }}
            echo "Now terminate this instance"
            EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die "wget instance-id has failed: $?"`"
            aws ec2 terminate-instances --instance-ids $EC2_INSTANCE_ID --region {region}
        """


def ssh_remote_exec(user, ip_address, script_path, port=None, pem=None,
                    profile=None, password=None, require_password=False, sudo=True, remote_script_dir=None):
    """
    run script remotely via ssh agent. 

    :param password: password, if the *ssh session* requires a password
    :param require_password: if the bash script that needs to be ran requires password
    :param user: username for the ssh login
    :param ip_address: address for the host
    :param pem: path to the public key for this login

    :param profile: the user profile you want to run the remote ssh command with.
            Calls "su - {profile}; bash ..." instead.

    # :param password: the plain text password for the user profile. This is typically not recommended
    #         but is okay here because this call is not recorded anywhere.
    #
    #       Calls "echo `PassWord` | sudo -kS su - {profile}; bash ..." instead.

    :param script_path: Something like:
                    >   /var/folders/q9/qh3g18bs0vq3xjqtvv636vfmx6y0dw/T/jaynes_launcher-6s2il8sm.sh

    :param port: default None, the port number
    :param sudo:
    :param remote_script_dir:

                The directory to which we send the launch script.

                This execution function runs in two modes: `upload` mode or `pipe`
                mode.

                `upload` mode first uploads the script before executing it.
                `pipe` mode just streams the script into bash with pipe.

                These two modes function the same for all intent and purposes
                (sudo/user, blocking/detached, etc). But with the `pipe` mode
                We don't have to avoid the scripts over-writing each other.
                With the `upload` mode, we have a record of the script (and arguments)
                being run.

                When using `upload` mode, you need to specify the remote_script_dir.
                Typically, you can just use `os.path.directory(<Jaynes>.launch_log)`
                for this.

                question: what script name does this use?

    :return:
    """

    options = "" if password is None else "-T "
    options += "-o 'StrictHostKeyChecking=no'"

    port_ = "" if port is None else f"-p {port}"
    pem_ = f'-i {pem}' if pem else ''
    sudo_ = 'sudo -n -s' if sudo else ""
    if remote_script_dir:  # `upload` mode
        assert os.path.isabs(remote_script_dir), "remote_script_dir need to be absolute"
        remote_path = pathJoin(remote_script_dir, os.path.basename(script_path))
        # this should be factorized out.
        send_file = f"""ssh {options} {user}@{ip_address} {port_} {pem_} 'mkdir -p {remote_script_dir}'\n""" \
                    f"""scp {port_.upper()} {pem_} {script_path} {user}@{ip_address}:{remote_script_dir}"""
        if profile:
            launch = f'''ssh {options} {user}@{ip_address} {port_} {pem_} "sudo {"-kS " if require_password else ""}su - {profile}; {sudo_} bash {remote_path}"'''
        else:
            launch = f"""ssh {options} {user}@{ip_address} {port_} {pem_} '{sudo_} bash {remote_path}'"""
        if password is not None:
            send_file = f"sshpass -p '{password}' {send_file}"
            launch = f"sshpass -p '{password}' {launch}"
        return send_file, launch
    else:  # `pipe` mode, requires piping in file from the outside.
        if profile:
            launch = f"""ssh {options} {user}@{ip_address} {port_} {pem_} 'sudo {"-kS " if require_password else ""}su - {profile}; {sudo_} bash -s'"""
        else:
            launch = f"""ssh {options} {user}@{ip_address} {port_} {pem_} '{sudo_} bash -s'"""
        if password is not None:
            launch = f"sshpass -p '{password}' {launch}"
        return None, launch
