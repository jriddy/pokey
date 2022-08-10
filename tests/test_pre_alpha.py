import sys
import pytest
from pokey import pre_alpha as pokey


def example_provider():
    return 1


def test_injected_function_lets_given_args_pass():
    @pokey.feed
    def example_fn(*, param=pokey.wants(example_provider)):
        return param

    explicity_passed_value = object()
    result = example_fn(param=explicity_passed_value)
    assert result == explicity_passed_value


def test_injected_function_will_provide_default_if_arg_not_given():
    default_value = object()

    def return_default_value():
        return default_value

    @pokey.feed
    def example_fn(*, param=pokey.wants(return_default_value)):
        return param

    assert example_fn() == default_value


def test_factory_function_not_called_until_function_called():
    called = False

    def factory():
        nonlocal called
        called = True
        return 1

    @pokey.feed
    def example_fn(*, param=pokey.wants(factory)):
        return param

    assert not called
    assert example_fn() == 1
    assert called


def test_can_describe_dependencies_of_injected_fn():
    @pokey.feed
    def example_fn(*, param=pokey.wants(example_provider)):
        return param

    # TODO: better name for this
    assert pokey.slot_names(example_fn) == {"param": "test_pre_alpha:example_provider"}


def test_lambdas_not_allowed_as_wants_first_params():
    with pytest.raises(TypeError, match=r"must be named to create binding"):
        @pokey.feed
        def example_fn(*, param=pokey.wants(lambda: 1)):
            ...


def test_cannot_reassign_binding_via_depedency_declartion():
    def test_binding_reassignment_factory():
        ...

    @pokey.feed
    def ex1(*, param=pokey.wants(test_binding_reassignment_factory)):
        ...

    def test_binding_reassignment_factory():
        ...

    with pytest.raises(ValueError, match=r"already has a root binding"):
        @pokey.feed
        def ex1(*, param=pokey.wants(test_binding_reassignment_factory)):
            ...


def test_simple_recursive_dependency():
    def simple_recursive_dependency_base() -> list[str]:
        return "Let's all".split()

    @pokey.feed
    def simple_recursive_dependency_middle(
        first_words: list[str] = pokey.wants(simple_recursive_dependency_base),
    ) -> list[str]:
        return [*first_words, "have", "a"]

    @pokey.feed
    def simple_recusrive_dependency_top(
        more_words: list[str] = pokey.wants(simple_recursive_dependency_middle),
    ) -> str:
        return " ".join(more_words + "big party!".split())

    assert simple_recusrive_dependency_top() == "Let's all have a big party!"


def test_contextual_rebind():
    def contextual_rebind_root_binding():
        return "root"

    @pokey.feed
    def show_binding(value: str = pokey.wants(contextual_rebind_root_binding)) -> str:
        return value

    assert show_binding() == "root"

    with pokey.bind_value("test_pre_alpha:contextual_rebind_root_binding", "override"):
        assert show_binding() == "override"

    assert show_binding() == "root"


@pytest.mark.skip(reason="Couldn't get this to work with inital implementation")
def test_contextual_rebind_invalidates_dependent_cached_values():
    def dep_value_root():
        return "root"

    @pokey.feed
    def dep_value_middle(value = pokey.wants(dep_value_root)):
        return " ".join([value] * 2)

    @pokey.feed
    def dep_value_end(value = pokey.wants(dep_value_middle)):
        return value

    assert dep_value_end() == "root root"

    with pokey.bind_value("test_pokey:dep_value_root", "newval"):
        assert dep_value_end() == "newval newval"


def test_import_wanted_name_works():
    @pokey.feed
    def load_secret_value(value: str = pokey.wants("_pokey_test_import:my_dependency")):
        return value

    assert "_pokey_test_import" not in sys.modules
    assert load_secret_value() == "super secret value"
    assert "_pokey_test_import" in sys.modules


def test_markers_implementations_typecheck_as_markers():
    assert isinstance(pokey._FactoryMarker("something", lambda: 2), pokey._Marker)
    assert isinstance(pokey._ValueMarker("otherthing", 1), pokey._Marker)
    assert isinstance(pokey._ImportMarker("mod:var"), pokey._Marker)
