import os
import signal
import subprocess
import sys
import tempfile
from textwrap import dedent

from jaynes.helpers import omit
from jaynes.launchers.base_launcher import Launcher, make_host_unpack_script, make_launch_script
from jaynes.shell import check_call
from jaynes.templates import ssh_remote_exec


class SSHPopen:
    """Wraps a subprocess.Popen that runs an SSH session.

    Adds the ability to kill the *remote* process tree when terminating,
    not just the local SSH client.
    """

    def __init__(self, proc, ip, username="ubuntu", port=None, pem=None, options=""):
        self._proc = proc
        self._ip = ip
        self._username = username
        self._port = port
        self._pem = pem
        self._options = options

    # ── proxy standard Popen attributes ──
    @property
    def pid(self):
        return self._proc.pid

    @property
    def returncode(self):
        return self._proc.returncode

    @property
    def stdin(self):
        return self._proc.stdin

    @property
    def stdout(self):
        return self._proc.stdout

    @property
    def stderr(self):
        return self._proc.stderr

    def poll(self):
        return self._proc.poll()

    def wait(self, timeout=None):
        return self._proc.wait(timeout=timeout)

    def communicate(self, input=None, timeout=None):
        return self._proc.communicate(input=input, timeout=timeout)

    def kill(self):
        self._kill_remote()
        self._kill_local(sig=signal.SIGKILL)

    def terminate(self):
        self._kill_remote()
        self._kill_local(sig=signal.SIGTERM)

    def _kill_local(self, sig=signal.SIGTERM):
        try:
            os.killpg(os.getpgid(self._proc.pid), sig)
        except (ProcessLookupError, OSError):
            try:
                self._proc.send_signal(sig)
            except (ProcessLookupError, OSError):
                pass

    def _kill_remote(self):
        """SSH into the node and kill any jaynes.entry processes."""
        ssh_cmd = ["ssh",
                   "-o", "ConnectTimeout=5",
                   "-o", "StrictHostKeyChecking=no"]
        if self._port:
            ssh_cmd += ["-p", str(self._port)]
        if self._pem:
            ssh_cmd += ["-i", self._pem]
        ssh_cmd += [f"{self._username}@{self._ip}",
                    "pkill -f 'python.*jaynes.entry'"]
        try:
            subprocess.run(ssh_cmd, timeout=10, capture_output=True)
        except Exception:
            pass


def ssh(
    script,
    ip,
    port=None,
    username="ubuntu",
    pem=None,
    profile=None,
    password=None,
    sudo=False,
    cleanup=True,
    block=False,
    console_mode=False,
    dry=False,
    verbose=False,
    options="",
    stdout=None,
    stderr=None,
    **_,
):
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
    with open(tf.name, "w") as f:
        bname = os.path.basename(tf.name)  # fixit: does kill require sudo?
        cleanup_script = dedent(f"""
            PROCESSES=$(ps aux | grep '[{bname[0]}]{bname[1:]}' | awk '{{print $2}}')
            if [ $PROCESSES ] 
            then
            {"sudo " if sudo else ""}kill $PROCESSES
            {f"echo 'cleaned up after {bname}" if verbose else ""}
            fi 
            """)
        f.write(script + cleanup_script if cleanup else "")
    tf.file.close()

    prelaunch_upload_script, launch = ssh_remote_exec(
        username,
        ip,
        tf.name,
        port=port,
        pem=pem,
        profile=profile,
        password=password,
        require_password=(profile is not None),
        sudo=sudo,
        options=options,
    )

    # todo: use pipe back to send binary from RPC calls
    if dry:
        if prelaunch_upload_script:
            print("script upload:\n", prelaunch_upload_script)
        print("launch script:\n", launch)
        return

    # note: first pre-upload the script
    if prelaunch_upload_script:
        # done: separate out the two commands
        p = check_call(prelaunch_upload_script, verbose=verbose, shell=True, stdout=stdout or sys.stdout, stderr=stderr or sys.stderr)
        if profile is not None:
            p.communicate(bytes(f"{password}\n"))

    pipe_in = "" if profile is None else f"{password}\n"
    if not prelaunch_upload_script:
        pipe_in = pipe_in + script + "\n"

    if verbose:
        print(">> launch script is")
        print(launch)
        print(">> ssh pipe-in: ")
        print(pipe_in)

    if block:
        p = subprocess.Popen(launch, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
        return p.communicate(bytes(pipe_in, "utf-8"))
    elif console_mode:
        p = subprocess.Popen(launch, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    else:
        p = subprocess.Popen(launch, shell=True, stdin=subprocess.PIPE, stdout=stdout or sys.stdout, stderr=stderr or sys.stderr,
                             start_new_session=True)

    p.stdin.write(bytes(pipe_in, "utf-8"))
    p.stdin.flush()
    p.stdin.close()

    return SSHPopen(p, ip=ip, username=username, port=port, pem=pem, options=options)


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
            print("Unpacking On Remote")
        ssh(script=unpack_script, **omit(self.config, "launch_dir", "type", "block"), block=True, verbose=verbose)

    # SSH does not support planning ahead.
    def plan_instance(self, verbose=None):
        pass

    def execute(self, verbose=None):
        self.launch_script = make_launch_script(
            runners=self.runners, mounts=self.all_mounts, unpack_on_host=self.host_unpacked, **self.config
        )
        self.runners.clear()
        if verbose:
            print(self.launch_script)

        return ssh(self.launch_script, **self.config)
