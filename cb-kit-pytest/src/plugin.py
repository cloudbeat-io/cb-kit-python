import pytest
from cloudbeat_common.models import CbConfig
from cloudbeat_common.reporter import CbTestReporter

from listener import CbTestListener
from pytest_reporter import CbPyTestReporter

print("--- cloudbeat_pytest")


def pytest_addoption(parser):
    group = parser.getgroup("cloudbeat")
    group.addoption(
        "--name",
        action="store",
        dest="name",
        default="World",
        help='Default "name" for hello().',
    )


def get_cb_config(config):
    return CbConfig()


def pytest_configure(config):
    print("--- pytest_configure")
    # if not config.option.cb_enabled:
    #    return
    cb_config: CbConfig = get_cb_config(config)
    config.cb_reporter = CbPyTestReporter(cb_config)
    test_listener = CbTestListener(config)
    config.pluginmanager.register(test_listener, 'cloudbeat_listener')


def pytest_sessionstart(session):
    if session.config.cb_reporter is None:
        return
    reporter: CbPyTestReporter = session.config.cb_reporter
    reporter.start_instance()
    # reporter.start_suite("default")


def pytest_sessionfinish(session):
    if session.config.cb_reporter is None:
        return
    reporter: CbPyTestReporter = session.config.cb_reporter
    # reporter.end_suite()
    reporter.end_instance()


@pytest.fixture
def hello(request):
    if request.config.cb_enabled is None:
        raise Exception("Sorry, no numbers below zero")

    def _hello(name=None):
        if not name:
            name = request.config.getoption("name")
        return "Hello {name}!".format(name=name)

    return _hello
