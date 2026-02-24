"""
CloudBeat API client

Python port of the Node.js @cloudbeat/client package.

V1 API: authenticated via API key (query parameter).
V2 API: authenticated via Bearer token (Authorization header).

Usage::

    from cloudbeat_common.client import RuntimeApiV1, RunOptions

    api = RuntimeApiV1(api_token="<token>")
    run_id = api.run_test_case(case_id=42, options=RunOptions(environment_name="prod"))
    status  = api.get_run_status(run_id)
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "https://api.cloudbeat.io"

# V1 endpoint prefixes
_EP_CASES = "/cases/api/case"
_EP_SUITES = "/suites/api/suite"
_EP_MONITORS = "/monitors/api/monitor"
_EP_RUNS = "/runs/api/run"
_EP_RESULTS = "/results/api/results"
_EP_PROJECTS = "/projects/api/project"

_RESULT_POLLING_RETRIES = 10
_RESULT_POLLING_INTERVAL_INCREASE = 1.0  # seconds added per retry


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class CbApiError(Exception):
    """Raised when a CloudBeat API call fails."""

    def __init__(self, message_or_exc: Any = "", response: Optional[requests.Response] = None):
        msg = message_or_exc if isinstance(message_or_exc, str) else str(message_or_exc)

        if response is not None:
            status = response.status_code
            if status == 500:
                msg = "Internal server error, please try again later."
            elif status == 401:
                msg = "Authentication failed, invalid API key."
            elif status == 404:
                msg = "A record or an endpoint does not exist."
            elif status == 204:
                msg = "A record or an endpoint does not have content."
            elif status == 422:
                try:
                    data = response.json() or {}
                    err_msg = data.get("errorMessage", "")
                    errors: List[str] = data.get("errors") or []
                    if err_msg:
                        if errors:
                            err_msg += ": " + " ".join(errors)
                        msg = err_msg
                    else:
                        msg = "Validation Failed"
                except Exception:
                    msg = "Validation Failed"
            else:
                msg = response.reason or str(status)

        super().__init__(msg)


# ---------------------------------------------------------------------------
# Response / request data models
# ---------------------------------------------------------------------------


@dataclass
class RunInstanceCaseStatus:
    id: Optional[int] = None
    name: Optional[str] = None
    order: int = 0
    progress: int = 0
    iterations_failed: int = 0
    iterations_passed: int = 0
    failures: List[Any] = field(default_factory=list)


@dataclass
class RunInstanceStatus:
    id: Optional[str] = None
    run_id: Optional[str] = None
    start_time: int = 0
    end_time: Optional[int] = None
    pending_duration: int = 0
    initializing_start_time: int = 0
    initializing_duration: int = 0
    running_start_time: Optional[int] = None
    running_duration: int = 0
    status: Optional[str] = None
    status_last_update: int = 0
    progress: int = 0
    capabilities: Dict[str, Any] = field(default_factory=dict)
    browser_name: Optional[str] = None
    browser_version: Optional[str] = None
    device_name: Optional[str] = None
    location_name: Optional[str] = None
    output_log: Optional[str] = None
    cases_status: List[RunInstanceCaseStatus] = field(default_factory=list)


@dataclass
class RunStatus:
    run_id: Optional[str] = None
    entity_id: Optional[int] = None
    entity_type: Optional[str] = None
    run_name: Optional[str] = None
    result_id: Optional[int] = None
    start_time: int = 0
    end_time: Optional[int] = None
    duration: Optional[int] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    status_last_update: int = 0
    executing_user_name: Optional[str] = None
    executing_user_id: Optional[int] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    instances: List[RunInstanceStatus] = field(default_factory=list)


@dataclass
class TestCaseTagDto:
    case_id: Optional[str] = None
    fqn: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ProjectSyncStatus:
    commit_hash: Optional[str] = None
    sync_date: Optional[str] = None
    sync_status: Optional[str] = None
    message: Optional[str] = None


@dataclass
class RunOptions:
    """Options for triggering a test run."""

    test_attributes: Optional[Dict[str, Any]] = None
    additional_parameters: Optional[Dict[str, Any]] = None
    environment_id: Optional[int] = None
    environment_name: Optional[str] = None
    release_name: Optional[str] = None
    sprint_name: Optional[str] = None
    build_name: Optional[str] = None
    pipeline_name: Optional[str] = None
    project_name: Optional[str] = None
    test_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.test_attributes is not None:
            d["testAttributes"] = self.test_attributes
        if self.additional_parameters is not None:
            d["additionalParameters"] = self.additional_parameters
        if self.environment_id is not None:
            d["environmentId"] = self.environment_id
        if self.environment_name is not None:
            d["environmentName"] = self.environment_name
        if self.release_name is not None:
            d["releaseName"] = self.release_name
        if self.sprint_name is not None:
            d["sprintName"] = self.sprint_name
        if self.build_name is not None:
            d["buildName"] = self.build_name
        if self.pipeline_name is not None:
            d["pipelineName"] = self.pipeline_name
        if self.project_name is not None:
            d["projectName"] = self.project_name
        if self.test_name is not None:
            d["testName"] = self.test_name
        return d


@dataclass
class RunStatusInfo:
    """V2: payload for updating run/instance status."""

    run_id: Optional[str] = None
    instance_id: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.run_id is not None:
            d["runId"] = self.run_id
        if self.instance_id is not None:
            d["instanceId"] = self.instance_id
        if self.status is not None:
            d["status"] = self.status
        if self.progress is not None:
            d["progress"] = self.progress
        return d


@dataclass
class CaseStatusUpdateReq:
    """V2: payload for updating a test case's runtime status."""

    # Used in the request path
    run_id: Optional[str] = None
    instance_id: Optional[str] = None
    # Request body fields
    id: Optional[str] = None            # internal case UUID
    fqn: Optional[str] = None
    parent_fqn: Optional[str] = None    # parent suite fqn
    parent_id: Optional[str] = None     # parent suite id
    name: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    run_status: Optional[str] = None    # e.g. "Running" / "Finished"
    test_status: Optional[str] = None   # e.g. "passed" / "failed"
    framework: Optional[str] = None
    language: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.run_id is not None:
            d["runId"] = self.run_id
        if self.instance_id is not None:
            d["instanceId"] = self.instance_id
        if self.id is not None:
            d["id"] = self.id
        if self.fqn is not None:
            d["fqn"] = self.fqn
        if self.parent_fqn is not None:
            d["parentFqn"] = self.parent_fqn
        if self.parent_id is not None:
            d["parentId"] = self.parent_id
        if self.name is not None:
            d["name"] = self.name
        if self.start_time is not None:
            d["startTime"] = self.start_time
        if self.end_time is not None:
            d["endTime"] = self.end_time
        if self.run_status is not None:
            d["runStatus"] = self.run_status
        if self.test_status is not None:
            d["testStatus"] = self.test_status
        if self.framework is not None:
            d["framework"] = self.framework
        if self.language is not None:
            d["language"] = self.language
        if self.capabilities is not None:
            d["capabilities"] = self.capabilities
        if self.timestamp is not None:
            d["timestamp"] = self.timestamp
        return d


@dataclass
class SuiteStatusUpdateReq:
    """V2: payload for updating a test suite's runtime status."""

    run_id: Optional[str] = None
    instance_id: Optional[str] = None
    suite_id: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.run_id is not None:
            d["runId"] = self.run_id
        if self.instance_id is not None:
            d["instanceId"] = self.instance_id
        if self.suite_id is not None:
            d["suiteId"] = self.suite_id
        if self.status is not None:
            d["status"] = self.status
        if self.progress is not None:
            d["progress"] = self.progress
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_epoch_ms(date_str: Optional[str]) -> Optional[int]:
    """Convert an ISO-8601 date string to milliseconds since the Unix epoch."""
    if not date_str:
        return None
    formats = (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def _parse_run_status(data: Dict[str, Any]) -> RunStatus:
    instances = [_parse_run_instance(i) for i in (data.get("instances") or [])]
    return RunStatus(
        run_id=data.get("runId"),
        entity_id=data.get("entityId"),
        entity_type=data.get("entityType"),
        run_name=data.get("runName"),
        result_id=data.get("resultId"),
        start_time=_to_epoch_ms(data.get("startTime")) or 0,
        end_time=_to_epoch_ms(data.get("endTime")),
        duration=data.get("duration"),
        status=data.get("status"),
        progress=data.get("progress"),
        status_last_update=_to_epoch_ms(data.get("statusLastUpdate")) or 0,
        executing_user_name=data.get("executingUserName"),
        executing_user_id=data.get("executingUserId"),
        project_name=data.get("projectName"),
        project_id=data.get("projectId"),
        instances=instances,
    )


def _parse_run_instance(data: Dict[str, Any]) -> RunInstanceStatus:
    cases_status = [_parse_case_status(cs) for cs in (data.get("casesStatus") or [])]
    return RunInstanceStatus(
        id=data.get("id"),
        run_id=data.get("runId"),
        start_time=_to_epoch_ms(data.get("startTime")) or 0,
        end_time=_to_epoch_ms(data.get("endTime")),
        pending_duration=data.get("pendingDuration") or 0,
        initializing_start_time=_to_epoch_ms(data.get("initializingStartTime")) or 0,
        initializing_duration=data.get("initializingDuration") or 0,
        running_start_time=_to_epoch_ms(data.get("runningStartTime")),
        running_duration=data.get("runningDuration") or 0,
        status=data.get("status"),
        status_last_update=_to_epoch_ms(data.get("statusLastUpdate")) or 0,
        progress=data.get("progress") or 0,
        capabilities=data.get("capabilitiesJson") or {},
        browser_name=data.get("browserName"),
        browser_version=data.get("browserVersion"),
        device_name=data.get("deviceName"),
        location_name=data.get("locationName"),
        output_log=data.get("outputLog"),
        cases_status=cases_status,
    )


def _parse_case_status(data: Dict[str, Any]) -> RunInstanceCaseStatus:
    return RunInstanceCaseStatus(
        id=data.get("id"),
        name=data.get("name"),
        order=data.get("order") or 0,
        progress=data.get("progress") or 0,
        iterations_failed=data.get("iterationsFailed") or 0,
        iterations_passed=data.get("iterationsPassed") or 0,
        failures=[],
    )


# ---------------------------------------------------------------------------
# Base HTTP client (internal)
# ---------------------------------------------------------------------------


class _CbRestApiClient:
    """
    Shared HTTP client base for V1 and V2 API implementations.

    V1 appends ``?apiKey=<token>`` (plus a random cache-buster on GET requests).
    V2 sends an ``Authorization: Bearer <token>`` header.
    """

    def __init__(self, base_url: str, auth_token: str, use_bearer: bool = False) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        self._use_bearer = use_bearer
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"
        if use_bearer:
            self._session.headers["Authorization"] = f"Bearer {auth_token}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_url(self, path: str, method: str = "POST") -> str:
        url = self._base_url + path
        if not self._use_bearer:
            sep = "&" if "?" in url else "?"
            url += f"{sep}apiKey={self._auth_token}"
            if method.upper() == "GET":
                rnd = random.randint(0, 999_999_999_999)
                url += f"&rnd={rnd}"
        return url

    def _get(self, path: str) -> requests.Response:
        url = self._make_url(path, method="GET")
        logger.debug("REQ: GET %s", url)
        response = self._session.get(url)
        logger.debug("RES: HTTP %s", response.status_code)
        return response

    def _post(self, path: str, json_data: Any = None) -> requests.Response:
        url = self._make_url(path, method="POST")
        logger.debug("REQ: POST %s", url)
        response = self._session.post(url, json=json_data)
        logger.debug("RES: HTTP %s", response.status_code)
        return response

    def _post_multipart(self, path: str, file_name: str, file_content: bytes) -> requests.Response:
        """POST a single file as multipart/form-data."""
        url = self._make_url(path, method="POST")
        logger.debug("REQ: POST (multipart) %s", url)
        # Pass Content-Type=None so requests can set the correct multipart boundary.
        response = self._session.post(
            url,
            files={"file": (file_name, file_content)},
            headers={"Content-Type": None},
        )
        logger.debug("RES: HTTP %s", response.status_code)
        return response


# ---------------------------------------------------------------------------
# V1 API
# ---------------------------------------------------------------------------


class _ApiBaseClientV1(_CbRestApiClient):
    """V1 base client — authenticates via API key query parameter."""

    def __init__(self, api_token: str, api_host_url: Optional[str] = None) -> None:
        super().__init__(
            base_url=api_host_url or DEFAULT_API_BASE_URL,
            auth_token=api_token,
            use_bearer=False,
        )


class RuntimeApiV1(_ApiBaseClientV1):
    """V1 API for triggering test executions and querying run status."""

    def run_test_case(self, case_id: int, options: Optional[RunOptions] = None) -> Optional[str]:
        """
        Start a test case run.

        Returns the run ID on success, or ``None`` if the case was not found
        (HTTP 404).
        """
        path = f"{_EP_CASES}/{case_id}/run"
        try:
            response = self._post(path, json_data=options.to_dict() if options else None)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if not data or not data.get("id"):
                raise CbApiError('Invalid response, "data.id" is missing.')
            return data["id"]
        except CbApiError:
            raise
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("run_test_case failed: %s", exc)
            raise CbApiError(str(exc)) from exc

    def run_test_suite(self, suite_id: int, options: Optional[RunOptions] = None) -> Optional[str]:
        """
        Start a test suite run.

        Returns the run ID on success, or ``None`` if the suite was not found.
        """
        path = f"{_EP_SUITES}/{suite_id}/run"
        try:
            response = self._post(path, json_data=options.to_dict() if options else None)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if not data or not data.get("id"):
                raise CbApiError('Invalid response, "data.id" is missing.')
            return data["id"]
        except CbApiError:
            raise
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("run_test_suite failed: %s", exc)
            raise CbApiError(str(exc)) from exc

    def run_monitor(self, monitor_id: str, options: Optional[RunOptions] = None) -> Optional[str]:
        """
        Start a monitor run.

        Returns the run ID on success, or ``None`` if the monitor was not found.
        """
        path = f"{_EP_MONITORS}/{monitor_id}/run"
        try:
            response = self._post(path, json_data=options.to_dict() if options else None)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if not data or not data.get("id"):
                raise CbApiError('Invalid response, "data.id" is missing.')
            return data["id"]
        except CbApiError:
            raise
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("run_monitor failed: %s", exc)
            raise CbApiError(str(exc)) from exc

    def get_run_status(self, run_id: str) -> RunStatus:
        """Retrieve the current status of a run, including all instance details."""
        path = f"{_EP_RUNS}/{run_id}"
        try:
            response = self._get(path)
            response.raise_for_status()
            data = response.json()
            if not data:
                raise CbApiError("Invalid response, no data received.")
            return _parse_run_status(data)
        except CbApiError:
            raise
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("get_run_status failed: %s", exc)
            raise CbApiError(str(exc)) from exc


class ResultApiV1(_ApiBaseClientV1):
    """V1 API for retrieving test results."""

    def get_result_by_run_id(self, run_id: str) -> Optional[Any]:
        """
        Fetch the test result for a completed run.

        Polls the endpoint until the result is ready (HTTP 200) or until
        ``_RESULT_POLLING_RETRIES`` attempts are exhausted.  Returns ``None``
        if the run was not found (HTTP 404) or the result is still not
        available after all retries.
        """
        path = f"{_EP_RESULTS}/run/{run_id}"
        delay = 1.0
        for _ in range(_RESULT_POLLING_RETRIES):
            try:
                response = self._get(path)
                if response.status_code == 404:
                    return None
                if response.status_code == 202:
                    # Result not ready yet — wait and retry.
                    time.sleep(delay)
                    delay += _RESULT_POLLING_INTERVAL_INCREASE
                    continue
                response.raise_for_status()
                data = response.json()
                if data:
                    return data
            except requests.HTTPError as exc:
                raise CbApiError(exc, response=exc.response) from exc
            except Exception as exc:
                logger.error("get_result_by_run_id failed: %s", exc)
                raise CbApiError(str(exc)) from exc
            time.sleep(delay)
            delay += _RESULT_POLLING_INTERVAL_INCREASE
        return None

    def get_result_test_cases_tags_by_run_id(
        self, run_id: str
    ) -> Optional[List[TestCaseTagDto]]:
        """Fetch the test-case tags for all cases in a run result."""
        path = f"{_EP_RESULTS}/run/{run_id}/cases/tags"
        try:
            response = self._get(path)
            response.raise_for_status()
            data = response.json()
            if data is None:
                raise CbApiError("Invalid response, no data received.")
            return [
                TestCaseTagDto(
                    case_id=item.get("caseId"),
                    fqn=item.get("fqn"),
                    tags=item.get("tags") or [],
                )
                for item in data
            ]
        except CbApiError:
            raise
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("get_result_test_cases_tags_by_run_id failed: %s", exc)
            raise CbApiError(str(exc)) from exc


class ProjectApiV1(_ApiBaseClientV1):
    """V1 API for managing project artifacts and sync status."""

    def upload_artifacts(
        self, project_id: str, file_name: str, file_content: bytes
    ) -> Optional[Any]:
        """Upload an artifact file to a project and return the server response."""
        path = f"{_EP_PROJECTS}/sync/artifacts/{project_id}/"
        try:
            response = self._post_multipart(path, file_name, file_content)
            response.raise_for_status()
            return response.json() if response.content else None
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("upload_artifacts failed: %s", exc)
            raise CbApiError(str(exc)) from exc

    def get_sync_status(self, project_id: str) -> ProjectSyncStatus:
        """Retrieve the artifact sync status of a project."""
        path = f"{_EP_PROJECTS}/{project_id}/sync/status"
        try:
            response = self._get(path)
            response.raise_for_status()
            data = response.json()
            if data is None:
                raise CbApiError("Invalid response, no data received.")
            return ProjectSyncStatus(
                commit_hash=data.get("commitHash"),
                sync_date=data.get("syncDate"),
                sync_status=data.get("syncStatus"),
                message=data.get("message"),
            )
        except CbApiError:
            raise
        except requests.HTTPError as exc:
            raise CbApiError(exc, response=exc.response) from exc
        except Exception as exc:
            logger.error("get_sync_status failed: %s", exc)
            raise CbApiError(str(exc)) from exc


# ---------------------------------------------------------------------------
# V2 API
# ---------------------------------------------------------------------------


class _ApiBaseClientV2(_CbRestApiClient):
    """V2 base client — authenticates via Bearer token."""

    def __init__(self, api_host_url: str, api_token: str) -> None:
        super().__init__(base_url=api_host_url, auth_token=api_token, use_bearer=True)


class RuntimeApiV2(_ApiBaseClientV2):
    """
    V2 API for posting test results and updating runtime status.

    All methods follow a fire-and-forget pattern: errors are logged but not
    re-raised, matching the behaviour of the Node.js implementation.
    """

    def add_instance_result(self, run_id: str, instance_id: str, result: Any) -> None:
        """
        Post the full test result for a run instance.

        *result* may be a plain ``dict`` or a
        :class:`~cloudbeat_common.models.TestResult` instance (serialised via
        :func:`~cloudbeat_common.json_util.to_json`).
        """
        path = f"/testresult/run/{run_id}/instance/{instance_id}"
        try:
            if isinstance(result, dict):
                payload = result
            else:
                import json
                from cloudbeat_common.json_util import to_json
                payload = json.loads(to_json(result))
            self._post(path, json_data=payload)
        except Exception as exc:
            logger.error("Failed to post new test results: %s", exc)

    def update_instance_status(self, status: RunStatusInfo) -> None:
        """Update the status of a run instance."""
        try:
            self._post("/status", json_data=status.to_dict())
        except Exception as exc:
            logger.error("Failed to update run status: %s", exc)

    def update_case_status(self, status: CaseStatusUpdateReq) -> None:
        """Update the runtime status of a specific test case."""
        path = f"/runtime/run/{status.run_id}/instance/{status.instance_id}/case/status"
        try:
            self._post(path, json_data=status.to_dict())
        except Exception as exc:
            logger.error("Failed to update case runtime status: %s", exc)

    def update_suite_status(self, status: SuiteStatusUpdateReq) -> None:
        """Update the runtime status of a specific test suite."""
        path = f"/runtime/run/{status.run_id}/instance/{status.instance_id}/suite/status"
        try:
            self._post(path, json_data=status.to_dict())
        except Exception as exc:
            logger.error("Failed to update suite runtime status: %s", exc)
