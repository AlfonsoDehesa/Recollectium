from __future__ import annotations

import io
import os

import pytest

from recollectium import cli_progress
from recollectium.cli_progress import SingleLineProgressReporter


LABELS = {
    "Very long curated label that should stay whole": "Curated long label",
}


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
    ECHO = 0b1000
    TCSADRAIN = 2

    def __init__(
        self,
        *,
        fail_getattr: bool = False,
        fail_setattr_calls: set[int] | None = None,
    ) -> None:
        self.fail_getattr = fail_getattr
        self.fail_setattr_calls = fail_setattr_calls or set()
        self.attrs = [1, 2, 3, self.ECHO | 0b0010]
        self.getattr_calls: list[int] = []
        self.setattr_calls: list[tuple[int, int, list[int]]] = []

    def tcgetattr(self, fd: int) -> list[int]:
        self.getattr_calls.append(fd)
        if self.fail_getattr:
            raise OSError("tcgetattr failed")
        return list(self.attrs)

    def tcsetattr(self, fd: int, when: int, attrs: list[int]) -> None:
        self.setattr_calls.append((fd, when, list(attrs)))
        if len(self.setattr_calls) in self.fail_setattr_calls:
            raise OSError("tcsetattr failed")


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
    assert "A much longer label" in frames[1]
    assert frames[2].endswith(" ")


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
