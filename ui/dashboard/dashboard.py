from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QDialog,
    QFormLayout,
    QSpinBox,
)
from PyQt6.QtCore import QTimer, Qt

from core.session_manager import SessionController
from core.recovery import RecoveryManager
from core.event_bus import bus
from config.settings import POMODORO_WORK_MIN


class PostSessionDialog(QDialog):
    def __init__(
        self,
        session_id,
        subject,
        topic,
        completed=True,
        parent=None,
    ):
        super().__init__(parent)

        self.session_id = session_id
        self.subject = subject
        self.topic = topic
        self.completed = completed

        self.setWindowTitle("Oturum Özeti")

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI';
            }

            QLabel {
                font-size: 14px;
            }

            QSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 5px;
            }

            QPushButton {
                background-color: #a6e3a1;
                color: #11111b;
                font-weight: bold;
                padding: 8px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        if self.completed:
            status_text = "oturumu tamamlandı."
        else:
            status_text = "oturumu yarıda kesildi."

        self.lbl_info = QLabel(
            f"{self.subject} - {self.topic} {status_text}\n"
            f"Lütfen soru istatistiklerini girin:"
        )

        layout.addWidget(self.lbl_info)

        self.spin_correct = QSpinBox()
        self.spin_correct.setRange(0, 500)
        form_layout.addRow(
            "Doğru Sayısı:",
            self.spin_correct,
        )

        self.spin_wrong = QSpinBox()
        self.spin_wrong.setRange(0, 500)
        form_layout.addRow(
            "Yanlış Sayısı:",
            self.spin_wrong,
        )

        self.spin_empty = QSpinBox()
        self.spin_empty.setRange(0, 500)
        form_layout.addRow(
            "Boş Sayısı:",
            self.spin_empty,
        )

        layout.addLayout(form_layout)

        self.btn_save = QPushButton(
            "Kaydet ve Bitir"
        )

        self.btn_save.clicked.connect(
            self.save_data
        )

        layout.addWidget(self.btn_save)

        self.setLayout(layout)

    def save_data(self):
        correct = self.spin_correct.value()
        wrong = self.spin_wrong.value()
        empty = self.spin_empty.value()

        # Hiç veri girilmediyse direkt kapat
        if (
            correct == 0
            and wrong == 0
            and empty == 0
        ):
            self.accept()
            return

        from database.repositories.analytics_repository import (
            AnalyticsRepository,
        )
        from database.models import QuestionBatch

        repo = AnalyticsRepository()

        batch = QuestionBatch(
            id=None,
            session_id=self.session_id,
            subject=self.subject,
            topic=self.topic,
            correct_count=correct,
            wrong_count=wrong,
            empty_count=empty,
        )

        repo.save_question_batch(batch)

        print(
            f"VERİ KAYDEDİLDİ: "
            f"{correct}D, {wrong}Y, {empty}B"
        )

        self.accept()


class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.session = SessionController()

        self.setWindowTitle(
            "YKS Sentinel - V0.1"
        )

        self.setFixedSize(350, 500)

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI';
            }

            QLabel {
                font-size: 14px;
            }

            QLineEdit,
            QComboBox {
                background-color: #313244;
                border: 1px solid #45475a;
                padding: 8px;
                border-radius: 4px;
                color: #cdd6f4;
            }

            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #74c7ec;
            }

            QPushButton#stopBtn {
                background-color: #f38ba8;
            }

            QPushButton#stopBtn:hover {
                background-color: #eba0ac;
            }
        """)

        self.time_left = (
            POMODORO_WORK_MIN * 60
        )

        self.init_ui()
        self.init_timers()

        QTimer.singleShot(
            100,
            self.check_recovery
        )

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        self.lbl_title = QLabel(
            "YKS SENTINEL"
        )

        self.lbl_title.setStyleSheet(
            "font-size: 20px; "
            "font-weight: bold; "
            "color: #a6e3a1;"
        )

        self.lbl_title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.lbl_status = QLabel(
            "Durum: BEKLEMEDE"
        )

        self.lbl_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.lbl_timer = QLabel(
            f"{POMODORO_WORK_MIN:02d}:00"
        )

        self.lbl_timer.setStyleSheet(
            "font-size: 60px; "
            "font-weight: bold; "
            "color: #f9e2af;"
        )

        self.lbl_timer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.input_subject = QComboBox()

        self.input_subject.addItems([
            "Matematik",
            "Türkçe",
            "Fizik",
            "Kimya",
            "Biyoloji",
            "Tarih",
            "Coğrafya",
        ])

        self.input_topic = QLineEdit()

        self.input_topic.setPlaceholderText(
            "Çalışılacak Konuyu Girin "
            "(Örn: Türev)"
        )

        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton(
            "OTURUMU BAŞLAT"
        )

        self.btn_start.clicked.connect(
            self.start_pomodoro
        )

        self.btn_stop = QPushButton(
            "DURDUR"
        )

        self.btn_stop.setObjectName(
            "stopBtn"
        )

        self.btn_stop.clicked.connect(
            self.stop_pomodoro
        )

        self.btn_stop.setEnabled(False)

        btn_layout.addWidget(
            self.btn_start
        )

        btn_layout.addWidget(
            self.btn_stop
        )

        layout.addWidget(
            self.lbl_title
        )

        layout.addWidget(
            self.lbl_status
        )

        layout.addWidget(
            self.lbl_timer
        )

        layout.addStretch()

        layout.addWidget(
            QLabel("Ders:")
        )

        layout.addWidget(
            self.input_subject
        )

        layout.addWidget(
            QLabel("Konu:")
        )

        layout.addWidget(
            self.input_topic
        )

        layout.addLayout(
            btn_layout
        )

        self.setLayout(layout)

    def init_timers(self):
        self.pomodoro_timer = QTimer()

        self.pomodoro_timer.timeout.connect(
            self.update_timer
        )

        self.guard_timer = QTimer()

        self.guard_timer.timeout.connect(
            lambda: bus.publish("GUARD_TICK")
        )

    def check_recovery(self):
        pending = (
            RecoveryManager.get_pending_recovery()
        )

        if not pending:
            return

        session_id = pending.get(
            "session_id"
        )

        subject = pending.get(
            "subject"
        )

        topic = pending.get(
            "topic"
        )

        remaining = pending.get(
            "remaining_seconds"
        )

        # Recovery verisinin temel doğrulaması
        if (
            not isinstance(session_id, int)
            or not isinstance(remaining, int)
            or remaining <= 0
        ):
            self.session.mark_as_interrupted(
                session_id
            )
            return

        mins, secs = divmod(
            remaining,
            60
        )

        reply = QMessageBox.question(
            self,
            "Oturum Kurtarma",
            f"Yarım kalan bir oturum bulundu!\n\n"
            f"Ders: {subject}\n"
            f"Konu: {topic}\n"
            f"Kalan Süre: {mins:02d}:{secs:02d}\n\n"
            f"Kaldığınız yerden devam etmek ister misiniz?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if (
            reply
            == QMessageBox.StandardButton.Yes
        ):
            try:
                self.input_subject.setCurrentText(
                    subject
                )

                self.input_topic.setText(
                    topic
                )

                self.time_left = remaining

                self.lbl_timer.setText(
                    f"{mins:02d}:{secs:02d}"
                )

                self.session.resume_session(
                    session_id,
                    remaining,
                )

                self.pomodoro_timer.start(
                    1000
                )

                self.guard_timer.start(
                    2000
                )

                self.lbl_status.setText(
                    "Durum: KURTARILDI "
                    "(Guard Aktif)"
                )

                self.lbl_status.setStyleSheet(
                    "color: #f38ba8;"
                )

                self.btn_start.setEnabled(
                    False
                )

                self.btn_stop.setEnabled(
                    True
                )

                self.input_topic.setEnabled(
                    False
                )

                self.input_subject.setEnabled(
                    False
                )

            except (
                ValueError,
                TypeError,
            ) as exc:
                print(
                    f"[Recovery Error] "
                    f"Oturum kurtarılamadı: {exc}"
                )

                self.session.mark_as_interrupted(
                    session_id
                )

        else:
            self.session.mark_as_interrupted(
                session_id
            )

    def start_pomodoro(self):
        topic = (
            self.input_topic
            .text()
            .strip()
        )

        if not topic:
            QMessageBox.warning(
                self,
                "Hata",
                "Lütfen bir konu girin!",
            )
            return

        subject = (
            self.input_subject.currentText()
        )

        self.session.start_session(
            subject,
            topic,
            POMODORO_WORK_MIN,
        )

        self.time_left = (
            POMODORO_WORK_MIN * 60
        )

        self.pomodoro_timer.start(
            1000
        )

        self.guard_timer.start(
            2000
        )

        self.lbl_status.setText(
            "Durum: ODAKLANILDI "
            "(Guard Aktif)"
        )

        self.lbl_status.setStyleSheet(
            "color: #f38ba8;"
        )

        self.btn_start.setEnabled(
            False
        )

        self.btn_stop.setEnabled(
            True
        )

        self.input_topic.setEnabled(
            False
        )

        self.input_subject.setEnabled(
            False
        )

    def stop_pomodoro(self):
        """
        Kullanıcı DURDUR'a basarsa:
        STUDYING -> INTERRUPTED
        """

        if self.session.active_session_id is None:
            return

        self.pomodoro_timer.stop()
        self.guard_timer.stop()

        active_id = (
            self.session.active_session_id
        )

        subject = (
            self.input_subject.currentText()
        )

        topic = (
            self.input_topic.text()
        )

        # Manuel durdurma = INTERRUPTED
        self.session.stop_session(
            interrupted=True
        )

        self.reset_ui()

        if active_id:
            dialog = PostSessionDialog(
                active_id,
                subject,
                topic,
                completed=False,
                parent=self,
            )

            dialog.exec()

    def complete_pomodoro(self):
        """
        Sayaç doğal olarak biterse:
        STUDYING -> COMPLETED
        """

        if self.session.active_session_id is None:
            return

        self.pomodoro_timer.stop()
        self.guard_timer.stop()

        active_id = (
            self.session.active_session_id
        )

        subject = (
            self.input_subject.currentText()
        )

        topic = (
            self.input_topic.text()
        )

        # Doğal bitiş = COMPLETED
        self.session.stop_session(
            interrupted=False
        )

        self.reset_ui()

        if active_id:
            dialog = PostSessionDialog(
                active_id,
                subject,
                topic,
                completed=True,
                parent=self,
            )

            dialog.exec()

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1

            mins, secs = divmod(
                self.time_left,
                60
            )

            self.lbl_timer.setText(
                f"{mins:02d}:{secs:02d}"
            )

            # Heartbeat
            if self.session.active_session_id:
                RecoveryManager.save_state(
                    self.session.active_session_id,
                    self.input_subject.currentText(),
                    self.input_topic.text(),
                    self.time_left,
                )

            # 00:00 olur olmaz tamamla
            if self.time_left == 0:
                self.complete_pomodoro()

        else:
            self.complete_pomodoro()

    def reset_ui(self):
        self.lbl_status.setText(
            "Durum: BEKLEMEDE"
        )

        self.lbl_status.setStyleSheet(
            "color: #cdd6f4;"
        )

        self.lbl_timer.setText(
            f"{POMODORO_WORK_MIN:02d}:00"
        )

        self.btn_start.setEnabled(
            True
        )

        self.btn_stop.setEnabled(
            False
        )

        self.input_topic.setEnabled(
            True
        )

        self.input_subject.setEnabled(
            True
        )

        self.input_topic.clear()