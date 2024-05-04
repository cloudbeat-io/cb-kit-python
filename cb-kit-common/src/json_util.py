import json

from cloudbeat_common.models import TestResult, SuiteResult, CaseResult, StepResult


def to_json(result: TestResult):
    return json.dumps(result, cls=CbResultEncoder, indent=4)


def _test_result_to_json(tr: TestResult):
    if not isinstance(tr, TestResult):
        return None
    return {
        "runId": tr.run_id,
        "instanceId": tr.instance_id,
        "startTime": tr.start_time,
        "endTime": tr.end_time,
        "duration": tr.duration,
        "capabilities": tr.capabilities,
        "options": tr.options,
        "metaData": tr.meta_data,
        "environmentVariables": tr.environment_variables,
        "testAttributes": tr.test_attributes,
        "suites": list(map(lambda s: _suite_result_to_json(s), tr.suites))
    }


def _suite_result_to_json(r: SuiteResult):
    if not isinstance(r, SuiteResult):
        return None
    return {
        "id": r.id,
        "name": r.name,
        "fqn": r.fqn,
        "startTime": r.start_time,
        "endTime": r.end_time,
        "duration": r.duration,
        "status": r.status,
        "cases": list(map(lambda c: _case_result_to_json(c), r.cases))
    }


def _case_result_to_json(r: CaseResult):
    if not isinstance(r, CaseResult):
        return None
    return {
        "id": r.id,
        "name": r.name,
        "display_name": r.display_name,
        "description": r.description,
        "fqn": r.fqn,
        "startTime": r.start_time,
        "endTime": r.end_time,
        "duration": r.duration,
        "status": r.status,
        "context": r.context,
        "arguments": r.arguments,
        "steps": list(map(lambda s: _step_result_to_json(s), r.steps)),
        "hooks": list(map(lambda s: _step_result_to_json(s), r.hooks))
    }


def _step_result_to_json(r: StepResult):
    if not isinstance(r, StepResult):
        return None
    return {
        "id": r.id,
        "name": r.name,
        "fqn": r.fqn,
        "startTime": r.start_time,
        "endTime": r.end_time,
        "duration": r.duration,
        "status": r.status,
        "steps": list(map(lambda s: _step_result_to_json(s), r.steps))
    }


class CbResultEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TestResult):
            return _test_result_to_json(obj)
        return super().default(obj)