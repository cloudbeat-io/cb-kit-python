"""
CloudBeat API client

V2 API: authenticated via Bearer token (Authorization header).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


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
# Request data models
# ---------------------------------------------------------------------------


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
# Base HTTP client (internal)
# ---------------------------------------------------------------------------


class _CbRestApiClient:
    """Shared HTTP client base — authenticates via Bearer token."""

    def __init__(self, base_url: str, auth_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"
        self._session.headers["Authorization"] = f"Bearer {auth_token}"

    def _post(self, path: str, json_data: Any = None) -> requests.Response:
        url = self._base_url + path
        logger.debug("REQ: POST %s", url)
        response = self._session.post(url, json=json_data)
        logger.debug("RES: HTTP %s", response.status_code)
        return response


# ---------------------------------------------------------------------------
# V2 API
# ---------------------------------------------------------------------------


class RuntimeApiV2(_CbRestApiClient):
    """
    V2 API for posting test results and updating runtime status.

    All methods follow a fire-and-forget pattern: errors are logged but not
    re-raised, matching the behaviour of the Node.js implementation.
    """

    def __init__(self, api_host_url: str, api_token: str) -> None:
        super().__init__(base_url=api_host_url, auth_token=api_token)

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
