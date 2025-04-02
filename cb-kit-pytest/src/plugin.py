import os

import pytest
from cloudbeat_common.models import CbConfig

from cloudbeat_pytest.listener import CbTestListener
from cloudbeat_pytest.pytest_reporter import CbPyTestReporter

from context import CbContext


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
    cb_config = CbConfig()
    if os.environ.get("CB_AGENT") is not None and os.environ["CB_AGENT"] == "true":
        cb_config.is_ready = True
    cb_config.run_id = os.environ.get("CB_RUN_ID")
    cb_config.instance_id = os.environ.get("CB_INSTANCE_ID")
    cb_config.project_id = os.environ.get("CB_PROJECT_ID")
    cb_config.api_endpoint_url = os.environ.get("CB_API_URL")
    cb_config.api_token = os.environ.get("CB_API_KEY")
    cb_config.selenium_url = os.environ.get("CB_SELENIUM_URL")
    cb_config.appium_url = os.environ.get("CB_APPIUM_URL")
    if os.environ.get("CB_BROWSER_NAME") is not None:
        cb_config.capabilities["browserName"] = os.environ["CB_BROWSER_NAME"]
    return cb_config


def pytest_configure(config):
    print("--- pytest_configure")
    # if not config.option.cb_enabled:
    #    return
    cb_config: CbConfig = get_cb_config(config)
    if not cb_config.is_ready:
        return
    config.cb_reporter = CbPyTestReporter(cb_config)
    test_listener = CbTestListener(config)
    config.pluginmanager.register(test_listener, 'cloudbeat_listener')


def pytest_sessionstart(session):
    if session.config.cb_reporter is None:
        return
    reporter: CbPyTestReporter = session.config.cb_reporter
    reporter.start_instance()


def pytest_sessionfinish(session):
    if session.config.cb_reporter is None:
        return
    reporter: CbPyTestReporter = session.config.cb_reporter
    reporter.end_instance()


@pytest.fixture(scope="session")
# instantiates ini file parses object
def cbx(request) -> CbContext:
    reporter = request.session.config.cb_reporter
    context = CbContext.init(reporter)
    return context
