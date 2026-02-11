import sys
from itertools import chain, islice

from _pytest.doctest import DoctestItem
from _pytest.nodes import Item
from _pytest.python import Class, Function, Module
from _pytest.reports import TestReport
from cloudbeat_common.models import TestStatus, FailureResult


def get_module_details(item: Item):
    head, maybe_class, tail = islice(chain(item.nodeid.split('::'), [None], [None]), 3)
    class_name = maybe_class if tail else None
    file_name, path = islice(chain(reversed(head.rsplit('/', 1)), [None]), 2)
    module_name = file_name.split('.')[0]
    package_name = path.replace('/', '.') if path else None
    fqn = f"{package_name + '.' if package_name is not None else ''}{module_name}"
    return {
        "package_name": package_name,
        "module_name": module_name,
        "class_name": class_name,
        "fqn": fqn
    }


def get_test_details(item: Item):
    return {
        "fqn": item.nodeid,
        "name": item.name
    }


def calculate_status(result: TestReport):
    if result.skipped:
        return TestStatus.SKIPPED
    elif result.failed:
        return TestStatus.FAILED
    return TestStatus.PASSED


def get_failure_from_test_report(result: TestReport):
    if not result.failed:
        return None

    failure = FailureResult()

    if result.longrepr is not None:
        # longrepr can be an ExceptionRepr (with reprcrash/reprtraceback) or a plain string
        if hasattr(result.longrepr, 'reprcrash') and result.longrepr.reprcrash is not None:
            crash = result.longrepr.reprcrash
            crash_message = crash.message or ''
            # reprcrash.message format is typically "ExceptionType: message details"
            # but for assertion errors, it's just "assert ..." without the type prefix
            if ':' in crash_message:
                failure.type = crash_message.split(':', 1)[0].strip()
                failure.message = crash_message.split(':', 1)[1].strip()
            else:
                failure.message = crash_message
                # Extract exception type from last line of longreprtext
                # Format: "path:lineno: ExceptionType"
                last_line = result.longreprtext.strip().rsplit('\n', 1)[-1]
                exc_type = last_line.rsplit(': ', 1)[-1] if ': ' in last_line else crash_message
                failure.type = exc_type
            failure.location = f"{crash.path}:{crash.lineno}"

        failure.stacktrace = result.longreprtext

    return failure


def get_description(item):
    if isinstance(item, (Class, Function, Module, Item)):
        if hasattr(item, "obj"):
            doc = item.obj.__doc__
            if doc is not None:
                return trim_docstring(doc)
    if isinstance(item, DoctestItem):
        return item.reportinfo()[2]


def trim_docstring(docstring: str) -> str:
    """
    Convert docstring.

    :param docstring: input docstring
    :return: trimmed docstring
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def get_test_parameters(item: Item):
    return item.callspec.params if hasattr(item, 'callspec') else None
