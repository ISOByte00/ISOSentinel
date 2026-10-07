"""
Dashboard View for YKS Sentinel.
Displays active timer, session state, control buttons, and daily summary statistics.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class StatCard(QFrame):
    def __init__(self, title: str, initial_value: str = "0", unit: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e222d;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #2d3342;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold;")

        self.val_lbl = QLabel(f"{initial_value} {unit}".strip())
        self.val_lbl.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)

    def set_value(self, value: str, unit: str = ""):
        self.val_lbl.setText(f"{value} {unit}".strip())


class DashboardView(QWidget):
    start_session_clicked = pyqtSignal()
    start_break_clicked = pyqtSignal()
    complete_session_clicked = pyqtSignal()
    interrupt_session_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # 1. Header & Active Session Info
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-radius: 12px;
                padding: 16px;
                border: 1px solid #30363d;
            }
        """)
        header_layout = QHBoxLayout(header_frame)

        info_layout = QVBoxLayout()
        self.session_title_lbl = QLabel("Aktif Çalışma Yok")
        self.session_title_lbl.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        
        self.session_subtitle_lbl = QLabel("Bir çalışma bloğu başlatmak için Ajanda'yı kullanın veya hızlı başlatın.")
        self.session_subtitle_lbl.setStyleSheet("color: #8b949e; font-size: 13px;")

        info_layout.addWidget(self.session_title_lbl)
        info_layout.addWidget(self.session_subtitle_lbl)

        self.state_badge = QLabel("IDLE")
        self.state_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_badge.setFixedSize(110, 34)
        self.update_state_badge("IDLE")

        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.state_badge)

        main_layout.addWidget(header_frame)

        # 2. Timer & Controls
        timer_frame = QFrame()
        timer_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-radius: 12px;
                padding: 24px;
                border: 1px solid #30363d;
            }
        """)
        timer_layout = QVBoxLayout(timer_frame)
        timer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.timer_display = QLabel("25:00")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Consolas", 64, QFont.Weight.Bold)
        self.timer_display.setFont(font)
        self.timer_display.setStyleSheet("color: #58a6ff;")
        timer_layout.addWidget(self.timer_display)

        self.pomodoro_counter_lbl = QLabel("Pomodoro Blok: -")
        self.pomodoro_counter_lbl.setStyleSheet("color: #8b949e; font-size: 14px;")
        self.pomodoro_counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_layout.addWidget(self.pomodoro_counter_lbl)

        timer_layout.addSpacing(15)

        # Button Controls
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_start = QPushButton("Çalışmayı Başlat")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_start.clicked.connect(self.start_session_clicked.emit)

        self.btn_break = QPushButton("Mola Ver")
        self.btn_break.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_break.setEnabled(False)
        self.btn_break.clicked.connect(self.start_break_clicked.emit)

        self.btn_complete = QPushButton("Tamamla & Soru Gir")
        self.btn_complete.setStyleSheet("""
            QPushButton {
                background-color: #8957e5;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #a371f7; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_complete.setEnabled(False)
        self.btn_complete.clicked.connect(self.complete_session_clicked.emit)

        self.btn_interrupt = QPushButton("İptal / Durdur")
        self.btn_interrupt.setStyleSheet("""
            QPushButton {
                background-color: #da3633;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #f85149; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_interrupt.setEnabled(False)
        self.btn_interrupt.clicked.connect(self.interrupt_session_clicked.emit)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_break)
        btn_layout.addWidget(self.btn_complete)
        btn_layout.addWidget(self.btn_interrupt)

        timer_layout.addLayout(btn_layout)
        main_layout.addWidget(timer_frame)

        # 3. Daily Summary Cards Grid
        summary_grid = QGridLayout()
        summary_grid.setSpacing(12)

        self.card_study = StatCard("GÜNLÜK ÇALIŞMA", "0", "dk")
        self.card_questions = StatCard("ÇÖZÜLEN SORU", "0", "adet")
        self.card_net = StatCard("TOPLAM NET", "0.0", "net")
        self.card_focus = StatCard("FOCUS SCORE", "100", "/ 100")
        self.card_violations = StatCard("İHLALLER", "0", "olay")

        summary_grid.addWidget(self.card_study, 0, 0)
        summary_grid.addWidget(self.card_questions, 0, 1)
        summary_grid.addWidget(self.card_net, 0, 2)
        summary_grid.addWidget(self.card_focus, 0, 3)
        summary_grid.addWidget(self.card_violations, 0, 4)

        main_layout.addLayout(summary_grid)
        main_layout.addStretch()

    def update_timer(self, seconds_left: int):
        mins = seconds_left // 60
        secs = seconds_left % 60
        self.timer_display.setText(f"{mins:02d}:{secs:02d}")

    def update_session_info(self, subject: str, topic: str, pomodoro_num: int = 0):
        if subject:
            self.session_title_lbl.setText(f"{subject} — {topic}")
            self.session_subtitle_lbl.setText("Odak koruma devrede. Yasaklı uygulamalar otomatik engellenmektedir.")
            self.pomodoro_counter_lbl.setText(f"Pomodoro Blok #{pomodoro_num}")
        else:
            self.session_title_lbl.setText("Aktif Çalışma Yok")
            self.session_subtitle_lbl.setText("Yeni oturum başlatmak için bekliyor.")
            self.pomodoro_counter_lbl.setText("Pomodoro Blok: -")

    def update_state_badge(self, state: str):
        self.state_badge.setText(state)
        colors = {
            "IDLE": ("#21262d", "#8b949e"),
            "PREPARING": ("#388bfd33", "#58a6ff"),
            "STUDY": ("#23863633", "#3fb950"),
            "BREAK": ("#d2992233", "#e3b341"),
            "COMPLETED": ("#8957e533", "#bc8cff"),
            "INTERRUPTED": ("#da363333", "#f85149"),
            "RECOVERY": ("#db6d2833", "#f0883e"),
            "ERROR": ("#b6232433", "#ff7b72")
        }
        bg, fg = colors.get(state, ("#21262d", "#8b949e"))
        self.state_badge.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {fg};
            border-radius: 6px;
            font-weight: bold;
            font-size: 13px;
        """)

    def update_stats(self, summary: dict):
        self.card_study.set_value(str(summary.get("study_minutes", 0)), "dk")
        self.card_questions.set_value(str(summary.get("total_questions", 0)), "adet")
        self.card_net.set_value(str(summary.get("total_net", 0.0)), "net")
        self.card_focus.set_value(str(summary.get("focus_score", 100)), "/ 100")
        self.card_violations.set_value(str(summary.get("violations_count", 0)), "olay")
