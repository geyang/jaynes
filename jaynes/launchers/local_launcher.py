import os
from textwrap import dedent

from jaynes.shell import ck


def launch_local_docker(self, launch_script, log_dir="/tmp/jaynes-mount", delay=None, verbose=False, dry=False,
                        root_config=None):
    # the log_dir is primarily used for the run script. Therefore it should use ued here instead.
    log_path = os.path.join(log_dir, "jaynes-launch.log")
    error_path = os.path.join(log_dir, "jaynes-launch.err.log")

    upload_script = '\n'.join(
        [m.upload_script for m in self.mounts if hasattr(m, "upload_script") and m.upload_script]
    )
    host_setup = "" if self.host_unpacked else "\n".join(
        [m.host_setup for m in self.mounts if hasattr(m, "host_setup") and m.host_setup]
    )

    remote_script = dedent(f"""
        #!/bin/bash
        # to allow process substitution
        set +o posix
        {root_config or ""}
        mkdir -p {log_dir}
        {{
            {host_setup}

            # upload_script
            {upload_script}

            {self.runners[0].setup_script}
            {self.runners[0].run_script}
            {self.runners[0].post_script}
            
            {f"sleep {delay}" if delay else ""}
        }} > >(tee -a {log_path}) 2> >(tee -a {error_path} >&2)
        """).strip()
    if verbose:
        print(remote_script)
    if not dry:
        ck(remote_script, shell=True)
    return self
