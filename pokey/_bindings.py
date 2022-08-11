from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from typing import Generic, Mapping, Sequence, TypeVar

import attrs
from immutables import Map

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


@attrs.define
class BindingsReference(Generic[_T_co]):
    _ctx: ContextVar[Map]

    @classmethod
    def _make(cls, name: str) -> BindingsReference:
        """Makes a bindings reference.

        Important note: the underlying ContextVar will never be garbage
        collected.  So these should only be defined at top-level for
        specific purposes (such as testing).
        """
        return cls(ContextVar(name, default=Map()))

    @property
    def bindings(self):
        return self._ctx.get()

    @contextmanager
    def scope(self) -> AbstractContextManager[None]:
        ctx = self._ctx
        token = ctx.set(ctx.get())
        try:
            yield
        finally:
            self._ctx.reset(token)

    def set(self, key: str, val: _T_co) -> None:
        ctx = self._ctx
        ctx.set(ctx.get().set(key, val))

    def set_many(self, kv: Mapping[str, _T_co]) -> None:
        # TODO: should be changed to update, and should match its signature
        ctx = self._ctx
        with ctx.get().mutate() as mm:
            mm.update(kv)
            ctx.set(mm.finish())

    def get_many(
        self, keys: Sequence[str], default: _T = None
    ) -> dict[str, _T_co | _T]:
        m = self.bindings
        return {k: m.get(k, default) for k in keys}

    def get(self, key: str) -> _T_co:
        return self._ctx.get().get(key)
