from cloudbeat_common.reporter import CbTestReporter
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener


# CloudBeat implementation of AbstractEventListener
class CbWebDriverListener(AbstractEventListener):
    def __init__(self, reporter: CbTestReporter):
        self._reporter = reporter

    def before_navigate_to(self, url, driver):
        self._reporter.start_step(f"Navigate to \"{url}\"")

    def after_navigate_to(self, url, driver):
        self._reporter.end_step()

    def before_click(self, element, driver):
        self._reporter.start_step(f"Click on {get_element_label(element)}")

    def after_click(self, element, driver):
        self._reporter.end_step()

    def before_find(self, by, value, driver) -> None:
        self._reporter.start_step(f"Find element by {by.upper()} \"{value}\"")

    def after_find(self, by, value, driver) -> None:
        self._reporter.end_step()

    def before_change_value_of(self, element, driver) -> None:
        self._reporter.start_step(f"Set value of {get_element_label(element)}")

    def after_change_value_of(self, element, driver) -> None:
        self._reporter.end_step()

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
