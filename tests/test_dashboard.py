from types import SimpleNamespace
from unittest.mock import Mock

from ui.dashboard.dashboard import DashboardWindow


def test_start_pomodoro_connects_ui_to_session_controller():
    session = SimpleNamespace(
        active_session_id=None,
        start_session=Mock(),
    )
    window = SimpleNamespace(
        input_topic=Mock(),
        input_subject=Mock(),
        session=session,
        time_left=None,
        pomodoro_timer=Mock(),
        guard_timer=Mock(),
        lbl_status=Mock(),
        btn_start=Mock(),
        btn_stop=Mock(),
    )
    window.input_topic.text.return_value = "  Türev  "
    window.input_subject.currentText.return_value = "Matematik"

    DashboardWindow.start_pomodoro(window)

    session.start_session.assert_called_once_with("Matematik", "Türev", 25)
    assert window.time_left == 25 * 60
    window.pomodoro_timer.start.assert_called_once_with(1000)
    window.guard_timer.start.assert_called_once_with(2000)
    window.btn_start.setEnabled.assert_called_once_with(False)
    window.btn_stop.setEnabled.assert_called_once_with(True)
    window.input_topic.setEnabled.assert_called_once_with(False)
    window.input_subject.setEnabled.assert_called_once_with(False)


def test_close_event_interrupts_active_session_and_stops_timers():
    session = SimpleNamespace(
        active_session_id=7,
        stop_session=Mock(),
    )
    event = Mock()
    window = SimpleNamespace(
        session=session,
        pomodoro_timer=Mock(),
        guard_timer=Mock(),
    )

    DashboardWindow.closeEvent(window, event)

    window.pomodoro_timer.stop.assert_called_once_with()
    window.guard_timer.stop.assert_called_once_with()
    session.stop_session.assert_called_once_with(interrupted=True)
    event.accept.assert_called_once_with()
