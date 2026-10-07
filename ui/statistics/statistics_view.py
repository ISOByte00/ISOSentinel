"""
Statistics and Batch Question Entry View for YKS Sentinel.
"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from config.settings import settings
from analytics.statistics import calculate_net_score, calculate_accuracy_rate


class StatisticsView(QWidget):
    question_batch_submitted = pyqtSignal(dict)  # batch dict

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

        # 1. Batch Question Entry Form
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-radius: 12px;
                padding: 16px;
                border: 1px solid #30363d;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)

        title = QLabel("Toplu Soru Girişi (Batch Entry)")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        form_layout.addWidget(title)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(10)

        # Exam
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

        # Total questions
        self.spin_total = QSpinBox()
        self.spin_total.setRange(1, 500)
        self.spin_total.setValue(40)
        self.spin_total.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")
        self.spin_total.valueChanged.connect(self._update_net_preview)

        # Correct
        self.spin_correct = QSpinBox()
        self.spin_correct.setRange(0, 500)
        self.spin_correct.setValue(32)
        self.spin_correct.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")
        self.spin_correct.valueChanged.connect(self._update_net_preview)

        # Wrong
        self.spin_wrong = QSpinBox()
        self.spin_wrong.setRange(0, 500)
        self.spin_wrong.setValue(6)
        self.spin_wrong.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")
        self.spin_wrong.valueChanged.connect(self._update_net_preview)

        # Empty
        self.spin_empty = QSpinBox()
        self.spin_empty.setRange(0, 500)
        self.spin_empty.setValue(2)
        self.spin_empty.setStyleSheet("padding: 8px; border-radius: 6px; background-color: #21262d; color: white;")

        inputs_layout.addWidget(QLabel("Sınav:"))
        inputs_layout.addWidget(self.combo_exam)
        inputs_layout.addWidget(QLabel("Ders:"))
        inputs_layout.addWidget(self.combo_subject)
        inputs_layout.addWidget(QLabel("Konu:"))
        inputs_layout.addWidget(self.combo_topic)
        inputs_layout.addWidget(QLabel("Toplam:"))
        inputs_layout.addWidget(self.spin_total)
        inputs_layout.addWidget(QLabel("D:"))
        inputs_layout.addWidget(self.spin_correct)
        inputs_layout.addWidget(QLabel("Y:"))
        inputs_layout.addWidget(self.spin_wrong)
        inputs_layout.addWidget(QLabel("B:"))
        inputs_layout.addWidget(self.spin_empty)

        form_layout.addLayout(inputs_layout)

        # Action and Live Net Display
        action_layout = QHBoxLayout()
        self.lbl_net_preview = QLabel("Hesaplanan Net: 30.50 | Doğruluk: %80.00")
        self.lbl_net_preview.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 14px;")

        self.btn_submit = QPushButton("Soru Girişini Kaydet")
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        self.btn_submit.clicked.connect(self._on_submit_clicked)

        action_layout.addWidget(self.lbl_net_preview)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_submit)

        form_layout.addLayout(action_layout)
        layout.addWidget(form_frame)

        self._on_exam_changed(self.combo_exam.currentText())
        self._update_net_preview()

        # 2. History Table
        hist_title = QLabel("Soru Kayıt Geçmişi")
        hist_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        layout.addWidget(hist_title)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(8)
        self.table_history.setHorizontalHeaderLabels([
            "ID", "Tarih", "Ders", "Konu", "Soru", "D / Y / B", "Net", "Başarı %"
        ])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.setStyleSheet("""
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
        layout.addWidget(self.table_history)

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

    def _update_net_preview(self):
        total = self.spin_total.value()
        correct = self.spin_correct.value()
        wrong = self.spin_wrong.value()
        empty = max(0, total - (correct + wrong))
        self.spin_empty.setValue(empty)

        net = calculate_net_score(correct, wrong)
        acc = calculate_accuracy_rate(correct, total)
        self.lbl_net_preview.setText(f"Hesaplanan Net: {net:.2f} | Başarı Oranı: %{acc:.1f}")

    def _on_submit_clicked(self):
        exam = self.combo_exam.currentText()
        subject = self.combo_subject.currentText()
        topic = self.combo_topic.currentText()
        total = self.spin_total.value()
        correct = self.spin_correct.value()
        wrong = self.spin_wrong.value()
        empty = self.spin_empty.value()

        if correct + wrong + empty != total:
            QMessageBox.warning(self, "Hata", "Doğru + Yanlış + Boş toplamı Toplam Soru sayısına eşit olmalıdır.")
            return

        batch_data = {
            "exam_type": exam,
            "subject": subject,
            "topic": topic,
            "total_questions": total,
            "correct_count": correct,
            "wrong_count": wrong,
            "empty_count": empty,
            "net_score": calculate_net_score(correct, wrong),
            "accuracy_rate": calculate_accuracy_rate(correct, total)
        }
        self.question_batch_submitted.emit(batch_data)
        QMessageBox.information(self, "Başarılı", f"{total} soru ({batch_data['net_score']:.2f} net) kaydedildi.")

    def update_history_table(self, batches: list):
        self.table_history.setRowCount(len(batches))
        for row, b in enumerate(batches):
            self.table_history.setItem(row, 0, QTableWidgetItem(str(b.id)))
            date_str = b.recorded_at.strftime("%d.%m %H:%M") if b.recorded_at else "-"
            self.table_history.setItem(row, 1, QTableWidgetItem(date_str))
            self.table_history.setItem(row, 2, QTableWidgetItem(f"{b.exam_type} - {b.subject}"))
            self.table_history.setItem(row, 3, QTableWidgetItem(b.topic))
            self.table_history.setItem(row, 4, QTableWidgetItem(str(b.total_questions)))
            self.table_history.setItem(row, 5, QTableWidgetItem(f"{b.correct_count} / {b.wrong_count} / {b.empty_count}"))
            self.table_history.setItem(row, 6, QTableWidgetItem(f"{b.net_score:.2f}"))
            self.table_history.setItem(row, 7, QTableWidgetItem(f"%{b.accuracy_rate:.1f}"))
