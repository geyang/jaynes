import requests
import json
from urllib.parse import urlencode, quote


class JaynesClient:
    def __init__(self, server="http://localhost:8092", token=None):
        self.server = server

    def post(self, path, data, **kwargs):
        if kwargs:
            path += "?" + urlencode(kwargs)
        r = requests.post(self.server + path, data=data)
        try:
            return r.json()
        except:
            return r

    def post_json(self, path, data, **kwargs):
        serialized = json.dumps(data)
        return self.post(path, data=serialized, **kwargs)

    def put(self, path, data, **kwargs):
        if kwargs:
            path += "?" + urlencode(kwargs)
        r = requests.put(self.server + path, data=data)
        if r.status_code > 200:
            print(r.text)
        try:
            return r.json()
        except:
            return r

    def gzip_local(self, dir, target):
        pass

    def upload_file(self, file, remote_path=None):
        """used to upload files that have been changed"""
        if remote_path is None:
            remote_path = file
        with open(file, 'rb') as f:
            text = f.read()
        r = self.put("/files/" + quote(remote_path), data=text)
        return r

    def update_file(self, file, remote_path=None, overwrite=True):
        """used to upload files that have been changed"""
        if remote_path is None:
            remote_path = file
        with open(file, 'rb') as f:
            text = f.read()
        r = self.post("/files/" + quote(remote_path), data=text, overwrite=overwrite)
        return r

    def unzip_remote(self, dir):
        pass

    def execute(self, cmd, timeout=None):
        return self.post_json("/exec", dict(cmd=cmd, timeout=timeout))

    def map(self, *cmds):
        return self.post_json("/exec", dict(cmds=cmds, timeout=None))


if __name__ == '__main__':
    from .server import run
    # test this
    client = JaynesClient()
    # client = JaynesClient(server="http://mars.ge.ngrok.io")
    # status, out, err = client.execute("touch 'echo \"yo\"' > .t")
    # status, out, err = client.execute("touch 'sleep 5' > .t")
    # status, out, err = client.execute("touch 'echo \"hey\"' >> .t")
    for i in range(1000):
        print(i)
        # status, out, err = client.execute("echo 'yo' & sleep 10 && echo 'done'")
        r = client.execute(f"SEED={i} python payload.py >> .log", timeout=0.01)
        print(r)
        # print(out, err)
    # status, stdout, stderr = client.execute('ls')
    # print(status, stdout, stderr)
    # outs = client.map('ls', "ls", "ls")
    # for status, stdout, stderr in outs:
    #     print(status, stdout, stderr)
    #
    # client.execute('mkdir -p ".test"')
    # client.execute('touch ".test/README.md"')
    # r = client.execute('ls ".test"')
    # print(r)
    # client.upload_file("../README.md", "$JYNMNT/.test/README.md")
    # client.execute('rm ".test"')
    # client.update_file("../README.md", ".test/README.md")
    # client.execute('rm ".test"')
    # run(f"gzip ")

# todo:
#   1. gzip locally
#   2. watch files locally
#   3. upload file that has changed
#   4. copy file to new location
#   5. launch remotely
