"""End-to-end tests of the plugin: pytest runs in a subprocess with the plugin and the results file is checked."""

import json
import os

import pytest


def _results(pytester):
    path = os.path.join(str(pytester.path), ".CB_TEST_RESULTS.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _cases(result):
    return {c["name"]: c for s in result["suites"] for c in s["cases"]}


def test_inactive_outside_cloudbeat(pytester, monkeypatch):
    monkeypatch.delenv("CB_AGENT", raising=False)
    pytester.makepyfile(test_sample="def test_ok():\n    assert True\n")
    run = pytester.runpytest_subprocess("-p", "cloudbeat_pytest.plugin")
    run.assert_outcomes(passed=1)
    assert _results(pytester) is None


def test_reports_suites_cases_and_statuses(pytester, monkeypatch):
    monkeypatch.setenv("CB_AGENT", "true")
    pytester.makepyfile(test_sample='''
import pytest

def test_passes():
    """Checks that it passes."""
    assert True

def test_fails():
    assert 1 == 2

@pytest.mark.skip(reason="not now")
def test_skipped():
    pass

@pytest.mark.parametrize("n", [1, 2])
def test_param(n):
    assert n
''')
    pytester.runpytest_subprocess("-p", "cloudbeat_pytest.plugin")
    result = _results(pytester)
    assert [s["fqn"] for s in result["suites"]] == ["test_sample"]
    cases = _cases(result)
    assert cases["test_passes"]["status"] == "passed"
    assert cases["test_passes"]["description"] == "Checks that it passes."
    assert cases["test_fails"]["status"] == "failed"
    assert cases["test_skipped"]["status"] == "skipped"
    assert cases["test_param[1]"]["status"] == "passed" and cases["test_param[2]"]["status"] == "passed"
    failure = cases["test_fails"]["failure"]
    assert failure["type"] == "ASSERT_ERROR"
    assert failure["isFatal"] is True
    assert failure["location"].endswith("test_sample.py:8")   # the failing assert


def test_driver_errors_carry_the_exception_name_in_subtype(pytester, monkeypatch):
    """The server reads camelCase keys (subType, isFatal, displayName): snake_case ones were dropped."""
    pytest.importorskip("selenium")
    monkeypatch.setenv("CB_AGENT", "true")
    # a stand-in for the Appium client's exceptions module
    pytester.mkpydir("appium")
    pytester.mkpydir("appium/common")
    pytester.path.joinpath("appium", "common", "exceptions.py").write_text(
        "class NoSuchContextException(Exception):\n    pass\n")
    pytester.makepyfile(test_drivers='''
from selenium.common.exceptions import NoSuchElementException
from appium.common.exceptions import NoSuchContextException

def test_selenium():
    raise NoSuchElementException("no such element: #login")

def test_appium():
    raise NoSuchContextException("No such context found: WEBVIEW_1")
''')
    pytester.runpytest_subprocess("-p", "cloudbeat_pytest.plugin")
    cases = _cases(_results(pytester))
    selenium = cases["test_selenium"]["failure"]
    assert (selenium["type"], selenium["subType"]) == ("SELENIUM_ERROR", "NoSuchElementException")
    appium = cases["test_appium"]["failure"]
    assert (appium["type"], appium["subType"]) == ("APPIUM_ERROR", "NoSuchContextException")
    assert "sub_type" not in appium and "is_fatal" not in appium
