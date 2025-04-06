from cloudbeat_common.reporter import CbTestReporter
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener


# CloudBeat implementation of AbstractEventListener
class CbWebDriverListener(AbstractEventListener):
    def __init__(self, reporter: CbTestReporter):
        self._reporter = reporter

    def before_navigate_to(self, url, driver):
        print(f"Before navigating to: {url}")

    def after_navigate_to(self, url, driver):
        print(f"After navigating to: {url}")

    def before_click(self, element, driver):
        print(f"Before clicking on element: {element.tag_name}")

    def after_click(self, element, driver):
        print(f"After clicking on element: {element.tag_name}")
