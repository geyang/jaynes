import os
from textwrap import dedent

from jaynes.shell import check_call


def launch_local_docker(mounts, runners, unpack_host=True, log_dir="/tmp/jaynes-mount", delay=None, verbose=False, dry=False,
                        root_config=None):
    # the log_dir is primarily used for the run script. Therefore it should use ued here instead.
    log_path = os.path.join(log_dir, "jaynes-launch.log")
    error_path = os.path.join(log_dir, "jaynes-launch.err.log")

    upload_script = '\n'.join(
        [m.upload_script for m in mounts if hasattr(m, "upload_script") and m.upload_script]
    )
    host_setup = "" if not unpack_host else "\n".join(
        [m.host_setup for m in mounts if hasattr(m, "host_setup") and m.host_setup]
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

            {runners[0].setup_script}
            {runners[0].run_script}
            {runners[0].post_script}
            
            {f"sleep {delay}" if delay else ""}
        }} > >(tee -a {log_path}) 2> >(tee -a {error_path} >&2)
        """).strip()
    if verbose:
        print(remote_script)
    if not dry:
        return check_call(remote_script, shell=True)
    return
