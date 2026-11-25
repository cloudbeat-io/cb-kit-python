import functools
import inspect
import logging
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
            arguments = _extract_step_args(func, args, kwargs)
            reporter.start_step(step_name, arguments=arguments)
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
            arguments = _extract_step_args(func, args, kwargs)
            reporter.start_step(resolved_name, arguments=arguments)
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


def _extract_step_args(func, args, kwargs):
    """Return [{name, value}, ...] for all non-self/cls bound parameters."""
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        result = []
        for name, value in bound.arguments.items():
            param = sig.parameters[name]
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if name in ('self', 'cls'):
                continue
            result.append({"name": name, "value": _safe_repr(value)})
        return result
    except Exception:
        return []


def _safe_repr(value):
    try:
        return repr(value)
    except Exception:
        return "<unknown>"


_LOG_LEVEL_MAP = {
    logging.DEBUG: 'debug',
    logging.INFO: 'info',
    logging.WARNING: 'warn',
    logging.ERROR: 'error',
    logging.CRITICAL: 'error',
}


class CbLoggingHandler(logging.Handler):
    """Routes Python logging records to the active CloudBeat case or step."""

    def emit(self, record):
        from cloudbeat_common.reporter import CbTestReporter
        reporter = CbTestReporter.get_instance()
        if reporter is None:
            return
        try:
            level = _LOG_LEVEL_MAP.get(record.levelno, 'info')
            reporter.add_log(record.getMessage(), level, 'user')
        except Exception:
            self.handleError(record)


class CbStreamWrapper:
    """Tees sys.stdout / sys.stderr writes to the active CloudBeat case or step."""

    def __init__(self, original, level):
        self._original = original
        self._level = level
        self._buf = []

    def write(self, text):
        self._original.write(text)
        if not text:
            return
        self._buf.append(text)
        if '\n' in text:
            self._flush_buf()

    def flush(self):
        if self._buf:
            self._flush_buf()
        self._original.flush()

    def _flush_buf(self):
        combined = ''.join(self._buf).rstrip('\n')
        self._buf = []
        for line in combined.splitlines():
            line = line.rstrip()
            if line:
                from cloudbeat_common.reporter import CbTestReporter
                reporter = CbTestReporter.get_instance()
                if reporter is not None:
                    reporter.add_log(line, self._level, 'user')

    def __getattr__(self, name):
        return getattr(self._original, name)


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
