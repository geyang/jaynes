Usage Pattern
================

First let's just create a simple directory with a single python file.

.. code:: bash

    git clone https://github.com/episodeyang/jaynes-starter-kit.git
    cd jaynes-starter-kit
    tree -L 2

::

    jaynes-starter-kit
    ├── 01_ssh_docker_configuration
    │   ├── README.md
    │   ├── figures
    │   ├── jaynes.yml
    │   └── launch_entry.py
    ├── 02_ec2_docker_configuration
    ├── 03_multiple_ssh_reacheable_machines
    ├── 04_slurm_configuration
    ├── 05_muti-mode_advanced_config
    └── README.md

You can start using Jaynes without setting up AWS or SLURM. In fact Jaynes is good
even for launching 20 parallel training runs on your own computer over-night!

Let's try to do that :)

.. code:: python

    import time
    from tqdm import trange
    from termcolor import cprint

    def launch(learning_rate, model_name, run_id):
        cprint(f"{run_id}: training model {model_name} with {learning_rate}", 'green')
        for i in trange(100):
            time.sleep(0.5)


    if __name__ == "__main__":
        import jaynes

        jaynes.config("local")
        for i in range(5):
            jaynes.run(launch, 1e-3, "CarbonFootprint", f"{i:02d}")



