"""Reusable CLI progress primitives."""

from __future__ import annotations

import shutil
import sys
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

try:
    import termios as _termios
except ImportError:  # pragma: no cover - exercised by monkeypatch on POSIX CI
    _termios = None  # type: ignore[assignment]


Clock = Callable[[], float]


def _termios_error_types() -> tuple[type[BaseException], ...]:
    errors: list[type[BaseException]] = [AttributeError, OSError, ValueError]
    termios_error = getattr(_termios, "error", None)
    if isinstance(termios_error, type) and issubclass(termios_error, BaseException):
        errors.append(termios_error)
    return tuple(errors)


def live_progress_title_limit() -> int | None:
    """Return a safe live-title length for terminal progress bars."""

    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    except OSError:
        return None
    if columns < 60:
        return None
    return max(12, min(24, columns - 60))


def compact_live_title(text: str, limit: int | None) -> str:
    """Compact whitespace and defensively ellipsize a live progress title."""

    compact = " ".join(text.split())
    if limit is None or len(compact) <= limit:
        return compact
    return compact[: max(1, limit - 1)].rstrip() + "…"


class SingleLineProgressReporter:
    """Render progress on one carriage-return-updated terminal line."""

    _clear_line = "\r\x1b[2K"

    def __init__(
        self,
        stream: Any,
        *,
        labels: Mapping[str, str] | None = None,
        clock: Clock = time.monotonic,
        min_render_interval: float = 0.25,
        title_limit: int | None = None,
        input_stream: Any | None = None,
    ) -> None:
        self._stream = stream
        self._input_stream = sys.stdin if input_stream is None else input_stream
        self._labels = dict(labels or {})
        self._clock = clock
        self._min_render_interval = min_render_interval
        self._title_limit = (
            live_progress_title_limit() if title_limit is None else title_limit
        )
        if self._title_limit is None:
            self._title_limit = 12
        self._active = False
        self._position = 0
        self._last_line_width = 0
        self._last_render_at: float | None = None
        self._last_rendered_line = ""
        self._last_progress_key: tuple[str, int] | None = None
        self._echo_fd: int | None = None
        self._echo_attrs: list[Any] | None = None

    def __enter__(self) -> SingleLineProgressReporter:
        self._active = True
        self._suppress_input_echo()
        return self

    def __exit__(self, *_: object) -> None:
        self.finish()

    def finish(self) -> None:
        """Clear the dynamic line and disable rendering."""

        try:
            if self._active and self._write(self._clear_line):
                self._last_line_width = 0
                self._last_rendered_line = ""
            self._active = False
        finally:
            self._restore_input_echo()

    def phase(self, label: str) -> None:
        """Render a phase-only progress update."""

        if not self._active:
            return
        if self._position < 5:
            self._position = min(self._position + 1, 5)
        self._render(label, self._position, None, None, force=True)

    def update(
        self,
        label: str,
        *,
        completed: int | None = None,
        total: int | None = None,
    ) -> None:
        """Render a counted or phase-like progress update."""

        if not self._active:
            return
        counted_total = int(total or 0)
        counted_completed = int(completed or 0)
        if counted_total <= 0 or counted_completed <= 0:
            self._position = min(self._position + 1, 98)
            self._render(label, self._position, None, None)
            return

        progress_key = (label, counted_total)
        first_progress_for_key = progress_key != self._last_progress_key
        completed_eval = counted_completed >= counted_total
        if completed_eval:
            self._position = 100
        else:
            fraction = min(max(counted_completed / counted_total, 0), 1)
            self._position = 5 + int(fraction * 93)
        self._render(
            label,
            self._position,
            counted_completed,
            counted_total,
            force=first_progress_for_key or completed_eval,
        )
        self._last_progress_key = progress_key

    def _render(
        self,
        label: str,
        percent: int,
        completed: int | None,
        total: int | None,
        *,
        force: bool = False,
    ) -> None:
        line = self._format_line(label, percent, completed, total)
        if line == self._last_rendered_line:
            return
        now = self._clock()
        if (
            not force
            and self._last_render_at is not None
            and now - self._last_render_at < self._min_render_interval
        ):
            return
        padding = " " * max(self._last_line_width - len(line), 0)
        if self._write(f"\r{line}{padding}"):
            self._last_line_width = len(line)
            self._last_render_at = now
            self._last_rendered_line = line

    def _write(self, text: str) -> bool:
        try:
            self._stream.write(text)
            self._stream.flush()
        except (OSError, ValueError):
            self._active = False
            self._last_line_width = 0
            return False
        return True

    def _suppress_input_echo(self) -> None:
        if _termios is None or self._echo_fd is not None:
            return
        try:
            if not self._input_stream.isatty() or not self._stream.isatty():
                return
            fd = self._input_stream.fileno()
            attrs = _termios.tcgetattr(fd)
            new_attrs = list(attrs)
            new_attrs[3] = new_attrs[3] & ~_termios.ECHO
            _termios.tcsetattr(fd, _termios.TCSADRAIN, new_attrs)
        except _termios_error_types():
            return
        self._echo_fd = fd
        self._echo_attrs = list(attrs)

    def _restore_input_echo(self) -> None:
        if _termios is None or self._echo_fd is None or self._echo_attrs is None:
            return
        fd = self._echo_fd
        attrs = self._echo_attrs
        self._echo_fd = None
        self._echo_attrs = None
        try:
            _termios.tcsetattr(fd, _termios.TCSADRAIN, attrs)
        except _termios_error_types():
            return

    def _format_line(
        self,
        label: str,
        percent: int,
        completed: int | None,
        total: int | None,
    ) -> str:
        display_label, curated = self._progress_label(label)
        short_label = (
            display_label
            if curated
            else compact_live_title(display_label, self._title_limit)
        )
        width = self._bar_width(short_label, completed, total)
        filled = min(width, max(0, round(width * percent / 100)))
        if filled >= width:
            bar = "━" * width
        else:
            bar = "━" * filled + "╺" + "─" * max(width - filled - 1, 0)
        count = (
            f" {completed}/{total}"
            if completed is not None and total is not None
            else ""
        )
        return f"\x1b[36m{short_label}\x1b[0m {bar} {percent:3d}%{count}"

    def _bar_width(self, label: str, completed: int | None, total: int | None) -> int:
        try:
            columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        except OSError:
            columns = 80
        count_width = (
            len(f" {completed}/{total}")
            if completed is not None and total is not None
            else 0
        )
        fixed_width = len(label) + len("  100%") + count_width + 1
        return max(10, min(30, columns - fixed_width))

    def _progress_label(self, text: str) -> tuple[str, bool]:
        compact = " ".join(text.split())
        label = self._labels.get(compact)
        if label is not None:
            return label, True
        return compact, False


class SingleLineStatusSpinner:
    """Render an honest single-line spinner for indeterminate status work."""

    _clear_line = "\r\x1b[2K"
    _frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(
        self,
        stream: Any,
        *,
        title: str,
        details: tuple[str, ...],
        clock: Clock = time.monotonic,
        render_interval: float = 0.25,
        autostart_thread: bool = True,
    ) -> None:
        self._stream = stream
        self._title = " ".join(title.split())
        self._details = tuple(" ".join(detail.split()) for detail in details if detail)
        self._clock = clock
        self._render_interval = render_interval
        self._autostart_thread = autostart_thread
        self._active = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_at: float | None = None
        self._frame_index = 0
        self._last_line_width = 0
        self._lock = threading.Lock()

    def __enter__(self) -> SingleLineStatusSpinner:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.finish()

    def start(self) -> None:
        """Start rendering the status line."""

        with self._lock:
            if self._active:
                return
            self._active = True
            self._stop_event.clear()
            self._start_at = self._clock()
            self._render_locked()
            if self._autostart_thread:
                self._thread = threading.Thread(
                    target=self._run,
                    name="recollectium-cli-status-spinner",
                    daemon=True,
                )
                self._thread.start()

    def finish(self) -> None:
        """Stop rendering and clear the dynamic line."""

        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(self._render_interval * 2, 0.1))
        with self._lock:
            self._thread = None
            if self._active and self._write(self._clear_line):
                self._last_line_width = 0
            self._active = False

    def tick(self) -> None:
        """Render one spinner frame, primarily for deterministic tests."""

        with self._lock:
            if not self._active:
                return
            self._render_locked()

    def _run(self) -> None:
        while not self._stop_event.wait(self._render_interval):
            self.tick()

    def _render_locked(self) -> None:
        line = self._format_line()
        padding = " " * max(self._last_line_width - len(line), 0)
        if self._write(f"\r{line}{padding}"):
            self._last_line_width = len(line)
            self._frame_index += 1

    def _format_line(self) -> str:
        frame = self._frames[self._frame_index % len(self._frames)]
        elapsed = self._elapsed_seconds()
        detail = self._current_detail(elapsed)
        return f"\x1b[36m{frame} {self._title}\x1b[0m — {elapsed}s — {detail}"

    def _elapsed_seconds(self) -> int:
        start_at = self._start_at
        if start_at is None:
            return 0
        return max(0, int(self._clock() - start_at))

    def _current_detail(self, elapsed: int) -> str:
        if not self._details:
            return "working"
        detail_index = max(self._frame_index, elapsed) % len(self._details)
        return self._details[detail_index]

    def _write(self, text: str) -> bool:
        try:
            self._stream.write(text)
            self._stream.flush()
        except (OSError, ValueError):
            self._active = False
            return False
        return True
