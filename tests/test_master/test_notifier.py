"""Tests for master.notifier — macOS notifications."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from control_room.master.notifier import (
    _escape,
    notify,
    notify_blocker,
    notify_completion,
    notify_failure,
    notify_review_complete,
)


class TestEscape:
    """Tests for AppleScript string escaping."""

    def test_escapes_quotes(self) -> None:
        assert _escape('say "hello"') == 'say \\"hello\\"'

    def test_escapes_backslashes(self) -> None:
        assert _escape("path\\to\\file") == "path\\\\to\\\\file"

    def test_no_escaping_needed(self) -> None:
        assert _escape("simple text") == "simple text"


class TestNotify:
    """Tests for the notify function."""

    @patch("control_room.master.notifier.subprocess.run")
    def test_successful_notification(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert notify("Title", "Message") is True
        mock_run.assert_called_once()

    @patch("control_room.master.notifier.subprocess.run")
    def test_failed_notification(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        assert notify("Title", "Message") is False

    @patch("control_room.master.notifier.subprocess.run")
    def test_osascript_called(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        notify("Test", "Body", sound="Ping")
        args = mock_run.call_args[0][0]
        assert args[0] == "osascript"

    @patch("control_room.master.notifier.subprocess.run")
    def test_timeout_handled(self, mock_run: MagicMock) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="osascript", timeout=5)
        assert notify("Title", "Message") is False


class TestNotificationTypes:
    """Tests for typed notification functions."""

    @patch("control_room.master.notifier.notify")
    def test_notify_completion(self, mock_notify: MagicMock) -> None:
        mock_notify.return_value = True
        assert notify_completion("s1", "My task", "my-repo") is True
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "my-repo" in call_args[1].get("title", "") or "my-repo" in str(call_args)

    @patch("control_room.master.notifier.notify")
    def test_notify_blocker(self, mock_notify: MagicMock) -> None:
        mock_notify.return_value = True
        assert notify_blocker("s1", "My task", "API timeout") is True

    @patch("control_room.master.notifier.notify")
    def test_notify_failure(self, mock_notify: MagicMock) -> None:
        mock_notify.return_value = True
        assert notify_failure("s1", "My task", "crashed") is True

    @patch("control_room.master.notifier.notify")
    def test_notify_review_passed(self, mock_notify: MagicMock) -> None:
        mock_notify.return_value = True
        assert notify_review_complete("my-repo", passed=True) is True
        call_args = str(mock_notify.call_args)
        assert "PASSED" in call_args

    @patch("control_room.master.notifier.notify")
    def test_notify_review_failed(self, mock_notify: MagicMock) -> None:
        mock_notify.return_value = True
        assert notify_review_complete("my-repo", passed=False) is True
        call_args = str(mock_notify.call_args)
        assert "ATTENTION" in call_args
