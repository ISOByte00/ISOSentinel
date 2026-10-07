"""
Violations and Anti-Bypass Audit View for YKS Sentinel.
Displays blocked applications, reasons, and system audit logs.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QPushButton, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt


class ViolationsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("İhlaller & Güvenlik Denetim Günlüğü")
        header.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. Process Violations Section
        v_widget = QWidget()
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(8)

        v_title_layout = QHBoxLayout()
        v_title = QLabel("Engellenen Uygulamalar (Process Violations)")
        v_title.setStyleSheet("color: #ff7b72; font-size: 14px; font-weight: bold;")
        
        btn_why = QPushButton("Seçili İhlalin Nedenini Göster")
        btn_why.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #58a6ff;
                border: 1px solid #30363d;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        btn_why.clicked.connect(self._show_selected_violation_reason)

        v_title_layout.addWidget(v_title)
        v_title_layout.addStretch()
        v_title_layout.addWidget(btn_why)
        v_layout.addLayout(v_title_layout)

        self.table_violations = QTableWidget()
        self.table_violations.setColumnCount(6)
        self.table_violations.setHorizontalHeaderLabels([
            "ID", "Tarih", "Uygulama (Exe)", "İşlem", "Neden / Açıklama", "Kural"
        ])
        self.table_violations.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_violations.setStyleSheet("""
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
        v_layout.addWidget(self.table_violations)
        splitter.addWidget(v_widget)

        # 2. System Events Section
        s_widget = QWidget()
        s_layout = QVBoxLayout(s_widget)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(8)

        s_title = QLabel("Sistem Güvenlik & Anti-Bypass Olayları")
        s_title.setStyleSheet("color: #e3b341; font-size: 14px; font-weight: bold;")
        s_layout.addWidget(s_title)

        self.table_events = QTableWidget()
        self.table_events.setColumnCount(4)
        self.table_events.setHorizontalHeaderLabels([
            "ID", "Tarih", "Olay Türü", "Detaylar"
        ])
        self.table_events.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_events.setStyleSheet("""
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
        s_layout.addWidget(self.table_events)
        splitter.addWidget(s_widget)

        layout.addWidget(splitter)

    def _show_selected_violation_reason(self):
        row = self.table_violations.currentRow()
        if row < 0:
            QMessageBox.information(self, "Bilgi", "Lütfen incelemek istediğiniz ihlali seçin.")
            return

        exe = self.table_violations.item(row, 2).text()
        reason = self.table_violations.item(row, 4).text()
        date_str = self.table_violations.item(row, 1).text()

        QMessageBox.information(
            self,
            f"Neden? — {exe}",
            f"Uygulama: {exe}\nZaman: {date_str}\n\nEngelleme Gerekçesi:\n{reason}"
        )

    def update_violations_table(self, violations: list):
        self.table_violations.setRowCount(len(violations))
        for row, v in enumerate(violations):
            self.table_violations.setItem(row, 0, QTableWidgetItem(str(v.id)))
            date_str = v.detected_at.strftime("%d.%m %H:%M:%S") if v.detected_at else "-"
            self.table_violations.setItem(row, 1, QTableWidgetItem(date_str))
            self.table_violations.setItem(row, 2, QTableWidgetItem(v.process_name))
            self.table_violations.setItem(row, 3, QTableWidgetItem(v.action_taken.upper()))
            self.table_violations.setItem(row, 4, QTableWidgetItem(v.reason))
            self.table_violations.setItem(row, 5, QTableWidgetItem(v.rule_name))

    def update_events_table(self, events: list):
        self.table_events.setRowCount(len(events))
        for row, e in enumerate(events):
            self.table_events.setItem(row, 0, QTableWidgetItem(str(e.id)))
            date_str = e.recorded_at.strftime("%d.%m %H:%M:%S") if e.recorded_at else "-"
            self.table_events.setItem(row, 1, QTableWidgetItem(date_str))
            self.table_events.setItem(row, 2, QTableWidgetItem(e.event_type))
            self.table_events.setItem(row, 3, QTableWidgetItem(e.details))
