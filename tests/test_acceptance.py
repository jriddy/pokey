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
