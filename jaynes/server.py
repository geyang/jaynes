import os
import asyncio
from aiofile import AIOFile, Reader, Writer
from sanic import Sanic
from sanic.response import json
from sanic.response import json
from params_proto.neo_proto import ParamsProto


# todo use neo_proto to support better logic in
#  init call
class ServerConfig(ParamsProto, prefix=""):
    server = None
    protocol = "http"
    host = "0.0.0.0"
    port = 8092
    token = None
    file_root = os.getcwd()
    envs = {
        "JYNMNT": os.environ.get("JYNMNT", os.getcwd() + "/jaynes-mounts")
    }

    @classmethod
    def __init__(cls, deps=None, **kwargs):
        cls.server = f"{cls.protocol}://{cls.host}:{cls.port}"
        cls._update(deps, **kwargs)

        if cls.envs:
            os.environ.update(cls.envs)

        print(f"Jaynes Server is now running!")
        print(cls.envs)


app = Sanic("Jaynes Server")


def interpolate(path: str, envs, is_path=True):
    if path is None:
        return path
    sorted_envs = list(envs.items())
    sorted_envs.sort(key=lambda kv: kv[0], reverse=True)
    for k, v in sorted_envs:
        path = path.replace("$" + k, v)
    # remove occasional double slash due to $TMPDIR end in "/"
    if is_path:
        return os.path.realpath(path)
    return path


# note: let's build this using an RPC pattern, where
#  the client controls the process. This makes scripting
#  easy.

@app.route("/files/<path:path>", methods=["PUT"], stream=True)
async def upload(request, path):
    content = b''
    path = interpolate(path, os.environ)
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)

    print(">>", dirname, path)

    # async with AIOFile(path, 'w+') as afp:
    while True:
        body = await request.stream.read()
        if body is None:
            break
        content += body  # .decode('utf-8')
        # await afp.write(content)
        # await afp.fsync()
    with open(path, "wb") as f:
        f.write(content)
    return json({"status": 1})


@app.route("/files/<path:path>", methods=["POST"], stream=True)
async def update(request, path):
    path = interpolate(path, os.environ)
    query_args = dict(request.query_args)
    overwrite = query_args.get('overwrite', True)
    content = b''
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)
    # info: currently NFS has a c bug, causing file streaming to fail.
    # async with AIOFile(path, 'w+' if overwrite else 'a') as afp:
    while True:
        body = await request.stream.read()
        if body is None:
            break
        content += body  # .decode('utf-8')
        # await afp.write(content)
        # await afp.fsync()
    with open(path, 'wb' if overwrite else 'ab') as f:
        f.write(content)
    return json({"status": 1})


async def run(cmd, timeout=None):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy()
    )

    com = proc.communicate()
    if timeout is not None:
        com = asyncio.wait_for(com, timeout)
    try:
        stdout, stderr = await com
        return stdout.decode(), stderr.decode(), proc.returncode,
    except asyncio.TimeoutError:
        return None, f"Timed out after {timeout} secs.", 0


@app.route("/exec", methods=["POST"])
async def execute(request):
    cmd = request.json.get('cmd', None)
    timeout = request.json.get('timeout', None)
    # cmd = interpolate(cmd, os.environ)
    if cmd is not None:
        result = await run(cmd, timeout)
        return json(result)
    cmds = request.json.get('cmds', [])
    # cmds = [interpolate(c, os.environ) for c in cmds]
    if cmds:
        results = await asyncio.gather(
            *[run(c, timeout) for c in cmds]
        )
        return json(results)
    return json([])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--host', dest='host', type=str,
                        help='host for the server')
    parser.add_argument('--port', dest='port', type=int,
                        help='port for the server')

    args = parser.parse_args()
    ServerConfig(host=args.host, port=args.port)
    app.run(host=ServerConfig.host, port=ServerConfig.port)
