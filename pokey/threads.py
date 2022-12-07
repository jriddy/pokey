from __future__ import annotations

import contextvars
import threading


class ContextThread(threading.Thread):
    """Copy context to thread when running it.

    This is meant to be a drop-in replacement for `threading.Thread` that merely copies
    the starting thread's context during `start()` and ensures the thread gets run
    in that during `run()`.
    """

    _contextvar_ctx: contextvars.Context

    def start(self) -> None:
        # superclass will take care of making sure start() gets called only once
        self._contextvar_ctx = contextvars.copy_context()
        super().start()

    def run(self) -> None:
        self._contextvar_ctx.run(super().run)


# TODO: context-aware ThreadPoolExecutor
