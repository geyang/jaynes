from .client import JaynesClient


class JaynesDaemon:
    def __init__(self, server_configs=tuple()):
        """watch local folder and upload to a list of servers"""
        self.server_configs = server_configs
        self.sleep = 3
        self.clients = [JaynesClient(c) for c in server_configs]

    def run(self):
        print('Jaynes daemon just started!')
        print('watching local folder...')
        print('gziping...')
        while True:
            import time
            time.sleep(self.sleep)
            # add logic to upload files
            print('change detected, now upload...')
            print('upload complete...')


if __name__ == '__main__':
    daemon = JaynesDaemon()
    daemon.run()
