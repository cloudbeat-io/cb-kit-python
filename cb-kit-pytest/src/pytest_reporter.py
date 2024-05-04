from cloudbeat_common.reporter import CbTestReporter
from cloudbeat_common.models import TestStatus
from _pytest.nodes import Item
from _pytest.reports import TestReport
from cloudbeat_pytest.helpers import get_module_details, get_test_details, calculate_status, get_description, get_test_parameters


class CbPyTestReporter(CbTestReporter):
    def start_protocol(self, item: Item):
        # Check if current test's module has already a related suite result
        module_details = get_module_details(item)
        current_suite_result = self._context["suite"] if "suite" in self._context else None
        if current_suite_result is None or current_suite_result.fqn != module_details["fqn"]:
            CbTestReporter.start_suite(self, module_details["module_name"], module_details["fqn"])
        test_details = get_test_details(item)
        case_result = CbTestReporter.start_case(self, test_details["name"], test_details["fqn"])
        # Set case status as SKIPPED by default, because if the test is skipped,
        # pytest_runtest_call hook won't be called and we won't get any indication
        # if the test has been skipped
        case_result.status = TestStatus.SKIPPED
        case_result.description = get_description(item)
        test_parameters = get_test_parameters(item)
        if test_parameters is not None and len(test_parameters) > 0:
            case_result.add_parameters(test_parameters)

    def end_protocol(self, item: Item):
        # Call end_case again (previously called in end_call),
        # so end_time will include teardown hook
        CbTestReporter.end_case(self)
        # Check if current test's module has already a related suite result
        module_details = get_module_details(item)
        suite_result = self._context["suite"] if "suite" in self._context else None
        if suite_result is None or suite_result.fqn != module_details["fqn"]:
            next(suite_result for suite in self.result.suites if suite.fqn == module_details["fqn"])
        if suite_result is None:
            return
        suite_result.end()

    def start_setup(self, item: Item):
        CbTestReporter.start_case_hook(self, "setup")

    def end_setup(self, item: Item, result: TestReport):
        CbTestReporter.end_case_hook(self)

    def start_teardown(self, item: Item):
        CbTestReporter.start_case_hook(self, "teardown")

    def end_teardown(self, item: Item, result: TestReport):
        CbTestReporter.end_case_hook(self)

    def end_call(self, item: Item, result: TestReport):
        status = calculate_status(result)
        CbTestReporter.end_case(self, status)
