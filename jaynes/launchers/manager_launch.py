import tempfile
from textwrap import dedent

from jaynes.client import JaynesClient
from jaynes.launchers.base_launcher import Launcher, make_launch_script


class Manager(Launcher):
    host_unpacked = None
    launch_script = None

    def setup_host(self, verbose=None, **_):
        if self.host_unpacked:
            return

        self.host_unpacked = True

        client = JaynesClient(server=self.config['host'])
        host_setup = [dedent(m.host_setup) for m in self.all_mounts if hasattr(m, "host_setup") and m.host_setup]
        if verbose:
            print(*host_setup, sep="--------")
        pipe_back = client.map(*host_setup)
        if verbose:
            print(pipe_back)
        return pipe_back

    def plan_instance(self, verbose=None):
        self.launch_script = make_launch_script(runners=self.runners, mounts=self.all_mounts,
                                                unpack_on_host=self.host_unpacked, **self.config)
        self.runners.clear()
        if verbose:
            print(self.launch_script)

    def execute(self, verbose=None):
        self.plan_instance(verbose=verbose)
        return launch_manager(self.launch_script, **self.config)


def launch_manager(launch_script, host, launch_dir, script_name="jaynes_launch.sh", project=None, user=None,
                   token=None, sudo=False, cleanup=True, verbose=False, timeout=None, **_):
    # from termcolor import cprint

    client = JaynesClient(host)
    remote_script_name = launch_dir + "/" + script_name

    with tempfile.NamedTemporaryFile(prefix="jaynes_launch-", suffix=".sh", mode="w+") as f:
        f.write(launch_script)
        f.flush()

        client.upload_file(f.name, remote_script_name)

    # need to implement the timeout on the server side to avoid congestion
    return client.execute(f"bash {remote_script_name}", timeout)
    # try:
    #     stdout, stderr, error = r
    #     if stdout:
    #         print(stdout)
    #     if error or stderr:
    #         cprint(stderr, color="red")
    # except Exception as e:
    #     cprint(r, color="red")
    # return r
