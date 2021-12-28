import os
import sys
import tempfile
from textwrap import dedent

from jaynes.helpers import omit
from jaynes.launchers.base_launcher import Launcher, make_host_unpack_script, make_launch_script
from jaynes.shell import check_call
from jaynes.templates import ssh_remote_exec


def ssh(script, ip, port=None, username="ubuntu", pem=None, profile=None,
        password=None, sudo=False, cleanup=True, block=False, console_mode=False, dry=False,
        verbose=False, **_):
    """
    run launch_script remotely by ip_address. First saves the run script locally as a file, then use
    scp to transfer the script to remote instance then run.

    :param username:
    :param ip:
    :param port:
    :param pem:
    :param sudo:
    :param cleanup: whether to attach clean up script at the end of the launch scrip
    :param block: whether wait for p.communication after calling. Blocks further execution.
    :param console_mode: do not block, do not use stdout.pipe when running from ipython console.
    :param profile: Suppose you want to run bash as a different user after ssh in, you can use this option to
                    pass in a different user name. This is inserted in the ssh boostrapping command, so the script
                    you run will not be affected (and will take up this user's login envs instead).
    :param password: The password for the user in case it is needed.
    :param dry:
    :param verbose:
    :return:
    """
    # todo: is this still used?
    tf = tempfile.NamedTemporaryFile(prefix="jaynes_launcher-", suffix=".sh", delete=False)
    with open(tf.name, 'w') as f:
        _ = os.path.basename(tf.name)  # fixit: does kill require sudo?
        cleanup_script = dedent(f"""
            PROCESSES=$(ps aux | grep '[{_[0]}]{_[1:]}' | awk '{{print $2}}')
            if [ $PROCESSES ] 
            then
            {"sudo " if sudo else ""}kill $PROCESSES
            {f"echo 'cleaned up after {_}" if verbose else ""}
            fi 
            """)
        f.write(script + cleanup_script if cleanup else "")
    tf.file.close()

    prelaunch_upload_script, launch = ssh_remote_exec(username, ip, tf.name,
                                                      port=port, pem=pem,
                                                      profile=profile,
                                                      password=password,
                                                      require_password=(profile is not None),
                                                      sudo=sudo)

    # todo: use pipe back to send binary from RPC calls
    if dry:
        if prelaunch_upload_script:
            print("script upload:\n", prelaunch_upload_script)
        print("launch script:\n", launch)
        return

    # note: first pre-upload the script
    if prelaunch_upload_script:
        # done: separate out the two commands
        p = check_call(prelaunch_upload_script, verbose=verbose, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        if profile is not None:
            p.communicate(bytes(f"{password}\n"))

    pipe_in = "" if profile is None else f"{password}\n"
    if not prelaunch_upload_script:
        pipe_in = pipe_in + script + "\n"

    if verbose:
        print('ssh pipe-in: ')
        print(pipe_in)

    import subprocess
    if block:
        # todo: not supported. stdout, stderr, requires subprocess.PIPE for the two.
        p = subprocess.Popen(launch, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        return p.communicate(bytes(pipe_in, 'utf-8'))
    elif console_mode:
        p = subprocess.Popen(launch, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(launch, shell=True, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)

    p.stdin.write(bytes(pipe_in, 'utf-8'))
    p.stdin.flush()


class SSH(Launcher):
    # Not need in GCP launch or EC2 launcher.
    host_unpacked = False
    launch_script = None

    def setup_host(self, verbose=None, **kw):
        if self.host_unpacked:
            return
        self.host_unpacked = True

        unpack_script = make_host_unpack_script(mounts=self.all_mounts, **self.config)

        if verbose:
            print('Unpacking On Remote')
        ssh(script=unpack_script, **omit(self.config, 'block'), block=True,
            verbose=verbose)

    # SSH does not support planning ahead.
    def plan_instance(self, verbose=None):
        pass

    def execute(self, verbose=None):
        self.launch_script = make_launch_script(runners=self.runners, mounts=self.all_mounts,
                                                unpack_on_host=self.host_unpacked, **self.config)
        self.runners.clear()
        if verbose:
            print(self.launch_script)

        return ssh(self.launch_script, **self.config)
