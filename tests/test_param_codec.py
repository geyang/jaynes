from jaynes.param_codec import serialize, deserialize


def test():
    def fn(a):
        return a + 1

    code = serialize(fn, [], {"a": 10})
    thunk, args, kwargs = deserialize(code)

    assert 11 == thunk(*args, **kwargs), "result should be 10 + 1 == 11"
    print('test standard succeeded!')


def test_empty():
    def fn():
        return 1

    code = serialize(fn)
    thunk, args, kwargs = deserialize(code)

    assert 1 == thunk(*args, **kwargs), "result should be 1"
    print('test empty input succeeded!')

if __name__ == "__main__":
    test()
    test_empty()
