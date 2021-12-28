from jaynes.constants import JAYNES_PARAMS_KEY
from jaynes.param_codec import serialize
from jaynes.shell import check_call, run


def test_ck():
    def fn(b):
        assert (b + 5) == 8, 'input b + 5 == 8'
        print(f"result is correct => {b + 5}")

    thunk_string = serialize(fn, [3])
    cmd = f"{JAYNES_PARAMS_KEY}={thunk_string} python -m jaynes.entry"
    check_call(cmd, verbose=True, shell=True)


def test_run():

    def fn(b):
        print(b + 5)

    thunk_string = serialize(fn, [10])
    cmd = f"{JAYNES_PARAMS_KEY}={thunk_string} python -m jaynes.entry"
    stdout, err = run(cmd, verbose=True, shell=True)
    assert stdout == b"15\n"


if __name__ == "__main__":
    test_ck()
    test_run()
