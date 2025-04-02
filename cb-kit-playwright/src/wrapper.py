from cloudbeat_common.reporter import CbTestReporter


class CbPlaywrightWrapper:
    def __init__(self, reporter: CbTestReporter):
        self._reporter = reporter

    def hello(self, world):
        print("hello" + world)
