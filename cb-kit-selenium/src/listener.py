from typing import Optional

from cloudbeat_common.models import TestStatus
from cloudbeat_common.reporter import CbTestReporter
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener

from cloudbeat_common.models import StepResult


# CloudBeat implementation of AbstractEventListener
class CbWebDriverListener(AbstractEventListener):
    def __init__(self, reporter: CbTestReporter):
        self._reporter = reporter
        # Track pending find operations to consolidate WebDriverWait retries
        # into a single step instead of one step per poll attempt
        self._pending_find = None       # (by, value) while a find step is open
        self._pending_find_step: Optional[StepResult] = None  # reference to the open StepResult

    def _reset_pending_find(self):
        """End a pending find step as FAILED (e.g. when a different operation starts)."""
        if self._pending_find is not None:
            self._pending_find = None
            self._pending_find_step = None

    def on_exception(self, exception, driver):
        # If this is a NoSuchElementException during a find, keep the step open —
        # WebDriverWait will likely retry and we don't want a separate step per attempt
        if self._pending_find is not None and isinstance(exception, NoSuchElementException):
            try:
                self._pending_find_step.screenshot = driver.get_screenshot_as_base64()
                self._pending_find_step.end(TestStatus.FAILED, exception)
                set_selenium_failure_type(self._pending_find_step)

            except Exception:
                pass
            return

        # For any other exception, close a pending find step first
        self._reset_pending_find()

        # Take screenshot before ending the step
        screenshot = None
        try:
            screenshot = driver.get_screenshot_as_base64()
        except Exception:
            pass

        # End the current step as failed (after_* won't be called on exception)
        step = self._reporter.end_step(TestStatus.FAILED, exception)
        set_selenium_failure_type(step)

        if step is not None and screenshot is not None:
            step.screenshot = screenshot

    def before_navigate_to(self, url, driver):
        self._reset_pending_find()
        self._reporter.start_step(f"Navigate to \"{url}\"")

    def after_navigate_to(self, url, driver):
        self._reporter.end_step()

    def before_click(self, element, driver):
        self._reset_pending_find()
        self._reporter.start_step(f"Click on {get_element_label(element)}")

    def after_click(self, element, driver):
        self._reporter.end_step()

    def before_find(self, by, value, driver) -> None:
        if self._pending_find == (by, value):
            # Same find being retried (e.g. by WebDriverWait) — reuse the open step
            return
        # Different find or first attempt — close any previous pending find and start fresh
        self._reset_pending_find()
        self._pending_find_step = self._reporter.start_step(f"Find element by {by.upper()} \"{value}\"")
        self._pending_find = (by, value)

    def after_find(self, by, value, driver) -> None:
        # Find succeeded, reset previously set failure details
        # if find was executed inside WebDriverWait
        if self._pending_find_step is not None:
            self._pending_find_step.failure = None
            self._pending_find_step.screenshot = None
        self._pending_find = None
        self._pending_find_step = None
        self._reporter.end_step()

    def before_change_value_of(self, element, driver) -> None:
        self._reset_pending_find()
        self._reporter.start_step(f"Set value of {get_element_label(element)}")

    def after_change_value_of(self, element, driver) -> None:
        self._reporter.end_step()

def set_selenium_failure_type(step: StepResult):
    if not step.failure:
        return
    if step.failure.sub_type == "NoSuchElementException":
        step.failure.type = "ELEMENT_NOT_FOUND"

def get_element_label(element):
    if element is None:
        return ""
    elm_text = element.text
    tag_name = element.tag_name
    elm_type = element.get_attribute("type")
    label = ""
    if tag_name == "a":
        label = "link "
    elif tag_name == "button":
        label = "button "
    elif tag_name == "option":
        label = "option "
    elif tag_name == "label":
        label = "label "
    elif tag_name == "input" and (elm_type == "button" or elm_type == "submit"):
        label = "button "
    elif tag_name == "input" and elm_type == "link":
        label = "link "

    if elm_text != "":
        return f"{label} \"{elm_text}\""
    else:
        return f"{label} <{tag_name}>"
