import threading
import time
from collections import OrderedDict, defaultdict
import platform
from typing import Optional

from cloudbeat_common.models import TestResult, CbConfig, SuiteResult, CaseResult, StepResult
from cloudbeat_common.json_util import to_json
from cloudbeat_common.client import CaseStatusUpdateReq, RuntimeApiV2

_LANGUAGE_NAME = "python"


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
    _instance: 'CbTestReporter' = None
    _result: TestResult = None
    _config: CbConfig = None

    def __init__(self, config: CbConfig):
        self._context = ThreadContext()
        self._config = config
        self._api_client: Optional[RuntimeApiV2] = None

        if config.api_endpoint_url and config.api_token:
            self._api_client = RuntimeApiV2(config.api_endpoint_url, config.api_token)

    @classmethod
    def get_instance(cls) -> 'CbTestReporter':
        return cls._instance

    def start_instance(self):
        CbTestReporter._instance = self
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
        CbTestReporter._instance = None
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
        suite_result: SuiteResult = self._context.get("suite")
        if suite_result is None:
            return None
        suite_result.end()
        return suite_result

    def start_case(self, name, fqn=None):
        suite_result: SuiteResult = self._context.get("suite")
        if suite_result is None:
            return None
        case_result = CaseResult()
        case_result.start(name, fqn)
        suite_result.add_case(case_result)
        self._context["case"] = case_result
        if self._api_client:
            caps = None
            if case_result.context and case_result.context.get("browserName"):
                caps = {"browserName": case_result.context["browserName"]}
            self._api_client.update_case_status(CaseStatusUpdateReq(
                timestamp=int(time.time() * 1000),
                run_id=self._config.run_id,
                instance_id=self._config.instance_id,
                id=case_result.id,
                fqn=case_result.fqn,
                parent_fqn=suite_result.fqn,
                parent_id=suite_result.id,
                name=case_result.name,
                start_time=case_result.start_time,
                run_status="Running",
                framework=self._config.framework,
                language=_LANGUAGE_NAME,
                capabilities=caps,
            ))
        return case_result

    def end_case(self, status=None, failure=None, skip_api=False):
        case_result: CaseResult = self._context.get("case")
        if case_result is None:
            return None
        case_result.end(status, failure)
        if self._api_client and not skip_api:
            suite_result: SuiteResult = self._context.get("suite")
            self._api_client.update_case_status(CaseStatusUpdateReq(
                timestamp=int(time.time() * 1000),
                run_id=self._config.run_id,
                instance_id=self._config.instance_id,
                id=case_result.id,
                fqn=case_result.fqn,
                parent_fqn=suite_result.fqn if suite_result else None,
                parent_id=suite_result.id if suite_result else None,
                name=case_result.name,
                start_time=case_result.start_time,
                end_time=case_result.end_time,
                run_status="Finished",
                test_status=case_result.status,
                framework=self._config.framework,
                language=_LANGUAGE_NAME,
            ))
        return case_result

    def start_case_hook(self, name):
        case_result: CaseResult = self._context.get("case")
        if case_result is None:
            return None
        return case_result.start_hook(name)

    def end_case_hook(self, status=None):
        case_result: CaseResult = self._context.get("case")
        if case_result is None:
            return None
        return case_result.end_hook(status)

    def start_step(self, name, fqn=None):
        case_result: CaseResult = self._context.get("case")
        if case_result is None:
            return None
        step_result = case_result.start_step(name, fqn)
        return step_result

    def end_step(self, status=None, exception=None):
        case_result: CaseResult = self._context.get("case")
        if case_result is None:
            return None
        return case_result.end_step(status, exception)

    def _add_system_attributes(self):
        self._result.test_attributes["agent.hostname"] = platform.node()
        self._result.test_attributes["agent.os.name"] = platform.system()
        # Determine OS version
        os_version = platform.version() if platform.system() != "Darwin" else platform.mac_ver()[0]
        self._result.test_attributes["agent.os.version"] = os_version

    @property
    def result(self):
        return self._result