import os

from .param_codec import deserialize
from .constants import JAYNES_PARAMS_KEY

if __name__ == "__main__":
    thunk_string = os.environ.get(JAYNES_PARAMS_KEY)
    assert thunk_string is not None, f"environment variable {JAYNES_PARAMS_KEY} does not exist!"
    # consider catching exceptions.
    fn, args, kwargs = deserialize(thunk_string)
    fn(*args, **kwargs)
