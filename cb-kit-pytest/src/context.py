from cloudbeat_pytest.pytest_reporter import CbPyTestReporter
import importlib
import sys


class CbContext:
    class __CbContext:
        _reporter: CbPyTestReporter = None

        def __init__(self, reporter: CbPyTestReporter):
            self._reporter = reporter

        def get_webdriver_listener(self):
            pass

    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not CbContext.instance:
            CbContext.instance = CbContext.__Report()
        return CbContext.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    # def __setattr__(self, name):
    #    return setattr(self.instance, name)

    @staticmethod
    def init(reporter: CbPyTestReporter):
        if not CbContext.instance:
            CbContext.instance = CbContext.__CbContext(reporter)
            print(sys.modules)
            if "cloudbeat_playwright" in sys.modules:
                pw_module = importlib.import_module(".wrapper", "cloudbeat_playwright")
                pw_wrapper_class = getattr(pw_module, "CbPlaywrightWrapper")
                CbContext.instance.__setattr__("pw", pw_wrapper_class(reporter))
            if "cloudbeat_selenium" in sys.modules:
                se_module = importlib.import_module("wrapper", "cloudbeat_selenium")
                se_wrapper_class = getattr(se_module, "CbSeleniumWrapper")
                CbContext.instance.__setattr__("se", se_wrapper_class(reporter))
        return CbContext.instance
