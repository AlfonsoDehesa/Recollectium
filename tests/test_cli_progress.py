from __future__ import annotations

import io
import os
import re
from collections.abc import Callable

import pytest

from recollectium import cli_progress
from recollectium.cli_progress import (
    SingleLineProgressReporter,
    SingleLineStatusSpinner,
)


LABELS = {
    "Very long curated label that should stay whole": "Curated long label",
}

ANSI_SEQUENCE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def visible_text(text: str) -> str:
    return ANSI_SEQUENCE.sub("", text)


class OSErrorStream(io.StringIO):
    def __init__(self, *, fail_on_flush: bool = False) -> None:
        super().__init__()
        self.fail_on_flush = fail_on_flush
        self.write_calls = 0
        self.flush_calls = 0

    def write(self, text: str) -> int:
        self.write_calls += 1
        raise OSError("stream write failed")

    def flush(self) -> None:
        self.flush_calls += 1
        if self.fail_on_flush:
            raise OSError("stream flush failed")


class FlushErrorStream(io.StringIO):
    def flush(self) -> None:
        raise OSError("stream flush failed")


class RecordingStream(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.writes: list[str] = []

    def write(self, text: str) -> int:
        self.writes.append(text)
        return super().write(text)


class TTYStringIO(io.StringIO):
    def __init__(
        self,
        *,
        fd: int = 10,
        is_tty: bool = True,
        fail_fileno: bool = False,
    ) -> None:
        super().__init__()
        self._fd = fd
        self._is_tty = is_tty
        self._fail_fileno = fail_fileno

    def isatty(self) -> bool:
        return self._is_tty

    def fileno(self) -> int:
        if self._fail_fileno:
            raise OSError("fileno failed")
        return self._fd


class FakeTermios:
    class error(Exception):
        pass

    ECHO = 0b1000
    TCSADRAIN = 2

    def __init__(
        self,
        *,
        fail_getattr: bool = False,
        fail_setattr_calls: set[int] | None = None,
        exception_type: type[Exception] = OSError,
    ) -> None:
        self.fail_getattr = fail_getattr
        self.fail_setattr_calls = fail_setattr_calls or set()
        self.exception_type = exception_type
        self.attrs = [1, 2, 3, self.ECHO | 0b0010]
        self.getattr_calls: list[int] = []
        self.setattr_calls: list[tuple[int, int, list[int]]] = []

    def tcgetattr(self, fd: int) -> list[int]:
        self.getattr_calls.append(fd)
        if self.fail_getattr:
            raise self.exception_type("tcgetattr failed")
        return list(self.attrs)

    def tcsetattr(self, fd: int, when: int, attrs: list[int]) -> None:
        self.setattr_calls.append((fd, when, list(attrs)))
        if len(self.setattr_calls) in self.fail_setattr_calls:
            raise self.exception_type("tcsetattr failed")
        self.attrs = list(attrs)


def test_single_line_progress_normal_frame_uses_cr_padding_not_clear_line() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(stream, min_render_interval=0, title_limit=40)

    with progress:
        progress.phase("A much longer label")
        progress.phase("Short")

    output = stream.getvalue()
    frames = output.split("\r")
    assert "\n" not in output
    assert "Status:" not in output
    assert output.count("\r") == 3
    assert output.count("\x1b[2K") == 1
    assert output.endswith("\r\x1b[2K")
    assert "A much longer label" in output
    assert "Short" in output
    assert "working" in output
    assert "╺" not in output
    assert "━" not in output
    assert "%" not in output
    assert any(frame in output for frame in ("⠋", "⠙", "⠹", "⠸", "⠼"))
    assert len(frames) == 4


def test_single_line_progress_status_shorter_render_pads_previous_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_progress, "_STATUS_SPINNER_FRAMES", ("⠋",))
    current_time = 100.0

    def clock() -> float:
        return current_time

    stream = RecordingStream()
    progress = SingleLineProgressReporter(
        stream,
        clock=clock,
        min_render_interval=0,
        title_limit=40,
    )

    with progress:
        progress.phase("A much longer label")
        current_time = 101.0
        progress.phase("Short")

    first_line = cli_progress._format_status_line(
        "⠋", "A much longer label", 0, "working"
    )
    second_line = cli_progress._format_status_line("⠋", "Short", 1, "working")
    padding = len(visible_text(first_line)) - len(visible_text(second_line))

    assert stream.writes[0] == f"\r{first_line}"
    assert stream.writes[1] == f"\r{second_line}{' ' * padding}"
    assert stream.writes[2] == "\r\x1b[2K"


def test_single_line_progress_update_with_unknown_total_uses_spinner() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    with progress:
        progress.update("Unknown total", completed=0, total=0)

    output = stream.getvalue()
    assert "\n" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Unknown total" in output
    assert "working" in output
    assert "%" not in output
    assert "╺" not in output
    assert "━" not in output


def test_single_line_progress_update_with_known_total_keeps_determinate_bar() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    with progress:
        progress.update("Counted work", completed=0, total=5)

    output = stream.getvalue()
    assert "\n" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Counted work" in output
    assert "0/5" in output
    assert "%" in output
    assert "╺" in output or "━" in output
    assert "working" not in output


def test_single_line_progress_does_not_suppress_echo_for_non_tty_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios()
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = io.StringIO()
    input_stream = TTYStringIO()

    with SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    ) as progress:
        progress.phase("Starting")

    assert fake_termios.getattr_calls == []
    assert fake_termios.setattr_calls == []
    assert "Starting" in stream.getvalue()


def test_single_line_progress_suppresses_and_restores_echo_for_ttys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios()
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = TTYStringIO(fd=20)
    input_stream = TTYStringIO(fd=30)

    with SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    ) as progress:
        progress.phase("Starting")

    assert fake_termios.getattr_calls == [30]
    assert fake_termios.setattr_calls == [
        (30, fake_termios.TCSADRAIN, [1, 2, 3, 0b0010]),
        (30, fake_termios.TCSADRAIN, [1, 2, 3, fake_termios.ECHO | 0b0010]),
    ]
    assert "Starting" in stream.getvalue()


def test_single_line_progress_restores_echo_on_context_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios()
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = TTYStringIO(fd=20)
    input_stream = TTYStringIO(fd=30)

    with pytest.raises(RuntimeError, match="boom"):
        with SingleLineProgressReporter(
            stream,
            min_render_interval=0,
            input_stream=input_stream,
        ) as progress:
            progress.phase("Starting")
            raise RuntimeError("boom")

    assert len(fake_termios.setattr_calls) == 2
    assert fake_termios.setattr_calls[-1] == (
        30,
        fake_termios.TCSADRAIN,
        [1, 2, 3, fake_termios.ECHO | 0b0010],
    )


@pytest.mark.parametrize(
    ("input_stream", "termios_module"),
    [
        (TTYStringIO(fail_fileno=True), FakeTermios()),
        (TTYStringIO(), FakeTermios(fail_getattr=True)),
        (TTYStringIO(), FakeTermios(fail_setattr_calls={1})),
        (
            TTYStringIO(),
            FakeTermios(
                fail_getattr=True,
                exception_type=FakeTermios.error,
            ),
        ),
        (
            TTYStringIO(),
            FakeTermios(
                fail_setattr_calls={1},
                exception_type=FakeTermios.error,
            ),
        ),
        (TTYStringIO(), None),
    ],
)
def test_single_line_progress_echo_suppression_failures_are_swallowed(
    monkeypatch: pytest.MonkeyPatch,
    input_stream: TTYStringIO,
    termios_module: FakeTermios | None,
) -> None:
    monkeypatch.setattr(cli_progress, "_termios", termios_module)
    stream = TTYStringIO()

    with SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    ) as progress:
        progress.phase("Still works")

    assert "Still works" in stream.getvalue()


def test_single_line_progress_finish_restores_echo_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios()
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = TTYStringIO(fd=20)
    input_stream = TTYStringIO(fd=30)
    progress = SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    )

    with progress:
        progress.phase("Starting")
        progress.finish()
        progress.finish()

    assert fake_termios.setattr_calls == [
        (30, fake_termios.TCSADRAIN, [1, 2, 3, 0b0010]),
        (30, fake_termios.TCSADRAIN, [1, 2, 3, fake_termios.ECHO | 0b0010]),
    ]


def test_single_line_progress_reenter_does_not_overwrite_saved_echo_attrs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios()
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = TTYStringIO(fd=20)
    input_stream = TTYStringIO(fd=30)
    progress = SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    )

    progress.__enter__()
    progress.__enter__()
    progress.finish()

    assert fake_termios.getattr_calls == [30]
    assert fake_termios.setattr_calls == [
        (30, fake_termios.TCSADRAIN, [1, 2, 3, 0b0010]),
        (30, fake_termios.TCSADRAIN, [1, 2, 3, fake_termios.ECHO | 0b0010]),
    ]
    assert fake_termios.attrs == [1, 2, 3, fake_termios.ECHO | 0b0010]


def test_single_line_progress_restores_echo_after_rendering_write_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios()
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = OSErrorStream()
    stream.isatty = lambda: True  # type: ignore[method-assign]
    input_stream = TTYStringIO(fd=30)

    with SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    ) as progress:
        progress.phase("Will fail")

    assert fake_termios.setattr_calls == [
        (30, fake_termios.TCSADRAIN, [1, 2, 3, 0b0010]),
        (30, fake_termios.TCSADRAIN, [1, 2, 3, fake_termios.ECHO | 0b0010]),
    ]


def test_single_line_progress_restore_echo_failure_is_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios(fail_setattr_calls={2})
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = TTYStringIO(fd=20)
    input_stream = TTYStringIO(fd=30)

    with SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    ) as progress:
        progress.phase("Starting")

    assert len(fake_termios.setattr_calls) == 2
    assert "Starting" in stream.getvalue()


def test_single_line_progress_restore_termios_error_failure_is_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_termios = FakeTermios(
        fail_setattr_calls={2},
        exception_type=FakeTermios.error,
    )
    monkeypatch.setattr(cli_progress, "_termios", fake_termios)
    stream = TTYStringIO(fd=20)
    input_stream = TTYStringIO(fd=30)

    with SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        input_stream=input_stream,
    ) as progress:
        progress.phase("Starting")

    assert len(fake_termios.setattr_calls) == 2
    assert "Starting" in stream.getvalue()


def test_single_line_progress_finish_uses_clear_line() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    with progress:
        progress.phase("Starting")

    assert stream.getvalue().endswith("\r\x1b[2K")


def test_single_line_progress_context_manager_finishes_line() -> None:
    stream = io.StringIO()

    with SingleLineProgressReporter(stream, min_render_interval=0) as progress:
        progress.phase("Starting")

    assert stream.getvalue().endswith("\r\x1b[2K")


def test_single_line_progress_update_ignores_inactive_reporter() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    progress.update("Inactive", completed=1, total=1)

    assert stream.getvalue() == ""


def test_single_line_progress_curated_labels_are_not_ellipsized() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(
        stream,
        labels=LABELS,
        min_render_interval=0,
        title_limit=5,
    )

    with progress:
        progress.phase("Very long curated label that should stay whole")

    output = stream.getvalue()
    assert "Curated long label" in output
    assert "…" not in output


def test_single_line_progress_unknown_labels_compact_to_title_limit() -> None:
    stream = io.StringIO()
    progress = SingleLineProgressReporter(
        stream,
        min_render_interval=0,
        title_limit=8,
    )

    with progress:
        progress.phase("Unknown     label with extra whitespace")

    output = stream.getvalue()
    assert "Unknown…" in output
    assert "Unknown     label" not in output


def test_single_line_progress_throttles_dedupes_but_forces_first_count_and_completion() -> (
    None
):
    now = [0.0]

    def clock() -> float:
        return now[0]

    stream = io.StringIO()
    progress = SingleLineProgressReporter(
        stream,
        clock=clock,
        min_render_interval=0.25,
        title_limit=40,
    )

    with progress:
        progress.update("Counting", completed=1, total=10)
        now[0] = 0.3
        progress.update("Counting", completed=1, total=10)
        for completed in range(2, 10):
            progress.update("Counting", completed=completed, total=10)
        progress.update("Counting", completed=10, total=10)

    output = stream.getvalue()
    assert "\n" not in output
    assert output.count("\r") == 4
    assert output.count("\x1b[2K") == 1
    assert output.count("1/10") == 1
    assert "2/10" in output
    assert "3/10" not in output
    assert "10/10" in output
    assert "100% 10/10" in output


def test_single_line_progress_forces_first_count_after_phase() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    stream = io.StringIO()
    progress = SingleLineProgressReporter(
        stream,
        clock=clock,
        min_render_interval=0.25,
        title_limit=40,
    )

    with progress:
        progress.phase("Phase")
        progress.update("Counting", completed=1, total=100)
        progress.update("Counting", completed=2, total=100)
        progress.update("Counting", completed=100, total=100)

    output = stream.getvalue()
    assert output.count("\r") == 4
    assert "Phase" in output
    assert "1/100" in output
    assert "2/100" not in output
    assert "100% 100/100" in output


def test_single_line_progress_write_oserror_disables_safely() -> None:
    stream = OSErrorStream()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    with progress:
        progress.phase("Will fail")
        progress.phase("Already disabled")

    assert stream.write_calls == 1


def test_single_line_progress_flush_oserror_disables_safely() -> None:
    stream = FlushErrorStream()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    with progress:
        progress.phase("Will fail")
        progress.phase("Already disabled")

    assert stream.getvalue().count("Will fail") == 1
    assert "Already disabled" not in stream.getvalue()


def test_live_progress_title_limit_handles_terminal_size_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_terminal_size_error(fallback: tuple[int, int]) -> os.terminal_size:
        raise OSError("terminal size unavailable")

    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        raise_terminal_size_error,
    )

    assert cli_progress.live_progress_title_limit() is None


def test_live_progress_title_limit_returns_none_for_narrow_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((59, 24)),
    )

    assert cli_progress.live_progress_title_limit() is None


def test_single_line_progress_uses_fallback_limit_when_terminal_size_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_terminal_size_error(fallback: tuple[int, int]) -> os.terminal_size:
        raise OSError("terminal size unavailable")

    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        raise_terminal_size_error,
    )
    stream = io.StringIO()
    progress = SingleLineProgressReporter(stream, min_render_interval=0)

    with progress:
        progress.phase("Unknown label that should compact")

    assert "Unknown lab…" in stream.getvalue()


def test_single_line_status_spinner_is_indeterminate_alive_and_clears() -> None:
    current_time = 100.0

    def clock() -> float:
        return current_time

    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title="Preparing model demo — verifying cached model",
        details=("checking local cache", "using model cache"),
        clock=clock,
        autostart_thread=False,
    )

    with spinner:
        current_time = 101.2
        spinner.tick()

    output = stream.getvalue()
    assert "demo" in output
    assert "verifying cached model" in output
    assert "checking local cache" in output
    assert "using model cache" in output
    assert "1s" in output
    assert "%" not in output
    assert "━" not in output
    assert output.endswith("\r\x1b[2K")


def test_single_line_status_spinner_narrow_terminal_truncates_to_one_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((30, 24)),
    )
    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title=(
            "Preparing embedding model sentence-transformers/"
            "all-MiniLM-L6-v2 — downloading model files if needed"
        ),
        details=("this can take a minute the first time from a slow network",),
        autostart_thread=False,
    )

    with spinner:
        spinner.tick()

    output = stream.getvalue()
    rendered_frames = [
        frame for frame in output.split("\r") if frame and frame != "\x1b[2K"
    ]

    assert rendered_frames
    assert "\n" not in output
    assert output.endswith("\r\x1b[2K")
    assert all(len(visible_text(frame).rstrip()) <= 30 for frame in rendered_frames)
    assert any("…" in frame for frame in rendered_frames)


def test_single_line_status_spinner_preserves_title_then_truncates_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((28, 24)),
    )
    spinner = SingleLineStatusSpinner(
        io.StringIO(),
        title="Short title",
        details=("long detail text",),
        autostart_thread=False,
    )

    line = visible_text(spinner._format_line())

    assert len(line) == 28
    assert "Short title" in line
    assert line.endswith("long d…")


def test_single_line_status_spinner_tiny_terminal_omits_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((8, 24)),
    )
    spinner = SingleLineStatusSpinner(
        io.StringIO(),
        title="Title",
        details=("detail",),
        autostart_thread=False,
    )

    line = visible_text(spinner._format_line())

    assert line == "⠋ … — 0s"


def test_single_line_status_spinner_too_narrow_for_elapsed_truncates_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_progress.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((1, 24)),
    )
    spinner = SingleLineStatusSpinner(
        io.StringIO(),
        title="Title",
        details=("detail",),
        autostart_thread=False,
    )

    line = visible_text(spinner._format_line())

    assert line == "…"


def test_status_spinner_truncation_helpers_handle_edge_widths() -> None:
    assert cli_progress._truncate_visible("already compact", 20) == "already compact"
    assert cli_progress._truncate_visible("too long", 1) == "…"
    assert cli_progress._truncate_visible("too long", 0) == ""


def test_single_line_status_spinner_uses_working_detail_when_empty() -> None:
    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title="  Preparing   model  ",
        details=(),
        autostart_thread=False,
    )

    with spinner:
        pass

    assert "Preparing model" in stream.getvalue()
    assert "working" in stream.getvalue()


def test_single_line_status_spinner_ignores_ticks_after_finish() -> None:
    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title="Preparing model",
        details=("checking local cache",),
        autostart_thread=False,
    )

    with spinner:
        pass
    output = stream.getvalue()
    spinner.tick()

    assert stream.getvalue() == output


def test_progress_reporter_initializes_phase_clock_when_missing() -> None:
    times = iter((10.0, 12.5, 12.5))
    stream = io.StringIO()
    reporter = cli_progress.SingleLineProgressReporter(
        stream, clock=lambda: next(times)
    )
    reporter._active = True
    reporter._phase_started_at = None

    reporter.phase("Downloading model cache")

    assert "2s" in stream.getvalue()
    assert reporter._phase_started_at == 10.0


def test_progress_reporter_skips_duplicate_status_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_progress, "_STATUS_SPINNER_FRAMES", ("⠋",))
    stream = io.StringIO()
    reporter = cli_progress.SingleLineProgressReporter(
        stream,
        clock=lambda: 1.0,
        min_render_interval=0,
    )
    reporter._active = True

    reporter.phase("Downloading model cache")
    output = stream.getvalue()
    reporter.phase("Downloading model cache")

    assert stream.getvalue() == output


def test_progress_reporter_returns_false_when_write_fails() -> None:
    stream = io.StringIO()
    reporter = cli_progress.SingleLineProgressReporter(stream)
    reporter._write = lambda _text: False  # type: ignore[method-assign]

    assert reporter._render("Downloading model cache", 10, 1, 10, force=True) is False


def test_single_line_status_spinner_disables_on_stream_error() -> None:
    stream = OSErrorStream()
    spinner = SingleLineStatusSpinner(
        stream,
        title="Preparing model",
        details=("checking local cache",),
        autostart_thread=False,
    )

    spinner.start()
    spinner.tick()
    spinner.finish()

    assert stream.write_calls == 1


def test_single_line_status_spinner_start_is_idempotent() -> None:
    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title="Preparing model",
        details=("checking local cache",),
        autostart_thread=False,
    )

    spinner.start()
    spinner.start()
    spinner.finish()

    assert stream.getvalue().count("Preparing model") == 1


def test_single_line_status_spinner_elapsed_is_zero_before_start() -> None:
    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title="Preparing model",
        details=("checking local cache",),
        autostart_thread=False,
    )

    assert "0s" in spinner._format_line()


def test_single_line_status_spinner_background_thread_ticks_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeEvent:
        def __init__(self) -> None:
            self.wait_calls: list[float] = []
            self.set_calls = 0

        def clear(self) -> None:
            self.wait_calls.clear()

        def set(self) -> None:
            self.set_calls += 1

        def wait(self, timeout: float) -> bool:
            self.wait_calls.append(timeout)
            return len(self.wait_calls) >= 3

    class FakeThread:
        def __init__(
            self,
            *,
            target: Callable[[], None],
            name: str,
            daemon: bool,
        ) -> None:
            self._target = target
            self.name = name
            self.daemon = daemon
            self.join_timeout: float | None = None

        def start(self) -> None:
            pass

        def run(self) -> None:
            self._target()

        def join(self, timeout: float | None = None) -> None:
            self.join_timeout = timeout

    fake_event = FakeEvent()
    thread_holder: dict[str, FakeThread] = {}

    def build_thread(
        *,
        target: Callable[[], None],
        name: str,
        daemon: bool,
    ) -> FakeThread:
        thread = FakeThread(target=target, name=name, daemon=daemon)
        thread_holder["thread"] = thread
        return thread

    monkeypatch.setattr(cli_progress.threading, "Event", lambda: fake_event)
    monkeypatch.setattr(cli_progress.threading, "Thread", build_thread)
    stream = io.StringIO()
    spinner = SingleLineStatusSpinner(
        stream,
        title="Preparing model",
        details=("checking local cache",),
        render_interval=0.01,
    )

    with spinner:
        thread_holder["thread"].run()

    assert stream.getvalue().count("Preparing model") == 3
    assert fake_event.wait_calls == [0.01, 0.01, 0.01]
    assert fake_event.set_calls == 1
    assert thread_holder["thread"].join_timeout == 0.1
