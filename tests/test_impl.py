import queue
import random
import threading
import time
from contextvars import copy_context

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


def test_threaded_rebinds_dont_interfere(scopey: Pokey) -> None:
    def my_binding():
        return "123"

    @scopey.injects
    def show_binding(value: str = scopey.wants(my_binding)):
        return value

    print(dict(scopey.ref.bindings))

    q = queue.Queue()

    def do_test(rebind_value: str | None):
        for _ in range(10):
            if rebind_value is None:
                time.sleep(random.random() / 100000)
                q.put(("123", show_binding()))
            else:
                with scopey.bind({"tests.test_impl:my_binding": rebind_value}):
                    time.sleep(random.random() / 100000)
                    q.put((rebind_value, show_binding()))

    def run_in_context(ctx, value):
        ctx.run(do_test, value)

    values = (None, "abc", "!@#")
    # TODO: we need to provide a thread function for this
    threads = [
        threading.Thread(target=run_in_context, args=(copy_context(), v))
        for v in values
    ]
    print(len(threads))
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    items = []
    while True:
        try:
            items.append(q.get(False))
        except queue.Empty:
            break

    print(items)
    print(len(items))
    assert all([expected == actual for expected, actual in items])
