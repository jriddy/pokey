from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar

import attrs
from immutables import Map


@attrs.define
class BindingsReference:
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
        token = self._ctx.set(self._ctx.get())
        try:
            yield
        finally:
            self._ctx.reset(token)

    def set(self, key, val):
        self._ctx.set(self._ctx.get().set(key, val))

    def get(self, key):
        return self._ctx.get().get(key)
