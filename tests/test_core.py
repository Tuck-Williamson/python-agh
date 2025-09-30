from agh import start


def test_start():
    assert start(["a", "bc", "abc"]) == "abc"
