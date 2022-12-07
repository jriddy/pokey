import sys

import pytest

from pokey import alpha as pokey


def example_provider():
    return 1


@pokey.injects
def example_function(*, param=pokey.wants(example_provider)):
    return param


def test_injected_function_lets_explicitly_given_args_pass():
    explicit_value = object()
    result = example_function(param=explicit_value)
    assert result == explicit_value


def test_pokey_will_provide_default_value_if_arg_not_given():
    assert example_function() == 1


def test_factory_function_not_called_until_needed():
    called = False

    def factory_function_not_called_until_needed():
        nonlocal called
        called = True
        return 35

    @pokey.injects
    def injected_function_that_doesnt_call_factories_until_needed(
        *, param=pokey.wants(factory_function_not_called_until_needed)
    ):
        return param

    assert not called
    assert injected_function_that_doesnt_call_factories_until_needed() == 35
    assert called


def test_factory_function_result_cached():
    calls = 0

    def factory_function_whose_result_should_be_cached():
        nonlocal calls
        calls += 1
        return "something"

    @pokey.injects
    def ex(*, param=pokey.wants(factory_function_whose_result_should_be_cached)):
        return param

    assert ex() == "something"
    assert calls == 1
    assert ex() == "something"
    assert calls == 1


def test_can_describe_dependencies_of_injected():
    @pokey.injects
    def describable_injected_function(*, param=pokey.wants(example_provider)):
        return param

    expected = {"param": "tests.test_acceptance:example_provider"}
    assert pokey.slot_names(describable_injected_function) == expected


def test_cannot_reassign_root_binding():
    def test_binding_reassignment_factory():
        ...

    @pokey.injects
    def ex1(*, param=pokey.wants(test_binding_reassignment_factory)):
        ...

    def test_binding_reassignment_factory():
        ...

    with pytest.raises(RuntimeError, match=r"already has a root binding"):

        @pokey.injects
        def ex1(*, param=pokey.wants(test_binding_reassignment_factory)):  # noqa: F811
            ...


def test_simple_recursive_dependency():
    def simple_recursive_dependency_base() -> list[str]:
        return "Let's all".split()

    @pokey.injects
    def simple_recursive_dependency_middle(
        first_words: list[str] = pokey.wants(simple_recursive_dependency_base),
    ) -> list[str]:
        return [*first_words, "have", "a"]

    @pokey.injects
    def simple_recusrive_dependency_top(
        more_words: list[str] = pokey.wants(simple_recursive_dependency_middle),
    ) -> str:
        return " ".join(more_words + "big party!".split())

    assert simple_recusrive_dependency_top() == "Let's all have a big party!"


def test_contextual_rebind():
    def contextual_rebind_root_binding():
        return "root"

    @pokey.injects
    def contextual_rebind_show_binding(
        value: str = pokey.wants(contextual_rebind_root_binding),
    ) -> str:
        return value

    assert contextual_rebind_show_binding() == "root"

    with pokey.bind(
        {"tests.test_acceptance:contextual_rebind_root_binding": "override"},
    ):
        assert contextual_rebind_show_binding() == "override"

    assert contextual_rebind_show_binding() == "root"


def test_contextual_rebind_invalidates_dependent_cached_values():
    def dep_value_root():
        return "root"

    @pokey.injects
    def dep_value_middle(value=pokey.wants(dep_value_root)):
        return " ".join([value] * 2)

    @pokey.injects
    def dep_value_end(value=pokey.wants(dep_value_middle)):
        return value

    assert dep_value_end() == "root root"

    with pokey.bind({"tests.test_acceptance:dep_value_root": "newval"}):
        assert dep_value_end() == "newval newval"


def test_import_wanted_name_works():
    @pokey.injects
    def load_secret_value(
        value: str = pokey.wants("tests._simple_test_import:my_dependency"),
    ):
        return value

    assert "tests._simple_test_import" not in sys.modules
    assert load_secret_value() == "super secret value"
    assert "tests._simple_test_import" in sys.modules
