import json

from cloudbeat_common.models import TestResult, SuiteResult, CaseResult, StepResult, FailureResult


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


def _case_result_to_json(c: CaseResult):
    if not isinstance(c, CaseResult):
        return None
    return {
        "id": c.id,
        "name": c.name,
        "display_name": c.display_name,
        "description": c.description,
        "fqn": c.fqn,
        "startTime": c.start_time,
        "endTime": c.end_time,
        "duration": c.duration,
        "status": c.status,
        "context": c.context,
        "arguments": c.arguments,
        "failure": _failure_result_to_json(c.failure),
        "steps": list(map(lambda s: _step_result_to_json(s), c.steps)),
        "hooks": list(map(lambda s: _step_result_to_json(s), c.hooks))
    }


def _step_result_to_json(s: StepResult):
    if not isinstance(s, StepResult):
        return None
    return {
        "id": s.id,
        "name": s.name,
        "fqn": s.fqn,
        "startTime": s.start_time,
        "endTime": s.end_time,
        "duration": s.duration,
        "status": s.status,
        "screenShot": s.screenshot,
        "failure": _failure_result_to_json(s.failure),
        "steps": list(map(lambda sub_step: _step_result_to_json(sub_step), s.steps))
    }

def _failure_result_to_json(f: FailureResult):
    if not isinstance(f, FailureResult):
        return None
    return {
        "type": f.type,
        "sub_type": f.sub_type,
        "message": f.message,
        "stacktrace": f.stacktrace,
        "location": f.location,
        "is_fatal": f.is_fatal
    }


class CbResultEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TestResult):
            return _test_result_to_json(obj)
        return super().default(obj)