import traceback
from typing import Optional


def get_failure_from_exception(exception: Optional[Exception]):
    if not exception:
        return None

    from cloudbeat_common.models import FailureResult
    failure = FailureResult()
    exc_module = getattr(exception.__class__, '__module__', '') or ''
    failure.sub_type = exception.__class__.__name__
    if exc_module.startswith('selenium.common.exceptions'):
        failure.type = 'SELENIUM_ERROR'
    elif 'AssertionError' in failure.sub_type:
        failure.type = 'ASSERT_ERROR'
    else:
        failure.type = 'GENERAL_ERROR'
    failure.message = _clean_exception_message(str(exception))
    failure.is_fatal = True

    tb = exception.__traceback__
    if tb is not None:
        failure.stacktrace = ''.join(traceback.format_exception(type(exception), exception, tb))
        # Walk frames from innermost to outermost and pick the deepest
        # frame that belongs to user code (not a library)
        frame = tb
        while frame is not None:
            filename = frame.tb_frame.f_code.co_filename
            if 'site-packages' not in filename and not filename.startswith('<'):
                failure.location = f"{filename}:{frame.tb_lineno}"
            frame = frame.tb_next

    return failure


def _clean_exception_message(message: str) -> Optional[str]:
    """Extract only the human-readable message, stripping Selenium/driver noise."""
    if not message:
        return None
    # Remove everything from "Stacktrace:" onwards
    idx = message.find('Stacktrace:')
    if idx != -1:
        message = message[:idx]
    # Remove Selenium's "Message:" prefix
    message = message.strip()
    if message.startswith('Message:'):
        message = message[len('Message:'):].strip()
    return message if message else None
