from jaynes.constants import JAYNES_PARAMS_KEY
from jaynes.param_codec import serialize
from jaynes.shell import ck


def test():
    def fn(b):
        assert (b + 5) == 8, 'input b + 5 == 8'
        print(f"result is correct => {b + 5}")

    thunk_string = serialize(fn, [3])
    cmd = f"{JAYNES_PARAMS_KEY}={thunk_string} python -m jaynes.entry"
    ck(cmd, shell=True)


if __name__ == "__main__":
    test()
