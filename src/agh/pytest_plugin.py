import subprocess

import pytest

from .agh_data import Assignment
from .agh_data import Submission
from .agh_data import OutputSectionData
from .agh_data import SubmissionFileData
from pathlib import Path

class AghPtPlugin:
    def __init__(self, config):
        self.config = config
        self.test_dirs = []
        self.results = {}

    def pytest_report_header(config, start_path, startdir):
        return "AGH Loaded"

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        terminalreporter.write_line("[purple]AGH[/] Test run complete.")
        # terminalreporter.write_line("JSON report saved to rich_parallel_report.json")


def pytest_addoption(parser):
    parser.addoption("--agh", action="store_true", help="Enable AGH, assignment grading helper, extensions.")


def pytest_configure(config):
    if config.getoption("--agh"):
        plugin = AghPtPlugin(config)
        config.pluginmanager.register(plugin, name="agh_plugin")
        config.addinivalue_line("markers", "build: This marks anything related to building a submission's exe.")
        config.addinivalue_line("markers", "render: This marks anything related to rendering a submission's documentation.")


@pytest.fixture
def agh_submission(request):
    return Submission.load(request.path.parent)


@pytest.fixture
def agh_assignment(request):
    print(request.path)
    return Assignment.load(request.path.parent)


@pytest.fixture
def resultsDir(agh_submission) -> Path:
    ret_val = agh_submission.evaluation_directory / "results"
    ret_val.mkdir(parents=True, exist_ok=True)
    return (ret_val)


def register_render_env_var(env_var_name: str, env_var_value, cache: pytest.Cache):
    env_vars = cache.get("agh_render_env_vars", set())
    env_vars.add(env_var_name)
    cache.set("agh_render_env_vars", list(env_vars))
    cache.set(env_var_name, env_var_value)


def storeRunOutErr(tgt_name: str, res, resultsDir):
    stdout_file = (resultsDir / f'{tgt_name}.stdout')
    stdout_file.write_text(res.stdout)
    stderr_file = (resultsDir / f'{tgt_name}.stderr')
    stderr_file.write_text(res.stderr)


evaluationDataOS = OutputSectionData(path=Path('eval_data_section.md'), title="Evaluation Data",
                                     heading_level=1)
yourCodeOS = OutputSectionData(path=Path('code_section.md'), title="Your Code", heading_level=1)


def _make_sections(resultsDir: Path, agh_assignment: Assignment, agh_submission: Submission):
    global evaluationDataOS, yourCodeOS
    evalOut = resultsDir / evaluationDataOS.path
    evalOut.write_text(evaluationDataOS.asQmdSection())

    codeOut = resultsDir / yourCodeOS.path
    for s_file in agh_assignment.required_files.values():
        if s_file.include_in_output:
            tgt = agh_submission.as_submitted_dir.absolute() / s_file.path.name

            # Create a submission file that points to my submission.
            my_sub_src_file = SubmissionFileData(**s_file.asdict())
            my_sub_src_file.path = tgt.relative_to(agh_submission.evaluation_directory)
            tgt = agh_submission.evaluation_directory / my_sub_src_file.path
            if not tgt.exists():
                tgt.touch()
            yourCodeOS.included_files.append(my_sub_src_file)
    codeOut.write_text(yourCodeOS.asQmdSection())


@pytest.fixture
def agh_build_makefile(agh_submission, shell, cache, request, resultsDir):
    request.applymarker(pytest.mark.build)

    def build(target: str | None = None):
        # Check to see if this is the first time we're building this submission.
        first_build = False
        if not cache.get("agh_build_makefile", False):
            first_build = True

        # Build the submission.
        cmd = ["make"]
        if target is not None:
            cmd.append(target)
        res = shell.run(*cmd, shell=True, cwd=agh_submission.evaluation_directory, env={"AGH_BUILD_TESTING": '1'})

        # Update permanent cache state for initial build ok.
        if first_build:
            cache.set("agh_build_makefile", True)
            build_ok_key = "agh_build_makefile_ok"
            register_render_env_var(build_ok_key, res.returncode == 0, cache)

        stdout_file = (resultsDir / f'{target if target else ""}build.stdout')
        stdout_file.parent.mkdir(exist_ok=True)
        stdout_file.write_text(res.stdout)
        stderr_file = (resultsDir / f'{target if target else ""}build.stderr')
        stderr_file.write_text(res.stderr)

        return res

    yield build

    # if build.res != 0:
    # print(f"Build failed for {agh_submission.submission_file}")


@pytest.fixture
def agh_env_vars(cache):
    environ = {}
    for env_var_name in cache.get("agh_render_env_vars", set()):
        environ[env_var_name] = str(cache.get(env_var_name, ""))
    return environ


@pytest.fixture
def agh_render_output(agh_submission: Submission, shell, agh_env_vars: dict[str, str], request: pytest.FixtureRequest,
                      resultsDir: Path, agh_assignment: Assignment):
    request.applymarker(pytest.mark.render)

    def render(target: str | None = agh_assignment._options.output_template_name, *args: str):
        _make_sections(resultsDir, agh_assignment, agh_submission)
        cmd = ["quarto", "render"]
        if target is not None:
            cmd.append(target)
        if len(args) > 0:
            cmd.extend(args)

        #Clear all render specific errors and warnings
        agh_submission.delWarning('render warning').delError('render error').delWarning('render issue').save()

        try:
            cmd_str = ' '.join(cmd)
            print(f'Executing quarto: {cmd_str}')
            res = shell.run(cmd_str, shell=True, cwd=agh_submission.evaluation_directory)
            (resultsDir/ '.render.stdout.txt').write_text(f"{cmd_str}\n" + res.stdout)
            (resultsDir/ '.render.stderr.txt').write_text(res.stderr)
            if res.returncode != 0:
                agh_submission.addWarning('render issue', f"Render '{cmd_str}' failed with return code {res.returncode}.").save()
                raise RuntimeError(f"quarto failed with return code {res.returncode}")
            agh_assignment.postProcessSubmissionRender(agh_submission, warning_callback=lambda warn: agh_submission.addWarning('render warning', warn)).save()
            return res
        except Exception as e:
            agh_submission.addError('render error', f"Quarto failed with error {e}.").save()
            request.raiseerror(f"Error rendering {agh_submission.submission_file}: {e}")

    return render


