import time
from typing import List

from attr import attrs, attrib
from attr import Factory
from collections import OrderedDict, defaultdict
import uuid


class TestStatus:
    FAILED = 'failed'
    BROKEN = 'broken'
    PASSED = 'passed'
    SKIPPED = 'skipped'
    UNKNOWN = 'unknown'


class StepType:
    GENERAL = 'general'
    HOOK = 'hook'
    TRANSACTION = 'transaction'
    HTTP = 'http'
    ASSERT = 'assert'


@attrs
class CbConfig:
    is_ready = attrib(default=False)
    run_id = attrib(default=None)
    run_group = attrib(default=None)
    instance_id = attrib(default=None)
    project_id = attrib(default=None)
    api_token = attrib(default=None)
    api_endpoint_url = attrib(default=None)
    selenium_url = attrib(default=None)
    appium_url = attrib(default=None)
    capabilities = attrib(default=defaultdict(OrderedDict))
    options = attrib(default=defaultdict(OrderedDict))
    metadata = attrib(default=defaultdict(OrderedDict))
    env_vars = attrib(default=defaultdict(OrderedDict))


@attrs
class TestResult:
    start_time = attrib(default=None)
    end_time = attrib(default=None)
    duration = attrib(default=None)

    run_id = attrib(default=None)
    instance_id = attrib(default=None)
    capabilities = attrib(default=defaultdict(OrderedDict))
    options = attrib(default=defaultdict(OrderedDict))
    meta_data = attrib(default=defaultdict(OrderedDict))
    environment_variables = attrib(default=defaultdict(OrderedDict))
    test_attributes = attrib(default=defaultdict(OrderedDict))

    hooks = attrib(default=Factory(list))
    suites = attrib(default=Factory(list))
    failures = attrib(default=Factory(list))
    status: TestStatus = attrib(default=None)

    def __iter__(self):
        yield from {
            "startTime": self.start_time,
            "endTime": self.end_time,
            "duration": self.duration,
            "runId": self.run_id,
            "instanceId": self.instance_id
        }.items()

    def __str__(self):
        return json.dumps(dict(self), cls=MyJSONEncoder, ensure_ascii=False)

    def start(self, run_id, instance_id, options, caps, metadata, env_vars):
        self.run_id = run_id
        self.instance_id = instance_id
        self.start_time = int(time.time() * 1000)
        self.options = options
        self.capabilities = caps
        self.meta_data = metadata
        self.environment_variables = env_vars

    def end(self):
        self.end_time = int(time.time() * 1000)
        self.duration = self.end_time - self.start_time


@attrs
class TestableResultBase:
    id = attrib(default=str(uuid.uuid4()))
    name = attrib(default=None)
    display_name = attrib(default=None)
    description = attrib(default=None)
    fqn = attrib(default=None)
    status = attrib(default=TestStatus.PASSED)
    attachments = attrib(default=Factory(list))
    arguments = attrib(default=Factory(list))
    hooks = attrib(default=Factory(list))
    start_time = attrib(default=None)
    end_time = attrib(default=None)
    duration = attrib(default=None)


@attrs
class SuiteResult(TestableResultBase):
    cases = attrib(default=Factory(list))

    def start(self, name, fqn=None):
        self.name = name
        self.fqn = fqn
        self.start_time = int(time.time() * 1000)

    def end(self, status=None):
        self.end_time = int(time.time() * 1000)
        self.duration = self.end_time - self.start_time
        # Mark suite as FAILED if at least one of the test case has failed
        has_failed_cases = any(c.status == TestStatus.FAILED for c in self.cases)
        if has_failed_cases and status is None:
            self.status = TestStatus.FAILED
        elif status is not None:
            self.status = status

    def add_case(self, case_result):
        self.cases.append(case_result)


@attrs
class StepResult(TestableResultBase):
    type: StepType = attrib(default=None)
    steps = attrib(default=Factory(list))
    logs = attrib(default=Factory(list))

    def start(self, name, fqn=None):
        self.name = name
        self.fqn = fqn
        self.start_time = int(time.time() * 1000)

    def end(self, status=TestStatus.PASSED):
        self.end_time = int(time.time() * 1000)
        self.duration = self.end_time - self.start_time
        self.status = status if status is not None else TestStatus.PASSED


@attrs
class CaseResult(TestableResultBase):
    context = defaultdict(OrderedDict)
    steps = attrib(default=Factory(list))
    _started_steps_stack: List[StepResult] = []

    def start(self, name, fqn=None):
        self.name = name
        self.fqn = fqn
        self.start_time = int(time.time() * 1000)

    def end(self, status=None):
        # End all unfinished steps
        for _ in range(len(self._started_steps_stack)):
            step_result = self._started_steps_stack.pop()
            step_result.end()
        # Do not override the calculated FAILED status by the status function argument
        if status is not None and self.status != TestStatus.FAILED:
            self.status = status
        self.end_time = int(time.time() * 1000)
        self.duration = self.end_time - self.start_time

    def start_hook(self, name):
        hook_result = StepResult()
        hook_result.start(name)
        hook_result.type = StepType.HOOK
        self.hooks.append(hook_result)
        self._started_steps_stack.append(hook_result)
        return hook_result

    def end_hook(self, status=TestStatus.PASSED):
        if len(self.hooks) == 0:
            return None
        last_hook = self.hooks[len(self.hooks) - 1]
        # End hook's child steps, if remain open
        if len(self._started_steps_stack) > 0:
            while last_step := self._started_steps_stack.pop():
                if last_step == last_hook:
                    break
                last_step.end()
        last_hook.end(status)
        return last_hook

    def start_step(self, name, fqn=None):
        # Check if there is a started step
        parent_step = self._started_steps_stack[len(self._started_steps_stack) - 1] \
            if len(self._started_steps_stack) > 0 else None
        step_result = StepResult()
        step_result.start(name, fqn)
        if parent_step is None:
            self.steps.append(step_result)
        else:
            parent_step.steps.append(step_result)
        self._started_steps_stack.append(step_result)
        return step_result

    def end_step(self, status=TestStatus.PASSED):
        if len(self._started_steps_stack) == 0 or len(self.steps) == 0:
            return None
        last_step = self._started_steps_stack.pop() \
            if len(self._started_steps_stack) > 0 else self.steps[len(self.steps) - 1]
        last_step.end(status)
        if status == TestStatus.FAILED:
            self.status = TestStatus.FAILED
        return last_step

    def add_parameters(self, parameters):
        # TODO: merge with the existing parameters
        self.context["params"] = parameters
