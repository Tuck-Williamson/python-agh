import subprocess


def test_main():
    assert subprocess.check_output(["agh", "foo", "foobar"], text=True) == "foobar\n"
