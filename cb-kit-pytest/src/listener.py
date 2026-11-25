import pytest

from cloudbeat_pytest.pytest_reporter import CbPyTestReporter


class CbTestListener:

    def __init__(self, config):
        self.config = config

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_runtest_protocol(self, item):
        reporter: CbPyTestReporter = item.config.cb_reporter
        reporter.start_protocol(item)
        yield
        reporter.end_protocol(item)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        reporter: CbPyTestReporter = item.config.cb_reporter
        reporter.start_setup(item)
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        reporter: CbPyTestReporter = item.config.cb_reporter
        reporter.start_teardown(item)
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        reporter: CbPyTestReporter = item.config.cb_reporter
        result = (yield).get_result()
        if call.when == "call":
            reporter.end_call(item, result)
        elif call.when == "setup":
            reporter.end_setup(item, result)
        elif call.when == "teardown":
            reporter.end_teardown(item, result)