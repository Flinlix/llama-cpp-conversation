"""A loop's variant: a measure every pass of the loop must make smaller, so that the loop ends."""

from __future__ import annotations

from .errors import InternalError


class LoopVariant:
    """The measure of one run of a loop, given at the start of each pass: a whole number, or a tuple of them.

    A pass that gives no smaller one than the pass before raises :class:`InternalError`, naming the loop.
    """

    __slots__ = ("_loop", "_last")

    def __init__(self, loop: str) -> None:
        self._loop = loop
        self._last: tuple[int, ...] | None = None

    def passes(self, measure: int | tuple[int, ...]) -> None:
        """Note the measure at the start of a pass; raise where it is not smaller than the last."""
        parts = measure if isinstance(measure, tuple) else (measure,)
        if min(parts) < 0 or self._last is not None and not parts < self._last:
            raise InternalError(f"{self._loop} made no progress: its measure went from "
                                f"{self._last!r} to {parts!r}")
        self._last = parts
