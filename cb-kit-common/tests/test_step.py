"""Tests for the cb.step decorator and cb.step_context context manager."""

import uuid

import pytest

from cloudbeat_common.models import CbConfig, TestStatus
from cloudbeat_common.reporter import CbTestReporter
from cloudbeat_common import cb


@pytest.fixture(autouse=True)
def _cleanup_reporter():
    """Ensure reporter singleton is cleared after each test."""
    yield
    CbTestReporter._instance = None


@pytest.fixture
def reporter():
    """Create and start a reporter with a suite and case context."""
    config = CbConfig()
    config.run_id = str(uuid.uuid4())
    config.instance_id = str(uuid.uuid4())
    r = CbTestReporter(config)
    r.start_instance()
    r.start_suite("test_suite", "test.suite")
    r.start_case("test_case", "test.suite.case")
    return r


class TestCbStepNoReporter:
    """cb.step is a no-op when no reporter is active."""

    def test_decorator_without_args(self):
        @cb.step
        def my_func():
            return 42

        assert my_func() == 42

    def test_decorator_with_name(self):
        @cb.step("Custom name")
        def my_func():
            return 42

        assert my_func() == 42

    def test_context_manager(self):
        with cb.step_context("Some step"):
            result = 42
        assert result == 42


class TestCbStepDecorator:
    """cb.step creates steps correctly in the reporter."""

    def test_step_with_function_qualname(self, reporter):
        @cb.step
        def my_action():
            pass

        my_action()
        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert "my_action" in case.steps[0].name
        assert case.steps[0].status == TestStatus.PASSED

    def test_step_with_custom_name(self, reporter):
        @cb.step("Custom step name")
        def my_action():
            pass

        my_action()
        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].name == "Custom step name"
        assert case.steps[0].status == TestStatus.PASSED

    def test_step_name_with_format_args(self, reporter):
        @cb.step("Login as {username}")
        def login(username, password):
            pass

        login("admin", "secret")
        case = reporter._context["case"]
        assert case.steps[0].name == "Login as admin"

    def test_step_returns_function_result(self, reporter):
        @cb.step("Get value")
        def get_value():
            return 42

        assert get_value() == 42

    def test_step_failed_on_exception(self, reporter):
        @cb.step("Failing step")
        def failing():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            failing()

        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].status == TestStatus.FAILED
        assert case.steps[0].failure is not None

    def test_exception_is_reraised(self, reporter):
        @cb.step
        def failing():
            raise RuntimeError("must propagate")

        with pytest.raises(RuntimeError, match="must propagate"):
            failing()

    def test_nested_steps(self, reporter):
        @cb.step("Inner step")
        def inner():
            pass

        @cb.step("Outer step")
        def outer():
            inner()

        outer()
        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].name == "Outer step"
        assert len(case.steps[0].steps) == 1
        assert case.steps[0].steps[0].name == "Inner step"

    def test_preserves_function_metadata(self, reporter):
        @cb.step("Named step")
        def documented_func():
            """This is the docstring."""
            pass

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is the docstring."

    def test_works_with_method(self, reporter):
        class MyPage:
            @cb.step("Click button")
            def click_button(self):
                pass

        page = MyPage()
        page.click_button()
        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].name == "Click button"

    def test_format_string_with_self_method(self, reporter):
        class MyPage:
            @cb.step("Enter {value} into field")
            def type_value(self, value):
                pass

        page = MyPage()
        page.type_value("hello")
        case = reporter._context["case"]
        assert case.steps[0].name == "Enter hello into field"


class TestCbStepContext:
    """cb.step_context creates steps as a context manager."""

    def test_creates_step(self, reporter):
        with cb.step_context("Context step"):
            pass

        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].name == "Context step"
        assert case.steps[0].status == TestStatus.PASSED

    def test_failed_on_exception(self, reporter):
        with pytest.raises(ValueError):
            with cb.step_context("Failing context"):
                raise ValueError("ctx error")

        case = reporter._context["case"]
        assert case.steps[0].status == TestStatus.FAILED

    def test_nested_context_managers(self, reporter):
        with cb.step_context("Outer"):
            with cb.step_context("Inner"):
                pass

        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].name == "Outer"
        assert len(case.steps[0].steps) == 1
        assert case.steps[0].steps[0].name == "Inner"

    def test_mixed_decorator_and_context(self, reporter):
        @cb.step("Decorator step")
        def action():
            with cb.step_context("Context sub-step"):
                pass

        action()
        case = reporter._context["case"]
        assert len(case.steps) == 1
        assert case.steps[0].name == "Decorator step"
        assert len(case.steps[0].steps) == 1
        assert case.steps[0].steps[0].name == "Context sub-step"


class TestCbStepArgumentCapture:
    """@cb.step captures function arguments in step.arguments."""

    def test_decorator_without_name_captures_args(self, reporter):
        @cb.step
        def login(username, password):
            pass

        login("admin", "secret")
        step = reporter._context["case"].steps[0]
        assert {"name": "username", "value": repr("admin")} in step.arguments
        assert {"name": "password", "value": repr("secret")} in step.arguments

    def test_decorator_with_name_captures_args(self, reporter):
        @cb.step("Login as {username}")
        def login(username, password):
            pass

        login("admin", "secret")
        step = reporter._context["case"].steps[0]
        assert step.name == "Login as admin"
        assert {"name": "username", "value": repr("admin")} in step.arguments
        assert {"name": "password", "value": repr("secret")} in step.arguments

    def test_self_excluded_from_arguments(self, reporter):
        class MyPage:
            @cb.step("Click {target}")
            def click(self, target):
                pass

        MyPage().click("button")
        step = reporter._context["case"].steps[0]
        names = [a["name"] for a in step.arguments]
        assert "self" not in names
        assert "target" in names

    def test_varargs_excluded_from_arguments(self, reporter):
        @cb.step("Do something")
        def action(*args, **kwargs):
            pass

        action(1, 2, key="val")
        step = reporter._context["case"].steps[0]
        assert step.arguments == []

    def test_no_params_gives_empty_arguments(self, reporter):
        @cb.step("No params")
        def action():
            pass

        action()
        assert reporter._context["case"].steps[0].arguments == []

    def test_step_context_has_empty_arguments(self, reporter):
        with cb.step_context("Block step"):
            pass

        assert reporter._context["case"].steps[0].arguments == []

    def test_bad_repr_falls_back_to_unknown(self, reporter):
        class Unrepresentable:
            def __repr__(self):
                raise RuntimeError("cannot repr")

        @cb.step("Step with bad arg")
        def action(val):
            pass

        action(Unrepresentable())
        step = reporter._context["case"].steps[0]
        assert step.arguments[0] == {"name": "val", "value": "<unknown>"}

    def test_arguments_serialized_in_json(self, reporter):
        import json
        from cloudbeat_common.json_util import to_json

        @cb.step("Login as {username}")
        def login(username):
            pass

        login("admin")
        reporter.end_case()
        reporter.end_suite()
        reporter.end_instance()

        with open(".CB_TEST_RESULTS.json") as f:
            data = json.load(f)

        step_json = data["suites"][0]["cases"][0]["steps"][0]
        assert step_json["arguments"] == [{"name": "username", "value": repr("admin")}]


class TestConsoleCapture:
    """CbTestReporter captures print() and logging output into case/step logs."""

    def test_print_goes_to_case_logs(self, reporter):
        reporter.start_console_capture()
        print("hello from test")
        reporter.stop_console_capture()
        case = reporter._context["case"]
        messages = [log.message for log in case.logs]
        assert "hello from test" in messages

    def test_logging_goes_to_case_logs(self, reporter):
        import logging
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        reporter.start_console_capture()
        logger.info("info log message")
        reporter.stop_console_capture()
        case = reporter._context["case"]
        messages = [log.message for log in case.logs]
        assert "info log message" in messages

    def test_log_level_mapped_correctly(self, reporter):
        import logging
        reporter.start_console_capture()
        logging.getLogger("test_logger").warning("warn msg")
        logging.getLogger("test_logger").error("error msg")
        reporter.stop_console_capture()
        case = reporter._context["case"]
        by_msg = {log.message: log.level for log in case.logs}
        assert by_msg.get("warn msg") == "warn"
        assert by_msg.get("error msg") == "error"

    def test_stderr_captured_as_error(self, reporter):
        import sys
        reporter.start_console_capture()
        print("stderr line", file=sys.stderr)
        reporter.stop_console_capture()
        case = reporter._context["case"]
        error_logs = [log for log in case.logs if log.level == "error"]
        assert any("stderr line" in log.message for log in error_logs)

    def test_print_inside_step_goes_to_step_logs(self, reporter):
        reporter.start_console_capture()
        with cb.step_context("My step"):
            print("inside step")
        reporter.stop_console_capture()
        case = reporter._context["case"]
        assert len(case.steps) == 1
        step_messages = [log.message for log in case.steps[0].logs]
        assert "inside step" in step_messages
        # should NOT appear in case-level logs
        case_messages = [log.message for log in case.logs]
        assert "inside step" not in case_messages

    def test_stop_is_idempotent(self, reporter):
        reporter.start_console_capture()
        reporter.stop_console_capture()
        reporter.stop_console_capture()  # second call must not raise

    def test_start_is_idempotent(self, reporter):
        reporter.start_console_capture()
        reporter.start_console_capture()  # second call must not wrap twice
        print("single capture")
        reporter.stop_console_capture()
        case = reporter._context["case"]
        messages = [log.message for log in case.logs]
        assert messages.count("single capture") == 1

    def test_logs_serialized_in_json(self, reporter):
        import json
        reporter.start_console_capture()
        print("serialized log")
        reporter.stop_console_capture()
        reporter.end_case()
        reporter.end_suite()
        reporter.end_instance()
        with open(".CB_TEST_RESULTS.json") as f:
            data = json.load(f)
        case_json = data["suites"][0]["cases"][0]
        assert "logs" in case_json
        messages = [entry["message"] for entry in case_json["logs"]]
        assert "serialized log" in messages
