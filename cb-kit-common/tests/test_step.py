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
