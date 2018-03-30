import os
import time


def train(log_dir, *args, **kwargs):
    with open(f"{log_dir}/test.log", 'a') as f:
        print(f"parameters include: {args, kwargs}", file=f)
        for i in range(100):
            print(f'{i} running output to startup.log')
            print(f"{i} output to script defined log", file=f)
            time.sleep(1.0)
            f.flush()


LOG_DIR = "dqn/some_experiment-1"
abs_path = os.path.abspath(LOG_DIR)
