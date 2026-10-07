"""
Agenda View for YKS Sentinel.
Manual session planning and topic-based study block launcher.
"""
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from config.settings import settings


class AgendaView(QWidget):
    start_planned_session = pyqtSignal(str, str, int)  # subject, topic, duration_minutes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.subjects_data = self._load_subjects()
        self._init_ui()

    def _load_subjects(self) -> dict:
        try:
            if settings.subjects_path.exists():
                with open(settings.subjects_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"TYT": [], "AYT": []}

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 1. Quick Launcher Card
        plan_frame = QFrame()
        plan_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-radius: 12px;
                padding: 16px;
                border: 1px solid #30363d;
            }
        """)
        plan_layout = QVBoxLayout(plan_frame)
        plan_layout.setSpacing(12)

        title = QLabel("Yeni Çalışma Oturumu Başlat")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        plan_layout.addWidget(title)

        form_layout = QHBoxLayout()
        form_layout.setSpacing(12)

        # Exam Type
        self.combo_exam = QComboBox()
        self.combo_exam.addItems(["TYT", "AYT"])
        self.combo_exam.currentTextChanged.connect(self._on_exam_changed)
        self.combo_exam.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")

        # Subject
        self.combo_subject = QComboBox()
        self.combo_subject.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")
        self.combo_subject.currentTextChanged.connect(self._on_subject_changed)

        # Topic
        self.combo_topic = QComboBox()
        self.combo_topic.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")

        # Duration
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(5, 180)
        self.spin_duration.setValue(settings.pomodoro.study_duration_minutes)
        self.spin_duration.setSuffix(" dakika")
        self.spin_duration.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")

        # Launch Button
        self.btn_launch = QPushButton("Oturumu Başlat")
        self.btn_launch.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                padding: 10px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.btn_launch.clicked.connect(self._on_launch_clicked)

        form_layout.addWidget(QLabel("Sınav:"))
        form_layout.addWidget(self.combo_exam)
        form_layout.addWidget(QLabel("Ders:"))
        form_layout.addWidget(self.combo_subject)
        form_layout.addWidget(QLabel("Konu:"))
        form_layout.addWidget(self.combo_topic)
        form_layout.addWidget(QLabel("Süre:"))
        form_layout.addWidget(self.spin_duration)
        form_layout.addWidget(self.btn_launch)

        plan_layout.addLayout(form_layout)
        layout.addWidget(plan_frame)

        # Initial populate
        self._on_exam_changed(self.combo_exam.currentText())

        # 2. Today's Sessions Table
        table_title = QLabel("Bugünkü Çalışma Oturumları")
        table_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        layout.addWidget(table_title)

        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(6)
        self.table_sessions.setHorizontalHeaderLabels([
            "ID", "Ders", "Konu", "Süre (dk)", "Durum", "Başlangıç"
        ])
        self.table_sessions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_sessions.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                color: #ffffff;
                border: 1px solid #30363d;
                border-radius: 8px;
                gridline-color: #30363d;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
        """)
        layout.addWidget(self.table_sessions)

    def _on_exam_changed(self, exam_type: str):
        self.combo_subject.clear()
        subjects = self.subjects_data.get(exam_type, [])
        for item in subjects:
            self.combo_subject.addItem(item["subject"])

    def _on_subject_changed(self, subject_name: str):
        self.combo_topic.clear()
        exam_type = self.combo_exam.currentText()
        subjects = self.subjects_data.get(exam_type, [])
        for item in subjects:
            if item["subject"] == subject_name:
                self.combo_topic.addItems(item.get("topics", []))
                break

    def _on_launch_clicked(self):
        subject = self.combo_subject.currentText()
        topic = self.combo_topic.currentText()
        duration = self.spin_duration.value()

        if not subject or not topic:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen ders ve konu seçin.")
            return

        self.start_planned_session.emit(subject, topic, duration)

    def update_sessions_table(self, sessions: list):
        self.table_sessions.setRowCount(len(sessions))
        for row, s in enumerate(sessions):
            self.table_sessions.setItem(row, 0, QTableWidgetItem(str(s.id)))
            self.table_sessions.setItem(row, 1, QTableWidgetItem(s.subject))
            self.table_sessions.setItem(row, 2, QTableWidgetItem(s.topic))
            self.table_sessions.setItem(row, 3, QTableWidgetItem(f"{s.actual_duration_minutes} / {s.planned_duration_minutes}"))
            self.table_sessions.setItem(row, 4, QTableWidgetItem(s.status))
            time_str = s.started_at.strftime("%H:%M") if s.started_at else "-"
            self.table_sessions.setItem(row, 5, QTableWidgetItem(time_str))
