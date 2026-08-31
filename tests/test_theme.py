from pathlib import Path

from whence.models import FileRecord, Origin
from whence.report import render_text
from whence.theme import Theme, detect


class _Stream:
    """The two attributes theme detection actually looks at."""

    def __init__(self, tty: bool, encoding: str = "utf-8") -> None:
        self._tty = tty
        self.encoding = encoding

    def isatty(self) -> bool:
        return self._tty


def _record() -> FileRecord:
    record = FileRecord(path="/case/a.txt", size=1, mtime="2026-08-24T19:00:00Z")
    record.origins.append(
        Origin(
            source="browser-download", url="https://example.org/a.txt", at="2026-08-24T19:00:00Z"
        )
    )
    return record


def test_a_pipe_gets_no_colour(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    assert detect(_Stream(tty=False)).colour is False


def test_a_terminal_gets_colour(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    assert detect(_Stream(tty=True)).colour is True


def test_no_color_is_honoured(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "xterm-256color")

    assert detect(_Stream(tty=True)).colour is False


def test_dumb_terminal_gets_no_colour(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")

    assert detect(_Stream(tty=True)).colour is False


def test_explicit_choice_beats_detection(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")

    assert detect(_Stream(tty=False), colour=True).colour is True


def test_plain_output_contains_no_escape_sequences():
    theme = Theme(colour=False, unicode=True, width=88)

    output = render_text([_record()], Path("/case"), theme=theme)

    assert "\x1b" not in output
    assert "example.org" in output


def test_styled_output_contains_escape_sequences():
    theme = Theme(colour=True, unicode=True, width=88)

    output = render_text([_record()], Path("/case"), theme=theme)

    assert "\x1b[" in output


def test_ascii_fallback_avoids_box_drawing():
    theme = Theme(colour=False, unicode=False, width=88)

    output = render_text([_record()], Path("/case"), theme=theme)

    assert output.isascii()


def test_confidence_meter_scales_with_the_score():
    theme = Theme(colour=False, unicode=False, width=88)

    assert theme.bar(90).count("#") > theme.bar(40).count("#")
    assert len(theme.bar(90)) == len(theme.bar(10)) == 5


def test_width_is_clamped_to_a_readable_range(monkeypatch):
    monkeypatch.setenv("COLUMNS", "400")
    assert detect(_Stream(tty=True)).width <= 110

    monkeypatch.setenv("COLUMNS", "20")
    assert detect(_Stream(tty=True)).width >= 48
