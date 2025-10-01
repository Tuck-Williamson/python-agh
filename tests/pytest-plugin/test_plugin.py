def test_bar_fixture(pytester):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        def test_good_agh_test_plugin(agh_test_plugin):
            assert agh_test_plugin == "bob"

        @pytest.mark.xfail
        def test_bad_agh_test_plugin(agh_test_plugin):
            assert agh_test_plugin == "alice"
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_good_agh_test_plugin PASSED*",
            "*::test_bad_agh_test_plugin XFAIL*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


# def test_help_message(pytester):
#     result = pytester.runpytest(
#         '--help',
#     )
#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         'agh-test-plugin:',
#         '*--foo=DEST_FOO*Set the value for the fixture "bar".',
#     ])
