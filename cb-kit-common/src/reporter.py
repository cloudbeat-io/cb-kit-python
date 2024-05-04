import threading
from collections import OrderedDict, defaultdict
import platform

from cloudbeat_common.models import TestResult, CbConfig, SuiteResult, CaseResult, StepResult
from cloudbeat_common.json_util import to_json


class ThreadContext:
    _thread_context = defaultdict(OrderedDict)
    _init_thread: threading.Thread

    @property
    def thread_context(self):
        context = self._thread_context[threading.current_thread()]
        if not context and threading.current_thread() is not self._init_thread:
            uuid, last_item = next(reversed(self._thread_context[self._init_thread].items()))
            context[uuid] = last_item
        return context

    def __init__(self, *args, **kwargs):
        self._init_thread = threading.current_thread()
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        self.thread_context.__setitem__(key, value)

    def __getitem__(self, item):
        return self.thread_context.__getitem__(item)

    def __iter__(self):
        return self.thread_context.__iter__()

    def __reversed__(self):
        return self.thread_context.__reversed__()

    def get(self, key):
        return self.thread_context.get(key)

    def pop(self, key):
        return self.thread_context.pop(key)

    def cleanup(self):
        stopped_threads = []
        for thread in self._thread_context.keys():
            if not thread.is_alive():
                stopped_threads.append(thread)
        for thread in stopped_threads:
            del self._thread_context[thread]


class CbTestReporter:
    _result: TestResult = None
    _config: CbConfig = None

    def __init__(self, config: CbConfig):
        self._context = ThreadContext()
        self._config = config

    def start_instance(self):
        self._result = TestResult()
        self._result.start(
            self._config.run_id,
            self._config.instance_id,
            self._config.options,
            self._config.capabilities,
            self._config.metadata,
            self._config.env_vars)
        self._add_system_attributes()

    def end_instance(self) -> None:
        if self._result is None:
            return
        self._result.end()
        # Serializing json
        json_str = to_json(self._result)

        # Writing to sample.json
        with open(".CB_TEST_RESULTS.json", "w") as outfile:
            outfile.write(json_str)

    def start_suite(self, name, fqn=None):
        if self._result is None:
            return None
        suite_result = SuiteResult()
        suite_result.start(name, fqn)
        self._result.suites.append(suite_result)
        self._context["suite"] = suite_result
        self._context["case"] = None
        return suite_result

    def end_suite(self):
        if self._context["suite"] is None:
            return None
        suite_result: SuiteResult = self._context["suite"]
        suite_result.end()
        return suite_result

    def start_case(self, name, fqn=None):
        if self._context["suite"] is None:
            return None
        case_result = CaseResult()
        case_result.start(name, fqn)
        suite_result: SuiteResult = self._context["suite"]
        suite_result.add_case(case_result)
        self._context["case"] = case_result
        return case_result

    def end_case(self, status=None):
        case_result: CaseResult = self._context["case"] if "case" in self._context else None
        if case_result is None:
            return None
        # TODO: end started steps of the case
        case_result.end(status)
        return case_result

    def start_case_hook(self, name):
        case_result: CaseResult = self._context["case"] if "case" in self._context else None
        if case_result is None:
            return None
        return case_result.start_hook(name)

    def end_case_hook(self, status=None):
        case_result: CaseResult = self._context["case"] if "case" in self._context else None
        if case_result is None:
            return None
        return case_result.end_hook(status)

    def start_step(self, name, fqn=None):
        if self._context["case"] is None:
            return None
        case_result: CaseResult = self._context["case"]
        step_result = case_result.start_step(name, fqn)
        return step_result

    def end_step(self):
        if self._context["case"] is None:
            return None
        case_result: CaseResult = self._context["case"]
        return case_result.end_step()

    def _add_system_attributes(self):
        self._result.test_attributes["agent.hostname"] = platform.node()
        self._result.test_attributes["agent.os.name"] = platform.system()
        # Determine OS version
        os_version = platform.version() if platform.system() != "Darwin" else platform.mac_ver()[0]
        self._result.test_attributes["agent.os.version"] = os_version

    @property
    def result(self):
        return self._result
