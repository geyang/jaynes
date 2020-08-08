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

    @classmethod
    def __init__(cls, deps=None, **kwargs):
        cls.server = f"{cls.protocol}://{cls.host}:{cls.port}"
        cls._update(deps, **kwargs)

        print("""
        Jaynes Server is now running!
        """)


app = Sanic("Jaynes Server")


# note: let's build this using an RPC pattern, where
#  the client controls the process. This makes scripting
#  easy.

@app.route("/files/<path:path>", methods=["PUT"], stream=True)
async def upload(request, path):
    print(path)
    content = ''
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)

    async with AIOFile(path, 'w+') as afp:
        while True:
            body = await request.stream.read()
            if body is None:
                break
            content += body.decode('utf-8')
            await afp.write(content)
            await afp.fsync()
    print(content)
    return json({"status": 1})


@app.route("/files/<path:path>", methods=["POST"], stream=True)
async def upload(request, path):
    print(path)
    query_args = dict(request.query_args)
    overwrite = query_args.get('overwrite', True)
    print(overwrite)
    content = ''
    async with AIOFile("/tmp/hello.txt", 'w+' if overwrite else 'a') as afp:
        while True:
            body = await request.stream.read()
            if body is None:
                break
            content += body.decode('utf-8')
            await afp.write(content)
            await afp.fsync()
    print(content)
    return json({"status": 1})


async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


@app.route("/exec", methods=["POST"])
async def execute(request):
    cmd = request.json.get('cmd', None)
    if cmd is not None:
        result = await run(cmd)
        return json(result)
    cmds = request.json.get('cmds', [])
    if cmds:
        results = await asyncio.gather(
            *[run(c) for c in cmds]
        )
        return json(results)
    return json([])


if __name__ == "__main__":
    ServerConfig()
    app.run(host=ServerConfig.host, port=ServerConfig.port)
