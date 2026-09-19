import pytest

from cloudbeat_pytest.context import CbContext


@pytest.fixture(autouse=True)
def reset_context():
    CbContext.instance = None
    yield
    CbContext.instance = None


def test_selenium_wrapper_is_attached_when_cloudbeat_selenium_is_loaded():
    """Regression: the wrapper module used to be imported as a top-level "wrapper" module,
    which raised ModuleNotFoundError as soon as cloudbeat_selenium was imported."""
    pytest.importorskip("selenium")
    pytest.importorskip("cloudbeat_selenium")

    reporter = object()
    context = CbContext.init(reporter)

    assert context.se is not None
    assert type(context.se).__name__ == "CbSeleniumWrapper"


def test_plugin_does_not_register_generic_options(pytestconfig):
    """Regression: a leftover "--name" option clashed with options of the projects under test."""
    option_names = {name for option in pytestconfig._parser._anonymous.options for name in option.names()}
    for group in pytestconfig._parser._groups:
        if group.name == "cloudbeat":
            option_names |= {name for option in group.options for name in option.names()}
    assert "--name" not in option_names
