from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import functools
import inspect
import pkgutil
from typing import Any, Callable, ClassVar, Generic, Iterable, Protocol, TypeVar, runtime_checkable
import attr
from immutables import Map


_DEPENDANTS_KEY = "*dependants"
_bindings_ref: ContextVar[Map] = ContextVar(
    f"{__name__}:_bindings_ref",
    default=Map({_DEPENDANTS_KEY: Map()}),
)


_T = TypeVar("_T")


@runtime_checkable
class _Marker(Protocol[_T]):
    name: str

    # the @runtime_checkable decorator makes using a property an issue:
    # it eagerly evaluates the propery, which we don't always want
    def get_value(self) -> _T:
        ...


@attr.define
class _FactoryMarker(Generic[_T]):
    name: str
    factory: Callable[[], _T]

    _UNSET: ClassVar[object] = object()
    _cached_value: _T | object = attr.field(default=_UNSET, kw_only=True)

    def get_value(self) -> _T:
        if self._cached_value is self._UNSET:
            self._cached_value = self.factory()
        return self._cached_value

    def reset(self):
        return attr.evolve(self, cached_value=self._UNSET)



@attr.define
class _PokyBox:
    markers: dict[str, _Marker]


def feed(f):
    markers = _get_markers(f)
    f.__pokey__ = _PokyBox(markers)

    # If the markers have dependencies, we need to record them
    # TODO: this won't work until call-time for import markers
    bindings = _bindings_ref.get()
    dependants: Map[str, frozenset[str]] = bindings[_DEPENDANTS_KEY]
    for marker in markers:
        if hasattr(marker, "factory") and hasattr(marker.factory, "__pokey__"):
            dependencies = marker.factory.__pokey__.markers
            with dependants.mutate() as dm:
                for dep in dependencies.keys():
                    dm[dep] = dm.get(dep, frozenset()) | {marker.name}
                bindings = bindings.set(_DEPENDANTS_KEY, dm.finish())
    _bindings_ref.set(bindings)

    @functools.wraps(f)
    def _resolver(*xs, **kw):
        bindings = _bindings_ref.get()
        for k, v in markers.items():
            if k not in kw:
                kw[k] = bindings.get(v.name).get_value()

        return f(*xs, **kw)

    return _resolver


def _get_markers(f):
    sig = inspect.signature(f)
    return {
        name: param.default
        for name, param
        in sig.parameters.items()
        if isinstance(param.default, _Marker)
    }


def wants(name_or_callable, /):
    if isinstance(name_or_callable, str):
        marker = _ImportMarker(name_or_callable)
    elif callable(name_or_callable):
        fn = name_or_callable
        name = _get_name_of_callable(fn)
        marker = _FactoryMarker(name, fn)
    else:
        raise TypeError("must be str or callable")

    # Set a root binding
    name = marker.name
    bindings = _bindings_ref.get()
    if name in bindings and bindings[name] != marker:
        raise ValueError(f"name {name!r} already has a root binding")
    _bindings_ref.set(bindings.set(name, marker))

    return marker


@attr.frozen
class _ImportMarker(Generic[_T]):
    name: str

    @functools.lru_cache(1)
    def get_value(self) -> _T:
        obj = pkgutil.resolve_name(self.name)
        # TODO: ostensibly, obj could be not callable
        return obj()


def _get_name_of_callable(f):
    name = f.__name__
    if name == "<lambda>":
        raise TypeError("callable must be named to create binding")

    return f"{f.__module__}:{name}"


# TODO: does this really belong in the API?
# It's more of a placeholder to have a test on names
def slot_names(f):
    return {k: v.name for k, v in f.__pokey__.markers.items()}


@attr.frozen
class _ValueMarker(Generic[_T]):
    name: str
    value: _T

    def get_value(self) -> _T:
        return self.value


def _clear_dependant_values_rec(name, bm, dm):
    for k in dm.get(name, ()):
        bm[k] = bm[k].reset()
        _clear_dependant_values_rec(k, bm, dm)


# TODO: placeholder for tests... API should be more well-thought out
@contextmanager
def bind_value(name, value):
    bindings = _bindings_ref.get()
    marker = _ValueMarker(name, value)
    with bindings.mutate() as bm:
        dependants = bindings[_DEPENDANTS_KEY]
        with dependants.mutate() as dm:
            _clear_dependant_values_rec(name, bm, dm)
        # TODO: reset dependants as well?

        bm[name] = marker

        token = _bindings_ref.set(bm.finish())
    try:
        yield
    finally:
        _bindings_ref.reset(token)
