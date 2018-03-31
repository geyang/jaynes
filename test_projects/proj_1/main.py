import os
import time


def train(log_dir, *args, **kwargs):
    with open(f"{log_dir}/test.log", 'a') as f:
        print(f"parameters include: {args, kwargs}", file=f)
        for i in range(300):
            print(f'{i} running output to startup.log ths and that')
            print(f"{i} output to script defined log you you ", file=f)
            time.sleep(1.0)
            f.flush()


LOG_DIR = "new-test-hahaha"
abs_path = os.path.abspath(LOG_DIR)
