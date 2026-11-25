"""Tests for the automation engine stamp ("automation" in each case's context)."""

import json
import types
import uuid

import pytest

from cloudbeat_common.automation import describe_driver
from cloudbeat_common.json_util import to_json
from cloudbeat_common.models import CbConfig
from cloudbeat_common.reporter import CbTestReporter


class FakeDriver:
    def __init__(self, capabilities):
        self.capabilities = capabilities


# a class that looks like the Appium client's driver (module appium.webdriver.webdriver)
AppiumLikeDriver = types.new_class("WebDriver", (FakeDriver,))
AppiumLikeDriver.__module__ = "appium.webdriver.webdriver"


class FakeEventFiring:
    def __init__(self, driver):
        self.wrapped_driver = driver


@pytest.fixture(autouse=True)
def _cleanup_reporter():
    yield
    CbTestReporter._instance = None


@pytest.fixture
def reporter():
    config = CbConfig()
    config.run_id = str(uuid.uuid4())
    config.instance_id = str(uuid.uuid4())
    r = CbTestReporter(config)
    r.start_instance()
    r.start_suite("suite", "suite")
    r.start_case("case", "suite.case")
    r.set_webdriver(None)   # the thread context outlives reporter instances
    return r


def test_ios_capabilities_are_appium():
    info = describe_driver(FakeDriver({"platformName": "iOS", "appium:automationName": "XCUITest",
                                       "appium:deviceName": "iPhone 16", "appium:platformVersion": "18.2"}))
    assert info == {"engine": "appium", "platform": "iOS", "automationName": "XCUITest",
                    "device": "iPhone 16", "platformVersion": "18.2"}


def test_appium_driver_class_is_appium_without_mobile_caps():
    assert describe_driver(AppiumLikeDriver({}))["engine"] == "appium"


def test_browser_is_selenium_and_wrapped_driver_is_unwrapped():
    info = describe_driver(FakeEventFiring(FakeDriver({"browserName": "chrome", "platformName": "linux"})))
    assert info == {"engine": "selenium", "platform": "linux", "browser": "chrome"}


def test_no_driver_gives_none():
    assert describe_driver(None) is None


def test_case_is_stamped_once_and_written_to_json(reporter):
    reporter.set_webdriver(FakeDriver({"platformName": "Android", "appium:automationName": "UiAutomator2"}))
    reporter.end_case()
    reporter.end_case()     # the pytest reporter ends a case twice (call, then protocol)
    case = reporter._result.suites[0].cases[0]
    assert case.context["automation"]["engine"] == "appium"
    data = json.loads(to_json(reporter._result))
    assert data["suites"][0]["cases"][0]["context"]["automation"]["automationName"] == "UiAutomator2"


def test_case_without_driver_has_no_stamp(reporter):
    reporter.end_case()
    assert "automation" not in reporter._result.suites[0].cases[0].context
