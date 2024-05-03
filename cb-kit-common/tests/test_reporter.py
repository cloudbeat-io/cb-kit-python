from src.reporter import CbTestReporter
from src.models import SuiteResult, CaseResult, StepResult


def test_init(cb_reporter: CbTestReporter):
    assert cb_reporter._config is not None
    assert cb_reporter.result is None


def test_start_instance(cb_reporter: CbTestReporter):
    cb_reporter.start_instance()
    assert cb_reporter.result is not None


def test_start_suite(cb_reporter: CbTestReporter):
    # cb_reporter.start_instance()
    # assert cb_reporter.result is not None
    cb_reporter.start_suite("my suite", "cb.python.suite")
    assert len(cb_reporter.result.suites) > 0
    assert cb_reporter.result.suites[0].name == "my suite"


def test_start_case(cb_reporter: CbTestReporter):
    case_name = "my case"
    case_fqn = "cb.python.suite.case"
    case_result: CaseResult = cb_reporter.start_case(case_name, case_fqn)
    assert len(cb_reporter.result.suites[0].cases) > 0
    assert case_result is not None
    assert cb_reporter.result.suites[0].cases[0] == case_result
    assert case_result.name == case_name
    assert case_result.fqn == case_fqn


def test_start_step(cb_reporter: CbTestReporter):
    step_name = "my step"
    step_result: StepResult = cb_reporter.start_step(step_name)
    assert len(cb_reporter.result.suites[0].cases[0].steps) > 0
    assert step_result is not None
    assert cb_reporter.result.suites[0].cases[0].steps[0] == step_result
    assert step_result.name == step_name


def test_start_sub_step(cb_reporter: CbTestReporter):
    step_name = "my sub step"
    step_result: StepResult = cb_reporter.start_step(step_name)
    assert step_result is not None
    assert len(cb_reporter.result.suites[0].cases[0].steps[0].steps) > 0, \
        "Sub step must be created"


def test_end_sub_step(cb_reporter: CbTestReporter):
    step_result: StepResult = cb_reporter.end_step()


def test_end_case(cb_reporter: CbTestReporter):
    case_result: CaseResult = cb_reporter.end_case()


def test_end_suite(cb_reporter: CbTestReporter):
    suite_result: SuiteResult = cb_reporter.end_suite()


def test_end_instance(cb_reporter: CbTestReporter):
    cb_reporter.end_instance()
