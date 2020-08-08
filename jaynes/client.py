import requests
import json
from urllib.parse import urlencode


class JaynesClient:
    def __init__(self, server="http://localhost:8092", token=None):
        self.server = server

    def post(self, path, data, **kwargs):
        if kwargs:
            path += "?" + urlencode(kwargs)
        r = requests.post(self.server + path, data=data)
        return r.json()

    def post_json(self, path, data, **kwargs):
        serialized = json.dumps(data)
        return self.post(path, data=serialized, **kwargs)

    def put(self, path, data, **kwargs):
        if kwargs:
            path += "?" + urlencode(kwargs)
        r = requests.put(self.server + path, data=data)
        if r.status_code > 200:
            print(r.text)
        return r.json()

    def gzip_local(self, dir, target):
        pass

    def upload_file(self, file, remote_path=None):
        """used to upload files that have been changed"""
        if remote_path is None:
            remote_path = file
        with open(file, 'rb') as f:
            text = f.read()
        r = self.put("/files/" + remote_path, data=text)
        return r

    def update_file(self, file, remote_path=None, overwrite=True):
        """used to upload files that have been changed"""
        if remote_path is None:
            remote_path = file
        with open(file, 'rb') as f:
            text = f.read()
        r = self.post("/files/" + remote_path, data=text, overwrite=overwrite)
        return r

    def unzip_remote(self, dir):
        pass

    def execute(self, cmd):
        return self.post_json("/exec", dict(cmd=cmd))

    def map(self, *cmds):
        return self.post_json("/exec", dict(cmds=cmds))


if __name__ == '__main__':
    # test this
    # client = JaynesClient()
    client = JaynesClient(server="http://d96a7f6c0acc.ngrok.io")
    status, stdout, stderr = client.execute('ls')
    print(status, stdout, stderr)
    outs = client.map('ls', "ls", "ls")
    for status, stdout, stderr in outs:
        print(status, stdout, stderr)

    client.execute('mkdir -p ".test"')
    client.execute('touch ".test/README.md"')
    r = client.execute('ls ".test"')
    print(r)
    client.upload_file("../README.md", ".test/README.md")
    client.execute('rm ".test"')
    client.update_file("../README.md", ".test/README.md")
    client.execute('rm ".test"')
