from cloudbeat_common.reporter import CbTestReporter
from cloudbeat_common.models import TestStatus
from _pytest.nodes import Item
from _pytest.reports import TestReport
from cloudbeat_pytest.helpers import get_module_details, get_test_details, calculate_status, get_failure_from_test_report, get_description, get_test_parameters


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
        self._context["captured_sections"] = 0
        case_result.description = get_description(item)
        test_parameters = get_test_parameters(item)
        if test_parameters is not None and len(test_parameters) > 0:
            case_result.add_parameters(test_parameters)
        self.start_console_capture()

    def end_protocol(self, item: Item):
        self.stop_console_capture()
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
        # pytest-rerunfailures runs setup / call / teardown again in the same protocol and counts the attempts in
        # item.execution_count (1 = first run): a new attempt replaces the failed one, so a test that passes on a
        # re-run is reported as passed, with reRunCount = the number of re-runs (CloudBeat counts it as flaky)
        attempt = getattr(item, "execution_count", 1)
        case_result = self._context.get("case")
        if case_result is not None and isinstance(attempt, int) and attempt > 1:
            case_result.restart_for_rerun(attempt - 1, TestStatus.SKIPPED)
        CbTestReporter.start_case_hook(self, "setup")

    def end_setup(self, item: Item, result: TestReport):
        self._add_captured_output(result)
        CbTestReporter.end_case_hook(self)

    def start_teardown(self, item: Item):
        CbTestReporter.start_case_hook(self, "teardown")

    def end_teardown(self, item: Item, result: TestReport):
        self._add_captured_output(result)
        CbTestReporter.end_case_hook(self)

    def _add_captured_output(self, result: TestReport):
        # While pytest captures output (the default, unless -s), it swaps sys.stdout / sys.stderr for its own
        # buffers in every phase, so the console wrapper sees nothing: take what pytest captured instead. A report
        # repeats the sections of the item's earlier phases (and, with pytest-rerunfailures, of earlier attempts),
        # so only the sections not seen yet for this test are added. With -s pytest captures nothing here and the
        # wrapper (start_console_capture) gets the output instead.
        try:
            sections = list(result.sections or [])
            seen = self._context.get("captured_sections") or 0
            for title, content in sections[seen:]:
                if title.startswith("Captured stdout"):
                    level = 'info'
                elif title.startswith("Captured stderr"):
                    level = 'error'
                else:
                    continue    # "Captured log …": logging records arrive through the logging handler
                for line in (content or '').splitlines():
                    line = line.rstrip()
                    if line:
                        self.add_log(line, level, 'user')
            self._context["captured_sections"] = len(sections)
        except Exception:
            pass

    def end_call(self, item: Item, result: TestReport):
        self._add_captured_output(result)
        status = calculate_status(result)
        failure = get_failure_from_test_report(result)
        CbTestReporter.end_case(self, status, failure, skip_api=True)
