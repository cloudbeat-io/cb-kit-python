import pytest

from cloudbeat_pytest.pytest_reporter import CbPyTestReporter


class CbTestListener:

    def __init__(self, config):
        self.config = config

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_runtest_protocol(self, item):
        reporter: CbPyTestReporter = item.config.cb_reporter
        print(f"Starting protocol: {item.name}")
        reporter.start_protocol(item)
        result = (yield).get_result()
        reporter.end_protocol(item)
        print(f"Finished protocol: {item.name}")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        reporter: CbPyTestReporter = item.config.cb_reporter
        reporter.start_setup(item)
        print(f"Starting setup hook: {item.name}")
        yield
        print(f"Finished setup hook: {item.name}")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        reporter: CbPyTestReporter = item.config.cb_reporter
        reporter.start_teardown(item)
        print(f"Starting teardown hook: {item.name}")
        yield
        print(f"Finished teardown hook: {item.name}")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        print(f"Starting call hook: {item.name}")
        yield
        print(f"Finished call hook: {item.name}")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        reporter: CbPyTestReporter = item.config.cb_reporter
        print(f"Starting makereport hook: {item.name}")
        result = (yield).get_result()
        if call.when == "call":
            reporter.end_call(item, result)
        elif call.when == "setup":
            reporter.end_setup(item, result)
        elif call.when == "teardown":
            reporter.end_teardown(item, result)
        # call.when
        print(f"Finished makereport hook: {item.name}")