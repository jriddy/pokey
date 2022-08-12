import pytest

from pokey._impl import Pokey

_test_pokey = Pokey._make_new(f"{__name__}:_test_pokey")


@pytest.fixture
def scopey():
    with _test_pokey.ref.scope():
        yield _test_pokey


def test_find_dependants(scopey: Pokey) -> None:
    def root_dep() -> str:
        return "root value"

    @scopey.injects
    def middle_dep(root: str = scopey.wants(root_dep)) -> str:
        return f"{root}, other value"

    @scopey.injects
    def top_dep(mid: str = scopey.wants(middle_dep)) -> str:
        return f"{mid}, last value"

    assert top_dep() == "root value, other value, last value"
    assert top_dep.markers["mid"].dependencies() == {"tests.test_impl:root_dep"}
    assert {k: v.marker.dependencies() for k, v in scopey.ref.bindings.items()} == {
        "tests.test_impl:root_dep": set(),
        "tests.test_impl:middle_dep": {"tests.test_impl:root_dep"},
    }
    assert scopey._find_dependants("tests.test_impl:root_dep") == {
        "tests.test_impl:middle_dep"
    }
