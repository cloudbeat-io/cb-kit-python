"""End-to-end runs of the plugin: re-runs (pytest-rerunfailures) and console output while pytest captures it."""

import json
import os

import pytest

pytest.importorskip("pytest_rerunfailures")

TEST_FILE = """
import os, pathlib

def test_flaky():
    marker = pathlib.Path("attempts.txt")
    n = int(marker.read_text()) + 1 if marker.exists() else 1
    marker.write_text(str(n))
    print(f"attempt {n}")
    assert n >= 3, f"failed on attempt {n}"

def test_stable():
    assert True

def test_always_fails():
    assert False, "always"
"""


def _run(pytester, monkeypatch):
    monkeypatch.setenv("CB_AGENT", "true")
    for name in ("CB_TEST_MONITOR_URL", "CB_TEST_MONITOR_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    pytester.makepyfile(test_sample=TEST_FILE)
    pytester.runpytest_subprocess("-p", "cloudbeat_pytest.plugin", "--reruns", "3")
    with open(os.path.join(str(pytester.path), ".CB_TEST_RESULTS.json")) as f:
        result = json.load(f)
    return {c["name"]: c for s in result["suites"] for c in s["cases"]}


def test_passed_on_rerun_is_passed_with_rerun_count(pytester, monkeypatch):
    cases = _run(pytester, monkeypatch)
    flaky = cases["test_flaky"]
    assert flaky["status"] == "passed"
    assert flaky["reRunCount"] == 2
    assert flaky["failure"] is None
    assert [log["message"] for log in flaky["logs"]] == ["attempt 3"]   # only the last attempt
    assert len([h for h in flaky["hooks"] if h["name"] == "setup"]) == 1


def test_not_rerun_has_no_count_and_exhausted_reruns_stay_failed(pytester, monkeypatch):
    cases = _run(pytester, monkeypatch)
    assert cases["test_stable"]["reRunCount"] is None
    assert cases["test_stable"]["status"] == "passed"
    assert cases["test_always_fails"]["status"] == "failed"
    assert cases["test_always_fails"]["reRunCount"] == 3
    assert "always" in cases["test_always_fails"]["failure"]["message"]


def test_print_and_logging_are_captured_while_pytest_captures_output(pytester, monkeypatch):
    monkeypatch.setenv("CB_AGENT", "true")
    pytester.makepyfile(test_output="""
import logging, sys

def test_out():
    print("printed line")
    print("to stderr", file=sys.stderr)
    logging.getLogger("app").warning("logged warning")
""")
    pytester.runpytest_subprocess("-p", "cloudbeat_pytest.plugin")
    with open(os.path.join(str(pytester.path), ".CB_TEST_RESULTS.json")) as f:
        case = json.load(f)["suites"][0]["cases"][0]
    logs = {log["message"]: log["level"] for log in case["logs"]}
    assert logs == {"printed line": "info", "to stderr": "error", "logged warning": "warn"}
