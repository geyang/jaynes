from params_proto import cli_parse


@cli_parse
class Args:
    seed = 0
    env_id = "CMaze"
    lr = 0.1


def launch(**kwargs):
    from ml_logger import logger
    Args.update(kwargs)
    logger.log_params(Args=vars(Args))

    s = f""" 
    the env_id is {kwargs['env_id']} 
    the lr is {kwargs['lr']} 
    the seed is {kwargs['seed']}
    """
    logger.log(s, flush=True)
    logger.log("run has finished!", color="green")


if __name__ == "__main__":
    import jaynes

    jaynes.config()

    for Args.lr in [0.01, 0.03, 0.1]:
        jaynes.run(launch, **vars(Args))

    for env_id in ["CMaze", "GoalMass"]:
        for lr in [0.01, 0.03, 0.1]:
            for seed in range(1):
                jaynes.run(launch, seed=seed, lr=lr, env_id=env_id, runner=dict(n_cpu=1))

                jaynes.listen()
