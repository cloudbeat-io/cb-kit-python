import traceback
from typing import Optional


def get_failure_from_exception(exception: Optional[Exception]):
    if not exception:
        return None

    from cloudbeat_common.models import FailureResult
    failure = FailureResult()
    failure.sub_type = exception.__class__.__name__
    failure.type = 'ASSERT_ERROR' if 'AssertionError' in failure.sub_type else 'GENERAL_ERROR'
    failure.message = str(exception) if str(exception) else None
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
