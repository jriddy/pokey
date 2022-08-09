import immutables

from pokey._bindings import BindingsReference

import pytest


_test_bindings_ref = BindingsReference._make(
    f"{__name__}._test_bindings_ref"
)


@pytest.fixture(scope="session")
def ref() -> BindingsReference:
    return _test_bindings_ref


def test_can_access_raw_map(ref: BindingsReference) -> None:
    assert isinstance(ref.bindings, immutables.Map)


def test_can_bind_in_context_and_be_clear_after(ref: BindingsReference) -> None:
    assert not ref.bindings
    with ref.scope():
        ref.set("key", "value")
        assert ref.get("key") == "value"
        ref.set("name", "something")
        assert ref.get("key") == "value"
        assert ref.get("name") == "something"
    assert not ref.bindings
