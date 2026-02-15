"""Unit tests for htan.model — DataModel class."""

from htan.model import DataModel


def test_datamodel_creates():
    dm = DataModel()
    assert dm is not None


def test_datamodel_is_usable():
    dm = DataModel()
    # DataModel should be instantiated without errors
    assert callable(getattr(dm, "components", None))
