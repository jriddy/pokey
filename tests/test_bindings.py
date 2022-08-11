import immutables
import pytest

from pokey._bindings import BindingsReference

_test_bindings_ref = BindingsReference._make(f"{__name__}._test_bindings_ref")


@pytest.fixture(scope="session")
def ref() -> BindingsReference:
    return _test_bindings_ref


def test_can_access_raw_map(ref: BindingsReference) -> None:
    assert isinstance(ref.bindings, immutables.Map)
    # We also shouldn't leave bindings between tests
    assert not ref.bindings


def test_can_bind_in_context_and_be_cleared_after(
    ref: BindingsReference,
) -> None:
    assert not ref.bindings
    with ref.scope():
        ref.set("key", "value")
        assert ref.get("key") == "value"
        ref.set("name", "something")
        assert ref.get("key") == "value"
        assert ref.get("name") == "something"
    assert not ref.bindings


@pytest.fixture(scope="function")
def fn_ref(ref) -> BindingsReference:
    with ref.scope():
        yield ref


def test_set_many_at_once(fn_ref):
    kv = {"a": 1, "b": 2, "c": 3}
    fn_ref.set_many(kv)
    assert fn_ref.get_many(kv.keys()) == kv
