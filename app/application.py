"""
Main Application Window and Wiring for YKS Sentinel.
Integrates GUI views, background guards, event bus, and database repositories.
"""
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

from database.database import DatabaseManager
from database.repositories import (
    SessionRepository, QuestionRepository, ViolationRepository, SystemEventRepository
)
from database.models import QuestionBatch
from core.session_manager import (
    SessionController, STATE_IDLE, STATE_PREPARING, STATE_STUDY, STATE_BREAK,
    STATE_COMPLETED, STATE_INTERRUPTED, STATE_RECOVERY, STATE_ERROR
)
from core.recovery import RecoveryManager
from core.event_bus import event_bus
from restrictions.process_guard import ProcessGuard
from restrictions.audit_logger import AuditMonitor
from analytics.statistics import calculate_daily_summary

from ui.dashboard.dashboard_view import DashboardView
from ui.agenda.agenda_view import AgendaView
from ui.statistics.statistics_view import StatisticsView
from ui.violations.violations_view import ViolationsView
from ui.settings.settings_view import SettingsView

logger = logging.getLogger(__name__)


class EventBridge(QObject):
    """Bridges background thread event_bus events safely to Qt main thread signals."""
    violation_signal = pyqtSignal(object)
    clock_changed_signal = pyqtSignal(object)


class SentinelMainWindow(QMainWindow):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.setWindowTitle("YKS Sentinel — Autonomous Study Guardian (v0.1 MVP)")
        self.resize(1150, 750)
        self.setMinimumSize(950, 600)

        # 1. Repositories
        self.db = db_manager
        self.session_repo = SessionRepository(self.db)
        self.question_repo = QuestionRepository(self.db)
        self.violation_repo = ViolationRepository(self.db)
        self.event_repo = SystemEventRepository(self.db)

        # 2. Core Controllers & Managers
        self.session_ctrl = SessionController(self.session_repo)
        self.recovery_mgr = RecoveryManager(self.session_repo, self.event_repo)
        self.process_guard = ProcessGuard(self.violation_repo)
        self.audit_monitor = AuditMonitor(self.event_repo)

        # 3. Qt-safe Event Bridge
        self.event_bridge = EventBridge()
        self.event_bridge.violation_signal.connect(self._on_violation_received)
        self.event_bridge.clock_changed_signal.connect(self._on_clock_changed_received)

        event_bus.subscribe("VIOLATION_DETECTED", lambda d: self.event_bridge.violation_signal.emit(d))
        event_bus.subscribe("CLOCK_CHANGED", lambda d: self.event_bridge.clock_changed_signal.emit(d))

        # 4. Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)

        # 5. Build UI & Wiring
        self._init_layout()
        self._connect_signals()

        # 6. Startup Recovery Check & Service Start
        self._run_startup_audit()
        self.audit_monitor.start()

        # Refresh all views
        self._refresh_all_data()

    def _init_layout(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d1117;
            }
            QLabel {
                color: #c9d1d9;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-right: 1px solid #30363d;
            }
        """)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(12, 24, 12, 24)
        s_layout.setSpacing(8)

        # Brand / Logo
        brand_lbl = QLabel("🛡️ YKS SENTINEL")
        brand_lbl.setStyleSheet("color: #58a6ff; font-size: 18px; font-weight: bold; padding: 8px;")
        s_layout.addWidget(brand_lbl)

        version_lbl = QLabel("Study Guardian v0.1")
        version_lbl.setStyleSheet("color: #8b949e; font-size: 11px; padding-left: 8px; margin-bottom: 16px;")
        s_layout.addWidget(version_lbl)

        # Nav Buttons
        self.nav_buttons = []
        self.btn_nav_dash = self._create_nav_btn("📌 Dashboard", 0)
        self.btn_nav_agenda = self._create_nav_btn("📅 Ajanda", 1)
        self.btn_nav_stats = self._create_nav_btn("📊 Soru & İstatistik", 2)
        self.btn_nav_violations = self._create_nav_btn("🛡️ İhlaller & Güvenlik", 3)
        self.btn_nav_settings = self._create_nav_btn("⚙️ Ayarlar", 4)

        for btn in [self.btn_nav_dash, self.btn_nav_agenda, self.btn_nav_stats, self.btn_nav_violations, self.btn_nav_settings]:
            s_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        s_layout.addStretch()

        # Guard Status Indicator
        self.guard_indicator = QLabel("● Guard Pasif")
        self.guard_indicator.setStyleSheet("color: #8b949e; font-size: 12px; padding: 8px;")
        s_layout.addWidget(self.guard_indicator)

        root_layout.addWidget(sidebar)

        # Main Stacked Pages
        self.stacked = QStackedWidget()
        self.view_dashboard = DashboardView()
        self.view_agenda = AgendaView()
        self.view_stats = StatisticsView()
        self.view_violations = ViolationsView()
        self.view_settings = SettingsView()

        self.stacked.addWidget(self.view_dashboard)
        self.stacked.addWidget(self.view_agenda)
        self.stacked.addWidget(self.view_stats)
        self.stacked.addWidget(self.view_violations)
        self.stacked.addWidget(self.view_settings)

        root_layout.addWidget(self.stacked)
        self._set_nav_page(0)

    def _create_nav_btn(self, text: str, page_index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
                color: #c9d1d9;
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #21262d;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        btn.clicked.connect(lambda: self._set_nav_page(page_index))
        return btn

    def _set_nav_page(self, index: int):
        self.stacked.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)

    def _connect_signals(self):
        # Dashboard actions
        self.view_dashboard.start_session_clicked.connect(self._on_start_quick_session)
        self.view_dashboard.start_break_clicked.connect(self._on_start_break)
        self.view_dashboard.complete_session_clicked.connect(self._on_complete_session)
        self.view_dashboard.interrupt_session_clicked.connect(self._on_interrupt_session)

        # Agenda actions
        self.view_agenda.start_planned_session.connect(self._on_start_planned_session)

        # Stats actions
        self.view_stats.question_batch_submitted.connect(self._on_question_batch_submitted)

        # Settings actions
        self.view_settings.policies_updated.connect(self.process_guard.reload_policies)

    def _run_startup_audit(self):
        result = self.recovery_mgr.perform_startup_check()
        if result["unexpected_shutdown"]:
            QMessageBox.warning(
                self,
                "Sistem Uyarısı",
                "Uygulama son çalışmasında düzgün kapatılmamış (UNEXPECTED_SHUTDOWN).\n"
                "Sistem durumu denetlendi ve güvenlik kaydı oluşturuldu."
            )
        if result["recovered_session"]:
            s = result["recovered_session"]
            QMessageBox.information(
                self,
                "Oturum Kurtarıldı",
                f"Yarım kalmış '{s.subject} - {s.topic}' oturumu kurtarılarak 'RECOVERY' olarak arşivlendi."
            )

    def _on_start_quick_session(self):
        """Switches to agenda to select subject or launches default session."""
        self._set_nav_page(1)  # Jump to Agenda

    def _on_start_planned_session(self, subject: str, topic: str, duration: int):
        if self.session_ctrl.get_state() != STATE_IDLE:
            QMessageBox.warning(self, "Uyarı", "Zaten aktif bir oturum devam ediyor.")
            return

        self.session_ctrl.prepare_session(subject, topic, duration)
        self.session_ctrl.start_study_block(duration)

        # Activate Process Guard
        if self.session_ctrl.current_session:
            self.process_guard.set_active_session(self.session_ctrl.current_session.id)
            self.process_guard.start()
            self.guard_indicator.setText("● Guard AKTİF")
            self.guard_indicator.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: bold; padding: 8px;")

        self.timer.start()
        self._set_nav_page(0)  # Jump back to Dashboard
        self._update_dashboard_state()

    def _on_start_break(self):
        self.session_ctrl.start_break_block()
        # During break, process guard remains active or can be paused depending on policy
        self._update_dashboard_state()

    def _on_complete_session(self):
        session_obj = self.session_ctrl.current_session
        self.session_ctrl.complete_session()
        self._stop_session_guard()
        self._update_dashboard_state()
        self._refresh_all_data()

        # Prompt user to enter questions for this completed session
        self._set_nav_page(2)

    def _on_interrupt_session(self):
        reply = QMessageBox.question(
            self,
            "Oturumu Durdur",
            "Mevcut çalışma oturumunu sonlandırmak istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.session_ctrl.interrupt_session("User stopped session")
            self._stop_session_guard()
            self._update_dashboard_state()
            self._refresh_all_data()

    def _stop_session_guard(self):
        self.timer.stop()
        self.process_guard.stop()
        self.process_guard.set_active_session(None)
        self.guard_indicator.setText("● Guard Pasif")
        self.guard_indicator.setStyleSheet("color: #8b949e; font-size: 12px; padding: 8px;")

    def _on_timer_tick(self):
        seconds_left = self.session_ctrl.tick_second()
        self.view_dashboard.update_timer(seconds_left)

        if seconds_left <= 0:
            current_state = self.session_ctrl.get_state()
            if current_state == STATE_STUDY:
                self.session_ctrl.start_break_block()
                self._update_dashboard_state()
                QMessageBox.information(self, "Mola Zamanı", "Çalışma bloğu tamamlandı! Mola zamanı başladı.")
            elif current_state == STATE_BREAK:
                QMessageBox.information(self, "Mola Bitti", "Mola süresi tamamlandı. Yeni bir çalışma bloğu başlatabilirsiniz.")
                self.session_ctrl.complete_session()
                self._stop_session_guard()
                self._update_dashboard_state()
                self._refresh_all_data()

    def _update_dashboard_state(self):
        state = self.session_ctrl.get_state()
        self.view_dashboard.update_state_badge(state)

        sess = self.session_ctrl.current_session
        if sess and state in [STATE_PREPARING, STATE_STUDY, STATE_BREAK]:
            self.view_dashboard.update_session_info(sess.subject, sess.topic, self.session_ctrl.pomodoro_count)
            self.view_dashboard.btn_start.setEnabled(False)
            self.view_dashboard.btn_break.setEnabled(state == STATE_STUDY)
            self.view_dashboard.btn_complete.setEnabled(True)
            self.view_dashboard.btn_interrupt.setEnabled(True)
        else:
            self.view_dashboard.update_session_info("", "")
            self.view_dashboard.btn_start.setEnabled(True)
            self.view_dashboard.btn_break.setEnabled(False)
            self.view_dashboard.btn_complete.setEnabled(False)
            self.view_dashboard.btn_interrupt.setEnabled(False)
            self.view_dashboard.update_timer(25 * 60)

    def _on_question_batch_submitted(self, batch_dict: dict):
        batch = QuestionBatch(
            study_session_id=self.session_ctrl.current_session.id if self.session_ctrl.current_session else None,
            exam_type=batch_dict["exam_type"],
            subject=batch_dict["subject"],
            topic=batch_dict["topic"],
            total_questions=batch_dict["total_questions"],
            correct_count=batch_dict["correct_count"],
            wrong_count=batch_dict["wrong_count"],
            empty_count=batch_dict["empty_count"],
            net_score=batch_dict["net_score"],
            accuracy_rate=batch_dict["accuracy_rate"]
        )
        self.question_repo.record_batch(batch)
        self._refresh_all_data()

    def _on_violation_received(self, violation):
        self.session_ctrl.register_interruption(f"Violation: {violation.process_name}")
        self._refresh_all_data()

    def _on_clock_changed_received(self, data):
        self.view_violations.update_events_table(self.event_repo.get_recent_events())

    def _refresh_all_data(self):
        # 1. Sessions
        today_sessions = self.session_repo.get_today_sessions()
        self.view_agenda.update_sessions_table(today_sessions)

        # 2. Question Batches
        all_batches = self.question_repo.get_all_batches()
        self.view_stats.update_history_table(all_batches)

        # 3. Violations & Events
        all_violations = self.violation_repo.get_all_violations()
        self.view_violations.update_violations_table(all_violations)

        recent_events = self.event_repo.get_recent_events()
        self.view_violations.update_events_table(recent_events)

        # 4. Summary & Focus Score
        summary = calculate_daily_summary(
            sessions=today_sessions,
            question_batches=self.question_repo.get_today_batches(),
            violations=self.violation_repo.get_today_violations()
        )
        self.view_dashboard.update_stats(summary)

    def closeEvent(self, event):
        """Graceful shutdown hook."""
        logger.info("Closing YKS Sentinel...")
        self._stop_session_guard()
        if self.session_ctrl.get_state() in [STATE_STUDY, STATE_BREAK]:
            self.session_ctrl.interrupt_session("Application exited during active session")
        self.audit_monitor.stop(is_clean=True)
        event.accept()
