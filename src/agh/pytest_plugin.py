import pytest

from .agh_data import Assignment
from .agh_data import Submission


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


@pytest.fixture
def agh_test_plugin(request):
    return "bob"


@pytest.fixture
def json_report_data(request):
    def add_data(key, value):
        nodeid = request.node.nodeid
        report_data = request.config._json_report_data.setdefault(nodeid, {})
        report_data[key] = value

    return add_data


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
    return Submission.load(request.path)


@pytest.fixture
def agh_assignment(request):
    print(request.path)
    return Assignment.load(request.path)


def register_render_env_var(env_var_name: str, env_var_value, cache: pytest.Cache):
    env_vars = cache.get("agh_render_env_vars", set())
    env_vars.add(env_var_name)
    cache.set("agh_render_env_vars", env_vars)
    cache.set(env_var_name, env_var_value)


@pytest.fixture
@pytest.mark.build
def agh_build_makefile(agh_submission, shell, cache):
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
        res = shell.run(cmd, shell=True, cwd=agh_submission.evaluation_directory, env={"AGH_BUILD_TESTING": 1})

        # Update permanent cache state for initial build ok.
        if first_build:
            cache.set("agh_build_makefile", True)
            build_ok_key = "agh_build_makefile_ok"
            register_render_env_var(build_ok_key, res.returncode == 0, cache)
        return res

    yield build

    if build.res != 0:
        print(f"Build failed for {agh_submission.submission_file}")


@pytest.fixture
def agh_env_vars(cache):
    environ = {}
    for env_var_name in cache.get("agh_render_env_vars", set()):
        environ[env_var_name] = cache.get(env_var_name, "")
    return environ


@pytest.fixture
@pytest.mark.render
def agh_render_quarto(agh_submission, shell, agh_env_vars, request):
    request.applymarker(pytest.mark.render)

    def render(target: str | None = None, *args):
        cmd = ["quarto", "render"]
        if target is not None:
            cmd.append(target)
        if len(args) > 0:
            cmd.extend(args)
        res = shell.run(cmd, shell=True, cwd=agh_submission.evaluation_directory, env=agh_env_vars)
        return res

    return render
