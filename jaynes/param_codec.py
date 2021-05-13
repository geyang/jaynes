import pickle

import base64
from typing import Any, Dict, Tuple

import cloudpickle


def deserialize(code):
    data = cloudpickle.loads(base64.b64decode(code))
    return data['thunk'], data['args'] or (), data['kwargs'] or {}


def serialize(fn, args: Tuple[Any] = None, kwargs: Dict[Any, Any] = None,
              protocol=pickle.DEFAULT_PROTOCOL):
    """
    for protocol see: https://stackoverflow.com/a/23582505/1560241
    :param fn:
    :param args:
    :param kwargs:
    :param protocole:
    :return:
    """
    code = cloudpickle.dumps(dict(thunk=fn, args=args, kwargs=kwargs), protocol=protocol)
    return base64.b64encode(code).decode("ascii")
