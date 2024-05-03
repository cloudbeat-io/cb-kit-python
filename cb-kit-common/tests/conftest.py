"""This module contains common Pytest fixtures and hooks for CB Kit Common unit tests."""

from unittest import mock
import uuid

from cloudbeat_common.reporter import CbTestReporter
# noinspection PyPackageRequirements
from pytest import fixture

from cloudbeat_common.models import CbConfig


@fixture(scope="module")
def cb_config():
    """Prepare configuration class for further CB reporter initialization."""
    config = CbConfig()
    config.run_id = str(uuid.uuid4())
    config.instance_id = str(uuid.uuid4())
    config.project_id = str(uuid.uuid4())
    config.capabilities = {"browserName": "chrome"}
    return config


@fixture(scope="module")
def cb_reporter(cb_config):
    reporter = CbTestReporter(cb_config)
    return reporter
