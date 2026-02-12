import functools
import inspect
from contextlib import contextmanager

from cloudbeat_common.models import TestStatus


def step(name_or_func=None):
    """Decorator that wraps a function as a CloudBeat step.

    Any steps created inside the decorated function (e.g. Selenium events)
    automatically become sub-steps of this step.

    Usage:
        @cb.step
        def do_something(self):
            ...

        @cb.step("Custom step name")
        def do_something(self):
            ...

        @cb.step("Login as {username}")
        def login(self, username, password):
            ...

    No-op when no reporter is active (e.g. running tests locally).
    """
    # @cb.step without parentheses — name_or_func IS the decorated function
    if callable(name_or_func):
        func = name_or_func
        step_name = func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from cloudbeat_common.reporter import CbTestReporter
            reporter = CbTestReporter.get_instance()
            if reporter is None:
                return func(*args, **kwargs)
            reporter.start_step(step_name)
            try:
                result = func(*args, **kwargs)
                reporter.end_step(TestStatus.PASSED)
                return result
            except Exception as e:
                reporter.end_step(TestStatus.FAILED, e)
                raise

        return wrapper

    # @cb_step("name") or @cb_step() — name_or_func is a string or None
    custom_name = name_or_func

    def decorator(func):
        base_name = custom_name if custom_name is not None else func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from cloudbeat_common.reporter import CbTestReporter
            reporter = CbTestReporter.get_instance()
            if reporter is None:
                return func(*args, **kwargs)

            resolved_name = _resolve_step_name(base_name, func, args, kwargs)
            reporter.start_step(resolved_name)
            try:
                result = func(*args, **kwargs)
                reporter.end_step(TestStatus.PASSED)
                return result
            except Exception as e:
                reporter.end_step(TestStatus.FAILED, e)
                raise

        return wrapper

    return decorator


def _resolve_step_name(name_template, func, args, kwargs):
    """Resolve format placeholders in step name using function arguments."""
    if '{' not in name_template:
        return name_template
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return name_template.format(**bound.arguments)
    except (TypeError, KeyError, IndexError):
        return name_template


@contextmanager
def step_context(name):
    """Context manager that wraps a block as a CloudBeat step.

    Usage:
        with cb.step_context("Verify results"):
            assert result == expected
    """
    from cloudbeat_common.reporter import CbTestReporter

    reporter = CbTestReporter.get_instance()
    if reporter is None:
        yield
        return

    reporter.start_step(name)
    try:
        yield
        reporter.end_step(TestStatus.PASSED)
    except Exception as e:
        reporter.end_step(TestStatus.FAILED, e)
        raise
