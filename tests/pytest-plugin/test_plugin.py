# import pytest
#
# from agh import Assignment
# from agh import Submission
# # from pytestshellutils import shell
#
# # def test_shell(shell: shell):
# #     res = shell.run("echo hello", shell=True)
# #     assert res.stdout.strip() == "hello"
# #
# # def test_shell_fail(shell: shell):
# #     assert shell.run("exit 1", shell=True).returncode == 1
# #
# # def test_shell_env(shell: shell):
# #     res = shell.run("echo $FOO", env={"FOO": "bar"}, shell=True)
# #     assert res.stdout.strip() == "bar"
#
# def test_bar_fixture(pytester):
#     """Make sure that pytest accepts our fixture."""
#
#     # create a temporary pytest test module
#     pytester.makepyfile("""
#         import pytest
#         def test_good_agh_test_plugin(agh_test_plugin):
#             assert agh_test_plugin == "bob"
#
#         @pytest.mark.xfail
#         def test_bad_agh_test_plugin(agh_test_plugin):
#             assert agh_test_plugin == "alice"
#     """)
#
#     # run pytest with the following cmd args
#     result = pytester.runpytest("-v")
#
#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines(
#         [
#             "*::test_good_agh_test_plugin PASSED*",
#             "*::test_bad_agh_test_plugin XFAIL*",
#         ]
#     )
#
#     # make sure that we get a '0' exit code for the testsuite
#     assert result.ret == 0
#
#
# @pytest.fixture
# def get_makefile_fixture(tmp_path, pytester):
#     """Make sure that pytest accepts our fixture."""
#     pytester.makefile(
#         "",
#         Makefile="""
# test:
# 	gcc -g -O0 ./test.c -o test
# bad_test:
#     gcc -g -O0 ./bad_test.c -o bad-test
#     """,
#     )
#
#     pytester.makefile(
#         ".c",
#         test="""
# #include "stdio.h"
# #include <stdlib.h>
#
# int main(int argc, char *argv[])
# {
#   printf("argc = %d\n", argc);
#   return EXIT_SUCCESS;
# }
# """,
#         bad_test="""
# #include "stdio.h"
# #include <stdlib.h>
#
# int main(int argc, char *argv[])
# {
#   printf("argc = %d\n")
#   return EXIT_BOB;
# }
# """,
#     )
#
# # class TestMarks:
# #     @pytest.mark.xfail
# #     def test_build(self, pytester):
# #         """Make sure that we can build a submission's exe."""
# #
# #         pytester.makepyfile("""
# #     import pytest
# #
# #     @pytest.mark.build('test')
# #     def test_makefile_build():
# #         assert
# #     """)
# #         result = pytester.runpytest("-v", "-m", "build")
# #         result.stdout.fnmatch_lines(
# #             [
# #                 "*::makefile_build PASS*",
# #             ]
# #         )
# #         assert result.ret == 0
# #
# #     # def test_help_message(pytester):
# #     #     result = pytester.runpytest(
# #     #         '--help',
# #     #     )
# #     #     # fnmatch_lines does an assertion internally
# #     #     result.stdout.fnmatch_lines([
# #     #         'agh-test-plugin:',
# #     #         '*--foo=DEST_FOO*Set the value for the fixture "bar".',
# #     #     ])
#
#
# @pytest.fixture
# def get_submission_fixture(pytester):
#     a = Assignment(pytester.path)
#     a.save()
#     a.create_missing_directories()
#     sub_file = a.unprocessed_dir / "1234-1231 - Tuck Williamson - September 30 23:29 - filename.c"
#     sub_file.touch()
#     s = a.AddSubmission(sub_file)
#     s.save()
#     return s
#
#
# @pytest.mark.xfail
# def test_assignment_fixture(pytester, get_submission_fixture: Submission):
#     """Testing that the assignment fixture returns the correct assignment."""
#     test_py = pytester.makepyfile(f"""
#     import pytest
#     from pathlib import Path
#
#     # @pytest.fixture
#     # def setup_assignment():
#     #     a = Assignment.load(Path('{get_submission_fixture.evaluation_directory.absolute()}'))
#     #     a.name = "Test Assignment"
#     #     a.save()
#
#     def test_assignment_ptp( agh_assignment):
#         assert agh_assignment.name == "Test Assignment"
#     """)
#     a = Assignment.load(get_submission_fixture.evaluation_directory)
#     a.name = "Test Assignment"
#     test_py.replace(a.tests_dir / test_py.name)
#     result = pytester.runpytest("-v")
#     result.stdout.fnmatch_lines(
#         [
#             "*::test_assignment_fixture PASSED*",
#         ]
#     )
#     assert result.ret == 0
#
#
# @pytest.mark.xfail
# def test_submission_fixture(pytester, get_submission_fixture: Submission):
#     pytester.makepyfile("""
#     import pytest
#
#     def test_submission_fixture(agh_submission):
#         pass
# """)
