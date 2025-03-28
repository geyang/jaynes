import base64
import cloudpickle
import pickle
from typing import Any, Dict, Tuple


def deserialize(code):
    blob = base64.b64decode(code)
    data = cloudpickle.loads(blob)
    return data["thunk"], data["args"] or (), data["kwargs"] or {}


def serialize(
    fn,
    args: Tuple[Any] = None,
    kwargs: Dict[Any, Any] = None,
    protocol=pickle.DEFAULT_PROTOCOL,
):
    """
    for protocol see: https://stackoverflow.com/a/23582505/1560241
    :param fn: the target function to serialize
    :param args:
    :param kwargs:
    :param protocole:
    :return:
    """
    payload = dict(thunk=fn, args=args, kwargs=kwargs)
    code = cloudpickle.dumps(payload, protocol=protocol)
    return base64.b64encode(code).decode("ascii")
