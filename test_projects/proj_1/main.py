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


class RUN:
    instance_prefix = "jaynes-test-instance-tag"
    log_dir = os.path.abspath("test-log-dir")
    s3_log_dir = "s3://ge-bair/"

# class Logging:
#     timestamp = ""
#     timesteps = ""
#     epoch = ""
#     n_iter = ""
#     loss_1 = ""
#     loss_2 = ""
#     # data
#     img_gen_10_categories = ""
#     mov_gen_10_categories = ""
