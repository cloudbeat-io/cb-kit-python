from cloudbeat_common.reporter import CbTestReporter
from selenium import webdriver
from selenium.webdriver.support.event_firing_webdriver import EventFiringWebDriver

from cloudbeat_selenium.listener import CbWebDriverListener

class CbSeleniumWrapper:
    def __init__(self, reporter: CbTestReporter):
        self._reporter = reporter

    def wrap(self, driver: webdriver):
        listener = CbWebDriverListener(self._reporter)
        if self._reporter is not None and hasattr(self._reporter, "set_webdriver"):
            self._reporter.set_webdriver(driver)
        return EventFiringWebDriver(driver, listener)
