import pytest

from .agh_data import Assignment
from .agh_data import Submission


class AghPtPlugin:
    def __init__(self, config):
        self.config = config
        self.test_dirs = []
        self.results = {}
        # self.progress = Progress(
        #     SpinnerColumn(),
        #     TextColumn("[bold blue]{task.fields[dir]}"),
        #     BarColumn(),
        #     TimeElapsedColumn(),
        # )
        # self.tasks = {}
        # self.json_data = {}

    # def pytest_collection_modifyitems(self, session, config, items):
    #     # Group tests by directory
    #     dir_map = {}
    #     for item in items:
    #         test_dir = Path(item.fspath).parent
    #         dir_map.setdefault(test_dir, []).append(item)
    #     # console.print(dir_map)
    #     self.test_dirs = list(dir_map.keys())

    # def pytest_sessionstart(self, session):
    #     console.print('[bold purple]RPP[/] session start.')
    #     self.live = Live(self.progress, refresh_per_second=10)
    #     self.live.start()

    # def pytest_sessionfinish(self, session, exitstatus):
    #     # self.live.stop()
    #     # Write JSON report
    #     with open("rich_parallel_report.json", "w") as f:
    #         json.dump(self.json_data, f, indent=2)

    # def pytest_configure(self, config):
    #     config._json_report_data = self.json_data

    # def pytest_unconfigure(self, config):
    #     self.live.stop()

    def pytest_report_header(config, start_path, startdir):
        return "AGH Loaded"

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        terminalreporter.write_line("[purple]AGH[/] Test run complete.")
        # terminalreporter.write_line("JSON report saved to rich_parallel_report.json")

    # def run_tests_async(self):
    #     return asyncio.run(self._run_all_tests())

    # async def _run_all_tests(self):
    #     console.print(f'\tTesting: {self.test_dirs}', style='purple')
    #     tasks = []
    #     for test_dir in self.test_dirs:
    #         task = self.progress.add_task("Running", dir=str(test_dir), total=1)
    #         self.tasks[test_dir] = task
    #         tasks.append(self._run_test_dir(test_dir, task))
    #     await asyncio.gather(*tasks)

    # async def _run_test_dir(self, test_dir, task_id):
    #     console.print(f'\t\tTesting [bold]{test_dir}[/ bold]:')
    #     cmd = [sys.executable, "-m", "pytest", str(test_dir), "--disable-warnings"]
    #     proc = await asyncio.create_subprocess_exec(
    #         *cmd,
    #         stdout=asyncio.subprocess.PIPE,
    #         stderr=asyncio.subprocess.PIPE,
    #     )
    #     await proc.communicate()
    #     self.progress.update(task_id, advance=1)


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


# @pytest.fixture(autouse=True)
# def agh_test_fixture():
#     print(">> test fixture")
#     yield True
#     print("<<>> done!")


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
