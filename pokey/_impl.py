from __future__ import annotations

import functools
import inspect
import pkgutil
from contextlib import contextmanager
from typing import Callable, Generic, Protocol, Set, TypeVar, runtime_checkable

import attrs

from ._bindings import BindingsReference

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

    # Currently defined dependencies only (for now)
    def dependencies(self) -> Set[str]:
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

    def dependencies(self) -> Set[str]:
        deps = set()
        if is_injected(self.factory):
            for m in self.factory.markers.values():
                deps.add(m.name)
                deps |= m.dependencies()
        return deps


@attrs.frozen
class ValueMarker(Resolver[V]):
    name: str
    value: V

    def resolve(self) -> V:
        return self.value

    def dependencies(self) -> Set[str]:
        return frozenset()


# TODO: redefine to not require mutation
@attrs.define
class NamedMarker(Resolver[V]):
    name: str
    _imported_marker: Resolver[V] | None = None

    def resolve(self) -> V:
        if self._imported_marker is None:
            factory = pkgutil.resolve_name(self.name)
            # TODO: probably do some validation/checking on factory
            self._imported_marker = FactoryMarker(self.name, factory)
        return self._imported_marker.resolve()

    def dependencies(self) -> Set[str]:
        im = self._imported_marker
        return frozenset() if im is None else im.dependencies()


# TODO: possibly disentangle this
Marker = Resolver


@attrs.frozen
class Tracker(Generic[V]):
    marker: Marker
    # TODO: we should probably use a private marker value here
    value: V | Ellipsis = ...

    evolve = attrs.evolve

    def cache(self, value: V) -> Tracker[V]:
        return self.evolve(value=value)

    def uncache(self) -> Tracker[V]:
        return self.evolve(value=...)


@attrs.define
class Pokey:
    ref: BindingsReference[Tracker]

    @classmethod
    def _make_new(cls, name):
        return cls(BindingsReference._make(name))

    # register the dependency, and return marker that we can use when registering
    # check that registry is compatible/unique (TODO: clarify)
    # marker types will depend on how we call wants (callable or str)
    # creates wrappers on wanted functions
    # TODO: Maybe deals with registering dependants?
    def wants(self, x):
        if isinstance(x, str):
            return NamedMarker(x)
        return FactoryMarker(f"{x.__module__}:{x.__name__}", x)

    # create a wrapper for this function that will fill in missing values when we call
    def injects(self, f):
        sig = inspect.signature(f)
        markers = {
            name: param.default
            for name, param in sig.parameters.items()
            if isinstance(param.default, Marker)
        }
        for marker in markers.values():
            self._register_marker(marker)

        @functools.wraps(f)
        def _injection_resolver(*xs, **kw):
            for k, v in markers.items():
                if k not in kw:
                    kw[k] = self._resolve_caching_value(marker)

            return f(*xs, **kw)

        _injection_resolver.markers = markers
        return _injection_resolver

    def _resolve_caching_value(self, marker: Marker[V]) -> V:
        key = marker.name
        # TODO: just getitem here
        tracker = self.ref.get(key)
        if tracker is None:
            raise KeyError(key)

        if tracker.value is ...:
            value = marker.resolve()
            tracker = tracker.cache(value)
            self.ref.set(key, tracker)

        return tracker.value

    def _register_marker(self, marker: Marker) -> None:
        maybe_tracker = self.ref.get(marker.name)
        if maybe_tracker is None:
            # unregistered, we can just add a new tracker
            self.ref.set(marker.name, Tracker(marker))
        elif maybe_tracker.marker == marker:
            # TODO: not sure if we need to do anything here...
            pass
        else:
            # we're trying to register a new function to the same name
            raise RuntimeError(f"{marker.name!r} already has a root binding")

    def slot_names(self, f):
        # TODO: set this on a better attribute/wrapper box
        return {k: v.name for k, v in f.markers.items()}

    @contextmanager
    def bind(self, kv):
        # TODO: what should we do with unrecognized keys?
        ref = self.ref
        with ref.scope():
            old_trackers = ref.get_many(kv.keys())
            new_trackers = {}
            for k, t in old_trackers.items():
                if t is None:
                    new_trackers[k] = Tracker(ValueMarker(k, kv[k]))
                else:
                    # invalidate all dependant caches
                    for dk in self._find_dependants(k):
                        new_trackers[dk] = ref.get(dk).uncache()
                    new_trackers[k] = t.evolve(
                        marker=ValueMarker(k, kv[k]), value=kv[k]
                    )
            ref.set_many(new_trackers)
            yield

    def _find_dependants(self, name: str) -> Set[str]:
        # TODO: this will be very slow as the number of bindings grows
        # we need to track dependants separatly if we want to make this practicable
        return {
            k for k, v in self.ref.bindings.items() if name in v.marker.dependencies()
        }


@staticmethod
def is_injected(x: object) -> bool:
    # TODO: better check
    return hasattr(x, "markers")
