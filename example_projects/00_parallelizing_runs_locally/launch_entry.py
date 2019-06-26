#
import jaynes


def launch(seed):
    import time, random
    print(f"""run {seed:04d} starting...""")
    delay = random.random()
    time.sleep(delay)
    print(f"""run {seed:04d} is done.""")


if __name__ == "__main__":
    jaynes.config()

    import time

    for seed in range(30):
        jaynes.run(launch, seed=seed)
        print(f"{seed:04d} launched")
    jaynes.listen()
