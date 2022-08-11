from __future__ import annotations

import functools
import inspect
from typing import Callable, Protocol, Set, TypeVar, runtime_checkable

import attrs

V = TypeVar("V")


@runtime_checkable
class Resolution(Protocol[V]):
    value: V
    cacheable: bool
    dependencies: Set[str]


@runtime_checkable
class Resolver(Protocol[V]):
    def resolve(self) -> V:
        ...


@attrs.frozen
class ObviousResolution(Resolution[V]):
    value: V
    cacheable: bool = True
    dependencies: Set[str] = attrs.field(factory=frozenset)


@attrs.frozen
class FactoryMarker(Resolver[V]):
    name: str
    factory: Callable[[], V]

    def resolve(self) -> V:
        # TODO: really do this
        return self.factory()


# TODO: possibly disentangle this
Marker = Resolver


class Pokey:
    @classmethod
    def _make_new(cls):
        return cls()

    # register the dependency, and return marker that we can use when registering
    # check that registry is compatible/unique (TODO: clarify)
    # marker types will depend on how we call wants (callable or str)
    # creates wrappers on wanted functions
    # TODO: Maybe deals with registering dependants?
    def wants(self, x):
        return FactoryMarker(f"{x.__module__}:{x.__name__}", x)

    # create a wrapper for this function that will fill in missing values when we call
    def injects(self, f):
        sig = inspect.signature(f)
        markers = {
            name: param.default
            for name, param in sig.parameters.items()
            if isinstance(param.default, Marker)
        }

        @functools.wraps(f)
        def _injection_resolver(*xs, **kw):
            for k, v in markers.items():
                if k not in kw:
                    kw[k] = v.resolve()

            return f(*xs, **kw)

        _injection_resolver.markers = markers
        return _injection_resolver

    def slot_names(self, f):
        # TODO: set this on a better attribute/wrapper box
        return {k: v.name for k, v in f.markers.items()}
